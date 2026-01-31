"""Modèles de données pour le tracker."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HandAction:
    """Action d'un joueur dans une main."""

    hand_id: int
    game_id: int
    betting_round: int  # 0=preflop, 1=flop, 2=turn, 3=river, 4=showdown
    player_seat: int
    action: str
    amount: Optional[int] = None


@dataclass
class PlayerStats:
    """Statistiques agrégées d'un joueur."""

    player_name: str
    total_hands: int = 0
    vpip_hands: int = 0  # Mains où le joueur a volontairement mis de l'argent preflop
    pfr_hands: int = 0   # Mains où le joueur a raise preflop
    total_bets: int = 0  # Nombre de bets/raises
    total_calls: int = 0 # Nombre de calls
    three_bet_opportunities: int = 0  # Opportunités de 3-bet
    three_bet_made: int = 0           # 3-bets effectués
    cbet_opportunities: int = 0       # Opportunités de c-bet
    cbet_made: int = 0                # C-bets effectués
    fold_to_3bet_opportunities: int = 0  # Fois où le joueur fait face à une 3-bet
    fold_to_3bet_made: int = 0           # Fois où le joueur fold à une 3-bet
    fold_to_cbet_opportunities: int = 0  # Fois où le joueur fait face à un c-bet
    fold_to_cbet_made: int = 0           # Fois où le joueur fold à un c-bet
    hands_saw_flop: int = 0              # Mains où le joueur a vu le flop
    hands_went_to_showdown: int = 0      # Mains allées jusqu'au showdown
    showdowns_won: int = 0               # Showdowns gagnés

    @property
    def vpip(self) -> float:
        """VPIP: Voluntarily Put $ In Pot (%)."""
        if self.total_hands == 0:
            return 0.0
        return (self.vpip_hands / self.total_hands) * 100

    @property
    def pfr(self) -> float:
        """PFR: Pre-Flop Raise (%)."""
        if self.total_hands == 0:
            return 0.0
        return (self.pfr_hands / self.total_hands) * 100

    @property
    def af(self) -> float:
        """AF: Aggression Factor = (bets + raises) / calls."""
        if self.total_calls == 0:
            return float('inf') if self.total_bets > 0 else 0.0
        return self.total_bets / self.total_calls

    @property
    def three_bet(self) -> float:
        """3-Bet %: % de fois où le joueur 3-bet quand il en a l'opportunité."""
        if self.three_bet_opportunities == 0:
            return 0.0
        return (self.three_bet_made / self.three_bet_opportunities) * 100

    @property
    def cbet(self) -> float:
        """C-Bet %: % de fois où le joueur fait un continuation bet."""
        if self.cbet_opportunities == 0:
            return 0.0
        return (self.cbet_made / self.cbet_opportunities) * 100

    @property
    def fold_to_3bet(self) -> float:
        """Fold to 3-Bet %: % de fois où le joueur fold face à une 3-bet."""
        if self.fold_to_3bet_opportunities == 0:
            return 0.0
        return (self.fold_to_3bet_made / self.fold_to_3bet_opportunities) * 100

    @property
    def fold_to_cbet(self) -> float:
        """Fold to C-Bet %: % de fois où le joueur fold face à un c-bet."""
        if self.fold_to_cbet_opportunities == 0:
            return 0.0
        return (self.fold_to_cbet_made / self.fold_to_cbet_opportunities) * 100

    @property
    def wtsd(self) -> float:
        """WTSD %: % de mains allant au showdown (parmi celles qui voient le flop)."""
        if self.hands_saw_flop == 0:
            return 0.0
        return (self.hands_went_to_showdown / self.hands_saw_flop) * 100

    @property
    def wsd(self) -> float:
        """W$SD %: % de showdowns gagnés."""
        if self.hands_went_to_showdown == 0:
            return 0.0
        return (self.showdowns_won / self.hands_went_to_showdown) * 100

    def to_dict(self) -> dict:
        """Convertit en dictionnaire pour affichage."""
        return {
            "name": self.player_name,
            "hands": self.total_hands,
            "vpip": round(self.vpip, 1),
            "pfr": round(self.pfr, 1),
            "af": round(self.af, 1) if self.af != float('inf') else "inf",
            "three_bet": round(self.three_bet, 1),
            "cbet": round(self.cbet, 1),
            "fold_to_3bet": round(self.fold_to_3bet, 1),
            "fold_to_cbet": round(self.fold_to_cbet, 1),
            "wtsd": round(self.wtsd, 1),
            "wsd": round(self.wsd, 1),
        }


@dataclass
class GameSession:
    """Informations sur une session de jeu."""

    pokerth_version: str
    date: str
    time: str
    log_version: int
