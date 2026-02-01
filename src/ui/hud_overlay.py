"""HUD Overlay pour afficher les stats des joueurs."""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QApplication, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QMouseEvent, QRegion

from ..database.models import PlayerStats
from .hud_settings import HUDSettingsDialog, HUD_STATS
from config import HUD_CONFIG


class PlayerHUDWidget(QFrame):
    """Widget HUD pour un joueur."""

    group_btn_clicked = pyqtSignal()
    reset_requested = pyqtSignal()
    drag_started = pyqtSignal(QPoint)  # Position globale du debut du drag
    drag_moved = pyqtSignal(QPoint)    # Nouvelle position globale

    def __init__(self, player_name: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._player_name = player_name
        self._stats: PlayerStats | None = None
        self._stat_labels: dict[str, QLabel] = {}
        self._is_grouped = False
        self._drag_start: QPoint | None = None

        self.setObjectName("hud")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._init_ui()
        self._init_context_menu()
        self._apply_style()

    def _init_ui(self) -> None:
        """Construit l'interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setSpacing(4)

        self.name_label = QLabel(self._player_name)
        self.name_label.setObjectName("name")
        self.name_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        top_row.addWidget(self.name_label, stretch=1)

        self.group_btn = QPushButton("G")
        self.group_btn.setObjectName("groupBtn")
        self.group_btn.setFixedSize(18, 18)
        self.group_btn.setToolTip("Group")
        self.group_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.group_btn.clicked.connect(self.group_btn_clicked.emit)
        top_row.addWidget(self.group_btn)

        layout.addLayout(top_row)

        self.stats_widget = QWidget()
        self.stats_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        enabled = HUDSettingsDialog.get_enabled_stats()
        labels = {s[0]: s[1].replace("%", "") for s in HUD_STATS}
        active = [sid for sid, _, _ in HUD_STATS if sid in enabled]

        for i in range(0, len(active), 2):
            row = QHBoxLayout()
            row.setSpacing(8)
            for j in range(2):
                if i + j < len(active):
                    sid = active[i + j]
                    label = QLabel(f"{labels[sid]}:-")
                    label.setObjectName("stat")
                    label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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

    @property
    def player_name(self) -> str:
        return self._player_name

    def set_grouped(self, grouped: bool) -> None:
        self._is_grouped = grouped
        self.group_btn.setText("U" if grouped else "G")
        self.group_btn.setToolTip("Ungroup" if grouped else "Group")
        self._apply_style()

    def update_stats(self, stats: PlayerStats) -> None:
        self._player_name = stats.player_name
        self._stats = stats
        self.name_label.setText(stats.player_name)
        self._update_values()

    def reload_settings(self) -> None:
        self._build_stats()
        self._apply_style()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            self.drag_started.emit(self._drag_start)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is not None:
            self.drag_moved.emit(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class HUDContainer(QWidget):
    """Fenetre conteneur transparent pour tous les HUDs."""

    def __init__(self):
        super().__init__(None)
        self._widgets: dict[str, PlayerHUDWidget] = {}
        self._grouped = False
        self._drag_start_pos: QPoint | None = None
        self._widget_start_positions: dict[str, QPoint] = {}

        self._init_window()

        # Timer pour maintenir la fenetre au premier plan
        self._raise_timer = QTimer(self)
        self._raise_timer.timeout.connect(self._raise_to_top)
        self._raise_timer.setInterval(500)  # Toutes les 500ms

    def _raise_to_top(self) -> None:
        """Eleve la fenetre au premier plan."""
        if self.isVisible():
            self.raise_()

    def _init_window(self) -> None:
        """Configure la fenetre."""
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_X11DoNotAcceptFocus)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Grande taille pour permettre le positionnement libre
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            self.setGeometry(geom)
        else:
            self.resize(1920, 1080)

    def _update_mask(self) -> None:
        """Met a jour le masque pour que seuls les widgets soient cliquables."""
        if not self._widgets:
            self.clearMask()
            return

        region = QRegion()
        for widget in self._widgets.values():
            # Ajoute la region de chaque widget au masque
            widget_rect = widget.geometry()
            region = region.united(QRegion(widget_rect))

        self.setMask(region)

    def add_widget(self, name: str, widget: PlayerHUDWidget) -> None:
        """Ajoute un widget."""
        widget.setParent(self)
        widget.drag_started.connect(lambda pos: self._on_drag_start(name, pos))
        widget.drag_moved.connect(lambda pos: self._on_drag_move(name, pos))
        self._widgets[name] = widget

        # Position initiale: en colonne
        y = sum(w.height() + 10 for w in self._widgets.values() if w != widget)
        widget.move(50, 50 + y)
        widget.show()
        self._update_mask()

    def remove_widget(self, name: str) -> PlayerHUDWidget | None:
        """Retire un widget."""
        widget = self._widgets.pop(name, None)
        if widget:
            widget.setParent(None)
            self._update_mask()
        return widget

    def get_widget(self, name: str) -> PlayerHUDWidget | None:
        return self._widgets.get(name)

    def get_widgets(self) -> dict[str, PlayerHUDWidget]:
        return self._widgets

    def set_grouped(self, grouped: bool) -> None:
        """Active/desactive le mode groupe."""
        self._grouped = grouped
        for widget in self._widgets.values():
            widget.set_grouped(grouped)

    def _on_drag_start(self, name: str, global_pos: QPoint) -> None:
        """Debut du drag d'un widget."""
        self._drag_start_pos = global_pos
        # Sauvegarde les positions de tous les widgets
        self._widget_start_positions = {
            n: w.pos() for n, w in self._widgets.items()
        }

    def _on_drag_move(self, name: str, global_pos: QPoint) -> None:
        """Mouvement pendant le drag."""
        if self._drag_start_pos is None:
            return

        delta = global_pos - self._drag_start_pos

        if self._grouped:
            # Mode groupe: tous les widgets bougent ensemble
            for n, start_pos in self._widget_start_positions.items():
                if n in self._widgets:
                    self._widgets[n].move(start_pos + delta)
        else:
            # Mode individuel: seul le widget drag bouge
            if name in self._widget_start_positions and name in self._widgets:
                self._widgets[name].move(self._widget_start_positions[name] + delta)

        self._update_mask()

    def reset_positions(self) -> None:
        """Remet les widgets en colonne."""
        y = 50
        for widget in self._widgets.values():
            widget.move(50, y)
            y += widget.height() + 10
        self._update_mask()


class HUDManager:
    """Gestionnaire des HUDs."""

    def __init__(self):
        self._container = HUDContainer()
        self._visible = False
        self._grouped = False
        self._pending_stats: dict[str, PlayerStats] = {}

    def _create_widget(self, name: str) -> PlayerHUDWidget:
        """Cree un nouveau widget HUD."""
        widget = PlayerHUDWidget(name)
        widget.group_btn_clicked.connect(self._toggle_group)
        widget.reset_requested.connect(self._on_reset)
        return widget

    def _toggle_group(self) -> None:
        """Active/desactive le mode groupe."""
        self._grouped = not self._grouped
        self._container.set_grouped(self._grouped)

    def _on_reset(self) -> None:
        """Reset les positions."""
        self._container.reset_positions()

    def show(self) -> None:
        """Affiche les HUDs."""
        self._visible = True
        if self._pending_stats:
            self.update_stats(self._pending_stats)
        self._container.show()
        self._container.raise_()
        self._container._raise_timer.start()

    def hide(self) -> None:
        """Masque les HUDs."""
        self._visible = False
        self._container._raise_timer.stop()
        self._container.hide()

    def is_visible(self) -> bool:
        return self._visible

    def reload_settings(self) -> None:
        """Recharge les parametres."""
        for widget in self._container.get_widgets().values():
            widget.reload_settings()
            widget.adjustSize()

    def update_stats(self, stats: dict[str, PlayerStats]) -> None:
        """Met a jour les stats."""
        self._pending_stats = stats
        widgets = self._container.get_widgets()

        # Cree les nouveaux widgets
        for name, player_stats in stats.items():
            if name not in widgets:
                widget = self._create_widget(name)
                widget.set_grouped(self._grouped)
                widget.adjustSize()
                self._container.add_widget(name, widget)

            self._container.get_widget(name).update_stats(player_stats)
            self._container.get_widget(name).adjustSize()

        # Supprime les joueurs absents
        to_remove = [n for n in widgets if n not in stats]
        for name in to_remove:
            widget = self._container.remove_widget(name)
            if widget:
                widget.deleteLater()

        # Met a jour le masque apres les changements de taille
        self._container._update_mask()

    def reset(self) -> None:
        self._on_reset()

    def clear(self) -> None:
        """Efface tout."""
        widgets = self._container.get_widgets()
        for name in list(widgets.keys()):
            widget = self._container.remove_widget(name)
            if widget:
                widget.deleteLater()

    def close(self) -> None:
        self.clear()
        self._container.hide()
        self._container.close()


# Alias
PlayerHUDWindow = PlayerHUDWidget
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
