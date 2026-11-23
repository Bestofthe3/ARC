# TODO: Figure out how all this works. Find the simplest solution.
# https://github.com/copilot/c/5061afb3-cab0-445b-98c:w2-b51985c6c33b
import multiprocessing as mp
import numpy as np
import time
import pygame
import mmap
from pathlib import Path

DRAW_FREQUENCY = 24
CLOCK_PERIOD = 1 / 10_000
INSTRUCTION_PERIOD = 10 * CLOCK_PERIOD
"""Every instruction's length must be a multiple of this period."""
RESOLUTION = (128, 128)
SCREEN_W, SCREEN_H = RESOLUTION
MEM_SECTION_SIZES = [
    8192, # Program memory
    105984, # Free memory
    16384, # Video memory
    512 # Memory dedicated to the Stack
]
MEM_SECTION_STARTS = [
    0x0, # Program memory
    0x2000, # Free memory
    0xBE00, # Video memory
    0xFE00 # Memory dedicated to the Stack
]

def bytes_to_word_ints(inp: bytes) -> np.ndarray:
    bin_digs = [f"{b:08b}" for b in inp]
    word_digs = []
    for i in range(0, len(bin_digs), 2): # <- THIS SEEMS TO WORK NOW
        word_digs.append(int(bin_digs[i] + bin_digs[i+1], 2))
    return word_digs

def words_to_bytes(inp: np.ndarray) -> bytes:
    res = bytearray()
    for i, word in enumerate(inp):
        left_half = bin(word)[2:][:8]
        res.append(int(left_half))
        right_half = bin(word)[2:][8:]
        res.append(int(right_half))
    return bytes(res)

def get_mem_data(section: int, file_lock) -> np.ndarray:
    '''Returns the data in `memory.bin` from section `section` as an
    array of 16-bit integers.
    
    If `section = 0`: return the data from word address 0x0000 to
    0x1FFF (AKA byte `0` to `16383`) inclusive. This is the Program
    Memory, or where all the instructions are stored.

    If `section = 1`: return data from word address `0x2000` to
    `0xBDFF` (AKA byte `16384` to `113663`) inclusive. This is the
    Video Memory, or VRAM, where the pixel data is stored.

    If `section = 2`: return data from word address `0xDE00` to
    `0xFDFF` (AKA byte `113664` to `130047`) inclusive. This is the
    Video Memory, or VRAM, where the pixel data is stored.
    
    If `section = 3`: return data from word address `0xFE00` to
    `0xFFFF` (AKA byte `130048` to `131070`) inclusive. This is where
    the Program Stack is stored, which starts at address `0xFFFF` and
    grows downwards.
    '''

    path =  "Data\\memory.bin"
    with file_lock:
        with open(path, 'rb') as f:
            with mmap.mmap(
                f.fileno(),
                length=0,
                access=mmap.ACCESS_READ
            ) as mm:
                # converts the word addresses to bytes for mapping to a list
                match section:
                    case 0:
                        data = mm[0 : (0x1FFFF + 1) * 2]
                    case 1:
                        data = mm[0x2000 : (0xBDFF + 1) * 2]
                    case 2:
                        data = mm[0xBE00 * 2 : (0xFDFF + 1) * 2]
                    case 3:
                        data = mm[0xFE00 : (0xFFFF + 1) * 2]
    return np.frombuffer(data, dtype=">u2").astype(np.uint16)

def write_mem_data(section: int, data: np.ndarray, file_lock) -> None:
    """`section` follows the same pattern as that in `get_mem_data`.
    
    0 -> Program Memory
    
    1 -> Free Memory
    
    2 -> Video Memory
    
    3 ->  Stack Memory
    """

    if data.size != MEM_SECTION_SIZES[section]:
        raise ValueError((
            f"VRAM section {section} must contain "
            f"{MEM_SECTION_SIZES[section]} words, got {data.size}"
        ))
    
    section_bytes = np.asarray(data, dtype=">u2").tobytes()
    with file_lock:
        path = Path("Data\\memory.bin")
        with path.open("r+b") as memory_file:
            memory_file.seek(MEM_SECTION_STARTS[section] * 2)
            memory_file.write(section_bytes)

def binary(inp: int) -> str:
    '''Returns the binary string of `inp`, without the `0b` prefix.'''
    return bin(inp)[2:]

'''
def update_shared_file(file_lock, payload):
    # Keep the whole read/modify/write operation protected.
    with file_lock:
        path = Path("Data\\memory.bin")
        # NOTE: change this to whatever modification operations you do on 
        # the file. Also change the 'payload' argument to be whatever the
        # code needs to change in the file.
        data = path.read_bytes() if path.exists() else b""
        path.write_bytes(data + payload)


def interpreter(file_lock, iteration):
    # Consider making this loop the interpreter.

    # Write data to vram only as often as the frame is being drawn
    # if iteration % instructions_per_draw == 0:
    #     write_vram(data, file_lock)
    ...

def draw(file_lock, iteration):
    Draws the pixel data from RAM address 0xDE00 to 0xFDFF to the screen.
    # CHANGE: Put one cycle of loop B's work here.
    # This function is called once each time loop B's schedule fires.
    pass

    # TODO: Consider removing this function

    with file_lock:
        path = Path("Data\\memory.bin") 
        data = bytes_to_word_ints(path.read_bytes() if path.exists() else b"")
        ...

    render_vram()
'''

def run_draw_loop(period, stop, file_lock):
    '''A function that runs once, but has a loop inside
    that runs once every interval of length `period`. Renders the data
    in the VRAM section of the `memory.bin` file to a 128x128 Pygame
    window.'''
    next_run = time.monotonic()

    pygame.init()
    screen = pygame.display.set_mode((256, 256), pygame.SCALED)
    pygame.display.set_caption("ARC Screen Output")
    screen.fill((0, 0, 0))
    display_surface = pygame.Surface(RESOLUTION)
    pixel_buffer = np.zeros(RESOLUTION, dtype=int)
    clock = pygame.Clock()
    try:
        while not stop.is_set():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    stop.set()
                    break

            if stop.is_set():
                break

            pixel_buffer = get_mem_data(2, file_lock).reshape(
                (SCREEN_H, SCREEN_W)
            )

            # Pygame boilerplate
            r = ((pixel_buffer >> 10) & 0x1F) * 255 // 31 # Leftmost (largest) 8 bits
            g = ((pixel_buffer >> 5) & 0x1F) * 255 // 31
            b = (pixel_buffer & 0x1F) * 255 // 31 # Rightmost (smallest) 8 bits
            rgb_rows = np.stack([r, g, b], axis=-1).astype(np.uint8)
            rgb_buffer = np.flip(rgb_rows, axis=0).swapaxes(0, 1)
            pygame.surfarray.blit_array(display_surface, rgb_buffer)
            scaled_surface = pygame.transform.scale(
                display_surface,
                screen.get_size()
            )
            screen.blit(scaled_surface, (0, 0))
            pygame.display.flip()

            # Timing boilerplate
            next_run += period
            now = time.monotonic()
            if next_run <= now:
                missed = int((now - next_run) // period) + 1
                next_run += missed * period
            stop.wait(max(0, next_run - time.monotonic()))
            clock.tick()

            #print(clock.get_fps())
    finally:
        pygame.quit()

    next_run = time.monotonic()

    while not stop.is_set():
        # Runs one cycle of this loop's function
        func(file_lock, iteration)
        iteration += 1

        # Aim for a steady period; skip missed runs rather than catching up.
        next_run += period
        now = time.monotonic()
        if next_run <= now:
            missed = int((now - next_run) // period) + 1
            next_run += missed * period

        stop.wait(max(0, next_run - time.monotonic()))


if __name__ == "__main__":
    stop = mp.Event()
    file_lock = mp.Lock()

    interpreter_process = mp.Process(
        target=run_interpreter_loop,
        args=(
            #1 / (draw_frequency * instructions_per_draw),
            stop,
            file_lock
        ),
    )
    draw_process = mp.Process(
        target=run_draw_loop,
        args=(
            1 / DRAW_FREQUENCY,
            stop,
            file_lock
        ),
    )

    interpreter_process.start()
    # Offsetting the vram read and write by 1/2 of the frequency time
    # TODO: consider removing this line
    time.sleep(1 / (DRAW_FREQUENCY * 2))
    draw_process.start()

    try:
        interpreter_process.join()
        draw_process.join()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        interpreter_process.join()
        draw_process.join()
