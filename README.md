# pokerth-tracker

A PokerTH Tracker

## Installation

### Prerequisites

- Python 3.10+
- pip
- xcb

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

## Usage

1. Activate the virtual environment (if not already active):
```bash
source venv/bin/activate
```

2. Run the application:
```bash
python main.py
```

## Troubleshooting
If you get a Core Dump at launch, install xcb dependencies. 
On Ubuntu/Debian :
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