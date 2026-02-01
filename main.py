#!/usr/bin/env python3
"""PokerTH Tracker - Point d'entrée principal."""

import os
import sys
import argparse
from pathlib import Path

# Force XWayland pour que le HUD reste au premier plan
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.main_window import MainWindow
from src.stats.calculator import calculate_stats_from_file


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="PokerTH Tracker - Real-time HUD for PokerTH"
    )
    parser.add_argument(
        "--analyze",
        type=str,
        metavar="FILE",
        help="Analyze a log file and display stats"
    )

    args = parser.parse_args()

    # Mode analyse seule
    if args.analyze:
        analyze_log(args.analyze)
        return 0

    # Mode GUI
    app = QApplication(sys.argv)
    app.setApplicationName("PokerTH Tracker")
    app.setOrganizationName("PTHTracker")

    # Style global
    app.setStyle("Fusion")

   
    # Mode normal - fenêtre principale
    window = MainWindow()
    window.show()

    return app.exec()


def analyze_log(log_path: str) -> None:
    """Analyze a log file and display stats."""
    path = Path(log_path)
    if not path.exists():
        print(f"Error: File not found: {log_path}")
        sys.exit(1)

    print(f"Analyzing: {path.name}")
    print("-" * 60)

    try:
        stats = calculate_stats_from_file(path)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not stats:
        print("No data found.")
        return

    # Sort by number of hands
    sorted_stats = sorted(
        stats.values(),
        key=lambda s: s.total_hands,
        reverse=True
    )

    # Display the table
    print(f"{'Player':<20} {'VPIP':>7} {'PFR':>7} {'AF':>7} {'Hands':>7}")
    print("-" * 60)

    for player_stats in sorted_stats:
        vpip = f"{player_stats.vpip:.1f}%"
        pfr = f"{player_stats.pfr:.1f}%"
        af = f"{player_stats.af:.1f}" if player_stats.af != float('inf') else "inf"

        print(
            f"{player_stats.player_name:<20} "
            f"{vpip:>7} "
            f"{pfr:>7} "
            f"{af:>7} "
            f"{player_stats.total_hands:>7}"
        )

    print("-" * 60)
    print(f"Total: {len(stats)} players")


if __name__ == "__main__":
    sys.exit(main())
