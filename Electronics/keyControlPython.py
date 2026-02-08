import serial
import time
from pynput import keyboard
from threading import Thread, Lock

# Connecting serial port to python
arduino_port = "COM7" 
baud_rate = 9600

try:
    arduino = serial.Serial(arduino_port, baud_rate, timeout=0.1)
    time.sleep(1)  
except Exception as e:
    print(f"Failed to connect to Arduino: {e}")
    exit()

key_state = {"w": False, "s": False, "a": False, "d": False, "e": False}

key_send_interval = 0.2 
serial_lock = Lock()

def send_no_key():
    while True:
        time.sleep(0.1) 
        if not any(key_state.values()):
            with serial_lock:
                arduino.write(b"NO_KEY\n")  

def send_key_periodically():
    while True:
        for key_char in key_state:
            if key_state[key_char]: 
                with serial_lock:
                    arduino.write(f"{key_char}\n".encode())  
                time.sleep(key_send_interval)  

def on_press(key):
    global last_key_press_time

    try:
        key_char = key.char 

        if key_char == "w" or key_char == "s" or key_char == "e" or key_char == "a" or key_char == "d":
            key_state[key_char] = True 
            print(f"Key pressed: {key_char}")

    except AttributeError:
        pass 


def on_release(key):
    global key_state

    if key == keyboard.Key.esc:
        print("ESC pressed. Exiting...")
        return False 

    try:
        key_char = key.char
        if key_char == "w" or key_char == "s" or key_char == "e" or key_char == "a" or key_char == "d":
            key_state[key_char] = False
            print(f"Key released: {key_char}")

    except AttributeError:
        pass 


# Join the threads together
Thread(target=send_no_key, daemon=True).start()  
Thread(target=send_key_periodically, daemon=True).start() 

# Start keyboard listener
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print("Listening for key presses... Press ESC to exit.")
    listener.join()

# Close serial connection
arduino.close()
