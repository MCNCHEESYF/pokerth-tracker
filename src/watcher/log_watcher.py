"""Surveillance des fichiers de log PokerTH en temps réel."""

import json
import os
import sqlite3
from dataclasses import asdict, fields as dataclass_fields
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QFileSystemWatcher, QTimer

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

    # Signaux de résultat (pour les appels asynchrones depuis un autre thread)
    table_stats_ready = pyqtSignal(dict)  # Résultat de get_table_stats()
    import_progress = pyqtSignal(int, int, str)  # Progrès import (current, total, filename)
    import_finished = pyqtSignal(int, dict)  # Résultat import (nombre de fichiers, stats)
    import_error = pyqtSignal(str)  # Erreur lors de l'import

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
        # Baseline: stats du fichier courant au dernier import (évite le double-comptage)
        self._imported_file_stats: dict[str, PlayerStats] = {}

        # Watcher Qt pour les fichiers (créé dans start() pour être dans le bon thread)
        self._file_watcher: QFileSystemWatcher | None = None

        # Timer pour vérifications périodiques (créé dans start() pour être dans le bon thread)
        self._poll_timer: QTimer | None = None
        self._poll_interval = 2000  # 2 secondes

    @pyqtSlot()
    def start(self) -> None:
        """Démarre la surveillance."""
        if not self.log_dir.exists():
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Crée le watcher Qt (doit être créé dans le thread où il sera utilisé)
        if self._file_watcher is None:
            self._file_watcher = QFileSystemWatcher(self)
            self._file_watcher.directoryChanged.connect(self._on_directory_changed)
            self._file_watcher.fileChanged.connect(self._on_file_changed)

        # Crée le timer (doit être créé dans le thread où il sera utilisé)
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_for_changes)

        # Surveille le répertoire
        self._file_watcher.addPath(str(self.log_dir))

        # Trouve le fichier de log le plus récent
        self._find_current_log()

        # Démarre le polling
        self._poll_timer.start(self._poll_interval)

    @pyqtSlot()
    def stop(self) -> None:
        """Arrête la surveillance."""
        if self._poll_timer:
            self._poll_timer.stop()
        if self._file_watcher:
            if self.current_log:
                self._file_watcher.removePath(str(self.current_log))
            self._file_watcher.removePath(str(self.log_dir))
        # Ferme proprement la connexion au fichier de log
        if self.parser:
            self.parser.close()

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
        # Ferme l'ancien parser si existant
        if self.parser:
            self.parser.close()

        # Retire l'ancien du watcher
        if self.current_log and self._file_watcher:
            self._file_watcher.removePath(str(self.current_log))

        self.current_log = log_path
        if self._file_watcher:
            self._file_watcher.addPath(str(log_path))

        # Initialise le parser
        self.parser = LogParser(log_path)
        self.calculator = StatsCalculator(self.parser)

        # Reset pour traiter tout le fichier (pas de fusion DB)
        self.last_action_id = 0
        self._current_file_stats = {}

        # Charge le baseline si le fichier a déjà été importé (évite le double-comptage)
        self._imported_file_stats = self.stats_db.get_imported_file_stats(str(log_path)) or {}

        self.new_log_detected.emit(str(log_path))

        # Process initial pour charger les stats du fichier
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
        """Traite les nouvelles données de la table en cours avec agrégation DB."""
        if not self.parser or not self.calculator:
            return

        try:
            # Rafraîchit la connexion pour voir les nouvelles données
            self.parser.refresh()

            # Vérifie s'il y a de nouvelles actions
            current_max_action = self.parser.get_last_processed_action_id()
            if current_max_action <= self.last_action_id:
                return

            # Calcule les stats du fichier actuel uniquement (pas de fusion DB)
            self._current_file_stats = self.calculator.calculate_all_players_stats()

            # Met à jour le dernier ActionID traité (en mémoire seulement)
            self.last_action_id = current_max_action

            # Vérifie si les joueurs de la table ont changé
            new_players = self.parser.get_current_table_players()
            if new_players != self.current_table_players:
                self.current_table_players = new_players
                self.table_players_changed.emit(new_players)

            # Émet les stats agrégées (DB + fichier courant) pour les joueurs de la table
            aggregated_stats = self.get_aggregated_table_stats()
            self.stats_updated.emit(aggregated_stats)
        except sqlite3.OperationalError:
            # La base est temporairement verrouillée par PokerTH, on réessaiera au prochain poll
            pass

    def get_current_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats de tous les joueurs de la DB."""
        return self.stats_db.get_all_players_stats()

    def get_table_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats des joueurs de la table actuelle (session en cours)."""
        if not self.current_table_players:
            return {}

        # Retourne les stats du fichier actuel pour les joueurs de la table
        return {
            name: stats
            for name, stats in self._current_file_stats.items()
            if name in self.current_table_players
        }

    def get_aggregated_table_stats(self) -> dict[str, PlayerStats]:
        """Récupère les stats agrégées (DB + fichier courant) pour les joueurs de la table."""
        if not self.current_table_players:
            return {}

        aggregated: dict[str, PlayerStats] = {}
        db_stats = self.stats_db.get_all_players_stats()

        for player_name in self.current_table_players:
            db_player = db_stats.get(player_name)
            file_player = self._current_file_stats.get(player_name)

            if db_player and file_player:
                # Soustrait le baseline importé pour éviter le double-comptage du fichier courant.
                # Formule: DB + fichier - baseline = DB + (nouvelles mains depuis l'import)
                # Si pas de baseline (fichier jamais importé), imp est None et on ajoute tout.
                imp = self._imported_file_stats.get(player_name)
                aggregated[player_name] = PlayerStats(
                    player_name=player_name,
                    total_hands=db_player.total_hands + file_player.total_hands - (imp.total_hands if imp else 0),
                    vpip_hands=db_player.vpip_hands + file_player.vpip_hands - (imp.vpip_hands if imp else 0),
                    pfr_hands=db_player.pfr_hands + file_player.pfr_hands - (imp.pfr_hands if imp else 0),
                    total_bets=db_player.total_bets + file_player.total_bets - (imp.total_bets if imp else 0),
                    total_calls=db_player.total_calls + file_player.total_calls - (imp.total_calls if imp else 0),
                    three_bet_opportunities=db_player.three_bet_opportunities + file_player.three_bet_opportunities - (imp.three_bet_opportunities if imp else 0),
                    three_bet_made=db_player.three_bet_made + file_player.three_bet_made - (imp.three_bet_made if imp else 0),
                    cbet_opportunities=db_player.cbet_opportunities + file_player.cbet_opportunities - (imp.cbet_opportunities if imp else 0),
                    cbet_made=db_player.cbet_made + file_player.cbet_made - (imp.cbet_made if imp else 0),
                    fold_to_3bet_opportunities=db_player.fold_to_3bet_opportunities + file_player.fold_to_3bet_opportunities - (imp.fold_to_3bet_opportunities if imp else 0),
                    fold_to_3bet_made=db_player.fold_to_3bet_made + file_player.fold_to_3bet_made - (imp.fold_to_3bet_made if imp else 0),
                    fold_to_cbet_opportunities=db_player.fold_to_cbet_opportunities + file_player.fold_to_cbet_opportunities - (imp.fold_to_cbet_opportunities if imp else 0),
                    fold_to_cbet_made=db_player.fold_to_cbet_made + file_player.fold_to_cbet_made - (imp.fold_to_cbet_made if imp else 0),
                    hands_saw_flop=db_player.hands_saw_flop + file_player.hands_saw_flop - (imp.hands_saw_flop if imp else 0),
                    hands_went_to_showdown=db_player.hands_went_to_showdown + file_player.hands_went_to_showdown - (imp.hands_went_to_showdown if imp else 0),
                    showdowns_won=db_player.showdowns_won + file_player.showdowns_won - (imp.showdowns_won if imp else 0),
                )
            elif db_player:
                # Seulement dans la DB
                aggregated[player_name] = db_player
            elif file_player:
                # Seulement dans le fichier courant
                aggregated[player_name] = file_player

        return aggregated

    def force_refresh(self) -> None:
        """Force un rafraîchissement complet des stats."""
        # Émet le signal avec TOUTES les stats de la DB
        all_db_stats = self.stats_db.get_all_players_stats()
        self.stats_updated.emit(all_db_stats)

    def save_pending_stats(self) -> None:
        """Persiste le delta du fichier courant dans la DB (mains jouées depuis le dernier import).

        À appeler après l'arrêt du thread du watcher, avant de détruire l'instance.
        """
        if not self.current_log or not self._current_file_stats:
            return

        for player_name, file_stats in self._current_file_stats.items():
            imported_stats = self._imported_file_stats.get(player_name)
            if imported_stats:
                # Calcule le delta champ par champ (nouvelles mains depuis l'import)
                delta_kwargs: dict = {"player_name": player_name}
                for f in dataclass_fields(PlayerStats):
                    if f.name == "player_name":
                        continue
                    delta_kwargs[f.name] = getattr(file_stats, f.name) - getattr(imported_stats, f.name)
                self.stats_db.merge_stats(PlayerStats(**delta_kwargs))
            else:
                # Pas de baseline; toutes les stats sont nouvelles
                self.stats_db.merge_stats(file_stats)

        # Met à jour le baseline avec les stats actuelles du fichier
        stats_json = json.dumps({name: asdict(stats) for name, stats in self._current_file_stats.items()})
        self.stats_db.set_last_processed_action(str(self.current_log), self.last_action_id, stats_json)
        self._imported_file_stats = dict(self._current_file_stats)

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

                # Marque ce fichier comme traité avec son dernier ActionID et ses stats (baseline)
                last_action = parser.get_last_processed_action_id()
                stats_json = json.dumps({name: asdict(stats) for name, stats in file_stats.items()})
                self.stats_db.set_last_processed_action(str(pdb_file), last_action, stats_json)

                imported += 1

            except Exception as e:
                # Log l'erreur mais continue avec les autres fichiers
                print(f"Erreur lors de l'import de {pdb_file.name}: {e}")

        # Met à jour le last_action_id pour le fichier actuel si on le surveille
        if self.current_log:
            self.last_action_id = self.stats_db.get_last_processed_action(str(self.current_log))

        return imported

    @pyqtSlot()
    def request_table_stats(self) -> None:
        """Calcule les stats agrégées de la table et émet table_stats_ready (appel asynchrone)."""
        stats = self.get_aggregated_table_stats()
        self.table_stats_ready.emit(stats)

    @pyqtSlot()
    def request_import_all_logs(self) -> None:
        """Importe tous les logs et émet les signaux de progression (appel asynchrone)."""
        try:
            def progress_callback(current: int, total: int, filename: str) -> None:
                self.import_progress.emit(current, total, filename)

            imported = self.import_all_logs(progress_callback)
            # Récupère les stats dans ce thread (pas dans le thread UI)
            all_stats = self.stats_db.get_all_players_stats()
            self.import_finished.emit(imported, all_stats)
        except Exception as e:
            self.import_error.emit(str(e))
