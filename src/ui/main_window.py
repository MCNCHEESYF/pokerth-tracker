"""Fenêtre principale de l'application."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QStatusBar,
    QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QSettings, QThread, QMetaObject, Q_ARG
from PyQt6.QtGui import QAction


class NumericTableWidgetItem(QTableWidgetItem):
    """Item de tableau avec tri numérique correct."""

    def __init__(self, text: str, value: float):
        super().__init__(text)
        self._value = value

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, NumericTableWidgetItem):
            return self._value < other._value
        return super().__lt__(other)

from ..database.log_parser import LogParser
from ..database.stats_db import StatsDB
from ..database.models import PlayerStats
from ..watcher.log_watcher import LogWatcher
from .hud_overlay import HUDManager
from .hud_settings import HUDSettingsDialog
from config import POKERTH_LOG_DIR, STATS_DB_PATH


class MainWindow(QMainWindow):
    """Fenêtre principale du PokerTH Tracker."""

    def __init__(self):
        super().__init__()
        self.settings = QSettings("PokerTHTracker", "PTHTracker")
        self.stats_db = StatsDB(STATS_DB_PATH)
        self._watcher_thread: QThread | None = None
        self.log_watcher: LogWatcher | None = None
        self.hud: HUDManager | None = None
        self.is_tracking = False
        # Flag pour savoir si le HUD attend des stats
        self._hud_waiting_for_stats = False
        # Thread et watcher temporaires pour l'import
        self._import_thread: QThread | None = None
        self._import_watcher: LogWatcher | None = None
        self._import_progress: QProgressDialog | None = None
        # Cache des stats et joueurs de la table pour le filtrage
        self._all_stats: dict[str, PlayerStats] = {}
        self._table_players: list[str] = []

        self._setup_window()
        self._setup_ui()
        self._setup_menu()
        self._load_settings()

    def _setup_window(self) -> None:
        """Configure la fenêtre principale."""
        self.setWindowTitle("PokerTH Tracker")
        self.setMinimumSize(800, 600)
        self.resize(900, 650)

    def _setup_ui(self) -> None:
        """Configure l'interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Section configuration
        config_group = QGroupBox("Configuration")
        config_layout = QHBoxLayout(config_group)

        self.log_dir_label = QLabel(f"Log folder: {POKERTH_LOG_DIR}")
        config_layout.addWidget(self.log_dir_label, stretch=1)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._browse_log_dir)
        config_layout.addWidget(self.browse_btn)

        layout.addWidget(config_group)

        # Section contrôles
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start tracking")
        self.start_btn.clicked.connect(self._toggle_tracking)
        self.start_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.start_btn)

        self.show_hud_btn = QPushButton("Show HUD")
        self.show_hud_btn.clicked.connect(self._toggle_hud)
        self.show_hud_btn.setEnabled(False)
        self.show_hud_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.show_hud_btn)

        self.refresh_btn = QPushButton("Import")
        self.refresh_btn.clicked.connect(self._refresh_stats)
        self.refresh_btn.setEnabled(True)  # Toujours actif pour permettre l'import
        self.refresh_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.refresh_btn)

        layout.addLayout(controls_layout)

        # Section stats
        stats_group = QGroupBox("Player statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(11)
        self.stats_table.setHorizontalHeaderLabels([
            "Player", "VPIP%", "PFR%", "AF", "3-Bet%", "C-Bet%",
            "F3B%", "FCB%", "WTSD%", "W$SD%", "Hands"
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 11):
            self.stats_table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.ResizeToContents
            )
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # Active le tri par clic sur les en-têtes
        self.stats_table.setSortingEnabled(True)
        # Tri par défaut: nombre de mains décroissant
        self.stats_table.sortByColumn(10, Qt.SortOrder.DescendingOrder)
        stats_layout.addWidget(self.stats_table)

        layout.addWidget(stats_group)

        # Barre de statut
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _setup_menu(self) -> None:
        """Configure le menu."""
        menubar = self.menuBar()

        # Menu Fichier
        file_menu = menubar.addMenu("&File")

        self.import_action = QAction("Import history...", self)
        self.import_action.triggered.connect(self._import_all_logs)
        file_menu.addAction(self.import_action)

        file_menu.addSeparator()

        clear_action = QAction("Clear stats", self)
        clear_action.triggered.connect(self._clear_stats)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Menu Options
        options_menu = menubar.addMenu("&Options")

        hud_settings_action = QAction("Configure HUD...", self)
        hud_settings_action.triggered.connect(self._open_hud_settings)
        options_menu.addAction(hud_settings_action)

        # Menu Aide
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _load_settings(self) -> None:
        """Charge les paramètres sauvegardés."""
        log_dir = self.settings.value("log_dir", str(POKERTH_LOG_DIR))
        self.log_dir = Path(log_dir)
        self.log_dir_label.setText(f"Log folder: {self.log_dir}")

        # Charge les stats existantes
        self._all_stats = self.stats_db.get_all_players_stats()
        self._update_stats_table(self._all_stats)

    def _save_settings(self) -> None:
        """Sauvegarde les paramètres."""
        self.settings.setValue("log_dir", str(self.log_dir))

    def _browse_log_dir(self) -> None:
        """Ouvre un dialogue pour sélectionner le dossier de logs."""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select PokerTH log folder",
            str(self.log_dir)
        )
        if dir_path:
            self.log_dir = Path(dir_path)
            self.log_dir_label.setText(f"Log folder: {self.log_dir}")
            self._save_settings()

    def _toggle_tracking(self) -> None:
        """Active/désactive le tracking."""
        if self.is_tracking:
            self._stop_tracking()
        else:
            self._start_tracking()

    def _start_tracking(self) -> None:
        """Démarre le tracking."""
        if not self.log_dir.exists():
            QMessageBox.warning(
                self,
                "Error",
                f"Log folder does not exist:\n{self.log_dir}"
            )
            return

        # Vérifie que le dernier log contient des actions
        pdb_files = list(self.log_dir.glob("pokerth-log-*.pdb"))
        if not pdb_files:
            QMessageBox.warning(
                self,
                "Error",
                f"No log files found in:\n{self.log_dir}"
            )
            return

        latest = max(pdb_files, key=lambda p: p.stat().st_mtime)
        try:
            parser = LogParser(latest)
            has_data = parser.has_actions()
            parser.close()
        except Exception:
            has_data = False

        if not has_data:
            QMessageBox.warning(
                self,
                "Error",
                f"The latest log file contains no actions yet:\n{latest.name}\n\n"
                "Start a game in PokerTH first, then try again."
            )
            return

        # Crée le thread pour le watcher
        self._watcher_thread = QThread(self)

        # Crée le watcher SANS parent (nécessaire pour moveToThread)
        self.log_watcher = LogWatcher(self.log_dir, self.stats_db)

        # Déplace le watcher dans le thread
        self.log_watcher.moveToThread(self._watcher_thread)

        # Connecte les signaux existants
        self.log_watcher.stats_updated.connect(self._on_stats_updated)
        self.log_watcher.new_log_detected.connect(self._on_new_log)
        self.log_watcher.table_players_changed.connect(self._on_table_changed)

        # Connecte les nouveaux signaux pour les appels asynchrones
        self.log_watcher.table_stats_ready.connect(self._on_table_stats_ready)

        # Démarre le watcher quand le thread démarre
        self._watcher_thread.started.connect(self.log_watcher.start)

        # Démarre le thread
        self._watcher_thread.start()

        self.is_tracking = True
        self.start_btn.setText("Stop tracking")
        # Le bouton HUD reste grisé jusqu'à ce qu'il y ait des stats
        self.show_hud_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.import_action.setEnabled(False)
        self.status_bar.showMessage("Tracking active - waiting for data...")

    def _stop_tracking(self) -> None:
        """Arrête le tracking."""
        if self.log_watcher and self._watcher_thread:
            # Invoque stop() dans le thread du watcher (thread-safe)
            QMetaObject.invokeMethod(
                self.log_watcher, "stop",
                Qt.ConnectionType.QueuedConnection
            )
            # Demande au thread de quitter (après stop())
            self._watcher_thread.quit()
            # Attend la fin du thread avec timeout
            if not self._watcher_thread.wait(5000):
                self._watcher_thread.terminate()
                self._watcher_thread.wait(1000)
            self._watcher_thread = None

        # Persiste les mains jouées (le thread est arrêté, pas de conflit)
        if self.log_watcher:
            self.log_watcher.save_pending_stats()

        self.log_watcher = None

        self.is_tracking = False
        self.start_btn.setText("Start tracking")
        self.show_hud_btn.setEnabled(False)
        self.show_hud_btn.setText("Show HUD")
        self.refresh_btn.setEnabled(True)
        self.import_action.setEnabled(True)

        # Cache le HUD
        if self.hud:
            self.hud.hide()

        # Recharge les stats de la DB pour afficher tous les joueurs
        self._all_stats = self.stats_db.get_all_players_stats()
        self._refresh_table_display()
        self.status_bar.showMessage("Tracking stopped")

    def _toggle_hud(self) -> None:
        """Affiche/masque le HUD."""
        if self.hud is None:
            self.hud = HUDManager(on_reset_callback=self._on_hud_reset)

            # Demande les stats de manière asynchrone
            if self.log_watcher:
                self._hud_waiting_for_stats = True
                self.log_watcher.request_table_stats()

            self.hud.show()
            self.show_hud_btn.setText("Hide HUD")
        else:
            if self.hud.is_visible():
                self.hud.hide()
                self.show_hud_btn.setText("Show HUD")
            else:
                # Demande des stats fraîches avant de réafficher le HUD
                if self.log_watcher:
                    self._hud_waiting_for_stats = True
                    self.log_watcher.request_table_stats()
                self.hud.show()
                self.show_hud_btn.setText("Hide HUD")

    def _refresh_stats(self) -> None:
        """Déclenche l'import de tous les logs (même comportement que Importer l'historique)."""
        self._import_all_logs()

    def _on_stats_updated(self, stats: dict[str, PlayerStats]) -> None:
        """Appelé quand les stats sont mises à jour."""
        # Cache les stats
        self._all_stats = stats

        # Met à jour la table avec le filtre actuel
        self._refresh_table_display()

        # Demande les stats de la table de manière asynchrone
        if self.is_tracking and self.log_watcher:
            self.log_watcher.request_table_stats()

    def _on_table_stats_ready(self, table_stats: dict[str, PlayerStats]) -> None:
        """Appelé quand les stats de la table sont prêtes (appel asynchrone)."""
        # Gère le flag d'attente du HUD
        if self._hud_waiting_for_stats:
            self._hud_waiting_for_stats = False
            if self.hud:
                self.hud.update_stats(table_stats)
            return

        # Active le bouton HUD quand il y a des stats de table exploitables
        if self.is_tracking:
            has_data = any(s.total_hands > 0 for s in table_stats.values())
            if has_data and not self.show_hud_btn.isEnabled():
                self.show_hud_btn.setEnabled(True)
                self.status_bar.showMessage("Tracking active")

            # Le HUD n'affiche que les joueurs de la table actuelle
            if self.hud and self.hud.is_visible():
                self.hud.update_stats(table_stats)

    def _on_new_log(self, log_path: str) -> None:
        """Appelé quand un nouveau fichier de log est détecté."""
        self.status_bar.showMessage(f"Nouveau log: {Path(log_path).name}")

    def _on_table_changed(self, players: list[str]) -> None:
        """Appelé quand les joueurs de la table changent."""
        self._table_players = players
        self.status_bar.showMessage(f"Table: {len(players)} players")

    def _on_hud_reset(self) -> None:
        """Appelé quand le HUD est réinitialisé (reset positions)."""
        if self.log_watcher:
            self._hud_waiting_for_stats = True
            self.log_watcher.request_table_stats()

    def _refresh_table_display(self) -> None:
        """Rafraîchit l'affichage de la table."""
        self._update_stats_table(self._all_stats)

    def _update_stats_table(self, stats: dict[str, PlayerStats]) -> None:
        """Met à jour le tableau des stats."""
        # Désactive le tri pendant la mise à jour (performance)
        self.stats_table.setSortingEnabled(False)
        self.stats_table.setRowCount(len(stats))

        for row, (name, player_stats) in enumerate(stats.items()):
            # Colonne 0: Nom du joueur (texte)
            self.stats_table.setItem(row, 0, QTableWidgetItem(name))

            # Colonne 1: VPIP%
            vpip_val = player_stats.vpip
            self.stats_table.setItem(row, 1, NumericTableWidgetItem(f"{vpip_val:.1f}", vpip_val))

            # Colonne 2: PFR%
            pfr_val = player_stats.pfr
            self.stats_table.setItem(row, 2, NumericTableWidgetItem(f"{pfr_val:.1f}", pfr_val))

            # Colonne 3: AF
            af_val = player_stats.af if player_stats.af != float('inf') else 9999
            af_text = f"{player_stats.af:.1f}" if player_stats.af != float('inf') else "inf"
            self.stats_table.setItem(row, 3, NumericTableWidgetItem(af_text, af_val))

            # Colonne 4: 3-Bet%
            three_bet_val = player_stats.three_bet if player_stats.three_bet_opportunities > 0 else -1
            three_bet_text = f"{player_stats.three_bet:.1f}" if player_stats.three_bet_opportunities > 0 else "-"
            self.stats_table.setItem(row, 4, NumericTableWidgetItem(three_bet_text, three_bet_val))

            # Colonne 5: C-Bet%
            cbet_val = player_stats.cbet if player_stats.cbet_opportunities > 0 else -1
            cbet_text = f"{player_stats.cbet:.1f}" if player_stats.cbet_opportunities > 0 else "-"
            self.stats_table.setItem(row, 5, NumericTableWidgetItem(cbet_text, cbet_val))

            # Colonne 6: Fold to 3-Bet%
            f3b_val = player_stats.fold_to_3bet if player_stats.fold_to_3bet_opportunities > 0 else -1
            f3b_text = f"{player_stats.fold_to_3bet:.1f}" if player_stats.fold_to_3bet_opportunities > 0 else "-"
            self.stats_table.setItem(row, 6, NumericTableWidgetItem(f3b_text, f3b_val))

            # Colonne 7: Fold to C-Bet%
            fcb_val = player_stats.fold_to_cbet if player_stats.fold_to_cbet_opportunities > 0 else -1
            fcb_text = f"{player_stats.fold_to_cbet:.1f}" if player_stats.fold_to_cbet_opportunities > 0 else "-"
            self.stats_table.setItem(row, 7, NumericTableWidgetItem(fcb_text, fcb_val))

            # Colonne 8: WTSD%
            wtsd_val = player_stats.wtsd if player_stats.hands_saw_flop > 0 else -1
            wtsd_text = f"{player_stats.wtsd:.1f}" if player_stats.hands_saw_flop > 0 else "-"
            self.stats_table.setItem(row, 8, NumericTableWidgetItem(wtsd_text, wtsd_val))

            # Colonne 9: W$SD%
            wsd_val = player_stats.wsd if player_stats.hands_went_to_showdown > 0 else -1
            wsd_text = f"{player_stats.wsd:.1f}" if player_stats.hands_went_to_showdown > 0 else "-"
            self.stats_table.setItem(row, 9, NumericTableWidgetItem(wsd_text, wsd_val))

            # Colonne 10: Nombre de mains
            hands_val = player_stats.total_hands
            self.stats_table.setItem(row, 10, NumericTableWidgetItem(str(hands_val), hands_val))

        # Réactive le tri (garde le tri actuel de l'utilisateur)
        self.stats_table.setSortingEnabled(True)

    def _clear_stats(self) -> None:
        """Efface toutes les stats."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Do you really want to clear all statistics?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.stats_db.clear_all_stats()
            self.stats_table.setRowCount(0)
            if self.hud:
                self.hud.clear()
            self.status_bar.showMessage("Stats cleared")

    def _import_all_logs(self) -> None:
        """Importe tous les fichiers .pdb du dossier de logs."""
        # Vérifie qu'un import n'est pas déjà en cours
        if self._import_thread is not None:
            QMessageBox.warning(
                self,
                "Import",
                "An import is already in progress."
            )
            return

        # Compte les fichiers
        pdb_files = list(self.log_dir.glob("pokerth-log-*.pdb"))
        if not pdb_files:
            QMessageBox.information(
                self,
                "Import",
                f"No log files found in:\n{self.log_dir}"
            )
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Import history",
            f"Import {len(pdb_files)} log files?\n\n"
            "Statistics will be merged with existing data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Crée le thread pour l'import
        self._import_thread = QThread(self)

        # Crée un watcher temporaire (SANS parent pour moveToThread)
        self._import_watcher = LogWatcher(self.log_dir, self.stats_db)
        self._import_watcher.moveToThread(self._import_thread)

        # Connecte les signaux de progrès et de fin
        self._import_watcher.import_progress.connect(self._on_import_progress)
        self._import_watcher.import_finished.connect(self._on_import_finished)
        self._import_watcher.import_error.connect(self._on_import_error)

        # Démarre l'import quand le thread démarre
        self._import_thread.started.connect(self._import_watcher.request_import_all_logs)

        # Progress dialog
        self._import_progress = QProgressDialog(
            "Import in progress...", "Cancel", 0, len(pdb_files), self
        )
        self._import_progress.setWindowTitle("Import history")
        self._import_progress.setModal(True)
        self._import_progress.canceled.connect(self._on_import_canceled)
        self._import_progress.show()

        # Démarre le thread
        self._import_thread.start()

    def _on_import_progress(self, current: int, total: int, filename: str) -> None:
        """Appelé lors de la progression de l'import."""
        if self._import_progress:
            self._import_progress.setMaximum(total)
            self._import_progress.setValue(current)
            self._import_progress.setLabelText(f"Import: {filename}")

    def _on_import_finished(self, imported: int, stats: dict[str, PlayerStats]) -> None:
        """Appelé quand l'import est terminé."""
        self._cleanup_import()

        # Rafraîchit l'affichage (les stats viennent du thread de l'import)
        self._all_stats = stats
        self._refresh_table_display()

        QMessageBox.information(
            self,
            "Import completed",
            f"{imported} files imported successfully.\n"
            f"{len(self._all_stats)} players in database."
        )
        self.status_bar.showMessage(f"Import completed: {imported} files")

    def _on_import_error(self, error: str) -> None:
        """Appelé en cas d'erreur lors de l'import."""
        self._cleanup_import()

        QMessageBox.warning(
            self,
            "Error",
            f"Error during import:\n{error}"
        )

    def _on_import_canceled(self) -> None:
        """Appelé quand l'utilisateur annule l'import."""
        self._cleanup_import()
        self.status_bar.showMessage("Import canceled")

    def _cleanup_import(self) -> None:
        """Nettoie les ressources d'import."""
        if self._import_progress:
            self._import_progress.close()
            self._import_progress = None

        if self._import_thread:
            self._import_thread.quit()
            self._import_thread.wait(3000)
            self._import_thread = None

        self._import_watcher = None

    def _open_hud_settings(self) -> None:
        """Ouvre la fenêtre de configuration du HUD."""
        dialog = HUDSettingsDialog(self)
        if dialog.exec() and self.hud:
            # Rafraîchit le HUD avec les nouveaux paramètres
            self.hud.reload_settings()
            # Demande les stats de manière asynchrone
            if self.log_watcher:
                self.log_watcher.request_table_stats()

    def _show_about(self) -> None:
        """Affiche la boîte de dialogue À propos."""
        QMessageBox.about(
            self,
            "About",
            "PokerTH Tracker v1.0 by ollika\n\n"
            "Real-time HUD for PokerTH\n\n"
            "Stats: VPIP, PFR, AF, 3-Bet, C-Bet,\n"
            "Fold to 3-Bet, Fold to C-Bet, WTSD, W$SD\n\n"
            "LONG LIVE PokerTH !"
        )

    def closeEvent(self, event) -> None:
        """Appelé à la fermeture."""
        if self.log_watcher and self._watcher_thread:
            QMetaObject.invokeMethod(
                self.log_watcher, "stop",
                Qt.ConnectionType.QueuedConnection
            )
            self._watcher_thread.quit()
            if not self._watcher_thread.wait(3000):
                self._watcher_thread.terminate()

        if self.hud:
            self.hud.close()
            self.hud = None
        self._save_settings()
        event.accept()
