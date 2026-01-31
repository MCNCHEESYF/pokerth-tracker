"""Calculateur de statistiques de poker."""

from collections import defaultdict
from pathlib import Path

from ..database.log_parser import LogParser
from ..database.models import PlayerStats, HandAction


class StatsCalculator:
    """Calcule les statistiques VPIP, PFR, AF, 3-Bet, C-Bet, etc. pour chaque joueur."""

    # Actions qui comptent comme VPIP (mise volontaire preflop, hors blindes)
    VPIP_ACTIONS = {"calls", "bets", "is all in with"}

    # Actions qui comptent comme PFR (raise preflop)
    # Note: Dans PokerTH, "bets" preflop = raise (car la BB est la mise initiale)
    PFR_ACTIONS = {"bets", "is all in with"}

    # Actions agressives (pour AF - tous les rounds)
    AGGRESSIVE_ACTIONS = {"bets", "is all in with"}

    # Actions passives (pour AF - tous les rounds)
    PASSIVE_ACTIONS = {"calls"}

    # Actions de raise/bet (pour détecter les 3-bets)
    RAISE_ACTIONS = {"bets", "is all in with"}

    # Actions de fold
    FOLD_ACTIONS = {"folds"}

    def __init__(self, parser: LogParser):
        """Initialise le calculateur avec un parser."""
        self.parser = parser

    def calculate_player_stats(self, player_name: str) -> PlayerStats:
        """Calcule les statistiques complètes d'un joueur.

        VPIP: % de mains où le joueur a volontairement mis de l'argent preflop
              (call, bet/raise), hors posts de blindes
        PFR:  % de mains où le joueur a raise preflop
        AF:   (bets + raises) / calls sur tous les rounds
        3-Bet: % de fois où le joueur re-raise après un raise preflop
        C-Bet: % de fois où le joueur bet au flop après avoir raise preflop
        """
        stats = PlayerStats(player_name=player_name)

        # Récupère les mains jouées et le siège du joueur par partie
        hands_played = self.parser.get_hands_played_by_player(player_name)
        stats.total_hands = len(hands_played)

        if stats.total_hands == 0:
            return stats

        # Récupère le siège du joueur pour chaque partie
        player_seats = self.parser.get_player_seats(player_name)

        # Analyse des actions preflop pour VPIP, PFR et 3-Bet
        preflop_by_hand: dict[tuple[int, int], list[HandAction]] = defaultdict(list)
        for action in self.parser.get_preflop_actions_by_player(player_name):
            key = (action.game_id, action.hand_id)
            preflop_by_hand[key].append(action)

        # On a aussi besoin de toutes les actions preflop (pas seulement du joueur)
        # pour détecter les opportunités de 3-bet
        all_preflop_by_hand = self._get_all_preflop_actions_by_hand(hands_played)

        # Mains où le joueur a raise preflop (pour c-bet)
        pfr_hands: set[tuple[int, int]] = set()

        for hand_key, actions in preflop_by_hand.items():
            has_vpip = False
            has_pfr = False

            for action in actions:
                action_type = action.action.lower()

                # Ignore les posts de blindes (ne compte pas comme VPIP)
                if "blind" in action_type:
                    continue

                # Vérifie VPIP
                if any(vpip_action in action_type for vpip_action in self.VPIP_ACTIONS):
                    has_vpip = True

                # Vérifie PFR
                if any(pfr_action in action_type for pfr_action in self.PFR_ACTIONS):
                    has_pfr = True

            if has_vpip:
                stats.vpip_hands += 1
            if has_pfr:
                stats.pfr_hands += 1
                pfr_hands.add(hand_key)

            # Analyse 3-bet: y avait-il un raise avant que le joueur agisse?
            game_id, hand_id = hand_key
            player_seat = player_seats.get(game_id)
            if player_seat is not None and hand_key in all_preflop_by_hand:
                all_actions = all_preflop_by_hand[hand_key]
                three_bet_result = self._analyze_three_bet(
                    all_actions, player_seat, actions
                )
                if three_bet_result["opportunity"]:
                    stats.three_bet_opportunities += 1
                    if three_bet_result["made"]:
                        stats.three_bet_made += 1

        # Analyse C-Bet et Fold to 3-Bet: pour les mains où le joueur a raise preflop
        for hand_key in pfr_hands:
            game_id, hand_id = hand_key
            player_seat = player_seats.get(game_id)
            if player_seat is not None:
                cbet_result = self._analyze_cbet(game_id, hand_id, player_seat)
                if cbet_result["opportunity"]:
                    stats.cbet_opportunities += 1
                    if cbet_result["made"]:
                        stats.cbet_made += 1

                # Analyse Fold to 3-Bet: le joueur a raise et quelqu'un l'a 3-bet
                fold_to_3bet_result = self._analyze_fold_to_3bet(
                    all_preflop_by_hand.get(hand_key, []), player_seat
                )
                if fold_to_3bet_result["opportunity"]:
                    stats.fold_to_3bet_opportunities += 1
                    if fold_to_3bet_result["folded"]:
                        stats.fold_to_3bet_made += 1

        # Analyse par main pour Fold to C-Bet, WTSD, W$SD
        for hand_key in hands_played:
            game_id, hand_id = hand_key
            player_seat = player_seats.get(game_id)
            if player_seat is None:
                continue

            # Vérifie si le joueur a vu le flop
            flop_actions = list(self.parser.get_actions(
                game_id=game_id, hand_id=hand_id, betting_round=1
            ))

            player_saw_flop = any(
                a.player_seat == player_seat for a in flop_actions
            )

            if player_saw_flop:
                stats.hands_saw_flop += 1

                # Fold to C-Bet: le joueur fait face à un c-bet et fold
                fold_to_cbet_result = self._analyze_fold_to_cbet(
                    game_id, hand_id, player_seat, all_preflop_by_hand.get(hand_key, [])
                )
                if fold_to_cbet_result["opportunity"]:
                    stats.fold_to_cbet_opportunities += 1
                    if fold_to_cbet_result["folded"]:
                        stats.fold_to_cbet_made += 1

                # WTSD: vérifie si la main est allée au showdown
                if self.parser.hand_has_showdown(game_id, hand_id):
                    # Vérifie si le joueur était encore dans la main au showdown
                    showdown_actions = list(self.parser.get_actions(
                        game_id=game_id, hand_id=hand_id, betting_round=4
                    ))
                    player_at_showdown = any(
                        a.player_seat == player_seat for a in showdown_actions
                    )

                    if player_at_showdown:
                        stats.hands_went_to_showdown += 1

                        # W$SD: vérifie si le joueur a gagné
                        winner_seat = self.parser.get_showdown_winner(game_id, hand_id)
                        if winner_seat == player_seat:
                            stats.showdowns_won += 1

        # Analyse de toutes les actions pour AF (tous les rounds, sauf showdown)
        for action in self.parser.get_all_actions_by_player(player_name):
            # Ignore le showdown (round 4)
            if action.betting_round == 4:
                continue

            action_type = action.action.lower()

            # Compte les actions agressives
            if any(agg in action_type for agg in self.AGGRESSIVE_ACTIONS):
                stats.total_bets += 1

            # Compte les calls
            if any(passive in action_type for passive in self.PASSIVE_ACTIONS):
                stats.total_calls += 1

        return stats

    def _get_all_preflop_actions_by_hand(
        self, hands: set[tuple[int, int]]
    ) -> dict[tuple[int, int], list[HandAction]]:
        """Récupère toutes les actions preflop pour un ensemble de mains."""
        result: dict[tuple[int, int], list[HandAction]] = defaultdict(list)
        for action in self.parser.get_actions(betting_round=0):
            key = (action.game_id, action.hand_id)
            if key in hands:
                result[key].append(action)
        return result

    def _analyze_three_bet(
        self,
        all_preflop_actions: list[HandAction],
        player_seat: int,
        player_actions: list[HandAction]
    ) -> dict[str, bool]:
        """Analyse si le joueur avait une opportunité de 3-bet et s'il l'a fait.

        3-Bet = re-raise après qu'un autre joueur ait raise.
        """
        result = {"opportunity": False, "made": False}

        # Cherche s'il y a eu un raise avant la première action du joueur
        raise_before_player = False
        player_first_action_index = None

        for i, action in enumerate(all_preflop_actions):
            if action.player_seat == player_seat:
                # Ignore les blindes
                if "blind" not in action.action.lower():
                    player_first_action_index = i
                    break

            # Un autre joueur a raise
            action_type = action.action.lower()
            if any(r in action_type for r in self.RAISE_ACTIONS):
                raise_before_player = True

        # Si quelqu'un a raise avant le joueur, c'est une opportunité de 3-bet
        if raise_before_player and player_first_action_index is not None:
            result["opportunity"] = True

            # Vérifie si le joueur a re-raise
            for action in player_actions:
                action_type = action.action.lower()
                if "blind" in action_type:
                    continue
                if any(r in action_type for r in self.RAISE_ACTIONS):
                    result["made"] = True
                    break

        return result

    def _analyze_cbet(
        self, game_id: int, hand_id: int, player_seat: int
    ) -> dict[str, bool]:
        """Analyse si le joueur avait une opportunité de c-bet et s'il l'a fait.

        C-Bet = bet au flop après avoir raise preflop.
        Opportunité = le joueur a raise preflop ET il y a des actions au flop.
        """
        result = {"opportunity": False, "made": False}

        # Récupère les actions du flop pour cette main
        flop_actions = list(self.parser.get_actions(
            game_id=game_id, hand_id=hand_id, betting_round=1
        ))

        if not flop_actions:
            # Pas d'actions au flop = pas d'opportunité de c-bet
            return result

        # Il y a des actions au flop, donc opportunité de c-bet
        result["opportunity"] = True

        # Vérifie si le joueur a bet au flop
        for action in flop_actions:
            if action.player_seat == player_seat:
                action_type = action.action.lower()
                if any(r in action_type for r in self.RAISE_ACTIONS):
                    result["made"] = True
                    break

        return result

    def _analyze_fold_to_3bet(
        self, all_preflop_actions: list[HandAction], player_seat: int
    ) -> dict[str, bool]:
        """Analyse si le joueur a fold face à une 3-bet.

        Opportunité = le joueur a raise et quelqu'un l'a re-raise après.
        """
        result = {"opportunity": False, "folded": False}

        player_raised = False
        three_bet_happened = False

        for action in all_preflop_actions:
            action_type = action.action.lower()

            if action.player_seat == player_seat:
                # Le joueur a raise
                if any(r in action_type for r in self.RAISE_ACTIONS):
                    player_raised = True
                # Le joueur fold après avoir raise et être 3-bet
                elif player_raised and three_bet_happened:
                    if any(f in action_type for f in self.FOLD_ACTIONS):
                        result["folded"] = True
                        break
            else:
                # Un autre joueur raise après le raise du joueur = 3-bet
                if player_raised and any(r in action_type for r in self.RAISE_ACTIONS):
                    three_bet_happened = True
                    result["opportunity"] = True

        return result

    def _analyze_fold_to_cbet(
        self, game_id: int, hand_id: int, player_seat: int,
        all_preflop_actions: list[HandAction]
    ) -> dict[str, bool]:
        """Analyse si le joueur a fold face à un c-bet.

        Opportunité = un autre joueur a raise preflop et bet au flop (c-bet).
        """
        result = {"opportunity": False, "folded": False}

        # Trouve qui a raise preflop (potentiel c-better)
        preflop_raiser_seat = None
        for action in all_preflop_actions:
            if action.player_seat != player_seat:
                action_type = action.action.lower()
                if any(r in action_type for r in self.RAISE_ACTIONS):
                    preflop_raiser_seat = action.player_seat
                    # On garde le dernier raiser (celui qui a l'initiative)

        if preflop_raiser_seat is None:
            return result

        # Récupère les actions du flop
        flop_actions = list(self.parser.get_actions(
            game_id=game_id, hand_id=hand_id, betting_round=1
        ))

        # Vérifie si le raiser preflop a bet au flop (c-bet)
        cbet_happened = False

        for action in flop_actions:
            action_type = action.action.lower()

            if action.player_seat == preflop_raiser_seat:
                if any(r in action_type for r in self.RAISE_ACTIONS):
                    cbet_happened = True
            elif action.player_seat == player_seat and cbet_happened:
                # Le joueur agit après le c-bet
                result["opportunity"] = True
                if any(f in action_type for f in self.FOLD_ACTIONS):
                    result["folded"] = True
                break

        return result

    def calculate_all_players_stats(self) -> dict[str, PlayerStats]:
        """Calcule les stats de tous les joueurs."""
        players = self.parser.get_players()
        return {
            player_name: self.calculate_player_stats(player_name)
            for player_name in players
        }

    def calculate_table_players_stats(self) -> dict[str, PlayerStats]:
        """Calcule les stats des joueurs de la table actuelle."""
        current_players = self.parser.get_current_table_players()
        return {
            player_name: self.calculate_player_stats(player_name)
            for player_name in current_players
        }


def calculate_stats_from_file(db_path: Path | str) -> dict[str, PlayerStats]:
    """Fonction utilitaire pour calculer les stats depuis un fichier."""
    parser = LogParser(db_path)
    calculator = StatsCalculator(parser)
    return calculator.calculate_all_players_stats()
