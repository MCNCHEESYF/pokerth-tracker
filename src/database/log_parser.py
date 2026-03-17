"""Parser des fichiers de log PokerTH (.pdb)."""

import sqlite3
from pathlib import Path
from typing import Generator

from .models import HandAction, GameSession

# Noms des rangs dans l'ordre PokerTH (card % 13 → index)
_CARD_RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']


def _cards_to_combo(card1: int, card2: int) -> str:
    """Convertit deux entiers de carte en nom de combinaison (ex: 'AKs', 'TT', '76o').

    Encodage PokerTH : value = card % 13  (0=2 … 12=A)
                       suit  = card // 13 (0=c, 1=d, 2=h, 3=s)
    """
    v1, s1 = card1 % 13, card1 // 13
    v2, s2 = card2 % 13, card2 // 13
    # Rang le plus élevé en premier
    if v1 < v2:
        v1, v2 = v2, v1
        s1, s2 = s2, s1
    r1 = _CARD_RANKS[v1]
    r2 = _CARD_RANKS[v2]
    if v1 == v2:
        return r1 + r2          # paire
    return r1 + r2 + ('s' if s1 == s2 else 'o')


class LogParser:
    """Parse les fichiers de log SQLite de PokerTH."""

    # Actions qui comptent comme VPIP (mise volontaire preflop)
    VPIP_ACTIONS = {"calls", "bets", "is all in with"}

    # Actions qui comptent comme PFR (raise preflop)
    PFR_ACTIONS = {"bets", "is all in with"}

    # Actions agressives (pour AF)
    AGGRESSIVE_ACTIONS = {"bets", "is all in with"}

    # Actions passives (pour AF)
    PASSIVE_ACTIONS = {"calls"}

    def __init__(self, db_path: Path | str):
        """Initialise le parser avec le chemin de la base."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Fichier de log introuvable: {db_path}")
        # Connexion persistante pour éviter l'overhead de reconnexion
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Retourne la connexion persistante (la crée si nécessaire)."""
        if self._conn is None:
            # Connexion en lecture seule, thread-safe, avec timeout pour les locks
            self._conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro",
                uri=True,
                check_same_thread=False,
                timeout=10
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Ferme la connexion."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def refresh(self) -> None:
        """Ferme et rouvre la connexion pour voir les nouvelles données."""
        self.close()

    def get_last_processed_action_id(self) -> int:
        """Retourne le plus grand ActionID présent dans la base."""
        try:
            conn = self._connect()
            cursor = conn.execute("SELECT MAX(ActionID) FROM Action")
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0
        except sqlite3.OperationalError:
            return 0

    def has_actions(self) -> bool:
        """Vérifie si le fichier de log contient au moins une action."""
        try:
            conn = self._connect()
            cursor = conn.execute("SELECT 1 FROM Action LIMIT 1")
            return cursor.fetchone() is not None
        except sqlite3.OperationalError:
            return False

    def get_session_info(self) -> GameSession | None:
        """Récupère les informations de la session."""
        conn = self._connect()
        cursor = conn.execute("SELECT * FROM Session LIMIT 1")
        row = cursor.fetchone()
        if row:
            return GameSession(
                pokerth_version=row["PokerTH_Version"],
                date=row["Date"],
                time=row["Time"],
                log_version=row["LogVersion"],
            )
        return None

    def get_players(self) -> dict[str, set[int]]:
        """Récupère tous les joueurs avec leurs sièges par partie.

        Returns:
            Dict {player_name: {game_ids où il a joué}}
        """
        players: dict[str, set[int]] = {}
        conn = self._connect()
        cursor = conn.execute("SELECT Player, UniqueGameID FROM Player")
        for row in cursor:
            name = row["Player"]
            game_id = row["UniqueGameID"]
            if name not in players:
                players[name] = set()
            players[name].add(game_id)
        return players

    def get_player_seat(self, game_id: int, player_name: str) -> int | None:
        """Récupère le siège d'un joueur dans une partie."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT Seat FROM Player WHERE UniqueGameID = ? AND Player = ?",
            (game_id, player_name)
        )
        row = cursor.fetchone()
        return row["Seat"] if row else None

    def get_player_seats(self, player_name: str) -> dict[int, int]:
        """Récupère le siège d'un joueur pour toutes ses parties.

        Returns:
            Dict {game_id: seat}
        """
        conn = self._connect()
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        return {row["UniqueGameID"]: row["Seat"] for row in cursor}

    def get_actions(
        self,
        game_id: int | None = None,
        hand_id: int | None = None,
        betting_round: int | None = None,
    ) -> Generator[HandAction, None, None]:
        """Récupère les actions avec filtres optionnels.

        Args:
            game_id: Filtrer par partie
            hand_id: Filtrer par main
            betting_round: Filtrer par round (0=preflop, 1=flop, etc.)
        """
        query = "SELECT * FROM Action WHERE 1=1"
        params: list = []

        if game_id is not None:
            query += " AND UniqueGameID = ?"
            params.append(game_id)
        if hand_id is not None:
            query += " AND HandID = ?"
            params.append(hand_id)
        if betting_round is not None:
            query += " AND BeRo = ?"
            params.append(betting_round)

        query += " ORDER BY ActionID"

        conn = self._connect()
        cursor = conn.execute(query, params)
        for row in cursor:
            yield HandAction(
                hand_id=row["HandID"],
                game_id=row["UniqueGameID"],
                betting_round=row["BeRo"],
                player_seat=row["Player"],
                action=row["Action"],
                amount=row["Amount"],
            )

    def get_preflop_actions_by_player(self, player_name: str) -> Generator[HandAction, None, None]:
        """Récupère toutes les actions preflop d'un joueur."""
        conn = self._connect()
        # Récupère les parties et sièges du joueur
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        player_games = {row["UniqueGameID"]: row["Seat"] for row in cursor}

        if not player_games:
            return

        # Récupère les actions preflop pour ces sièges
        placeholders = ",".join("?" * len(player_games))
        query = f"""
            SELECT a.* FROM Action a
            WHERE a.UniqueGameID IN ({placeholders})
            AND a.BeRo = 0
            ORDER BY a.UniqueGameID, a.HandID, a.ActionID
        """
        cursor = conn.execute(query, list(player_games.keys()))

        for row in cursor:
            game_id = row["UniqueGameID"]
            if row["Player"] == player_games.get(game_id):
                yield HandAction(
                    hand_id=row["HandID"],
                    game_id=row["UniqueGameID"],
                    betting_round=row["BeRo"],
                    player_seat=row["Player"],
                    action=row["Action"],
                    amount=row["Amount"],
                )

    def get_hands_played_by_player(self, player_name: str) -> set[tuple[int, int]]:
        """Retourne l'ensemble des (game_id, hand_id) où le joueur était présent.

        Utilise la table Action pour ne compter que les mains où le joueur a
        réellement joué (excluant les mains après son élimination).
        """
        conn = self._connect()
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        player_games = {row["UniqueGameID"]: row["Seat"] for row in cursor}
        if not player_games:
            return set()

        result = set()
        for game_id, seat in player_games.items():
            cursor = conn.execute(
                "SELECT DISTINCT HandID FROM Action WHERE UniqueGameID = ? AND Player = ?",
                (game_id, seat)
            )
            for row in cursor:
                result.add((game_id, row["HandID"]))
        return result

    def hand_has_showdown(self, game_id: int, hand_id: int) -> bool:
        """Vérifie si une main a eu un showdown (round 4)."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT 1 FROM Action WHERE UniqueGameID = ? AND HandID = ? AND BeRo = 4 LIMIT 1",
            (game_id, hand_id)
        )
        return cursor.fetchone() is not None

    def get_showdown_winner(self, game_id: int, hand_id: int) -> int | None:
        """Retourne le siège du gagnant au showdown (première action 'wins' au round 4)."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT Player FROM Action WHERE UniqueGameID = ? AND HandID = ? AND BeRo = 4 AND Action = 'wins' LIMIT 1",
            (game_id, hand_id)
        )
        row = cursor.fetchone()
        return row["Player"] if row else None

    def get_current_table_players(self) -> list[str]:
        """Retourne les noms des joueurs de la partie la plus récente."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT Player FROM Player WHERE UniqueGameID = (SELECT MAX(UniqueGameID) FROM Player)"
        )
        return [row["Player"] for row in cursor]

    def get_all_actions_by_player(self, player_name: str) -> Generator[HandAction, None, None]:
        """Récupère toutes les actions d'un joueur (tous rounds)."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        player_games = {row["UniqueGameID"]: row["Seat"] for row in cursor}

        if not player_games:
            return

        placeholders = ",".join("?" * len(player_games))
        query = f"""
            SELECT a.* FROM Action a
            WHERE a.UniqueGameID IN ({placeholders})
            ORDER BY a.UniqueGameID, a.HandID, a.ActionID
        """
        cursor = conn.execute(query, list(player_games.keys()))
        for row in cursor:
            game_id = row["UniqueGameID"]
            if row["Player"] == player_games.get(game_id):
                yield HandAction(
                    hand_id=row["HandID"],
                    game_id=row["UniqueGameID"],
                    betting_round=row["BeRo"],
                    player_seat=row["Player"],
                    action=row["Action"],
                    amount=row["Amount"],
                )

    # Positions par nombre de joueurs (offset depuis le dealer, 0=BTN)
    _POSITION_NAMES: dict[int, list[str]] = {
        2:  ['BTN', 'BB'],
        3:  ['BTN', 'SB', 'BB'],
        4:  ['BTN', 'SB', 'BB', 'UTG'],
        5:  ['BTN', 'SB', 'BB', 'UTG', 'CO'],
        6:  ['BTN', 'SB', 'BB', 'UTG', 'HJ', 'CO'],
        7:  ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'HJ', 'CO'],
        8:  ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'MP', 'HJ', 'CO'],
        9:  ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'UTG+2', 'MP', 'HJ', 'CO'],
        10: ['BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'UTG+2', 'MP', 'MP+1', 'HJ', 'CO'],
    }

    def get_player_vpip_combos(self, player_name: str) -> list[tuple[str, str, int]]:
        """Retourne les combos VPIP du joueur avec position et nombre de joueurs.

        Seules les mains où le joueur a volontairement mis de l'argent preflop
        (call, bet ou raise — hors blind forcée) et dont les cartes sont connues
        (showdown) sont incluses.

        Returns:
            Liste de (combo, position, n_players) par main VPIP visible.
        """
        conn = self._connect()
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        player_games = {row["UniqueGameID"]: row["Seat"] for row in cursor}

        if not player_games:
            return []

        # Collecte les (game_id, hand_id) où le joueur a VPIP'd preflop
        placeholders = ",".join("?" * len(player_games))
        cursor = conn.execute(
            f"""SELECT UniqueGameID, HandID, Player FROM Action
                WHERE UniqueGameID IN ({placeholders})
                AND BeRo = 0
                AND Action IN ('calls', 'bets', 'is all in with')""",
            list(player_games.keys())
        )
        vpip_hands: set[tuple[int, int]] = set()
        for row in cursor:
            game_id = row["UniqueGameID"]
            if row["Player"] == player_games.get(game_id):
                vpip_hands.add((game_id, row["HandID"]))

        if not vpip_hands:
            return []

        results: list[tuple[str, str, int]] = []
        cursor = conn.execute(
            f"SELECT * FROM Hand WHERE UniqueGameID IN ({placeholders})",
            list(player_games.keys())
        )

        for row in cursor:
            game_id = row["UniqueGameID"]
            hand_id = row["HandID"]
            if (game_id, hand_id) not in vpip_hands:
                continue

            player_seat = player_games.get(game_id)
            if player_seat is None:
                continue

            card1 = row[f"Seat_{player_seat}_Card_1"]
            card2 = row[f"Seat_{player_seat}_Card_2"]
            if card1 is None or card2 is None:
                continue

            dealer_seat = row["Dealer_Seat"]
            occupied = [s for s in range(1, 11) if row[f"Seat_{s}_Cash"] is not None]
            n_players = len(occupied)

            if dealer_seat in occupied and player_seat in occupied:
                dealer_idx = occupied.index(dealer_seat)
                player_idx = occupied.index(player_seat)
                offset = (player_idx - dealer_idx) % n_players
                names = self._POSITION_NAMES.get(n_players)
                position = names[offset] if names else f"P{offset}"
            else:
                position = "?"

            combo = _cards_to_combo(card1, card2)
            results.append((combo, position, n_players))

        return results
