"""Surveillance des fichiers de log PokerTH en temps réel."""

import os
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher, QTimer

from ..database.log_parser import LogParser
from ..database.stats_db import StatsDB
from ..database.models import PlayerStats
from ..stats.calculator import StatsCalculator


class LogWatcher(QObject):
    """Surveille les fichiers de log PokerTH et émet des signaux lors des changements."""

    # Signal émis quand les stats sont mises à jour
    stats_updated = pyqtSignal(dict)  # dict[str, PlayerStats]

    # Signal émis quand un nouveau fichier de log est détecté
    new_log_detected = pyqtSignal(str)  # chemin du fichier

    # Signal émis quand les joueurs de la table changent
    table_players_changed = pyqtSignal(list)  # list[str]

    def __init__(
        self,
        log_dir: Path | str,
        stats_db: StatsDB,
        parent: QObject | None = None
    ):
        """Initialise le watcher.

        Args:
            log_dir: Répertoire des logs PokerTH
            stats_db: Base de données des stats
            parent: Parent Qt
        """
        super().__init__(parent)
        self.log_dir = Path(log_dir)
        self.stats_db = stats_db
        self.current_log: Path | None = None
        self.parser: LogParser | None = None
        self.calculator: StatsCalculator | None = None
        self.last_action_id: int = 0
        self.current_table_players: list[str] = []
        # Stats calculées pour le fichier actuel (pour calculer les deltas)
        self._current_file_stats: dict[str, PlayerStats] = {}

        # Watcher Qt pour les fichiers
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.directoryChanged.connect(self._on_directory_changed)
        self._file_watcher.fileChanged.connect(self._on_file_changed)

        # Timer pour vérifications périodiques (certaines modifications échappent au watcher)
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_for_changes)
        self._poll_interval = 2000  # 2 secondes

    def start(self) -> None:
        """Démarre la surveillance."""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Surveille le répertoire
        self._file_watcher.addPath(str(self.log_dir))

        # Trouve le fichier de log le plus récent
        self._find_current_log()

        # Démarre le polling
        self._poll_timer.start(self._poll_interval)

    def stop(self) -> None:
        """Arrête la surveillance."""
        self._poll_timer.stop()
        if self.current_log:
            self._file_watcher.removePath(str(self.current_log))
        self._file_watcher.removePath(str(self.log_dir))

    def _find_current_log(self) -> None:
        """Trouve le fichier de log le plus récent."""
        pdb_files = list(self.log_dir.glob("pokerth-log-*.pdb"))
        if not pdb_files:
            return

        # Trie par date de modification
        latest = max(pdb_files, key=lambda p: p.stat().st_mtime)

        if latest != self.current_log:
            self._switch_to_log(latest)

    def _switch_to_log(self, log_path: Path) -> None:
        """Change vers un nouveau fichier de log."""
        # Retire l'ancien du watcher
        if self.current_log:
            self._file_watcher.removePath(str(self.current_log))

        self.current_log = log_path
        self._file_watcher.addPath(str(log_path))

        # Initialise le parser
        self.parser = LogParser(log_path)
        self.calculator = StatsCalculator(self.parser)

        # Récupère le dernier ActionID traité
        self.last_action_id = self.stats_db.get_last_processed_action(str(log_path))

        # Calcule les stats actuelles du fichier (pour les deltas futurs)
        self._current_file_stats = self.calculator.calculate_all_players_stats()

        self.new_log_detected.emit(str(log_path))

        # Process initial (va émettre les stats de la DB)
        self._process_updates()

    def _on_directory_changed(self, path: str) -> None:
        """Appelé quand le contenu du répertoire change."""
        self._find_current_log()

    def _on_file_changed(self, path: str) -> None:
        """Appelé quand un fichier surveillé change."""
        if self.current_log and Path(path) == self.current_log:
            self._process_updates()

    def _poll_for_changes(self) -> None:
        """Vérifie périodiquement les changements."""
        self._find_current_log()
        if self.current_log and self.parser:
            self._process_updates()

    def _process_updates(self) -> None:
        """Traite les nouvelles données et met à jour les stats."""
        if not self.parser or not self.calculator:
            return

        # Vérifie s'il y a de nouvelles actions
        current_max_action = self.parser.get_last_processed_action_id()
        if current_max_action <= self.last_action_id:
            return

        # Recalcule les stats de TOUS les joueurs du fichier
        new_stats = self.calculator.calculate_all_players_stats()

        # Calcule les DELTAS (nouvelles stats - anciennes stats du fichier)
        # et fusionne avec les stats existantes dans la DB
        for player_name, stats in new_stats.items():
            old_stats = self._current_file_stats.get(player_name)
            if old_stats:
                # Calcule le delta
                delta = PlayerStats(
                    player_name=player_name,
                    total_hands=stats.total_hands - old_stats.total_hands,
                    vpip_hands=stats.vpip_hands - old_stats.vpip_hands,
                    pfr_hands=stats.pfr_hands - old_stats.pfr_hands,
                    total_bets=stats.total_bets - old_stats.total_bets,
                    total_calls=stats.total_calls - old_stats.total_calls,
                    three_bet_opportunities=stats.three_bet_opportunities - old_stats.three_bet_opportunities,
                    three_bet_made=stats.three_bet_made - old_stats.three_bet_made,
                    cbet_opportunities=stats.cbet_opportunities - old_stats.cbet_opportunities,
                    cbet_made=stats.cbet_made - old_stats.cbet_made,
                    fold_to_3bet_opportunities=stats.fold_to_3bet_opportunities - old_stats.fold_to_3bet_opportunities,
                    fold_to_3bet_made=stats.fold_to_3bet_made - old_stats.fold_to_3bet_made,
                    fold_to_cbet_opportunities=stats.fold_to_cbet_opportunities - old_stats.fold_to_cbet_opportunities,
                    fold_to_cbet_made=stats.fold_to_cbet_made - old_stats.fold_to_cbet_made,
                    hands_saw_flop=stats.hands_saw_flop - old_stats.hands_saw_flop,
                    hands_went_to_showdown=stats.hands_went_to_showdown - old_stats.hands_went_to_showdown,
                    showdowns_won=stats.showdowns_won - old_stats.showdowns_won,
                )
                # Fusionne le delta avec les stats de la DB
                if delta.total_hands > 0:
                    self.stats_db.merge_stats(delta)
            else:
                # Nouveau joueur dans ce fichier, fusionne directement
                self.stats_db.merge_stats(stats)

        # Met à jour les stats du fichier actuel
        self._current_file_stats = new_stats

        # Met à jour le dernier ActionID traité
        self.last_action_id = current_max_action
        self.stats_db.set_last_processed_action(str(self.current_log), current_max_action)

        # Vérifie si les joueurs de la table ont changé
        new_players = self.parser.get_current_table_players()
        if new_players != self.current_table_players:
            self.current_table_players = new_players
            self.table_players_changed.emit(new_players)

        # Émet le signal avec TOUTES les stats de la DB
        all_db_stats = self.stats_db.get_all_players_stats()
        self.stats_updated.emit(all_db_stats)

    def get_current_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats de tous les joueurs de la DB."""
        return self.stats_db.get_all_players_stats()

    def get_table_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats des joueurs de la table actuelle."""
        if not self.current_table_players:
            return {}

        stats = {}
        for player_name in self.current_table_players:
            player_stats = self.stats_db.get_player_stats(player_name)
            if player_stats:
                stats[player_name] = player_stats
        return stats

    def force_refresh(self) -> None:
        """Force un rafraîchissement complet des stats."""
        # Émet le signal avec TOUTES les stats de la DB
        all_db_stats = self.stats_db.get_all_players_stats()
        self.stats_updated.emit(all_db_stats)

    def import_all_logs(self, progress_callback: Callable[[int, int, str], None] | None = None) -> int:
        """Importe tous les fichiers .pdb du répertoire de logs.

        Args:
            progress_callback: Fonction appelée avec (current, total, filename) pour le progrès

        Returns:
            Nombre de fichiers importés
        """
        pdb_files = sorted(self.log_dir.glob("pokerth-log-*.pdb"))
        total = len(pdb_files)
        imported = 0

        # IMPORTANT: Vide la base avant l'import pour éviter les doublons
        self.stats_db.clear_all_stats()

        for i, pdb_file in enumerate(pdb_files):
            if progress_callback:
                progress_callback(i + 1, total, pdb_file.name)

            try:
                # Parse le fichier
                parser = LogParser(pdb_file)
                calculator = StatsCalculator(parser)

                # Calcule les stats de tous les joueurs du fichier
                file_stats = calculator.calculate_all_players_stats()

                # Fusionne avec les stats existantes
                for player_name, stats in file_stats.items():
                    self.stats_db.merge_stats(stats)

                # Marque ce fichier comme traité avec son dernier ActionID
                last_action = parser.get_last_processed_action_id()
                self.stats_db.set_last_processed_action(str(pdb_file), last_action)

                imported += 1

            except Exception as e:
                # Log l'erreur mais continue avec les autres fichiers
                print(f"Erreur lors de l'import de {pdb_file.name}: {e}")

        # Met à jour le last_action_id pour le fichier actuel si on le surveille
        if self.current_log:
            self.last_action_id = self.stats_db.get_last_processed_action(str(self.current_log))

        return imported
