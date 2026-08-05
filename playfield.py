from math.random import random_int
from hardware.serial import serial_move, serial_send, serial_send_byte, serial_reverse


PLAYFIELD_LEFT: const[uint8] = 3
PLAYFIELD_TOP: const[uint8] = 3
MESSAGES_LEFT: const[uint8] = 1
MESSAGES_TOP: const[uint8] = 1

EASY_WIDTH: const[uint8] = 8
EASY_HEIGHT: const[uint8] = 8
EASY_SHIFT: const[uint8] = 3
EASY_MASK: const[uint8] = 0x7
EASY_MINES: const[uint8] = 8

MEDIUM_WIDTH: const[uint8] = 16
MEDIUM_HEIGHT: const[uint8] = 16
MEDIUM_SHIFT: const[uint8] = 4
MEDIUM_MASK: const[uint8] = 0xF
MEDIUM_MINES: const[uint8] = 40

HARD_WIDTH: const[uint8] = 32
HARD_HEIGHT: const[uint8] = 16
HARD_SHIFT: const[uint8] = 5
HARD_MASK: const[uint8] = 0x1F
HARD_MINES: const[uint8] = 95

MODE_EASY: const[uint8] = 1
MODE_MEDIUM: const[uint8] = 2
MODE_HARD: const[uint8] = 3

STATE_PLAYING: const[uint8] = 0
STATE_WON: const[uint8] = 1
STATE_LOST: const[uint8] = 2


# General playfield globals.
__playfield: str[HARD_WIDTH * HARD_HEIGHT + 1]
__mode: uint8
__spots_left: uint16
__generated: bool


# Constants for figuring out the playfield state.
PLAYFIELD_PROXIMITY_COUNT: const[uint8] = 0x07
PLAYFIELD_MINE: const[uint8] = 0x08
PLAYFIELD_REVEALED: const[uint8] = 0x10
PLAYFIELD_FLAGGED: const[uint8] = 0x20
PLAYFIELD_INITIALIZED: const[uint8] = 0x40


# Constants for displaying counts.
COUNTS: const[str] = " 12345678       "


def playfield_init(mode: uint8) -> void:
    """
    Initialize the game by setting up the playfield for the given mode.
    """

    global __mode
    global __spots_left
    global __generated

    # Display what we're doing, since this can take a bit.
    serial_move(MESSAGES_TOP, MESSAGES_LEFT)
    serial_send("Initializing playfield...")

    __mode = mode
    __generated = False

    size: uint16 = 0
    if mode == MODE_EASY:
        size = EASY_WIDTH * EASY_HEIGHT
        __spots_left = (EASY_WIDTH * EASY_HEIGHT) - EASY_MINES
    elif mode == MODE_MEDIUM:
        size = MEDIUM_WIDTH * MEDIUM_HEIGHT
        __spots_left = (MEDIUM_WIDTH * MEDIUM_HEIGHT) - MEDIUM_MINES
    elif mode == MODE_HARD:
        size = HARD_WIDTH * HARD_HEIGHT
        __spots_left = (HARD_WIDTH * HARD_HEIGHT) - HARD_MINES
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid mode {mode} parameter to playfield_init"

    pos: uint16
    for pos in range(size):
        __playfield[pos] = chr(PLAYFIELD_INITIALIZED)
    __playfield[size] = "\x00"


def __get_loc(xpos: uint8, ypos: uint8) -> uint16:
    """
    Gets the offset into the playfield given an x/y coordinate.
    """

    if __mode == MODE_EASY:
        return (ypos << EASY_SHIFT) + xpos
    elif __mode == MODE_MEDIUM:
        return (ypos << MEDIUM_SHIFT) + xpos
    elif __mode == MODE_HARD:
        return (ypos << HARD_SHIFT) + xpos
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid game mode mode {__mode}"
        return 0


def __playfield_message(message: const[str]) -> void:
    """
    Display a message in the playfield message area.
    """
    serial_send("\0337")
    serial_move(MESSAGES_TOP, MESSAGES_LEFT)
    serial_send(message)
    serial_send("\0338")


def __playfield_increment(loc: uint16) -> void:
    """
    Increment the mine count at a location.
    """
    __playfield[loc] = chr(ord(__playfield[loc]) + 1)


def __playfield_generate(xpos: uint8, ypos: uint8) -> void:
    """
    Generates the playfield based on the user's first selection, making sure
    that they can never click a mine on the first click.
    """

    global __generated
    __generated = True

    # Display what we're doing, since this can take quite a bit.
    serial_send("\0337")
    serial_move(MESSAGES_TOP, MESSAGES_LEFT)
    serial_send("Placing mines...")

    dmz: uint16 = __get_loc(xpos, ypos)

    shift: uint8
    mask: uint8
    width: uint8
    height: uint8
    size: uint16
    mines: uint8
    if __mode == MODE_EASY:
        shift = EASY_SHIFT
        mask = EASY_MASK
        width = EASY_WIDTH
        height = EASY_HEIGHT
        size = (EASY_WIDTH * EASY_HEIGHT) - 1
        mines = EASY_MINES
    elif __mode == MODE_MEDIUM:
        shift = MEDIUM_SHIFT
        mask = MEDIUM_MASK
        width = MEDIUM_WIDTH
        height = MEDIUM_HEIGHT
        size = (MEDIUM_WIDTH * MEDIUM_HEIGHT) - 1
        mines = MEDIUM_MINES
    elif __mode == MODE_HARD:
        shift = HARD_SHIFT
        mask = HARD_MASK
        width = HARD_WIDTH
        height = HARD_HEIGHT
        size = (HARD_WIDTH * HARD_HEIGHT) - 1
        mines = HARD_MINES
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid game mode mode {__mode}"

        shift = 0
        mask = 0
        width = 0
        height = 0
        mines = 0
        size = 0

    while mines:
        loc: uint16 = random_int(0, size)

        # Skip placing a mine here if it has one.
        if ord(__playfield[loc]) & PLAYFIELD_MINE:
            continue

        # Skip placing a mine here if it is where the player clicked.
        if loc == dmz:
            continue

        __playfield[loc] = chr(PLAYFIELD_MINE | PLAYFIELD_INITIALIZED)
        mx: uint8 = loc & mask
        my: uint8 = loc >> shift

        # Mark adjacent spots with the number of mines nearby.
        left: bool = mx == 0
        right: bool = mx == width - 1
        top: bool = my == 0
        bottom: bool = my == height - 1

        if not left:
            prv: uint16 = loc - 1
            __playfield_increment(prv)

            if not top:
                __playfield_increment(prv - width)
            if not bottom:
                __playfield_increment(prv + width)
        if not right:
            nxt: uint16 = loc + 1
            __playfield_increment(nxt)

            if not top:
                __playfield_increment(nxt - width)
            if not bottom:
                __playfield_increment(nxt + width)

        if not top:
            __playfield_increment(loc - width)
        if not bottom:
            __playfield_increment(loc + width)

        mines -= 1

    # Erase any message display.
    serial_move(MESSAGES_TOP, MESSAGES_LEFT)
    serial_send("\033[2K\0338")


def __playfield_reveal(xpos: uint8, ypos: uint8, step_val: char, return_val: char) -> void:
    """
    Reveal a single position that we know is safe due to it being adjacent
    to a blank space. It could be a flag, at which point we refuse to reveal.
    It could be a number, at which point we reveal and stop. It could be a
    blank, at which point we reveal and then recurse. It could be already
    revealed, at which point we stop.
    """

    loc: uint16 = __get_loc(xpos, ypos)
    state: uint8 = ord(__playfield[loc])
    if state & (PLAYFIELD_REVEALED | PLAYFIELD_FLAGGED):
        # This is either revealed or flagged, so don't handle it.
        return

    width: uint8
    height: uint8
    if __mode == MODE_EASY:
        width = EASY_WIDTH
        height = EASY_HEIGHT
    elif __mode == MODE_MEDIUM:
        width = MEDIUM_WIDTH
        height = MEDIUM_HEIGHT
    elif __mode == MODE_HARD:
        width = HARD_WIDTH
        height = HARD_HEIGHT
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid game mode mode {__mode}"

        width = 0
        height = 0

    state |= PLAYFIELD_REVEALED
    __playfield[loc] = chr(state)
        
    global __spots_left
    __spots_left -= 1

    # Need to draw the count or an empty space.
    serial_send("\033[")
    serial_send_byte(ord(step_val))
    serial_send_byte(ord(COUNTS[state & PLAYFIELD_PROXIMITY_COUNT]))
    serial_send("\033[D")

    # Now, need to recurse again!
    if not state & PLAYFIELD_PROXIMITY_COUNT:
        # Need to recursively walk and reveal other tiles.
        if xpos != 0:
            __playfield_reveal(xpos - 1, ypos, 'D', 'C')
        if xpos != width - 1:
            __playfield_reveal(xpos + 1, ypos, 'C', 'D')
        if ypos != 0:
            __playfield_reveal(xpos, ypos - 1, 'A', 'B')
        if ypos != height - 1:
            __playfield_reveal(xpos, ypos + 1, 'B', 'A')

    serial_send("\033[")
    serial_send_byte(ord(return_val))


def playfield_click(xpos: uint8, ypos: uint8) -> uint8:
    """
    Simulate a "left click" of the playfield, which in this version is
    done by pressing space or return. Returns True if the player revealed
    a mine
    """

    if not __generated:
        __playfield_generate(xpos, ypos)

    assert __generated, "Failed to generate playfield!"

    loc: uint16 = __get_loc(xpos, ypos)
    width: uint8
    height: uint8
    if __mode == MODE_EASY:
        width = EASY_WIDTH
        height = EASY_HEIGHT
    elif __mode == MODE_MEDIUM:
        width = MEDIUM_WIDTH
        height = MEDIUM_HEIGHT
    elif __mode == MODE_HARD:
        width = HARD_WIDTH
        height = HARD_HEIGHT
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid game mode mode {__mode}"

        width = 0
        height = 0

    state: uint8 = ord(__playfield[loc])
    if state & PLAYFIELD_REVEALED:
        return STATE_PLAYING if __spots_left else STATE_WON

    # Put us into special character mode.
    serial_send_byte(ord("\x0E"))

    # If we flagged a spot, don't let the player accidentally reveal it.
    if not state & PLAYFIELD_FLAGGED:
        state |= PLAYFIELD_REVEALED
        __playfield[loc] = chr(state)

        # Draw what's actually there.
        if state & PLAYFIELD_MINE:
            # Uh oh, revealed a mine.
            serial_send("*\033[D")
        else:
            # Need to draw the count or an empty space.
            serial_send_byte(ord(COUNTS[state & PLAYFIELD_PROXIMITY_COUNT]))
            serial_send("\033[D")

        if state & PLAYFIELD_MINE:
            serial_send_byte(ord("\x0F"))
            return STATE_LOST
        
        global __spots_left
        __spots_left -= 1

        if not state & PLAYFIELD_PROXIMITY_COUNT:
            # Need to recursively walk and reveal other tiles.
            if xpos != 0:
                __playfield_reveal(xpos - 1, ypos, 'D', 'C')
            if xpos != width - 1:
                __playfield_reveal(xpos + 1, ypos, 'C', 'D')
            if ypos != 0:
                __playfield_reveal(xpos, ypos - 1, 'A', 'B')
            if ypos != height - 1:
                __playfield_reveal(xpos, ypos + 1, 'B', 'A')

    serial_send_byte(ord("\x0F"))
    return STATE_PLAYING if __spots_left else STATE_WON


def playfield_flag(xpos: uint8, ypos: uint8) -> void:
    """
    Simulate a "right click" of the playfield, which in this version is
    done by pressing f to flag. Returns true if this updated the playfield
    or false if it did not.
    """

    if not __generated:
        return

    loc: uint16 = __get_loc(xpos, ypos)

    state: uint8 = ord(__playfield[loc])

    # We don't want to flag already revealed spots.
    if not state & PLAYFIELD_REVEALED:
        # Toggle the flag.
        if state & PLAYFIELD_FLAGGED:
            state &= ~PLAYFIELD_FLAGGED
        else:
            state |= PLAYFIELD_FLAGGED
        
        __playfield[loc] = chr(state)

        if state & PLAYFIELD_FLAGGED:
            # Draw the flag diamond to signify a marked spot.
            serial_send("\x0E\140\033[D\x0F")
        else:
            # Draw a placeholder dot to indicate we haven't revealed yet.
            serial_send("\x0E\176\033[D\x0F")


def playfield_draw(xpos: uint8, ypos: uint8, state: uint8) -> void:
    """
    Draw the playfield, including the cursor spot.
    """

    if state == STATE_WON:
        __playfield_message("Successfully swept mine field, you win!")
    elif state == STATE_LOST:
        __playfield_message("Revealed a mine, you lose!")

    width: uint8 = 0
    height: uint8 = 0
    loc: uint16 = __get_loc(xpos, ypos)
    pos: uint8 = 0

    if __mode == MODE_EASY:
        width = EASY_WIDTH
        height = EASY_HEIGHT
    elif __mode == MODE_MEDIUM:
        width = MEDIUM_WIDTH
        height = MEDIUM_HEIGHT
    elif __mode == MODE_HARD:
        width = HARD_WIDTH
        height = HARD_HEIGHT
    else:
        # Should never happen unless there's a programmer error
        assert False, f"Invalid game mode mode {__mode}"

    serial_move(PLAYFIELD_TOP, PLAYFIELD_LEFT)

    # Swap to alternate drawing set for box drawing and diamond/middle dot. Save
    # the serial position for faster moving back.
    serial_send("\x0E\0337\x6C")
    for pos in range(width):
        serial_send_byte(ord("\x71"))

    # Finish drawing the top bits, move to the next line.
    serial_send("\x6B\0338\033D\0337\x78")

    pos = 0
    ch: char
    for ch in __playfield:
        if pos == width:
            # Move back to the beginning of the line, move down one line, resave.
            serial_send("\x78\0338\033D\0337\x78")
            pos = 0

        if ord(ch) & PLAYFIELD_REVEALED:
            # Draw what's actually there.
            if ord(ch) & PLAYFIELD_MINE:
                # Uh oh, revealed a mine.
                serial_send_byte(ord("*"))
            else:
                # Need to draw the count or an empty space.
                serial_send_byte(ord(COUNTS[ord(ch) & PLAYFIELD_PROXIMITY_COUNT]))
        elif ord(ch) & PLAYFIELD_FLAGGED:
            # Draw the flag diamond to signify a marked spot.
            serial_send_byte(ord("\140"))
        elif state == STATE_WON:
            # Draw the flag diamond to signify a swept spot.
            serial_send_byte(ord("\140"))
        elif state == STATE_LOST and ord(ch) & PLAYFIELD_MINE:
            # Draw all the mines that the player missed.
            serial_send_byte(ord("*"))
        else:
            # Draw a placeholder dot to indicate we haven't revealed yet.
            serial_send_byte(ord("\176"))

        pos += 1

    # Draw the bottom bits.
    serial_send("\x78\0338\033D\x6D")
    for pos in range(width):
        serial_send_byte(ord("\x71"))

    # Swap back to normal drawing set.
    serial_send("\x6A\x0F")

    if state == STATE_PLAYING:
        # Move below the playfield to display instructions.
        serial_move(PLAYFIELD_TOP + 3 + height, MESSAGES_LEFT)
        serial_send("[SPACE] to reveal the spot under the cursor")
        serial_move(PLAYFIELD_TOP + 4 + height, MESSAGES_LEFT)
        serial_send("[F] to toggle a flag under the cursor")
        serial_move(PLAYFIELD_TOP + 5 + height, MESSAGES_LEFT)
        serial_send("[Q] to quit back to the menu")

        # Erase any message display.
        serial_move(MESSAGES_TOP, MESSAGES_LEFT)
        serial_send("\033[2K")

    # Move cursor to the right spot.
    serial_move(PLAYFIELD_TOP + 1 + ypos, PLAYFIELD_LEFT + 1 + xpos)
