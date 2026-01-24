import whisper
import sounddevice as sd
import numpy as np
import re
import queue
import sys
import json
import os
from difflib import SequenceMatcher

SAMPLE_RATE = 16000
MODEL_NAME = "small.en"
SQUARE_REGEX = r"[a-h][1-8]"
MEMORY_FILE = "piece_memory.json"

STOPWORDS = {
    "move", "from", "to", "go",
    "please", "the", "a", "an"
}

audio_queue = queue.Queue()

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def detect_piece_with_learning(text, memory):
    words = text.split()
    best_piece = None
    best_score = 0
    best_word = None

    for word in words:
        for piece, variants in memory.items():
            for v in variants:
                score = similarity(word, v)
                if score > best_score:
                    best_score = score
                    best_piece = piece
                    best_word = word

    if best_score > 0.75:
        return best_piece, best_word

    return None, None

def reinforce_learning(memory, piece, word):
    if word and word not in memory[piece]:
        memory[piece].append(word)
        save_memory(memory)
        print(f"[LEARNED] '{word}' → {piece}")

def record_audio():
    input("\nPress ENTER to speak...")

    duration = 5

    print("🎙️ Recording for 5 seconds...")

    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype=np.float32
    )

    sd.wait()
    return audio.flatten()



def speech_to_text(model, audio):
    result = model.transcribe(audio, fp16=False)
    return result["text"].lower().strip()

def parse_chess_command(text, memory):
    words = [w.strip(".,") for w in text.split()]
    squares = re.findall(SQUARE_REGEX, text)

    if len(squares) < 2:
        return None

    from_sq, to_sq = squares[0], squares[1]

    piece, heard_word = detect_piece_with_learning(text, memory)

    if piece is None:
        for w in words:
            if w in memory:
                piece = w
                break

    if piece is None:
        print("❓ Piece samajh nahi aaya")
        piece = input("Correct piece likho (pawn/rook/bishop/knight/queen/king): ").lower()

        if piece not in memory:
            memory[piece] = []

        for w in words:
            if w in STOPWORDS:
                continue
            if re.match(SQUARE_REGEX, w):
                continue
            reinforce_learning(memory, piece, w)
            break

    return {
        "piece": piece,
        "from": from_sq,
        "to": to_sq
    }

def main():
    print("Chess Voice Parser Started")
    model = whisper.load_model(MODEL_NAME)
    memory = load_memory()

    while True:
        audio = record_audio()
        text = speech_to_text(model, audio)
        print(f"\nYou said: {text}")

        parsed = parse_chess_command(text, memory)

        if parsed:
            print("Parsed Move:")
            print(parsed)
        else:
            print("Invalid input")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()
