# TODO: Figure out how all this works. Find the simplest solution.
# https://github.com/copilot/c/5061afb3-cab0-445b-98c:w2-b51985c6c33b
import multiprocessing as mp
import time
from pathlib import Path
from renderer import render_vram

instructions_per_draw = 4
draw_frequency = 24

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
'''

def interpreter(file_lock, iteration):
    # NOTE: everything in this function and the next will be changed to be
    # the code for the two processing loops.
    # Consider making this loop the interpreter.

    # TEST: this is here until proper code running is implemented
    # By the way, what is the best way to do large lists of numbers like this?
    data = [0] * 128 * 128
    data[500] = 30000

    # Write data to vram only as often as the frame is being drawn
    if iteration % instructions_per_draw == 0:
        write_vram(data)


def draw(file_lock, iteration):
    '''Draws the pixel data from RAM address 0xDE00 to 0xFDFF to the screen.'''
    # CHANGE: Put one cycle of loop B's work here.
    # This function is called once each time loop B's schedule fires.
    pass

    with file_lock:
        path = Path("Data\\memory.bin") 
        data = bytes_to_words(path.read_bytes() if path.exists() else b"")
        # TODO: write the stuff with the pygame rendering and whatnot from
        # the old emulator file so render a test scene with the data in
        # memory.bin

    render_vram()


def run_periodically(period, func, stop, file_lock):
    iteration = 0
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
    # TODO: Global variables in python?
    # Also, try to find where hexed.it is stored on the computer so you can
    # modify the memory file to test if some of the code so far is working

    # CHANGE: Set the periods for loops A and B.
    process_a = mp.Process(
        target=run_periodically,
        args=(1 / (draw_frequency * instructions_per_draw), interpreter, stop, file_lock),
    )
    process_b = mp.Process(
        target=run_periodically,
        args=(1 / draw_frequency, draw, stop, file_lock),
    )

    process_a.start()
    # Offsetting the vram read and write by 1/2 of the frequency time
    time.sleep(1/ (draw_frequency * 2))
    process_b.start()

    try:
        process_a.join()
        process_b.join()
    except KeyboardInterrupt:
        stop.set()
        process_a.join()
        process_b.join()
