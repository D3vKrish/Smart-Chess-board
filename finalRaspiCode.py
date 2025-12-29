'''
Arduino codes: m --> Move, h --> Hint, n --> New Game, a --> Abort Game, q --> Quit Game
Default bot level: 10
Default bot move time: 500ms
'''
import time
import serial
import subprocess
import chess
import chess.engine

# Communication setup
SERIAL_PORT = "/dev/ttyAMA0"   # or /dev/ttyUSB0 for raspberry pi 0
BAUDRATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
ser.flush()

# Chessboard setup
board = chess.Board()
engine = chess.engine.SimpleEngine.popen_uci("stockfish")

# Functions
def sendtoboard(msg):
    print("-> Arduino:", msg)
    ser.write(f"heyArduino{msg}\n".encode())
    time.sleep(0.1)

def getboard():
    print("Waiting for Arduino...")
    while True:
        if ser.in_waiting:
            msg = ser.readline().decode().strip().lower()
            if msg.startswith("heypi"):
                msg = msg[len("heypi"):].strip() #message recieved is of foramte heypi <message>
                print("<- Arduino:", msg)
                return msg

def sendToScreen(l1, l2="", l3="", size="14"):
    subprocess.Popen([
        "python3",
        "/home/pi/SmartChess/RaspberryPiCode/printToOLED.py",
        "-a", l1, "-b", l2, "-c", l3, "-s", size
    ])

# Game logic functions
def newgame():
    global board
    board.reset()
    sendToScreen("NEW", "GAME", "", "30")
    time.sleep(1)
    sendToScreen("Please enter", "your move")
    return ""

def get_engine_move(movetime_ms):
    limit = chess.engine.Limit(time=movetime_ms / 1000)
    result = engine.play(board, limit)
    move = result.move.uci()
    return move

def get_hint():
    limit = chess.engine.Limit(time=0.5)
    info_list = engine.analyse(board, limit, multipv = 1)
    info = info_list[0] if isinstance(info_list, list) else info_list
    pv = info.get("pv")
    hint = pv[0].uci() if pv else "----"
    return hint

def bmove(fmove, bmessage, movetime):
    try:
        user_move = chess.Move.from_uci(bmessage[1:5])
        if user_move not in board.legal_moves:
            raise ValueError
        board.push(user_move)
    except Exception:
        sendToScreen("Illegal move!", "Try again")
        sendtoboard("error")
        return fmove
    
    if board.is_game_over():
        sendToScreen("Game Over", board.result())
        sendtoboard("gameover")
        return "GAMEOVER"

    sendToScreen(
        user_move.uci()[:2] + "->" + user_move.uci()[2:],
        "",
        "Thinking..."
    )

    engine_move = get_engine_move(movetime)

    engine_move_obj = chess.Move.from_uci(engine_move)
    board.push(engine_move_obj)
    if board.is_game_over():
        sendToScreen("Game Over", board.result())


    sendToScreen(
        engine_move[:2] + "->" + engine_move[2:],
        "",
        "Your go..."
    )

    sendtoboard(f"m{engine_move}")

    return fmove + " " + user_move.uci() + " " + engine_move

# Main gameplay loop
time.sleep(1)
sendtoboard("Against PC")

while True:
    sendtoboard("ReadyStockfish")

    sendToScreen("Choose computer", "difficulty level", "(0 -> 20)")
    try:
        skill = int(getboard())
    except ValueError:
        skill = 10
    engine.configure({"Skill Level": int(skill)})
    sendToScreen("Choose computer", "move time", "(100 – 2000ms)")
    try:
        movetime = int(getboard())
        movetime = max(100, min(2000, movetime))
    except ValueError:
        movetime = 500

    fmove = newgame()

    while True:
        bmessage = getboard()
        if not bmessage:
            continue
        code = bmessage[0]

        if code == "m":
            fmove = bmove(fmove, bmessage, movetime)
            if fmove == "GAMEOVER":
                break

        elif code == "n":
            fmove = newgame()

        elif code == "h":
            if board.turn == chess.WHITE:
                if engine.is_alive():
                    hint = get_hint()
                    sendToScreen("Hint:", hint)
            else:
                sendToScreen("Wait for", "your turn")
        elif code == "a":
            sendToScreen("Game Aborted")
            board.reset()
            continue
        elif code == "q":
            sendToScreen("Quitting", "Goodbye!")
            engine.quit()
            ser.close()
            exit(0)
        else:
            sendtoboard("error")
