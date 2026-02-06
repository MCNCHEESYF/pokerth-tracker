"""Configuration du PokerTH Tracker."""

import os
import sys
from pathlib import Path

# Chemins par défaut (varient selon l'OS)
HOME = Path.home()

if sys.platform == "win32":
    _appdata = Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming"))
    POKERTH_LOG_DIR = _appdata / "pokerth" / "log"
    STATS_DB_PATH = _appdata / "pokerth_tracker" / "stats.db"
elif sys.platform == "darwin":
    POKERTH_LOG_DIR = HOME / "Library" / "Application Support" / "pokerth" / "log"
    STATS_DB_PATH = HOME / "Library" / "Application Support" / "pokerth_tracker" / "stats.db"
else:
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
