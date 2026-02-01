"""HUD Overlay pour afficher les stats des joueurs."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QApplication, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QMouseEvent

from ..database.models import PlayerStats
from .hud_settings import HUDSettingsDialog, HUD_STATS
from config import HUD_CONFIG


class PlayerHUDWidget(QFrame):
    """Widget HUD pour un joueur (widget enfant, pas une fenetre)."""

    group_btn_clicked = pyqtSignal()
    reset_requested = pyqtSignal()
    drag_started = pyqtSignal(QPoint)  # Position globale du debut du drag
    drag_moved = pyqtSignal(QPoint)    # Position globale actuelle
    drag_ended = pyqtSignal()

    def __init__(self, player_name: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._player_name = player_name
        self._stats: PlayerStats | None = None
        self._stat_labels: dict[str, QLabel] = {}
        self._is_grouped = False

        self.setObjectName("hud")
        self._init_ui()
        self._init_context_menu()
        self._apply_style()

    def _init_ui(self) -> None:
        """Construit l'interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Ligne du haut: nom + bouton groupe
        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.name_label = QLabel(self._player_name)
        self.name_label.setObjectName("name")
        top_row.addWidget(self.name_label, stretch=1)

        self.group_btn = QPushButton("G")
        self.group_btn.setObjectName("groupBtn")
        self.group_btn.setFixedSize(18, 18)
        self.group_btn.setToolTip("Group")
        self.group_btn.clicked.connect(self.group_btn_clicked.emit)
        top_row.addWidget(self.group_btn)

        layout.addLayout(top_row)

        # Container pour les stats
        self.stats_widget = QWidget()
        self.stats_layout = QVBoxLayout(self.stats_widget)
        self.stats_layout.setContentsMargins(0, 0, 0, 0)
        self.stats_layout.setSpacing(2)
        layout.addWidget(self.stats_widget)

        self._build_stats()

    def _init_context_menu(self) -> None:
        """Configure le menu contextuel."""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)

    def _show_menu(self, pos: QPoint) -> None:
        """Affiche le menu contextuel."""
        menu = QMenu(self)
        reset_action = menu.addAction("Reset positions")
        reset_action.triggered.connect(self.reset_requested.emit)
        menu.exec(self.mapToGlobal(pos))

    def _build_stats(self) -> None:
        """Construit l'affichage des stats."""
        # Vide le layout
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            if item.widget():
                item.widget().deleteLater()

        self._stat_labels.clear()

        # Recupere les stats activees
        enabled = HUDSettingsDialog.get_enabled_stats()

        # Map stat_id -> short label
        labels = {s[0]: s[1].replace("%", "") for s in HUD_STATS}

        # Filtre et organise en lignes de 2
        active = [sid for sid, _, _ in HUD_STATS if sid in enabled]

        for i in range(0, len(active), 2):
            row = QHBoxLayout()
            row.setSpacing(8)

            for j in range(2):
                if i + j < len(active):
                    sid = active[i + j]
                    label = QLabel(f"{labels[sid]}:-")
                    label.setObjectName("stat")
                    self._stat_labels[sid] = label
                    row.addWidget(label)

            self.stats_layout.addLayout(row)

        if self._stats:
            self._update_values()

    def _update_values(self) -> None:
        """Met a jour les valeurs des stats."""
        if not self._stats:
            return

        s = self._stats
        labels = {st[0]: st[1].replace("%", "") for st in HUD_STATS}

        values = {
            "vpip": f"{s.vpip:.0f}" if s.vpip < 100 else "99+",
            "pfr": f"{s.pfr:.0f}" if s.pfr < 100 else "99+",
            "af": f"{s.af:.1f}" if s.af != float('inf') else "inf",
            "three_bet": f"{s.three_bet:.0f}" if s.three_bet_opportunities > 0 else "-",
            "cbet": f"{s.cbet:.0f}" if s.cbet_opportunities > 0 else "-",
            "fold_to_3bet": f"{s.fold_to_3bet:.0f}" if s.fold_to_3bet_opportunities > 0 else "-",
            "fold_to_cbet": f"{s.fold_to_cbet:.0f}" if s.fold_to_cbet_opportunities > 0 else "-",
            "wtsd": f"{s.wtsd:.0f}" if s.hands_saw_flop > 0 else "-",
            "wsd": f"{s.wsd:.0f}" if s.hands_went_to_showdown > 0 else "-",
            "hands": str(s.total_hands),
        }

        for sid, lbl in self._stat_labels.items():
            lbl.setText(f"{labels[sid]}:{values[sid]}")

    def _apply_style(self) -> None:
        """Applique le style."""
        cfg = HUD_CONFIG
        alpha = f"{int(cfg['opacity'] * 255):02x}"
        border = "#00aa55" if self._is_grouped else cfg["border_color"]

        self.setStyleSheet(f"""
            #hud {{
                background-color: {cfg["bg_color"]}{alpha};
                border: 2px solid {border};
                border-radius: 6px;
            }}
            #name {{
                color: {cfg["text_color"]};
                font-size: {cfg["font_size"]}px;
                font-weight: bold;
            }}
            #stat {{
                color: {cfg["stat_color"]};
                font-size: {cfg["font_size"] - 1}px;
                font-family: monospace;
            }}
            #groupBtn {{
                background-color: {"rgba(0,170,85,200)" if self._is_grouped else "rgba(80,80,120,200)"};
                border: 1px solid {border};
                border-radius: 3px;
                color: {cfg["text_color"]};
                font-size: 10px;
                font-weight: bold;
            }}
            #groupBtn:hover {{
                background-color: {"rgba(0,200,100,220)" if self._is_grouped else "rgba(100,100,150,220)"};
            }}
        """)

    # --- API publique ---

    def set_grouped(self, grouped: bool) -> None:
        """Definit l'etat de groupement."""
        self._is_grouped = grouped
        self.group_btn.setText("U" if grouped else "G")
        self.group_btn.setToolTip("Ungroup" if grouped else "Group")
        self._apply_style()

    def update_stats(self, stats: PlayerStats) -> None:
        """Met a jour les stats du joueur."""
        self._player_name = stats.player_name
        self._stats = stats
        self.name_label.setText(stats.player_name)
        self._update_values()

    def reload_settings(self) -> None:
        """Recharge les parametres d'affichage."""
        self._build_stats()

    # --- Events souris ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.drag_moved.emit(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_ended.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class HUDContainer(QWidget):
    """Fenetre conteneur transparente pour tous les HUDs."""

    def __init__(self):
        super().__init__()
        self._widgets: dict[str, PlayerHUDWidget] = {}
        self._positions: dict[str, QPoint] = {}  # Positions relatives au container
        self._grouped = False
        self._drag_start: QPoint | None = None
        self._drag_widget: PlayerHUDWidget | None = None
        self._drag_widget_start_pos: QPoint | None = None

        self._init_window()

    def _init_window(self) -> None:
        """Configure la fenetre conteneur."""
        self.setWindowTitle("HUD Container")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Taille initiale grande pour couvrir l'ecran
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.setGeometry(geo)
        else:
            self.resize(1920, 1080)

    def _on_drag_started(self, widget: PlayerHUDWidget, global_pos: QPoint) -> None:
        """Un widget commence a etre deplace."""
        self._drag_start = global_pos
        self._drag_widget = widget
        if self._grouped:
            # Mode groupe: on sauvegarde la position de la fenetre
            self._drag_widget_start_pos = self.pos()
        else:
            # Mode individuel: on sauvegarde la position du widget
            self._drag_widget_start_pos = widget.pos()

    def _on_drag_moved(self, widget: PlayerHUDWidget, global_pos: QPoint) -> None:
        """Un widget est en cours de deplacement."""
        if self._drag_start and self._drag_widget == widget:
            delta = global_pos - self._drag_start
            new_pos = self._drag_widget_start_pos + delta
            if self._grouped:
                # Mode groupe: deplace la fenetre entiere
                self.move(new_pos)
            else:
                # Mode individuel: deplace le widget
                widget.move(new_pos)

    def _on_drag_ended(self, widget: PlayerHUDWidget) -> None:
        """Fin du deplacement d'un widget."""
        if self._drag_widget == widget:
            # Sauvegarde la position relative
            self._positions[self._get_widget_name(widget)] = widget.pos()
        self._drag_start = None
        self._drag_widget = None
        self._drag_widget_start_pos = None

    def _get_widget_name(self, widget: PlayerHUDWidget) -> str:
        """Trouve le nom du joueur associe a un widget."""
        for name, w in self._widgets.items():
            if w is widget:
                return name
        return ""

    def _on_group_clicked(self) -> None:
        """Toggle le groupement."""
        if self._grouped:
            self._ungroup()
        else:
            self._group()

    def _group(self) -> None:
        """Groupe tous les widgets."""
        self._grouped = True
        for w in self._widgets.values():
            w.set_grouped(True)

    def _ungroup(self) -> None:
        """Degroupe tous les widgets."""
        self._grouped = False
        for w in self._widgets.values():
            w.set_grouped(False)

    def _on_reset(self) -> None:
        """Reset les positions."""
        self._grouped = False
        self._positions.clear()

        # Repositionne le conteneur
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.topLeft())

        # Repositionne les widgets en cascade
        for i, (name, w) in enumerate(self._widgets.items()):
            w.set_grouped(False)
            pos = QPoint(100 + i * 30, 100 + i * 30)
            w.move(pos)
            self._positions[name] = pos

    def update_stats(self, stats: dict[str, PlayerStats]) -> None:
        """Met a jour les stats des joueurs."""
        # Cree les nouveaux widgets
        for name, player_stats in stats.items():
            if name not in self._widgets:
                widget = PlayerHUDWidget(name, parent=self)
                widget.group_btn_clicked.connect(self._on_group_clicked)
                widget.reset_requested.connect(self._on_reset)
                widget.drag_started.connect(lambda pos, w=widget: self._on_drag_started(w, pos))
                widget.drag_moved.connect(lambda pos, w=widget: self._on_drag_moved(w, pos))
                widget.drag_ended.connect(lambda w=widget: self._on_drag_ended(w))
                widget.set_grouped(self._grouped)
                self._widgets[name] = widget

                # Position
                if name in self._positions:
                    widget.move(self._positions[name])
                else:
                    idx = len(self._widgets) - 1
                    pos = QPoint(100 + idx * 30, 100 + idx * 30)
                    widget.move(pos)
                    self._positions[name] = pos

                widget.adjustSize()
                widget.show()

            self._widgets[name].update_stats(player_stats)

        # Supprime les joueurs absents
        to_remove = [n for n in self._widgets if n not in stats]
        for name in to_remove:
            widget = self._widgets.pop(name)
            self._positions[name] = widget.pos()
            widget.deleteLater()

    def reload_settings(self) -> None:
        """Recharge les parametres pour tous les widgets."""
        for w in self._widgets.values():
            w.reload_settings()
            w.adjustSize()

    def clear(self) -> None:
        """Efface tous les widgets."""
        for w in self._widgets.values():
            w.deleteLater()
        self._widgets.clear()


class HUDManager:
    """Gestionnaire des HUDs."""

    def __init__(self):
        self._container: HUDContainer | None = None
        self._visible = False
        self._pending_stats: dict[str, PlayerStats] = {}

    def _ensure_container(self) -> HUDContainer:
        """Cree le conteneur si necessaire."""
        if self._container is None:
            self._container = HUDContainer()
        return self._container

    def show(self) -> None:
        """Affiche le HUD."""
        self._visible = True
        container = self._ensure_container()
        if self._pending_stats:
            container.update_stats(self._pending_stats)
        container.show()

    def hide(self) -> None:
        """Masque le HUD."""
        self._visible = False
        if self._container:
            self._container.hide()

    def is_visible(self) -> bool:
        """Retourne l'etat de visibilite."""
        return self._visible

    def reload_settings(self) -> None:
        """Recharge les parametres pour tous les widgets."""
        if self._container:
            self._container.reload_settings()

    def update_stats(self, stats: dict[str, PlayerStats]) -> None:
        """Met a jour les stats des joueurs."""
        self._pending_stats = stats
        if self._visible:
            container = self._ensure_container()
            container.update_stats(stats)

    def reset(self) -> None:
        """Reset les positions."""
        if self._container:
            self._container._on_reset()

    def clear(self) -> None:
        """Efface tous les widgets."""
        if self._container:
            self._container.clear()

    def close(self) -> None:
        """Ferme le conteneur."""
        if self._container:
            self._container.close()
            self._container = None


# Alias pour compatibilite
HUDOverlay = PlayerHUDWidget


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)

    manager = HUDManager()
    demo_stats = {
        "Player1": PlayerStats("Player1", total_hands=150, vpip_hands=38, pfr_hands=25,
                               total_bets=45, total_calls=30),
        "Player2": PlayerStats("Player2", total_hands=200, vpip_hands=50, pfr_hands=10,
                               total_bets=20, total_calls=60),
        "Player3": PlayerStats("Player3", total_hands=75, vpip_hands=30, pfr_hands=20,
                               total_bets=35, total_calls=25),
    }
    manager.update_stats(demo_stats)
    manager.show()

    sys.exit(app.exec())
