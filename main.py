import sys

from hardware.serial import (
    serial_has_byte,
    serial_recv_byte,
    serial_clear,
    serial_send,
    serial_recv,
    serial_move,
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
        
        elif recvd == " " or recvd == "\n":
            # Space or return is for revealing.
            return INPUT_REVEAL

        elif recvd == "f" or recvd == "F":
            # F key is for toggling a flag.
            return INPUT_FLAG

    return 0


def menu() -> uint8:
    serial_clear()

    # Draw the top logo.
    serial_move(2, 32)
    serial_send("\x0E\0337\x6C\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x6B")
    serial_send("\0338\033D\0337\x78\x0F Mine Sweeper \x0E\x78")
    serial_send("\0338\033D\x6D\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x71\x6A\x0F")

    # Draw the menu itself.
    serial_move(6, 29)
    serial_send("\x0E\140\x0F Beginner (8x8)")
    serial_move(7, 29)
    serial_send("\x0E\140\x0F Intermediate (16x16)")
    serial_move(8, 29)
    serial_send("\x0E\140\x0F Expert (32x16)")
    serial_move(9, 29)
    serial_send("\x0E\140\x0F Quit Game")

    # Handle menu input.
    serial_move(6, 29)
    MODE_QUIT: const[uint8] = MODE_HARD + 1
    mode: uint8 = MODE_EASY

    while True:
        action: uint8 = get_input()
        if action == INPUT_UP:
            if mode != MODE_EASY:
                mode -= 1
                serial_send("\033[A")
            continue
        if action == INPUT_DOWN:
            if mode != MODE_QUIT:
                mode += 1
                serial_send("\033[B")
            continue
        if action == INPUT_REVEAL:
            return 0 if mode == MODE_QUIT else mode

    return 0


def game(mode: uint8) -> void:
    serial_clear()
    serial_move(2, 2)
    serial_send("Initializing playfield...")
    playfield_init(mode)
    playfield_draw(0, 0)

    # Erase the initializing playfield display.
    serial_send("\0337")
    serial_move(2, 2)
    serial_send("\033[2K\0338")

    xpos: uint8 = 0
    ypos: uint8 = 0
    width: uint8
    height: uint8
    if mode == MODE_EASY:
        width = EASY_WIDTH
        height = EASY_HEIGHT
    elif mode == MODE_MEDIUM:
        width = MEDIUM_WIDTH
        height = MEDIUM_HEIGHT
    elif mode == MODE_HARD:
        width = HARD_WIDTH
        height = HARD_HEIGHT
    else:
        # Should never happen.
        assert False, f"Unexpected mode {mode} in game loop!"

        width = 0
        height = 0

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


def main() -> void:
    # Set up for box drawing with faster swapping.
    serial_send("\033(B\033)0")

    # Main game loop.
    while True:
        # Draw the new game menu.
        mode: uint8 = menu()

        if not mode:
            # Chose to exit.
            return

        # Play selected game.
        game(mode)
