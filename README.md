# Automated Voice-Controlled Chess Board

A Raspberry Pi–powered smart chessboard that lets players speak their moves aloud.
The system interprets voice commands using **OpenAI Whisper**, validates moves with **Stockfish**, and renders the game visually using **Pygame**. Mouse-based input is also fully supported.

---

## Overview

This project combines three core capabilities:

- **Speech recognition** via OpenAI Whisper
- **Chess engine integration** via Stockfish
- **Graphical game simulation** via Pygame

Together, they enable a hands-free chess experience with full rule validation and AI gameplay — including physical piece movement via a gantry-based Arduino system.

---

## Features

- Voice-controlled move input using Whisper AI
- Mouse-controlled move input via Pygame GUI
- Real-time graphical chessboard display
- Stockfish AI opponent
- Move validation using `python-chess`
- Dual-serial Arduino communication
- Physical piece movement support (gantry-based)
- Move-type detection (normal, capture, castling, promotion, en passant)

---

## System Requirements

### Software

- Python 3.8 or higher
- Raspberry Pi / Linux / Windows
- Microphone (for voice control)

### Hardware

- Raspberry Pi or PC
- Arduino (×2)
- Stepper motor drivers
- Servo motors

---

## Installation

### Python Dependencies
```bash
pip3 install pyserial chess pygame openai-whisper sounddevice numpy scipy torch
```

### Stockfish
```bash
sudo apt update
sudo apt install -y stockfish
```

Verify the installation:
```bash
which stockfish
```

Expected output:
```
/usr/games/stockfish
```

---

## Hardware Architecture

The system uses two serial connections:

| Device | Purpose |
|--------|---------|
| `/dev/ttyUSB0` | Movement Arduino (motor control) |
| `/dev/ttyACM0` | Keypad / Input Arduino |

### Communication Protocol

All messages follow a simple handshake protocol:
```
Raspberry Pi → Arduino:  heyArduino <command>
Arduino → Raspberry Pi:  heypi <response>
```

The system waits for a `heypi ok` confirmation after each physical move before proceeding.

### Arduino Command Codes

| Code | Meaning |
|------|---------|
| `m` | Normal move |
| `c` | Capture |
| `a` | Castling |
| `e` | En passant |
| `p` | Promotion |
| `n` | New game |
| `h` | Hint |
| `b` | Abort |
| `q` | Quit |

### Example Command
```
heyArduino m e2e4 d4
```

| Part | Meaning |
|------|---------|
| `m` | Move type (normal) |
| `e2e4` | UCI move notation |
| `d4` | Home reference square |

---

## Assets

Create an `images/` folder in the project root containing the following piece image files:

| File | Description |
|------|-------------|
| `wp.png` | White Pawn |
| `bp.png` | Black Pawn |
| `wn.png` | White Knight |
| `bn.png` | Black Knight |
| `wb.png` | White Bishop |
| `bb.png` | Black Bishop |
| `wr.png` | White Rook |
| `br.png` | Black Rook |
| `wq.png` | White Queen |
| `bq.png` | Black Queen |
| `wk.png` | White King |
| `bk.png` | Black King |

---

## Running the Application
```bash
python3 RaspiCode.py
```

## Testing motor movement and callibration

To callibrate the lenght of a step and direction of motor movement, upload keyControlArduino file to motor arduino and then run the keyControlPython file after updating the port on which the arduino is connected. This helps set the distance moved during 1 step and get an idea of board dimensions.
```bash
python3 keyControlPython.py
```

---

## Usage

### Voice Commands

Speak moves in natural language, for example:
```
pawn e2 to e4
knight g1 to f3
bishop c4 to f7
```

### Mouse Control

1. Click a piece to select it
2. Click a destination square to move

Illegal moves are automatically rejected. Valid moves are executed and passed to the AI opponent.

---

## Physical Board Workflow
```
1. Player inputs move (voice or mouse)
        ↓
2. Move validated using python-chess
        ↓
3. Move command sent to Arduino
        ↓
4. Gantry moves piece physically
        ↓
5. Arduino sends confirmation: heypi ok
        ↓
6. Stockfish calculates AI response
        ↓
7. AI move executed physically
```

---
