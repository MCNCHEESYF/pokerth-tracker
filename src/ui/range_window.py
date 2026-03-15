"""Fenêtre d'affichage de la range d'un joueur (grille 13x13)."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


_GRID_RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']

# Ordre d'affichage des positions dans le dropdown
_POSITION_ORDER = [
    'BTN', 'SB', 'BB', 'UTG', 'UTG+1', 'UTG+2', 'MP', 'MP+1', 'HJ', 'CO'
]


def _cell_combo(row: int, col: int) -> str:
    """Retourne le nom du combo poker pour la cellule (row, col) de la grille 13x13."""
    r1, r2 = _GRID_RANKS[row], _GRID_RANKS[col]
    if row == col:
        return r1 + r2
    elif row < col:
        return r1 + r2 + 's'
    else:
        return r2 + r1 + 'o'


class RangeWindow(QWidget):
    """Fenêtre affichant la range showdown d'un joueur avec filtres position/joueurs."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self._player_name = ""
        self._all_occurrences: list[tuple[str, str, int]] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setMinimumSize(570, 630)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Titre
        self._title_label = QLabel("")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self._title_label.setFont(font)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._title_label)

        # Filtres
        filters_group = QGroupBox("Filters")
        filters_layout = QHBoxLayout(filters_group)

        filters_layout.addWidget(QLabel("Position:"))
        self._pos_combo = QComboBox()
        self._pos_combo.setMinimumWidth(90)
        self._pos_combo.currentIndexChanged.connect(self._refresh_grid)
        filters_layout.addWidget(self._pos_combo)

        filters_layout.addSpacing(16)

        filters_layout.addWidget(QLabel("Players:"))
        self._n_combo = QComboBox()
        self._n_combo.setMinimumWidth(70)
        self._n_combo.currentIndexChanged.connect(self._refresh_grid)
        filters_layout.addWidget(self._n_combo)

        filters_layout.addStretch()

        self._count_label = QLabel("0 hands")
        filters_layout.addWidget(self._count_label)

        layout.addWidget(filters_group)

        # Grille 13x13
        self._grid = QTableWidget(13, 13)
        self._grid.setHorizontalHeaderLabels(_GRID_RANKS)
        self._grid.setVerticalHeaderLabels(_GRID_RANKS)
        self._grid.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._grid.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._grid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._grid.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._grid.horizontalHeader().setMinimumSectionSize(30)
        self._grid.verticalHeader().setMinimumSectionSize(30)
        layout.addWidget(self._grid)

        # Légende
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Diagonal = pairs  |  Top-right = suited  |  Bottom-left = offsuit"))
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        self._init_grid_labels()

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self.closed.emit()

    def _init_grid_labels(self) -> None:
        """Initialise les cellules de la grille avec les noms de combos."""
        for row in range(13):
            for col in range(13):
                combo = _cell_combo(row, col)
                item = QTableWidgetItem(combo)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setBackground(QColor(240, 240, 240))
                self._grid.setItem(row, col, item)

    def update_data(self, player_name: str, occurrences: list[tuple[str, str, int]]) -> None:
        """Met à jour les données affichées.

        Args:
            player_name: Nom du joueur
            occurrences: Liste de (combo, position, n_players)
        """
        self._player_name = player_name
        self._all_occurrences = occurrences
        self.setWindowTitle(f"Range — {player_name}")
        self._title_label.setText(f"Showdown range — {player_name}")
        self._update_filter_options()
        self._refresh_grid()
        self.show()
        self.raise_()

    def _update_filter_options(self) -> None:
        """Met à jour les options des dropdowns selon les données disponibles."""
        # Positions disponibles, dans l'ordre standard
        available_positions = {pos for _, pos, _ in self._all_occurrences}
        ordered_positions = [p for p in _POSITION_ORDER if p in available_positions]
        # Positions inconnues en fin
        unknown = sorted(available_positions - set(_POSITION_ORDER))
        ordered_positions.extend(unknown)

        # Bloquer les signaux pendant la mise à jour
        self._pos_combo.blockSignals(True)
        prev_pos = self._pos_combo.currentText()
        self._pos_combo.clear()
        self._pos_combo.addItem("All")
        for pos in ordered_positions:
            self._pos_combo.addItem(pos)
        idx = self._pos_combo.findText(prev_pos)
        self._pos_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._pos_combo.blockSignals(False)

        # Nombres de joueurs disponibles
        available_n = sorted({n for _, _, n in self._all_occurrences})

        self._n_combo.blockSignals(True)
        prev_n = self._n_combo.currentText()
        self._n_combo.clear()
        self._n_combo.addItem("All")
        for n in available_n:
            self._n_combo.addItem(str(n))
        idx = self._n_combo.findText(prev_n)
        self._n_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self._n_combo.blockSignals(False)

    def _get_filtered_counts(self) -> dict[str, int]:
        """Retourne le nombre d'occurrences par combo selon les filtres actifs."""
        pos_filter = self._pos_combo.currentText()
        n_filter = self._n_combo.currentText()

        counts: dict[str, int] = {}
        for combo, pos, n in self._all_occurrences:
            if pos_filter != "All" and pos != pos_filter:
                continue
            if n_filter != "All" and str(n) != n_filter:
                continue
            counts[combo] = counts.get(combo, 0) + 1
        return counts

    def _refresh_grid(self) -> None:
        """Rafraîchit les couleurs et textes de la grille selon les filtres."""
        counts = self._get_filtered_counts()
        total = sum(counts.values())
        self._count_label.setText(f"{total} hand{'s' if total != 1 else ''}")

        max_count = max(counts.values(), default=1)

        for row in range(13):
            for col in range(13):
                combo = _cell_combo(row, col)
                count = counts.get(combo, 0)
                item = self._grid.item(row, col)
                if item is None:
                    continue

                if count > 0:
                    ratio = count / max_count
                    # Vert (120°) → jaune (60°) → rouge (0°) selon le ratio
                    hue = int(120 * (1.0 - ratio))
                    color = QColor.fromHsv(hue, 220, 210)
                    item.setBackground(color)
                    item.setForeground(QColor(0, 0, 0))
                    item.setText(f"{combo}\n{count}")
                else:
                    item.setBackground(QColor(240, 240, 240))
                    item.setForeground(QColor(0, 0, 0))
                    item.setText(combo)
