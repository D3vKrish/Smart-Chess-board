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
from scipy.signal import resample
import sounddevice as sd
import numpy as np
import re
import pygame
import subprocess


# Communication setup
#SERIAL_PORT = "COM13" 
#SERIAL_PORT_2 = "COM14"
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_PORT_2 = "/dev/ttyACM0"
BAUDRATE = 9600

movSer = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
keySer = serial.Serial(SERIAL_PORT_2, BAUDRATE, timeout=1)

movSer.flush()
keySer.flush()

# Chessboard setup
board = chess.Board()
engine_path = "/usr/games/stockfish"
##engine_path = r"/home/pi/chessBoard/stockfish-android-armv8"  
#engine_path = r"C:\Users\Krish Garg\stockfish\stockfish-windows-x86-64-avx2.exe"  
engine = chess.engine.SimpleEngine.popen_uci(engine_path)
print("Loading Whisper (tiny.en)...")
model = whisper.load_model("tiny.en") 
print("Whisper ready.")
SAMPLERATE = 44100
timeout_time = 45
DURATION = 3 
mic_enabled = False
mouse_enabled = False

#Setting up pygame
pygame.init()
TIMER_UPDATE = pygame.USEREVENT + 1
pygame.time.set_timer(TIMER_UPDATE, 1000)
BOARD_SIZE = 600
LABEL_MARGIN = 40
WIDTH = BOARD_SIZE + LABEL_MARGIN
HEIGHT = BOARD_SIZE + 2*LABEL_MARGIN
SQ_SIZE = BOARD_SIZE // 8
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Auto Chess Board")
print("Caption set to:", pygame.display.get_caption())
BOARD_X = LABEL_MARGIN
BOARD_Y = LABEL_MARGIN
FONT = pygame.font.SysFont("arial", 30)
LABEL_COLOR = pygame.Color("white")

#Setting up timer
clock = pygame.time.Clock()
fps = 60
white_time = 6000  
white_time_left = white_time
white_timer_running = False
start_time = pygame.time.get_ticks()

# Load piece images
IMAGES = {}
pieces = ["wp","bp","wn","bn","wb","bb","wr","br","wq","bq","wk","bk"]
for piece in pieces:
    IMAGES[piece] = pygame.transform.scale(
        pygame.image.load(f'images/{piece}.png'), 
        (SQ_SIZE,SQ_SIZE)
    )

# Pygame Functions
game_start_ticks = None
GAME_DURATION_MS = 20 * 60 * 1000 

def start_timer():
    global game_start_ticks
    game_start_ticks = pygame.time.get_ticks()

def draw_timer():
    if game_start_ticks is None:
        return
    elapsed = pygame.time.get_ticks() - game_start_ticks
    remaining = max(0, GAME_DURATION_MS - elapsed)
    mins = remaining // 60000
    secs = (remaining % 60000) // 1000
    color = pygame.Color("red") if remaining < 30000 else LABEL_COLOR 
    timer_text = FONT.render(f"{mins:02d}:{secs:02d}", True, color)
    if(remaining <= 0):
        timer_text = FONT.render("Time over", True, color)
        SCREEN.blit(timer_text, (BOARD_X + BOARD_SIZE - timer_text.get_width(), 
                              LABEL_MARGIN // 2 - timer_text.get_height() // 2))
        time.sleep(5)
        exit(0)
    else:
        SCREEN.blit(timer_text, (BOARD_X + BOARD_SIZE - timer_text.get_width(), 
                              LABEL_MARGIN // 2 - timer_text.get_height() // 2))
    
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
        y = BOARD_Y + BOARD_SIZE + 5
        SCREEN.blit(label, (x, y))
           
def draw_rank_labels():
    for i in range(8):
        rank = str(8 - i)
        label = FONT.render(rank, True, LABEL_COLOR)
        x = 10
        y = BOARD_Y + i * SQ_SIZE + SQ_SIZE // 2 - label.get_height() // 2
        SCREEN.blit(label, (x, y))
        
def redraw():
    SCREEN.fill((0, 0, 0))  
    title = FONT.render("Auto Chess Board", True, LABEL_COLOR)
    SCREEN.blit(title, (BOARD_X + BOARD_SIZE // 2 - title.get_width() // 2, LABEL_MARGIN // 2 - title.get_height() // 2))
    draw_timer()
    draw_board()
    draw_pieces()
    draw_file_labels()
    draw_rank_labels()
    pygame.display.flip()

SCREEN.fill((0,0,0))
redraw()
time.sleep(1)
#Movement functions
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
    
def parse_move(text):
    text = text.lower()

    replacements = {
        "for": "4", "four": "4",
        "to": "2", "too": "2", "two": "2",
        "one": "1", "won": "1",
        "free": "3", "three": "3",
        "sea": "c", "see": "c",
        "bee": "b", "be ": "b ", "p":"b",
        "dee": "d",
        "dee": "d",
        "x":"e",
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
    while time.time() - start < 600:
        if arduino.in_waiting:
            msg = arduino.readline().decode().strip().lower()
            if msg.lower().startswith("heypi"):
                msg = msg.split("heypi",1)[1].strip()
                print(f"Arduino: {msg}")
                return msg
        for event in pygame.event.get():
            if event.type == TIMER_UPDATE:
                redraw()
        time.sleep(0.01)
    raise TimeoutError("No response from Arduino")

#Voice command functions
def record_audio(duration, samplerate=44100):
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

    audio = np.concatenate(audio, axis=0).squeeze()

    target_rate = 16000
    num_samples = int(len(audio) * target_rate / samplerate)
    audio_16k = resample(audio, num_samples)

    return audio_16k

def listen_and_interpret():
    print("\nSpeak command (move / hint / new game)...")
    sendtoboard(keySer, "CHOICE")
    while True:
        choice = getboard(keySer).strip().lower()
        if choice.lower() == "y":
            break
        else:
            return "mouse"
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
    
selected_square = None

def draw_highlight(square, color):
    r = 7 - chess.square_rank(square)
    c = chess.square_file(square)
    highlight = pygame.Surface((SQ_SIZE, SQ_SIZE), pygame.SRCALPHA)
    if color == "green":
        highlight.fill((0, 255, 0, 120))
    else:
        highlight.fill((255, 255, 0, 120))
    SCREEN.blit(highlight, (BOARD_X + c * SQ_SIZE, BOARD_Y + r * SQ_SIZE))

def handle_mouse_click(pos):
    global selected_square
    x, y = pos
    if not (BOARD_X <= x < BOARD_X + BOARD_SIZE and BOARD_Y <= y < BOARD_Y + BOARD_SIZE):
        return None
    col = (x - BOARD_X) // SQ_SIZE
    row = (y - BOARD_Y) // SQ_SIZE
    square = chess.square(col, 7 - row)

    if selected_square is None:
        piece = board.piece_at(square)
        if piece:
            selected_square = square
            draw_board()
            draw_highlight(square, "green")
            draw_pieces()
            draw_file_labels()
            draw_rank_labels()
            pygame.display.flip()
        return None
    else:
        from_sq = selected_square
        to_sq = square
        selected_square = None
        redraw()
        if from_sq == to_sq:
            return None
        move_uci = chess.square_name(from_sq) + chess.square_name(to_sq)
        return f"m{move_uci}"

def get_mouse_move():
    global selected_square
    if board.turn != chess.WHITE:
        return None 
    selected_square = None
    redraw()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if engine:
                    engine.quit()
                movSer.close()
                keySer.close()
                pygame.quit()
                exit(0)
            elif event.type == TIMER_UPDATE:
                redraw()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                result = handle_mouse_click(event.pos)
                if result:
                    return result
        time.sleep(0.02)

# Game logic functions
def newgame():
    global board
    board.reset()
    start_timer()
    time.sleep(1)
    redraw()
    with open("data.txt","w") as f:
        f.write("d4\n")
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
    redraw()
    return hint

def wait_for_ok(arduino, timeout=120):
    start = time.time()
    while time.time() - start < 600:
        if arduino.in_waiting:
            msg = arduino.readline().decode(errors="ignore").strip().lower()
            if "heypi" in msg and "ok" in msg:
                return
        for event in pygame.event.get():
            if event.type == TIMER_UPDATE:
                redraw()
        time.sleep(0.01)
    raise TimeoutError("Arduino did not respond with OK")

                    

#Confirm player's move
def bmove(fmove, bmessage, movetime):
    try:
        if board.is_game_over():
            sendtoboard(movSer, "gameover")
            return "GAMEOVER"
        
        move_uci = bmessage[1:5]
        user_move = chess.Move.from_uci(move_uci)
        piece = board.piece_at(user_move.from_square)
        color = piece.color if piece else None
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
        home = ""
        with open("data.txt") as f:
            lines = f.readlines()
            home = lines[-1].strip()
        if not home:
            home = "d4"
        sendtoboard(movSer, f"{move_type}{user_move}{home}")
        with open("data.txt","a") as f:
            f.write(user_move.uci()[0:2] + "\n")
            f.write(user_move.uci()[2:4] + "\n")
        if move_type == "a":
            if(user_move.uci()[2:4] == "g1"):
                end = "f1"
            elif(user_move.uci()[2:4] == "c1"):
                end = "d1"
            elif(user_move.uci()[2:4] == "g8"):
                end = "f8"
            elif(user_move.uci()[2:4] == "c8"):
                end = "d8"
            with open("data.txt","a") as f:
                f.write(f"{end}\n")
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
    move_type = check_move_type(board, engine_move_obj.uci())
    # Handle promotion FIRST
    if move_type == "p":
            promo = getboard(keySer).strip().lower()
            promo_map = {"a":"q", "b":"r", "c":"b", "d":"n"}
            engine_move += promo_map.get(promo, "q")
            eng_move = chess.Move.from_uci(engine_move)

            if eng_move not in board.legal_moves:
                raise ValueError("Illegal promotion")
    board.push(engine_move_obj)
    redraw()
    home = ""
    with open("data.txt") as f:
            lines = f.readlines()
            home = lines[-1].strip()
    if not home:
        home = "d4"
    sendtoboard(movSer,f"{move_type}{engine_move}{home}")
    with open("data.txt","a") as f:
            f.write(engine_move_obj.uci()[0:2] + "\n")
            f.write(engine_move_obj.uci()[2:4] + "\n")
    if move_type == "a":
        if(engine_move_obj.uci()[2:4] == "g1"):
            end = "f1"
        elif(engine_move_obj.uci()[2:4] == "c1"):
            end = "d1"
        elif(engine_move_obj.uci()[2:4] == "g8"):
            end = "f8"
        elif(engine_move_obj.uci()[2:4] == "c8"):
            end = "d8"
        with open("data.txt","a") as f:
            f.write(f"{end}\n")
    wait_for_ok(movSer)
    return fmove + " " + user_move.uci() + " " + engine_move

# Main gameplay loop
time.sleep(1)
try:
    start = time.time()
    while time.time() - start < 600:
        sendtoboard(movSer, "READY")
        while True:
            if getboard(movSer).lower() == "startgame":
                break
            time.sleep(0.05)
        sendtoboard(keySer, "READY")
        while True:
            if getboard(keySer).lower() == "startgame":
                break
            time.sleep(0.05)
        sendtoboard(keySer, "CHOICE")
        while True:
            choice = getboard(keySer).strip().lower()
            if choice == "m":
                mic_enabled = False
                mouse_enabled = True
                break
            elif choice == "y":
                mic_enabled = True
                mouse_enabled = False
                break
            elif choice == "n":
                mic_enabled = False
                mouse_enabled = False
                break
        
        print("Skill level? (1:Easy; 2:Medium; 3:Hard)")
        sendtoboard(keySer, "CHOICE")
        skillL = 10
        while True:
            choice = getboard(keySer).strip().lower()
            if choice == "m":
                skillL = 20
                break
            elif choice == "y":
                skillL = 13
                break
            elif choice == "n":
                skillL = 6
                break
        engine.configure({"Skill Level": skillL})
        movetime = 500
        fmove = newgame()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if engine:
                        engine.quit()
                    movSer.close()
                    keySer.close()
                    pygame.quit()
                    exit(0)
            if mouse_enabled:
                bmessage = get_mouse_move()
            else:
                sendtoboard(keySer, "GET") 
                if (mic_enabled):
                    bmessage = listen_and_interpret() 
                    if bmessage == "mouse":
                        bmessage = get_mouse_move()
                else:
                    bmessage = getboard(keySer)
            if not bmessage:
                continue
            code = bmessage[0]

            if code == "m":
                fmove = bmove(fmove, bmessage, movetime)
                if fmove == "GAMEOVER":
                    if engine:
                        engine.quit()
                    movSer.close()
                    exit(0)
                if fmove == "RETRY":
                    continue
            elif code == "n":
                fmove = newgame()
                break

            elif code == "h":
                if board.turn == chess.WHITE:
                    engine.ping()
                    hint = get_hint()
                    if hint != "----":
                        hint_move = chess.Move.from_uci(hint)
                        redraw()
                        draw_highlight(hint_move.from_square, "yellow")  
                        draw_highlight(hint_move.to_square, "yellow") 
                        pygame.display.flip()
                else:
                    pass
            elif code == "a":
                board.reset()
                continue
            elif code == "q":
                if engine:
                    engine.quit()
                movSer.close()
                exit(0)
            else:
                sendtoboard(movSer, "error")
except KeyboardInterrupt:
    print("Exiting...")
    if engine:
        engine.quit()
    movSer.close()
    keySer.close()
