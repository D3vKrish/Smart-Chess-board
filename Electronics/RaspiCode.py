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
import whisper
import sounddevice as sd
import numpy as np
import re
import pygame
#os.environ["OMP_NUM_THREADS"] = "1"

# Communication setup
SERIAL_PORT = "/dev/ttyUSB0"   # or /dev/ttyUSB0 for raspberry pi 0
#SERIAL_PORT = "COM7"
BAUDRATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
ser.flush()

# Chessboard setup
board = chess.Board()
engine_path = r"/home/pi/chessBoard/stockfish-android-armv8"  
#engine_path = r"C:\Users\Krish Garg\stockfish\stockfish-windows-x86-64-avx2.exe"  # Windows path for testing on PC
engine = chess.engine.SimpleEngine.popen_uci(engine_path)
print("Loading Whisper (tiny.en)...")
model = whisper.load_model("tiny.en")  #Using tiny model for faster processing on raspi
SAMPLERATE = 16000
DURATION = 3  # seconds to listen
#print(sd.query_devices())
#sd.default.device = 1  # change to your USB mic index
mic_enabled = False

#Setting up pygame
pygame.init()
WIDTH = HEIGHT = 640
SQ_SIZE = WIDTH // 8
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Voice Chess Board")

# Functions
#Function to print the board
# def print_board():
#     """Print the current board in ASCII."""
#     print("\n" + board.unicode(borders=True) + "\n")

def draw_board():
    colors = [pygame.Color("white"), pygame.Color("gray")]
    for r in range(8):
        for c in range(8):
            color = colors[(r+c) % 2]
            pygame.draw.rect(SCREEN, color, pygame.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            r = 7 - (square // 8)
            c = square % 8
            color = 'w' if piece.color else 'b'
            key = color + piece.symbol().lower()
            img = IMAGES[key]
            SCREEN.blit(img, pygame.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

#Check move type: Capture, Promotion, or Normal
def check_move_type(board, move_uci):
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        return None
    if board.is_capture(move):
        return "c"

    piece = board.piece_at(move.from_square)
    if (piece and piece.piece_type == chess.PAWN
        and piece.color == chess.WHITE
        and chess.square_rank(move.to_square) == 7):
        return "p"
    return "m"
#Get all possible legal moves from a square
#TODO: Will implement later once rest of code is properly tested
def get_legal_moves_from_square(board, square_name):
    try:
        square = chess.parse_square(square_name)
    except ValueError:
        return []

    if board.piece_at(square) is None:
        return []

    return [
        move.uci()
        for move in board.legal_moves
        if move.from_square == square
    ]

def parse_move(text):
    text = text.lower()

    replacements = {
        "for": "4", "four": "4",
        "to": "2", "too": "2", "two": "2",
        "one": "1", "won": "1",
        "free": "3", "three": "3",
        "sea": "c", "see": "c",
        "bee": "b", "be ": "b ",
        "dee": "d",
        "gee": "g"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    coords = re.findall(r"[a-h][1-8]", text)

    if len(coords) == 2:
        return coords[0], coords[1]

    return None, None


def listen_and_interpret():
    print("\nSpeak command (move / hint / new game)...")

    input("Press ENTER and speak...") # TODO: Change to button press on raspi
    audio = sd.rec(int(SAMPLERATE * DURATION), samplerate=SAMPLERATE, channels=1)
    sd.wait()

    audio = np.squeeze(audio)
    result = model.transcribe(audio, language="en")
    text = result["text"].strip().lower()

    print(f"Heard: {text}")

    # --- COMMAND DETECTION ---
    if "new game" in text or "restart" in text:
        return "n"

    if "hint" in text or "help" in text:
        return "h"
    
    if "abort" in text or "stop" in text:
        return "a"
    
    if "quit" in text or "exit" in text:
        return "q"

    # --- MOVE DETECTION ---
    src, dst = parse_move(text)
    if src and dst:
        return f"m{src}{dst}"

    print("Could not understand command")
    return ""

#Send data to Arduino
def sendtoboard(msg):
    print("-> Arduino:", msg)
    ser.write(f"heyArduino {msg}\n".encode())
    time.sleep(0.1)

#Receive data from Arduino
def getboard():
    print("Waiting for Arduino...")
    start = time.time()
    while time.time() - start < 30:
        if ser.in_waiting:
            msg = ser.readline().decode().strip().lower()
            if msg.lower().startswith("heypi"):
                msg = msg[len("heypi"):].strip()
                print(f"Arduino: {msg}")
                return msg
        time.sleep(0.01)
    raise TimeoutError("No response from Arduino")

#Print on OLED screen
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
    #sendToScreen("NEW", "GAME", "", "30")
    time.sleep(1)
    #sendToScreen("Please enter", "your move")
    print_board()
    return ""

def get_engine_move(movetime_ms):
    limit = chess.engine.Limit(time=movetime_ms / 1000)
    result = engine.play(board, limit)
    move = result.move.uci()
    return move

def get_hint():
    limit = chess.engine.Limit(time=0.5)
    info_list = engine.analyse(board, limit, multipv = 1)  #TODO: Check if multipv is supported on raspi
    info = info_list[0] if isinstance(info_list, list) else info_list
    pv = info.get("pv")
    hint = pv[0].uci() if pv else "----"
    return hint

def wait_for_ok():
    while True:
        if ser.in_waiting:
            msg = ser.readline().decode(errors="ignore").strip().lower()
            if msg.startswith("heypi"):
                payload = msg[len("heypi"):].strip()
                print("Arduino:", payload)
                if payload == "ok":
                    break

#Confirm player's move
def bmove(fmove, bmessage, movetime):
    try:
        move_uci = bmessage[1:5]
        user_move = chess.Move.from_uci(move_uci)
        if user_move not in board.legal_moves:
            raise ValueError
        move_type = check_move_type(board, user_move.uci())
        sendtoboard(f"{move_type}{user_move}")
        if(move_type == "p"):
            promo = getboard().strip().lower()
            promo_map = {"a":"q", "b":"r", "c":"b", "d":"n"}
            move_uci += promo_map.get(promo, "q")
            user_move = chess.Move.from_uci(move_uci)
            if user_move not in board.legal_moves:
                raise ValueError
        wait_for_ok()
        board.push(user_move)
        print_board()

    except Exception:
        #sendToScreen("Illegal move!", "Try again")
        sendtoboard("Illegal Move")
        return "RETRY"
    
    if board.is_game_over():
        #sendToScreen("Game Over", board.result())
        sendtoboard("gameover")
        return "GAMEOVER"

    '''sendToScreen(
        user_move.uci()[:2] + "->" + user_move.uci()[2:],
        "",
        "Thinking..."
    )'''

    engine_move = get_engine_move(movetime)

    engine_move_obj = chess.Move.from_uci(engine_move)
    board.push(engine_move_obj)
    print_board()
   # if board.is_game_over():
        #sendToScreen("Game Over", board.result())


    '''sendToScreen(
        engine_move[:2] + "->" + engine_move[2:],
        "",
        "Your go..."
    )'''

    sendtoboard(f"m{engine_move}")
    wait_for_ok()
    return fmove + " " + user_move.uci() + " " + engine_move

# Main gameplay loop
time.sleep(1)
try:
    while True:
        sendtoboard("READY")
        while True:
            if getboard().lower() == "startgame":
                break
            time.sleep(0.05)
        sendtoboard("CHOICE")
        choice = getboard().strip().lower()
        if choice.lower() == "y":
            mic_enabled = True
        else:
            mic_enabled = False
        #sendToScreen("Choose computer", "difficulty level", "(0 -> 20)")
       
        # try:
        #     skill = getboard()
        # except ValueError:
        #     skill = 10
        # engine.configure({"Skill Level": int(skill)})
        # #sendToScreen("Choose computer", "move time", "(100 – 2000ms)")
        # try:
        #     movetime = 2000 - int(skill)
        # except ValueError:
        #     movetime = 500

        #TODO: Fixded for now, make it dynamic later, same with skill level
        engine.configure({"Skill Level": 10})
        movetime = 500
        fmove = newgame()

        while True:
            sendtoboard("GET") 
            if (mic_enabled):
                bmessage = listen_and_interpret()  # --> For voice command input
            else:
                bmessage = getboard()  #--> For arduino communication
            if not bmessage:
                continue
            code = bmessage[0]

            if code == "m":
                fmove = bmove(fmove, bmessage, movetime)
                if fmove == "GAMEOVER":
                    break
                if fmove == "RETRY":
                    continue
            elif code == "n":
                fmove = newgame()
                break

            elif code == "h":
                if board.turn == chess.WHITE:
                    if engine.ping():
                        hint = get_hint()
                        #sendToScreen("Hint:", hint)
                else:
                    pass
                    #sendToScreen("Wait for", "your turn")
            elif code == "a":
                #sendToScreen("Game Aborted")
                board.reset()
                continue
            elif code == "q":
                #sendToScreen("Quitting", "Goodbye!")
                if engine and engine.is_alive():
                    engine.quit()
                ser.close()
                exit(0)
            else:
                sendtoboard("error")
except KeyboardInterrupt:
    print("Exiting...")
    if engine and engine.is_alive():
        engine.quit()
    ser.close()
