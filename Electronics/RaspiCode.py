'''
Arduino codes: m --> Move, h --> Hint, n --> New Game, a --> Abort Game, q --> Quit Game
Default bot level: 10
Default bot move time: 500ms
'''
import time
import serial
import chess
import chess.engine
import whisper
import sounddevice as sd
import numpy as np
import re
import pygame
#os.environ["OMP_NUM_THREADS"] = "1"

# Communication setup
SERIAL_PORT = "COM7" 
SERIAL_PORT_2 = "COM14"
BAUDRATE = 9600

movSer = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
keySer = serial.Serial(SERIAL_PORT_2, BAUDRATE, timeout=1)

movSer.flush()
keySer.flush()

# Chessboard setup
board = chess.Board()
#engine_path = "/usr/games/stockfish"
##engine_path = r"/home/pi/chessBoard/stockfish-android-armv8"  
engine_path = r"C:\Users\Krish Garg\stockfish\stockfish-windows-x86-64-avx2.exe"  # Windows path for testing on PC
engine = chess.engine.SimpleEngine.popen_uci(engine_path)
print("Loading Whisper (small.en)...")
model = whisper.load_model("tiny.en")  #Using tiny model for faster processing on raspi
SAMPLERATE = 16000
DURATION = 3  # seconds to listen
#print(sd.query_devices())
#sd.default.device = 1  # change to your USB mic index
mic_enabled = False

#Setting up pygame

pygame.init()
BOARD_SIZE = 800
LABEL_MARGIN = 40
WIDTH = HEIGHT = BOARD_SIZE + LABEL_MARGIN
SQ_SIZE = BOARD_SIZE // 8
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Voice Chess Board")
BOARD_X = LABEL_MARGIN
BOARD_Y = 0
FONT = pygame.font.SysFont("arial", 40)
LABEL_COLOR = pygame.Color("white")

# Load piece images
IMAGES = {}
pieces = ["wp","bp","wn","bn","wb","bb","wr","br","wq","bq","wk","bk"]
for piece in pieces:
    IMAGES[piece] = pygame.transform.scale(
        pygame.image.load(f'images/{piece}.png'), 
        (SQ_SIZE,SQ_SIZE)
    )

# Pygame Functions
def draw_board():
    colors = [pygame.Color("white"), pygame.Color("gray")]
    for r in range(8):
        for c in range(8):
            color = colors[(r + c) % 2]
            pygame.draw.rect(
                SCREEN,
                color,
                pygame.Rect(
                    BOARD_X + c * SQ_SIZE,
                    BOARD_Y + r * SQ_SIZE,
                    SQ_SIZE,
                    SQ_SIZE
                )
            )

def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            rank = chess.square_rank(square)
            file = chess.square_file(square)
            r = 7 - rank
            c = file
            color = 'w' if piece.color else 'b'
            key = color + piece.symbol().lower()
            img = IMAGES[key]
            SCREEN.blit(
                img,
                pygame.Rect(
                    BOARD_X + c * SQ_SIZE,
                    BOARD_Y + r * SQ_SIZE,
                    SQ_SIZE,
                    SQ_SIZE
                )
            )

def draw_file_labels():
    files = "abcdefgh"
    for i, f in enumerate(files):
        label = FONT.render(f, True, LABEL_COLOR)
        x = BOARD_X + i * SQ_SIZE + SQ_SIZE // 2 - label.get_width() // 2
        y = BOARD_SIZE + 5
        SCREEN.blit(label, (x, y))
        
def draw_rank_labels():
    for i in range(8):
        rank = str(8 - i)
        label = FONT.render(rank, True, LABEL_COLOR)
        x = 10
        y = BOARD_Y + i * SQ_SIZE + SQ_SIZE // 2 - label.get_height() // 2
        SCREEN.blit(label, (x, y))
        
def redraw():
    draw_board()
    draw_pieces()
    draw_file_labels()
    draw_rank_labels()
    pygame.display.flip()
        
#Movement functions
#Check move type: Capture, Promotion, or Normal
def check_move_type(board, move_uci):
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        return None
    if board.is_capture(move):
        return "c"
    if board.is_castling(move):
        return "a"
    if board.is_en_passant(move):
        return "e"
    piece = board.piece_at(move.from_square)
    if (piece and piece.piece_type == chess.PAWN
        and piece.color == chess.WHITE
        and chess.square_rank(move.to_square) == 7):
        return "p"
    elif (piece and piece.piece_type == chess.PAWN
        and piece.color == chess.BLACK
        and chess.square_rank(move.to_square) == 0):
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

#Send data to Arduino
def sendtoboard(arduino, msg):
    print(f"-> Arduino:", msg)
    arduino.write(f"heyArduino {msg}\n".encode())
    time.sleep(0.1)
    
#Receive data from Arduino
def getboard(arduino):
    print("Waiting for Arduino...")
    start = time.time()
    while time.time() - start < 30:
        if arduino.in_waiting:
            msg = arduino.readline().decode().strip().lower()
            if msg.lower().startswith("heypi"):
                msg = msg.split("heypi",1)[1].strip()
                print(f"Arduino: {msg}")
                return msg
        time.sleep(0.01)
    raise TimeoutError("No response from Arduino")

#Voice command functions
def record_audio(duration, samplerate=16000):
    audio = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        audio.append(indata.copy())

    with sd.InputStream(
        samplerate=samplerate,
        channels=1,
        dtype="float32",
        callback=callback
    ):
        sd.sleep(int(duration * 1000))

    audio = np.concatenate(audio, axis=0)
    return audio.squeeze()

def listen_and_interpret():
    print("\nSpeak command (move / hint / new game)...")

    #input("Press ENTER and speak...")
    sendtoboard(keySer, "CHOICE")
    while True:
        choice = getboard(keySer).strip().lower()
        if choice.lower() == "y":
            break
        else:
            return "keypad"
    audio = record_audio(DURATION, SAMPLERATE)
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
    
# Game logic functions
def newgame():
    global board
    board.reset()
    time.sleep(1)
    redraw()
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

def wait_for_ok(arduino, timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        if arduino.in_waiting:
            msg = arduino.readline().decode(errors="ignore").strip().lower()
            if "heypi" in msg and "ok" in msg:
                return
        pygame.event.pump()
        time.sleep(0.01)
    raise TimeoutError("Arduino did not respond with OK")

                    

#Confirm player's move
def bmove(fmove, bmessage, movetime):
    try:
        move_uci = bmessage[1:5]
        user_move = chess.Move.from_uci(move_uci)

        if user_move not in board.legal_moves:
            raise ValueError("Illegal base move")

        move_type = check_move_type(board, user_move.uci())
        # Handle promotion FIRST
        if move_type == "p":
            promo = getboard(keySer).strip().lower()
            promo_map = {"a":"q", "b":"r", "c":"b", "d":"n"}
            move_uci += promo_map.get(promo, "q")
            user_move = chess.Move.from_uci(move_uci)

            if user_move not in board.legal_moves:
                raise ValueError("Illegal promotion")

        #Send to board after all moves have been validated
        board.push(user_move)
        redraw()
        sendtoboard(movSer, f"{move_type}{user_move}")
        wait_for_ok(movSer)
        
        

    except Exception as e:
        print("Move error:", e)
        sendtoboard(movSer, "Illegal Move")
        return "RETRY"
        
    if board.is_game_over():
        sendtoboard(movSer, "gameover")
        return "GAMEOVER"

    engine_move = get_engine_move(movetime)
    engine_move_obj = chess.Move.from_uci(engine_move)
    board.push(engine_move_obj)
    redraw()
    sendtoboard(movSer,f"m{engine_move}")
    wait_for_ok(movSer)
    return fmove + " " + user_move.uci() + " " + engine_move

# Main gameplay loop
time.sleep(1)
try:
    while True:
        sendtoboard(movSer, "READY")
        while True:
            pygame.event.pump()
            if getboard(movSer).lower() == "startgame":
                break
            time.sleep(0.05)
        sendtoboard(keySer, "READY")
        while True:
            pygame.event.pump()
            if getboard(keySer).lower() == "startgame":
                break
            time.sleep(0.05)
        sendtoboard(keySer, "CHOICE")
        choice = getboard(keySer).strip().lower()
        if choice.lower() == "y":
            mic_enabled = True
        else:
            mic_enabled = False
        
        #TODO: Fixded for now, make it dynamic later, same with skill level
        engine.configure({"Skill Level": 10})
        movetime = 500
        fmove = newgame()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if engine and engine.is_alive():
                        engine.quit()
                    movSer.close()
                    keySer.close()
                    pygame.quit()
                    exit(0)
            sendtoboard(keySer, "GET") 
            if (mic_enabled):
                bmessage = listen_and_interpret()  # --> For voice command input
                if bmessage == "keypad":
                    bmessage = getboard(keySer) 
            else:
                bmessage = getboard(keySer)  #--> For arduino communication
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
                    engine.ping()
                    hint = get_hint()
                else:
                    pass
            elif code == "a":
                board.reset()
                continue
            elif code == "q":
                if engine and engine.is_alive():
                    engine.quit()
                movSer.close()
                exit(0)
            else:
                sendtoboard(movSer, "error")
except KeyboardInterrupt:
    print("Exiting...")
    if engine and engine.is_alive():
        engine.quit()
    movSer.close()
    keySer.close()
