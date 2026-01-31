"""Dialogue de configuration du HUD."""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QGroupBox, QLabel
)
from PyQt6.QtCore import QSettings


# Définition des stats disponibles pour le HUD
HUD_STATS = [
    ("vpip", "VPIP%", "Voluntarily Put $ In Pot"),
    ("pfr", "PFR%", "Pre-Flop Raise"),
    ("af", "AF", "Aggression Factor"),
    ("three_bet", "3-Bet%", "3-Bet percentage"),
    ("cbet", "C-Bet%", "Continuation Bet"),
    ("fold_to_3bet", "F3B%", "Fold to 3-Bet"),
    ("fold_to_cbet", "FCB%", "Fold to C-Bet"),
    ("wtsd", "WTSD%", "Went To ShowDown"),
    ("wsd", "W$SD%", "Won $ at ShowDown"),
    ("hands", "Mains", "Nombre de mains"),
]

# Stats activées par défaut
DEFAULT_STATS = {"vpip", "pfr", "af", "hands"}


class HUDSettingsDialog(QDialog):
    """Dialogue pour configurer les stats affichées dans le HUD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings("PokerTHTracker", "PTHTracker")
        self.checkboxes: dict[str, QCheckBox] = {}

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Configure l'interface."""
        self.setWindowTitle("Configuration du HUD")
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Groupe des stats
        stats_group = QGroupBox("Stats a afficher")
        stats_layout = QVBoxLayout(stats_group)

        for stat_id, stat_name, stat_desc in HUD_STATS:
            checkbox = QCheckBox(f"{stat_name} - {stat_desc}")
            checkbox.setObjectName(stat_id)
            self.checkboxes[stat_id] = checkbox
            stats_layout.addWidget(checkbox)

        layout.addWidget(stats_group)

        # Note
        note_label = QLabel(
            "Note: Les stats seront organisees automatiquement\n"
            "en lignes de 2 dans le HUD."
        )
        note_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note_label)

        # Boutons
        buttons_layout = QHBoxLayout()

        reset_btn = QPushButton("Reinitialiser")
        reset_btn.clicked.connect(self._reset_defaults)
        buttons_layout.addWidget(reset_btn)

        buttons_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Enregistrer")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_and_close)
        buttons_layout.addWidget(save_btn)

        layout.addLayout(buttons_layout)

    def _load_settings(self) -> None:
        """Charge les paramètres sauvegardés."""
        enabled_stats = self.settings.value("hud_stats", list(DEFAULT_STATS))
        if isinstance(enabled_stats, str):
            enabled_stats = [enabled_stats]

        for stat_id, checkbox in self.checkboxes.items():
            checkbox.setChecked(stat_id in enabled_stats)

    def _save_and_close(self) -> None:
        """Sauvegarde les paramètres et ferme."""
        enabled_stats = [
            stat_id for stat_id, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]
        self.settings.setValue("hud_stats", enabled_stats)
        self.accept()

    def _reset_defaults(self) -> None:
        """Réinitialise aux valeurs par défaut."""
        for stat_id, checkbox in self.checkboxes.items():
            checkbox.setChecked(stat_id in DEFAULT_STATS)

    @staticmethod
    def get_enabled_stats() -> set[str]:
        """Récupère les stats activées depuis les paramètres."""
        settings = QSettings("PokerTHTracker", "PTHTracker")
        enabled_stats = settings.value("hud_stats", list(DEFAULT_STATS))
        if isinstance(enabled_stats, str):
            enabled_stats = [enabled_stats]
        return set(enabled_stats) if enabled_stats else DEFAULT_STATS
