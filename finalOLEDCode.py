#!/usr/bin/env python3
"""
OLED text display script (Python 3)

Based on Adafruit examples.
For Linux computers using CPython + Adafruit Blinka.
"""

import sys
import getopt
import board
import digitalio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# -----------------------------
# Parse command-line arguments
# -----------------------------
argv = sys.argv[1:]

textLine1 = ""
textLine2 = ""
textLine3 = ""
textSize = 12   # default size

try:
    opts, args = getopt.getopt(
        argv,
        "ha:b:c:s:",
        ["firstLine=", "secondLine=", "thirdLine=", "textSize="]
    )
except getopt.GetoptError:
    print("Usage:")
    print("  printToOLED.py -a <line1> -b <line2> -c <line3> -s <textsize>")
    sys.exit(2)

for opt, arg in opts:
    if opt == "-h":
        print("printToOLED.py -a <firstline> -b <secondline> -c <thirdline> -s <textsize>")
        sys.exit()
    elif opt in ("-a", "--firstLine"):
        textLine1 = arg
    elif opt in ("-b", "--secondLine"):
        textLine2 = arg
    elif opt in ("-c", "--thirdLine"):
        textLine3 = arg
    elif opt in ("-s", "--textSize"):
        textSize = int(arg)

# -----------------------------
# OLED setup
# -----------------------------
WIDTH = 128
HEIGHT = 64

oled_reset = None
i2c = board.I2C()

oled = adafruit_ssd1306.SSD1306_I2C(
    WIDTH,
    HEIGHT,
    i2c,
    addr=0x3C,
    reset=oled_reset
)

# Clear display
oled.fill(0)
oled.show()

# -----------------------------
# Create image buffer
# -----------------------------
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)

# Load font
font_path = "/home/pi/SmartChess/RaspberryPiCode/WorkSans-Medium.ttf"
font = ImageFont.truetype(font_path, textSize)

# -----------------------------
# Helper to center text
# -----------------------------
def draw_centered_text(y, text):
    if not text:
        return
    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    x = (oled.width - text_width) // 2
    draw.text((x, y), text, font=font, fill=255)

# -----------------------------
# Draw text
# -----------------------------
draw_centered_text(0, textLine1)
draw_centered_text(20, textLine2)
draw_centered_text(40, textLine3)

# -----------------------------
# Display on OLED
# -----------------------------
oled.image(image)
oled.show()
