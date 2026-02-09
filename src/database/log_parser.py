"""Parser des fichiers de log PokerTH (.pdb)."""

import sqlite3
from pathlib import Path
from typing import Generator

from .models import HandAction, GameSession


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
                timeout=2
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

    def get_hands_played_by_player(self, player_name: str) -> set[tuple[int, int]]:
        """Récupère les (game_id, hand_id) où le joueur a joué."""
        hands: set[tuple[int, int]] = set()
        conn = self._connect()
        cursor = conn.execute(
            "SELECT UniqueGameID, Seat FROM Player WHERE Player = ?",
            (player_name,)
        )
        player_games = {row["UniqueGameID"]: row["Seat"] for row in cursor}

        if not player_games:
            return hands

        placeholders = ",".join("?" * len(player_games))
        query = f"""
            SELECT DISTINCT a.UniqueGameID, a.HandID, a.Player
            FROM Action a
            WHERE a.UniqueGameID IN ({placeholders})
        """
        cursor = conn.execute(query, list(player_games.keys()))

        for row in cursor:
            game_id = row["UniqueGameID"]
            if row["Player"] == player_games.get(game_id):
                hands.add((game_id, row["HandID"]))

        return hands

    def get_current_table_players(self) -> list[str]:
        """Récupère les joueurs de la dernière partie (table actuelle)."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT MAX(UniqueGameID) as max_id FROM Game"
        )
        row = cursor.fetchone()
        if not row or row["max_id"] is None:
            return []

        max_game_id = row["max_id"]
        cursor = conn.execute(
            "SELECT Player FROM Player WHERE UniqueGameID = ? ORDER BY Seat",
            (max_game_id,)
        )
        return [row["Player"] for row in cursor]

    def get_last_processed_action_id(self) -> int:
        """Récupère l'ID de la dernière action."""
        conn = self._connect()
        cursor = conn.execute("SELECT MAX(ActionID) as max_id FROM Action")
        row = cursor.fetchone()
        return row["max_id"] if row and row["max_id"] else 0

    def get_actions_since(self, action_id: int) -> Generator[HandAction, None, None]:
        """Récupère les actions depuis un certain ID (pour updates incrémentaux)."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT * FROM Action WHERE ActionID > ? ORDER BY ActionID",
            (action_id,)
        )
        for row in cursor:
            yield HandAction(
                hand_id=row["HandID"],
                game_id=row["UniqueGameID"],
                betting_round=row["BeRo"],
                player_seat=row["Player"],
                action=row["Action"],
                amount=row["Amount"],
            )

    def hand_has_showdown(self, game_id: int, hand_id: int) -> bool:
        """Vérifie si une main est allée jusqu'au showdown."""
        conn = self._connect()
        cursor = conn.execute(
            "SELECT 1 FROM Action WHERE UniqueGameID = ? AND HandID = ? AND BeRo = 4 LIMIT 1",
            (game_id, hand_id)
        )
        return cursor.fetchone() is not None

    def get_showdown_winner(self, game_id: int, hand_id: int) -> int | None:
        """Récupère le siège du gagnant au showdown (si disponible).

        Cherche l'action 'wins' dans le round showdown.
        """
        conn = self._connect()
        cursor = conn.execute(
            "SELECT Player FROM Action WHERE UniqueGameID = ? AND HandID = ? AND BeRo = 4 AND Action LIKE '%wins%' LIMIT 1",
            (game_id, hand_id)
        )
        row = cursor.fetchone()
        return row["Player"] if row else None
