import sys

from hardware.serial import (
    serial_has_byte,
    serial_recv_byte,
    serial_clear,
    serial_send,
    serial_recv,
)
from math.random import (
    random_step,
)
from playfield import (
    playfield_init,
    playfield_click,
    playfield_flag,
    playfield_draw,
    MODE_EASY,
    MODE_MEDIUM,
    MODE_HARD,
    EASY_WIDTH,
    EASY_HEIGHT,
    MEDIUM_WIDTH,
    MEDIUM_HEIGHT,
    HARD_WIDTH,
    HARD_HEIGHT,
)


INPUT_UP: const[uint8] = 1
INPUT_DOWN: const[uint8] = 2
INPUT_LEFT: const[uint8] = 3
INPUT_RIGHT: const[uint8] = 4
INPUT_REVEAL: const[uint8] = 5
INPUT_FLAG: const[uint8] = 6


def get_input() -> uint8:
    while True:
        # Wait for a byte to become available.
        while not serial_has_byte():
            random_step()

        # Read that byte, ignore it if it isn't one of our controls.
        recvd: char = chr(serial_recv_byte())
        if recvd == "\033":
            # We care about escape sequences on account of needing to read arrow keys.
            while True:
                while not serial_has_byte():
                    pass

                # Escape codes always start with an escape character, and always end with a letter.
                # We can check for upper and lowercase letters by always clearing the lowercase bit.
                # We can save a comparison (which is extremely slow due to being SW implemented) by
                # subtracting the low comparison value and relying on overflow wraparound to put values
                # lower than the start above the high comparison.
                recvd = chr(serial_recv_byte() & 0b11011111)
                if ord(recvd) - ord('A') < 26:
                    # It might be an arrow key, check for that here.
                    if recvd == 'A':
                        return INPUT_UP
                    if recvd == 'B':
                        return INPUT_DOWN
                    if recvd == 'C':
                        return INPUT_RIGHT
                    if recvd == 'D':
                        return INPUT_LEFT

                    # We don't care about this, swallow it.
                    break
        
        elif recvd == " ":
            # Space is for revealing.
            return INPUT_REVEAL

        elif recvd == "f" or recvd == "F":
            # F key is for toggling a flag.
            return INPUT_FLAG

    return 0


def main() -> void:
    serial_clear()
    serial_send("Minesweeper")

    # Set up for box drawing with faster swapping.
    serial_send("\033(B\033)0")

    playfield_init(MODE_EASY)
    playfield_draw(0, 0)

    xpos: uint8 = 0
    ypos: uint8 = 0
    width: uint8 = EASY_WIDTH
    height: uint8 = EASY_HEIGHT

    while True:
        action: uint8 = get_input()
        if action == INPUT_UP:
            if ypos != 0:
                ypos -= 1
                serial_send("\033[A")
            continue

        elif action == INPUT_DOWN:
            if ypos != height - 1:
                ypos += 1
                serial_send("\033[B")
            continue

        elif action == INPUT_LEFT:
            if xpos != 0:
                xpos -= 1
                serial_send("\033[D")
            continue

        elif action == INPUT_RIGHT:
            if xpos != width - 1:
                xpos += 1
                serial_send("\033[C")
            continue

        elif action == INPUT_REVEAL:
            playfield_click(xpos, ypos)

        elif action == INPUT_FLAG:
            playfield_flag(xpos, ypos)

    # Exit on enter pressed.
    serial_recv(echo_input=False, allow_empty=True)
