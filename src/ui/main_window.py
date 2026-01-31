"""Fenêtre principale de l'application."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QStatusBar,
    QMessageBox, QProgressDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QSettings
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
        self.log_watcher: LogWatcher | None = None
        self.hud: HUDManager | None = None
        self.is_tracking = False
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
        self.setMinimumSize(800, 400)

    def _setup_ui(self) -> None:
        """Configure l'interface."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Section configuration
        config_group = QGroupBox("Configuration")
        config_layout = QHBoxLayout(config_group)

        self.log_dir_label = QLabel(f"Dossier logs: {POKERTH_LOG_DIR}")
        config_layout.addWidget(self.log_dir_label, stretch=1)

        self.browse_btn = QPushButton("Parcourir...")
        self.browse_btn.clicked.connect(self._browse_log_dir)
        config_layout.addWidget(self.browse_btn)

        layout.addWidget(config_group)

        # Section contrôles
        controls_layout = QHBoxLayout()

        self.start_btn = QPushButton("Demarrer le tracking")
        self.start_btn.clicked.connect(self._toggle_tracking)
        self.start_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.start_btn)

        self.show_hud_btn = QPushButton("Afficher HUD")
        self.show_hud_btn.clicked.connect(self._toggle_hud)
        self.show_hud_btn.setEnabled(False)
        self.show_hud_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.show_hud_btn)

        self.refresh_btn = QPushButton("Rafraichir")
        self.refresh_btn.clicked.connect(self._import_all_logs)
        self.refresh_btn.setMinimumHeight(40)
        controls_layout.addWidget(self.refresh_btn)

        # Séparateur
        controls_layout.addSpacing(20)

        # Toggle pour filtrer les joueurs
        self.table_only_checkbox = QCheckBox("Table uniquement")
        self.table_only_checkbox.setToolTip("Afficher uniquement les joueurs de la table actuelle")
        self.table_only_checkbox.stateChanged.connect(self._on_filter_changed)
        self.table_only_checkbox.setEnabled(False)  # Désactivé tant que le tracking n'est pas lancé
        controls_layout.addWidget(self.table_only_checkbox)

        layout.addLayout(controls_layout)

        # Section stats
        stats_group = QGroupBox("Statistiques des joueurs")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(11)
        self.stats_table.setHorizontalHeaderLabels([
            "Joueur", "VPIP%", "PFR%", "AF", "3-Bet%", "C-Bet%",
            "F3B%", "FCB%", "WTSD%", "W$SD%", "Mains"
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
        self.status_bar.showMessage("Pret")

    def _setup_menu(self) -> None:
        """Configure le menu."""
        menubar = self.menuBar()

        # Menu Fichier
        file_menu = menubar.addMenu("&Fichier")

        import_action = QAction("Importer l'historique...", self)
        import_action.triggered.connect(self._import_all_logs)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        clear_action = QAction("Effacer les stats", self)
        clear_action.triggered.connect(self._clear_stats)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quitter", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Menu Options
        options_menu = menubar.addMenu("&Options")

        hud_settings_action = QAction("Configurer le HUD...", self)
        hud_settings_action.triggered.connect(self._open_hud_settings)
        options_menu.addAction(hud_settings_action)

        # Menu Aide
        help_menu = menubar.addMenu("&Aide")

        about_action = QAction("A propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _load_settings(self) -> None:
        """Charge les paramètres sauvegardés."""
        log_dir = self.settings.value("log_dir", str(POKERTH_LOG_DIR))
        self.log_dir = Path(log_dir)
        self.log_dir_label.setText(f"Dossier logs: {self.log_dir}")

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
            "Sélectionner le dossier de logs PokerTH",
            str(self.log_dir)
        )
        if dir_path:
            self.log_dir = Path(dir_path)
            self.log_dir_label.setText(f"Dossier logs: {self.log_dir}")
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
                "Erreur",
                f"Le dossier de logs n'existe pas:\n{self.log_dir}"
            )
            return

        self.log_watcher = LogWatcher(self.log_dir, self.stats_db, self)
        self.log_watcher.stats_updated.connect(self._on_stats_updated)
        self.log_watcher.new_log_detected.connect(self._on_new_log)
        self.log_watcher.table_players_changed.connect(self._on_table_changed)
        self.log_watcher.start()

        self.is_tracking = True
        self.start_btn.setText("Arreter le tracking")
        # Le bouton HUD reste grisé jusqu'à ce qu'il y ait des stats
        self.show_hud_btn.setEnabled(False)
        # Force le mode "Table uniquement" pendant le tracking
        self.table_only_checkbox.setChecked(True)
        self.table_only_checkbox.setEnabled(False)
        self.status_bar.showMessage("Tracking actif - en attente de donnees...")

    def _stop_tracking(self) -> None:
        """Arrête le tracking."""
        if self.log_watcher:
            self.log_watcher.stop()
            self.log_watcher = None

        self.is_tracking = False
        self.start_btn.setText("Demarrer le tracking")
        self.show_hud_btn.setEnabled(False)
        # Réactive la checkbox et décoche pour afficher tous les joueurs
        self.table_only_checkbox.setEnabled(True)
        self.table_only_checkbox.setChecked(False)
        # Rafraîchit l'affichage pour montrer tous les joueurs
        self._all_stats = self.stats_db.get_all_players_stats()
        self._refresh_table_display()
        self.status_bar.showMessage("Tracking arrete")

    def _toggle_hud(self) -> None:
        """Affiche/masque le HUD."""
        if self.hud is None:
            self.hud = HUDManager()

            # Met à jour le HUD avec les stats des joueurs de la table actuelle
            if self.log_watcher:
                stats = self.log_watcher.get_table_stats()
                self.hud.update_stats(stats)

            self.hud.show()
            self.show_hud_btn.setText("Masquer HUD")
        else:
            if self.hud.is_visible():
                self.hud.hide()
                self.show_hud_btn.setText("Afficher HUD")
            else:
                self.hud.show()
                self.show_hud_btn.setText("Masquer HUD")

    def _refresh_stats(self) -> None:
        """Force un rafraîchissement des stats (tous les joueurs)."""
        # Charge toutes les stats de la DB
        self._all_stats = self.stats_db.get_all_players_stats()
        self._refresh_table_display()
        self.status_bar.showMessage(f"Stats rafraichies: {len(self._all_stats)} joueurs")

    def _on_stats_updated(self, stats: dict[str, PlayerStats]) -> None:
        """Appelé quand les stats sont mises à jour (joueurs de la table uniquement)."""
        # Fusionne les stats des joueurs de la table dans le cache
        for name, player_stats in stats.items():
            self._all_stats[name] = player_stats

        # Met à jour la table avec le filtre actuel
        self._refresh_table_display()

        # Active le bouton HUD quand il y a des stats exploitables
        if self.is_tracking:
            has_data = any(s.total_hands > 0 for s in stats.values())
            if has_data and not self.show_hud_btn.isEnabled():
                self.show_hud_btn.setEnabled(True)
                self.status_bar.showMessage("Tracking actif")

            # Met à jour le HUD avec les stats de la table
            if self.hud and self.hud.is_visible():
                self.hud.update_stats(stats)

    def _on_new_log(self, log_path: str) -> None:
        """Appelé quand un nouveau fichier de log est détecté."""
        self.status_bar.showMessage(f"Nouveau log: {Path(log_path).name}")

    def _on_table_changed(self, players: list[str]) -> None:
        """Appelé quand les joueurs de la table changent."""
        self._table_players = players
        self.status_bar.showMessage(f"Table: {len(players)} joueurs")
        # Rafraîchit l'affichage si le filtre "table uniquement" est actif
        if self.table_only_checkbox.isChecked():
            self._refresh_table_display()

    def _on_filter_changed(self, state: int) -> None:
        """Appelé quand le filtre table/tous change."""
        self._refresh_table_display()

    def _refresh_table_display(self) -> None:
        """Rafraîchit l'affichage de la table avec le filtre actuel."""
        if self.table_only_checkbox.isChecked() and self._table_players:
            # Filtre pour n'afficher que les joueurs de la table
            filtered_stats = {
                name: stats for name, stats in self._all_stats.items()
                if name in self._table_players
            }
            self._update_stats_table(filtered_stats)
        else:
            # Affiche tous les joueurs
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
            "Voulez-vous vraiment effacer toutes les statistiques ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.stats_db.clear_all_stats()
            self.stats_table.setRowCount(0)
            if self.hud:
                self.hud.clear()
            self.status_bar.showMessage("Stats effacees")

    def _import_all_logs(self) -> None:
        """Importe tous les fichiers .pdb du dossier de logs."""
        # Compte les fichiers
        pdb_files = list(self.log_dir.glob("pokerth-log-*.pdb"))
        if not pdb_files:
            QMessageBox.information(
                self,
                "Import",
                f"Aucun fichier de log trouve dans:\n{self.log_dir}"
            )
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Import de l'historique",
            f"Importer {len(pdb_files)} fichiers de log ?\n\n"
            "Les statistiques seront fusionnees avec les donnees existantes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Crée un watcher temporaire pour l'import
        temp_watcher = LogWatcher(self.log_dir, self.stats_db)

        # Progress dialog
        progress = QProgressDialog(
            "Import en cours...", "Annuler", 0, len(pdb_files), self
        )
        progress.setWindowTitle("Import de l'historique")
        progress.setModal(True)
        progress.show()

        def on_progress(current: int, total: int, filename: str) -> None:
            if progress.wasCanceled():
                return
            progress.setValue(current)
            progress.setLabelText(f"Import: {filename}")
            # Force le traitement des événements Qt
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

        try:
            imported = temp_watcher.import_all_logs(on_progress)
            progress.close()

            # Rafraîchit l'affichage
            self._all_stats = self.stats_db.get_all_players_stats()
            self._refresh_table_display()

            QMessageBox.information(
                self,
                "Import termine",
                f"{imported} fichiers importes avec succes.\n"
                f"{len(self._all_stats)} joueurs dans la base."
            )
            self.status_bar.showMessage(f"Import termine: {imported} fichiers")

        except Exception as e:
            progress.close()
            QMessageBox.warning(
                self,
                "Erreur",
                f"Erreur lors de l'import:\n{e}"
            )

    def _open_hud_settings(self) -> None:
        """Ouvre la fenêtre de configuration du HUD."""
        dialog = HUDSettingsDialog(self)
        if dialog.exec() and self.hud:
            # Rafraîchit le HUD avec les nouveaux paramètres
            self.hud.reload_settings()
            if self.log_watcher:
                table_stats = self.log_watcher.get_table_stats()
                self.hud.update_stats(table_stats)

    def _show_about(self) -> None:
        """Affiche la boîte de dialogue À propos."""
        QMessageBox.about(
            self,
            "A propos",
            "PokerTH Tracker v1.2\n\n"
            "HUD temps reel pour PokerTH\n\n"
            "Stats: VPIP, PFR, AF, 3-Bet, C-Bet,\n"
            "Fold to 3-Bet, Fold to C-Bet, WTSD, W$SD"
        )

    def closeEvent(self, event) -> None:
        """Appelé à la fermeture."""
        self._stop_tracking()
        if self.hud:
            self.hud.close()
            self.hud = None
        self._save_settings()
        event.accept()
