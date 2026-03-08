"""Base de données pour les statistiques persistantes."""

import json
import sqlite3
from pathlib import Path

from .models import PlayerStats


class StatsDB:
    """Gère la persistence des statistiques des joueurs."""

    SCHEMA = """
        CREATE TABLE IF NOT EXISTS player_stats (
            player_name TEXT PRIMARY KEY,
            total_hands INTEGER DEFAULT 0,
            vpip_hands INTEGER DEFAULT 0,
            pfr_hands INTEGER DEFAULT 0,
            total_bets INTEGER DEFAULT 0,
            total_calls INTEGER DEFAULT 0,
            three_bet_opportunities INTEGER DEFAULT 0,
            three_bet_made INTEGER DEFAULT 0,
            cbet_opportunities INTEGER DEFAULT 0,
            cbet_made INTEGER DEFAULT 0,
            fold_to_3bet_opportunities INTEGER DEFAULT 0,
            fold_to_3bet_made INTEGER DEFAULT 0,
            fold_to_cbet_opportunities INTEGER DEFAULT 0,
            fold_to_cbet_made INTEGER DEFAULT 0,
            hands_saw_flop INTEGER DEFAULT 0,
            hands_went_to_showdown INTEGER DEFAULT 0,
            showdowns_won INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS processed_logs (
            log_path TEXT PRIMARY KEY,
            last_action_id INTEGER DEFAULT 0,
            last_processed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS player_ranges (
            player_name TEXT,
            combo TEXT,
            position TEXT,
            n_players INTEGER,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (player_name, combo, position, n_players)
        );
    """

    # Migration pour ajouter les nouvelles colonnes si elles n'existent pas
    MIGRATIONS = [
        "ALTER TABLE player_stats ADD COLUMN three_bet_opportunities INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN three_bet_made INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN cbet_opportunities INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN cbet_made INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN fold_to_3bet_opportunities INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN fold_to_3bet_made INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN fold_to_cbet_opportunities INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN fold_to_cbet_made INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN hands_saw_flop INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN hands_went_to_showdown INTEGER DEFAULT 0",
        "ALTER TABLE player_stats ADD COLUMN showdowns_won INTEGER DEFAULT 0",
        "ALTER TABLE processed_logs ADD COLUMN stats_json TEXT",
        "ALTER TABLE processed_logs ADD COLUMN ranges_json TEXT",
    ]

    def __init__(self, db_path: Path | str):
        """Initialise la base de données."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Crée une connexion thread-safe."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Active le mode WAL pour de meilleures performances multi-thread
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        """Initialise le schéma de la base."""
        with self._connect() as conn:
            conn.executescript(self.SCHEMA)
            # Exécute les migrations pour les bases existantes
            for migration in self.MIGRATIONS:
                try:
                    conn.execute(migration)
                except sqlite3.OperationalError:
                    pass  # Colonne existe déjà
            conn.commit()

    def get_player_stats(self, player_name: str) -> PlayerStats | None:
        """Récupère les stats d'un joueur."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT * FROM player_stats WHERE player_name = ?",
                (player_name,)
            )
            row = cursor.fetchone()
            if row:
                return PlayerStats(
                    player_name=row["player_name"],
                    total_hands=row["total_hands"],
                    vpip_hands=row["vpip_hands"],
                    pfr_hands=row["pfr_hands"],
                    total_bets=row["total_bets"],
                    total_calls=row["total_calls"],
                    three_bet_opportunities=row["three_bet_opportunities"],
                    three_bet_made=row["three_bet_made"],
                    cbet_opportunities=row["cbet_opportunities"],
                    cbet_made=row["cbet_made"],
                    fold_to_3bet_opportunities=row["fold_to_3bet_opportunities"],
                    fold_to_3bet_made=row["fold_to_3bet_made"],
                    fold_to_cbet_opportunities=row["fold_to_cbet_opportunities"],
                    fold_to_cbet_made=row["fold_to_cbet_made"],
                    hands_saw_flop=row["hands_saw_flop"],
                    hands_went_to_showdown=row["hands_went_to_showdown"],
                    showdowns_won=row["showdowns_won"],
                )
        return None

    def get_all_players_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats de tous les joueurs."""
        stats: dict[str, PlayerStats] = {}
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM player_stats ORDER BY total_hands DESC")
            for row in cursor:
                stats[row["player_name"]] = PlayerStats(
                    player_name=row["player_name"],
                    total_hands=row["total_hands"],
                    vpip_hands=row["vpip_hands"],
                    pfr_hands=row["pfr_hands"],
                    total_bets=row["total_bets"],
                    total_calls=row["total_calls"],
                    three_bet_opportunities=row["three_bet_opportunities"],
                    three_bet_made=row["three_bet_made"],
                    cbet_opportunities=row["cbet_opportunities"],
                    cbet_made=row["cbet_made"],
                    fold_to_3bet_opportunities=row["fold_to_3bet_opportunities"],
                    fold_to_3bet_made=row["fold_to_3bet_made"],
                    fold_to_cbet_opportunities=row["fold_to_cbet_opportunities"],
                    fold_to_cbet_made=row["fold_to_cbet_made"],
                    hands_saw_flop=row["hands_saw_flop"],
                    hands_went_to_showdown=row["hands_went_to_showdown"],
                    showdowns_won=row["showdowns_won"],
                )
        return stats

    def save_player_stats(self, stats: PlayerStats) -> None:
        """Sauvegarde les stats d'un joueur (insert ou update)."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO player_stats
                    (player_name, total_hands, vpip_hands, pfr_hands, total_bets, total_calls,
                     three_bet_opportunities, three_bet_made, cbet_opportunities, cbet_made,
                     fold_to_3bet_opportunities, fold_to_3bet_made,
                     fold_to_cbet_opportunities, fold_to_cbet_made,
                     hands_saw_flop, hands_went_to_showdown, showdowns_won)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_name) DO UPDATE SET
                    total_hands = excluded.total_hands,
                    vpip_hands = excluded.vpip_hands,
                    pfr_hands = excluded.pfr_hands,
                    total_bets = excluded.total_bets,
                    total_calls = excluded.total_calls,
                    three_bet_opportunities = excluded.three_bet_opportunities,
                    three_bet_made = excluded.three_bet_made,
                    cbet_opportunities = excluded.cbet_opportunities,
                    cbet_made = excluded.cbet_made,
                    fold_to_3bet_opportunities = excluded.fold_to_3bet_opportunities,
                    fold_to_3bet_made = excluded.fold_to_3bet_made,
                    fold_to_cbet_opportunities = excluded.fold_to_cbet_opportunities,
                    fold_to_cbet_made = excluded.fold_to_cbet_made,
                    hands_saw_flop = excluded.hands_saw_flop,
                    hands_went_to_showdown = excluded.hands_went_to_showdown,
                    showdowns_won = excluded.showdowns_won,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                stats.player_name,
                stats.total_hands,
                stats.vpip_hands,
                stats.pfr_hands,
                stats.total_bets,
                stats.total_calls,
                stats.three_bet_opportunities,
                stats.three_bet_made,
                stats.cbet_opportunities,
                stats.cbet_made,
                stats.fold_to_3bet_opportunities,
                stats.fold_to_3bet_made,
                stats.fold_to_cbet_opportunities,
                stats.fold_to_cbet_made,
                stats.hands_saw_flop,
                stats.hands_went_to_showdown,
                stats.showdowns_won,
            ))
            conn.commit()

    def save_all_stats(self, all_stats: dict[str, PlayerStats]) -> None:
        """Sauvegarde les stats de plusieurs joueurs."""
        with self._connect() as conn:
            for stats in all_stats.values():
                conn.execute("""
                    INSERT INTO player_stats
                        (player_name, total_hands, vpip_hands, pfr_hands, total_bets, total_calls,
                         three_bet_opportunities, three_bet_made, cbet_opportunities, cbet_made,
                         fold_to_3bet_opportunities, fold_to_3bet_made,
                         fold_to_cbet_opportunities, fold_to_cbet_made,
                         hands_saw_flop, hands_went_to_showdown, showdowns_won)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(player_name) DO UPDATE SET
                        total_hands = excluded.total_hands,
                        vpip_hands = excluded.vpip_hands,
                        pfr_hands = excluded.pfr_hands,
                        total_bets = excluded.total_bets,
                        total_calls = excluded.total_calls,
                        three_bet_opportunities = excluded.three_bet_opportunities,
                        three_bet_made = excluded.three_bet_made,
                        cbet_opportunities = excluded.cbet_opportunities,
                        cbet_made = excluded.cbet_made,
                        fold_to_3bet_opportunities = excluded.fold_to_3bet_opportunities,
                        fold_to_3bet_made = excluded.fold_to_3bet_made,
                        fold_to_cbet_opportunities = excluded.fold_to_cbet_opportunities,
                        fold_to_cbet_made = excluded.fold_to_cbet_made,
                        hands_saw_flop = excluded.hands_saw_flop,
                        hands_went_to_showdown = excluded.hands_went_to_showdown,
                        showdowns_won = excluded.showdowns_won,
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    stats.player_name,
                    stats.total_hands,
                    stats.vpip_hands,
                    stats.pfr_hands,
                    stats.total_bets,
                    stats.total_calls,
                    stats.three_bet_opportunities,
                    stats.three_bet_made,
                    stats.cbet_opportunities,
                    stats.cbet_made,
                    stats.fold_to_3bet_opportunities,
                    stats.fold_to_3bet_made,
                    stats.fold_to_cbet_opportunities,
                    stats.fold_to_cbet_made,
                    stats.hands_saw_flop,
                    stats.hands_went_to_showdown,
                    stats.showdowns_won,
                ))
            conn.commit()

    def merge_stats(self, new_stats: PlayerStats) -> PlayerStats:
        """Fusionne de nouvelles stats avec les stats existantes."""
        existing = self.get_player_stats(new_stats.player_name)
        if existing:
            merged = PlayerStats(
                player_name=new_stats.player_name,
                total_hands=existing.total_hands + new_stats.total_hands,
                vpip_hands=existing.vpip_hands + new_stats.vpip_hands,
                pfr_hands=existing.pfr_hands + new_stats.pfr_hands,
                total_bets=existing.total_bets + new_stats.total_bets,
                total_calls=existing.total_calls + new_stats.total_calls,
                three_bet_opportunities=existing.three_bet_opportunities + new_stats.three_bet_opportunities,
                three_bet_made=existing.three_bet_made + new_stats.three_bet_made,
                cbet_opportunities=existing.cbet_opportunities + new_stats.cbet_opportunities,
                cbet_made=existing.cbet_made + new_stats.cbet_made,
                fold_to_3bet_opportunities=existing.fold_to_3bet_opportunities + new_stats.fold_to_3bet_opportunities,
                fold_to_3bet_made=existing.fold_to_3bet_made + new_stats.fold_to_3bet_made,
                fold_to_cbet_opportunities=existing.fold_to_cbet_opportunities + new_stats.fold_to_cbet_opportunities,
                fold_to_cbet_made=existing.fold_to_cbet_made + new_stats.fold_to_cbet_made,
                hands_saw_flop=existing.hands_saw_flop + new_stats.hands_saw_flop,
                hands_went_to_showdown=existing.hands_went_to_showdown + new_stats.hands_went_to_showdown,
                showdowns_won=existing.showdowns_won + new_stats.showdowns_won,
            )
            self.save_player_stats(merged)
            return merged
        else:
            self.save_player_stats(new_stats)
            return new_stats

    def get_last_processed_action(self, log_path: str) -> int:
        """Récupère le dernier ActionID traité pour un fichier log."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT last_action_id FROM processed_logs WHERE log_path = ?",
                (log_path,)
            )
            row = cursor.fetchone()
            return row["last_action_id"] if row else 0

    def set_last_processed_action(
        self,
        log_path: str,
        action_id: int,
        stats_json: str | None = None,
        ranges_json: str | None = None,
    ) -> None:
        """Enregistre le dernier ActionID traité, les stats et les ranges du fichier."""
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO processed_logs (log_path, last_action_id, stats_json, ranges_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(log_path) DO UPDATE SET
                    last_action_id = excluded.last_action_id,
                    stats_json = excluded.stats_json,
                    ranges_json = excluded.ranges_json,
                    last_processed = CURRENT_TIMESTAMP
            """, (log_path, action_id, stats_json, ranges_json))
            conn.commit()

    def get_file_ranges(self, log_path: str) -> dict[str, list] | None:
        """Récupère les ranges par joueur stockées pour un fichier log."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT ranges_json FROM processed_logs WHERE log_path = ?",
                (log_path,)
            )
            row = cursor.fetchone()
            if row and row["ranges_json"]:
                return json.loads(row["ranges_json"])
        return None

    def subtract_stats(self, stats: PlayerStats) -> None:
        """Soustrait les stats d'un joueur des totaux globaux (mise à jour incrémentale)."""
        with self._connect() as conn:
            conn.execute("""
                UPDATE player_stats SET
                    total_hands                  = MAX(0, total_hands - ?),
                    vpip_hands                   = MAX(0, vpip_hands - ?),
                    pfr_hands                    = MAX(0, pfr_hands - ?),
                    total_bets                   = MAX(0, total_bets - ?),
                    total_calls                  = MAX(0, total_calls - ?),
                    three_bet_opportunities      = MAX(0, three_bet_opportunities - ?),
                    three_bet_made               = MAX(0, three_bet_made - ?),
                    cbet_opportunities           = MAX(0, cbet_opportunities - ?),
                    cbet_made                    = MAX(0, cbet_made - ?),
                    fold_to_3bet_opportunities   = MAX(0, fold_to_3bet_opportunities - ?),
                    fold_to_3bet_made            = MAX(0, fold_to_3bet_made - ?),
                    fold_to_cbet_opportunities   = MAX(0, fold_to_cbet_opportunities - ?),
                    fold_to_cbet_made            = MAX(0, fold_to_cbet_made - ?),
                    hands_saw_flop               = MAX(0, hands_saw_flop - ?),
                    hands_went_to_showdown       = MAX(0, hands_went_to_showdown - ?),
                    showdowns_won                = MAX(0, showdowns_won - ?),
                    last_updated                 = CURRENT_TIMESTAMP
                WHERE player_name = ?
            """, (
                stats.total_hands, stats.vpip_hands, stats.pfr_hands,
                stats.total_bets, stats.total_calls,
                stats.three_bet_opportunities, stats.three_bet_made,
                stats.cbet_opportunities, stats.cbet_made,
                stats.fold_to_3bet_opportunities, stats.fold_to_3bet_made,
                stats.fold_to_cbet_opportunities, stats.fold_to_cbet_made,
                stats.hands_saw_flop, stats.hands_went_to_showdown, stats.showdowns_won,
                stats.player_name,
            ))
            conn.commit()

    def subtract_file_ranges(self, ranges: dict[str, list]) -> None:
        """Soustrait les ranges d'un fichier des compteurs globaux."""
        with self._connect() as conn:
            for player_name, occurrences in ranges.items():
                counts: dict[tuple, int] = {}
                for entry in occurrences:
                    key = (entry[0], entry[1], entry[2])
                    counts[key] = counts.get(key, 0) + 1
                conn.executemany("""
                    UPDATE player_ranges
                    SET count = MAX(0, count - ?)
                    WHERE player_name = ? AND combo = ? AND position = ? AND n_players = ?
                """, [(cnt, player_name, combo, pos, n) for (combo, pos, n), cnt in counts.items()])
            conn.execute("DELETE FROM player_ranges WHERE count <= 0")
            conn.commit()

    def get_imported_file_stats(self, log_path: str) -> dict[str, PlayerStats] | None:
        """Charge les stats importées pour un fichier log depuis le baseline persisté."""
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT stats_json FROM processed_logs WHERE log_path = ?",
                (log_path,)
            )
            row = cursor.fetchone()
            if row and row["stats_json"]:
                data = json.loads(row["stats_json"])
                return {name: PlayerStats(**player_data) for name, player_data in data.items()}
        return None

    def get_all_processed_log_paths(self) -> list[str]:
        """Retourne tous les chemins de fichiers log traités."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT log_path FROM processed_logs")
            return [row["log_path"] for row in cursor]

    def merge_player_combos(self, player_name: str, occurrences: list[tuple[str, str, int]]) -> None:
        """Fusionne des occurrences de combos pour un joueur dans la base."""
        if not occurrences:
            return
        counts: dict[tuple[str, str, int], int] = {}
        for combo, pos, n in occurrences:
            key = (combo, pos, n)
            counts[key] = counts.get(key, 0) + 1

        with self._connect() as conn:
            conn.executemany("""
                INSERT INTO player_ranges (player_name, combo, position, n_players, count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(player_name, combo, position, n_players) DO UPDATE SET
                    count = count + excluded.count
            """, [(player_name, combo, pos, n, cnt) for (combo, pos, n), cnt in counts.items()])
            conn.commit()

    def get_player_combos(self, player_name: str) -> list[tuple[str, str, int]]:
        """Retourne les combos d'un joueur sous forme de liste d'occurrences (une par count)."""
        result: list[tuple[str, str, int]] = []
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT combo, position, n_players, count FROM player_ranges WHERE player_name = ?",
                (player_name,)
            )
            for row in cursor:
                result.extend([(row["combo"], row["position"], row["n_players"])] * row["count"])
        return result

    def clear_all_stats(self) -> None:
        """Efface toutes les stats (pour debug/reset)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM player_stats")
            conn.execute("DELETE FROM processed_logs")
            conn.execute("DELETE FROM player_ranges")
            conn.commit()
