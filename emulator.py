# TODO: Figure out how all this works. Find the simplest solution.
# https://github.com/copilot/c/5061afb3-cab0-445b-98c:w2-b51985c6c33b
import multiprocessing as mp
import time
from pathlib import Path
from renderer import render_vram

instructions_per_draw = 4
draw_frequency = 24

def bytes_to_words(inp: bytes) -> list[int]:
    bin_digs = [f"{b:08b}" for b in inp]
    word_digs = []
    for i in range(0, len(bin_digs) + 1, 2):
        word_digs.append(bin_digs[i] + bin_digs[i+1])
    return word_digs

def words_to_bytes(inp: list[int]) -> bytes:
    res = bytearray()
    for i, word in enumerate(inp):
        left_half = bin(inp)[2:][:8]
        res.append(int(left_half))
        right_half = bin(inp)[2:][8:]
        res.append(int(right_half))

def read_vram_data() -> list[int]:
    path =  Path("Data\\memory.bin")
    data = path.read_bytes() if path.exists() else b""
    return bytes_to_words(data)

def write_vram(data: list[int], file_lock) -> None:
    with file_lock:
        path = Path("Data\\memory.bin")
        path.write_bytes(words_to_bytes(data))

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
