# PokerTH Tracker

A HUD (Heads-Up Display) and statistics system for [PokerTH](https://www.pokerth.net/). It analyses PokerTH log files in real time and displays each player's statistics directly on screen during a game.

---

## Features

- Real-time tracking of played hands
- HUD overlay on the PokerTH window with per-player stats
- Historical import of all past games
- Range visualisation (grid of hands shown at showdown)
- SQLite database to persist stats between sessions

---

## Installation

### Prerequisites

- Python 3.10+
- pip
- libxcb (Linux)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/MCNCHEESYF/pokerth-tracker.git
cd pokerth-tracker
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
source venv/bin/activate
```

4. Install dependencies:
```bash
pip install -r requirements.txt
```

### Run the application

```bash
source venv/bin/activate
python main.py
```

### Troubleshooting

If you get a Core Dump on launch, install the libxcb dependencies.

On Ubuntu/Debian:
```bash
sudo apt install -y \
  libxcb-cursor0 \
  libxkbcommon-x11-0 \
  libxcb-xinerama0 \
  libxcb-render0 \
  libxcb-shape0 \
  libxcb-randr0 \
  libxcb-icccm4 \
  libxcb-keysyms1 \
  libxcb-image0 \
  libxcb-util1
```

On Fedora/RHEL:
```bash
sudo dnf install -y \
  xcb-util-cursor \
  libxkbcommon-x11 \
  xcb-util-image \
  xcb-util-keysyms \
  xcb-util-wm
```

---

## Interface

### Main window

#### Log folder
At the top of the window, the application shows the folder it reads PokerTH logs from.
- **Browse…** — Opens a folder picker to change the log path. Default: `~/.pokerth/log`.

#### Main buttons

| Button | Description |
|--------|-------------|
| **Start tracking** / **Stop tracking** | Starts or stops real-time monitoring of the active log file. The label toggles between both states. Disabled during an import. |
| **Show HUD** / **Hide HUD** | Shows or hides the overlay HUD. Available only when tracking is active and stats are present. |
| **Show Range** / **Hide Range** | Opens or closes the range window for the player selected in the table. Available only when a player is selected. |
| **Import** | Imports all `.pdb` files from the log folder (incremental: only new or modified files are processed). Disabled during tracking. |

#### Statistics table

Displays stats for all known players. Click a column header to sort. Sorted by number of hands (descending) by default.

| Column | Meaning |
|--------|---------|
| **Player** | Player username |
| **VPIP%** | % of hands where the player voluntarily put money in preflop |
| **PFR%** | % of hands where the player raised preflop |
| **AF** | Aggression factor (bets+raises / calls) |
| **3-Bet%** | % of 3-bets when the opportunity arises |
| **C-Bet%** | % of continuation bets after being the preflop aggressor |
| **F3B%** | % of times the player folds to a 3-bet |
| **FCB%** | % of times the player folds to a C-Bet |
| **WTSD%** | % of hands that go to showdown (among hands that see the flop) |
| **W$SD%** | % of showdowns won |
| **Hands** | Total number of recorded hands |

---

### Menu

#### File
- **Import history…** — Same action as the Import button.
- **Clear stats** — Deletes all statistics from the database (confirmation required).
- **Quit** *(Ctrl+Q)* — Closes the application cleanly.

#### Options
- **Configure HUD…** — Opens the HUD configuration dialog.

#### Help
- **About** — Displays the version and feature list.

---

### HUD overlay

Once tracking is active and the HUD is shown, each player at the current table gets a small floating panel on top of the PokerTH window.

- **Move** a panel: left-click and drag.
- **G / U button** (on each panel): toggles between *Grouped* mode (all panels move together) and *Individual* mode.
- **Right-click** on a panel: context menu with the **Reset positions** option to snap all panels back into a horizontal line.

The stats shown in the HUD are those configured in *Options > Configure HUD…*.

---

### HUD configuration

Accessible via *Options > Configure HUD…*

- **Checkboxes**: select which statistics to display from the 10 available.
- **Reset**: restores the default selection (VPIP, PFR, AF, Hands).
- **Cancel**: discards changes.
- **Save**: saves and closes the dialog.

Stats are automatically arranged in rows of 2 inside the HUD.

---

### Range window

Accessible by selecting a player in the table and clicking **Show Range**.

Displays a 13×13 grid representing the hands shown at showdown by that player.

- **Diagonal**: pairs (AA, KK, QQ…)
- **Top-right triangle**: suited hands (AKs, KQs…)
- **Bottom-left triangle**: offsuit hands (AKo, KQo…)
- **Colour gradient**: green (frequent) → yellow → red (rare) → grey (never seen)

#### Available filters
- **Position**: filters hands by the player's position (BTN, SB, BB, UTG, CO…).
- **Number of players**: filters by table size at the time of the hand.
- A counter shows the number of hands matching the active filters.

---

## Data

- **Database**: `~/.pokerth_tracker/stats.db` (SQLite)
- **PokerTH logs**: `~/.pokerth/log` (default)

Stats from the current session and imported historical data are combined automatically to avoid duplicates.
