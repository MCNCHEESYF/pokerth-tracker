"""Configuration du PokerTH Tracker."""

import os
from pathlib import Path

# Chemins par défaut
HOME = Path.home()
POKERTH_LOG_DIR = HOME / ".pokerth" / "log"
STATS_DB_PATH = HOME / ".pokerth_tracker" / "stats.db"

# Créer le répertoire de données si nécessaire
STATS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configuration du HUD
HUD_CONFIG = {
    "opacity": 0.95,  # 95% opaque par défaut
    "font_size": 12,
    "bg_color": "#000000",  # Fond noir
    "text_color": "#eef0f2",
    "stat_color": "#00ff88",
    "border_color": "#333333",
}
