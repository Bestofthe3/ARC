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
SECTION_SIZES = [
    # These are measured in 16-bit words
    8192, # Program memory
    40448, # Free memory
    16384, # Video memory
    512, # Memory dedicated to the Stack

    # This is measured in 64-bit blocks
    65536
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

def find_section(inp: int) -> int:
    '''Given a word address `inp` in memory, returns what section
    of memory that word will be found in.'''
    if not isinstance(inp, int) or inp < 0 or inp > 0xFFFF:
        raise ValueError(f"input to find_section() must be int between 0 and 0xFFFF: got {inp}")
    elif inp < 0x2000:
        return 0
    elif inp < 0xBE00:
        return 1
    elif inp > 0xFE00:
        return 2
    elif inp <= 0xFFFF:
        return 3

def get_data(section: int, file_lock) -> np.ndarray:
    '''Returns a section of data from one of the data files as an
    array of 16-bit integers.
    
    If `section = 0`: return the data in memory from word address 0x0000
    to 0x1FFF (AKA byte `0` to `16383`) inclusive. This is the Program
    Memory, or where all the instructions are stored.

    If `section = 1`: return data in memory from word address `0x2000`
    to
    `0xBDFF` (AKA byte `16384` to `113663`) inclusive. This is the
    Video Memory, or VRAM, where the pixel data is stored.

    If `section = 2`: return data in memory from word address `0xDE00`
    to `0xFDFF` (AKA byte `113664` to `130047`) inclusive. This is the
    Video Memory, or VRAM, where the pixel data is stored.
    
    If `section = 3`: return data in memory from word address `0xFE00`
    to `0xFFFF` (AKA byte `130048` to `131070`) inclusive. This is where
    the Program Stack is stored, which starts at address `0xFFFF` and
    grows downwards.

    If `section = 4`: return all 512 Kb of data stored in `disc.bin`.
    '''

    path =  "Data\\memory.bin" if section != 4 else "Data\\disc.bin"
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
                        data = mm[0 : (0x1FFF + 1) * 2]
                    case 1:
                        data = mm[0x2000 * 2 : (0xBDFF + 1) * 2]
                    case 2:
                        data = mm[0xBE00 * 2 : (0xFDFF + 1) * 2]
                    case 3:
                        data = mm[0xFE00  * 2: (0xFFFF + 1) * 2]
                    case 4:
                        data = mm[:]
    return np.frombuffer(data, dtype=">u2").astype(np.uint16)

def write_data(section: int, data: np.ndarray, file_lock) -> None:
    """`section` follows the same pattern as that in `get_data`.
    
    0 -> Program Memory
    
    1 -> Free Memory
    
    2 -> Video Memory
    
    3 -> Stack Memory

    4 -> Disc
    """

    if data.size != SECTION_SIZES[section]:
        raise ValueError((
            f"memory section {section} must contain "
            f"{SECTION_SIZES[section]} words, got {data.size}"
        ))
    
    section_bytes = np.asarray(data, dtype=">u2").tobytes()
    with file_lock:
        if section != 4:
            path = Path("Data\\memory.bin")
            with path.open("r+b") as memory_file:
                memory_file.seek(MEM_SECTION_STARTS[section] * 2)
                memory_file.write(section_bytes)
        else:
            # TODO: test if this works
            path = Path("Data\\disc.bin")
            with path.open("r+b") as memory_file:
                memory_file.write(section_bytes)

def binary(inp: int, length: int | None = None) -> str:
    '''Returns the binary string of `inp`, without the `0b` prefix.
    
    if `length` is an integer, the result will have either leading
    zeros placed to the left or will be truncated from left to right
    until its length is the same as `length`.'''
    
    if not isinstance(length, int) or length < 0:
        raise ValueError(f"length must be a positive integer: got {length}")
    if length == 0:
        return ''
    elif length is not None:
        res = bin(inp)[2:]
        if len(res) < length:
            return ('0' * (length - len(res))) + res
        elif len(res) > length:
            return res[len(res) - length :]
    else:
        return bin(inp)[2:]

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

            pixel_buffer = get_data(2, file_lock).reshape(
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

def run_interpreter_loop(stop, file_lock):
    '''A function that runs once per process, but has a loop inside
    that runs once every interval of length `period`.'''
    instruction_addr = 0 # The memory is word-addressable
    next_run = time.monotonic()
    program_data = get_mem_data(0, file_lock)
    free_mem = get_mem_data(1, file_lock)
    video_mem = get_mem_data(2, file_lock)
    stack_mem = get_mem_data(3, file_lock)
    frame_period = 1 / DRAW_FREQUENCY
    next_vram_write = next_run + frame_period

    while not stop.is_set():
        now = time.monotonic()
        if now >= next_run:
            #instruction_start_time = time.perf_counter()

            opcode = program_data[instruction_addr] >> 12

            # Running the instructions
            match opcode:
                case 0: # NOP
                    time.sleep(INSTRUCTION_PERIOD)
                    instruction_addr += 1
                case 1: # READ
                    ...

                case 2: # WRITE
                    ...
                case 3: # LOAD
                    ...
                case 4: # STORE
                    ...
                case 5: # ARITH
                    ...
                case 6: # BARITH
                    ...
                case 7: # SHIFT
                    ...
                case 8: # PUSHPOP
                    ...
                case 9: # SET
                    ...
                case 10: # MOVE
                    ...
                case 11: # JIF
                    ...
                case 12: # JIFF
                    ...
                case 13: # TIME
                    ...
                case 14: # READIO
                    ...
                case 15: # EXIT
                    ...
                    stop.set()
                    break

            #i += 1
            # Aim for a steady instruction period; skip missed runs.
            next_run += INSTRUCTION_PERIOD
            now = time.monotonic()
            if next_run <= now:
                missed = int((now - next_run) // INSTRUCTION_PERIOD) + 1
                next_run += missed * INSTRUCTION_PERIOD
            
            #print((time.perf_counter() - instruction_start_time) / INSTRUCTION_PERIOD)

        # Writing the video_mem variable to memory.bin
        # TODO: Consider writing every variable to their respective .bin files
        now = time.monotonic()
        if now >= next_vram_write:
            write_mem_data(2, video_mem, file_lock)
            now = time.monotonic()
            missed = int((now - next_vram_write) // frame_period) + 1
            next_vram_write += missed * frame_period

        next_wake = min(next_run, next_vram_write)
        stop.wait(max(0, next_wake - time.monotonic()))

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
