"""An emulator for the ARC Microcomputer. Comes pre-installed with
multiple programs. You can decide which program to run by changing
the 'pixel_buffer = Programs.console_program()' line in main()."""

import pygame
import numpy as np
import time
import math as m

SCREEN_SIZE = 256
BLACK = 0
WHITE = 255
CHARACTERS = [' ', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '(', ')', '[', ']', '{', '}', '+', '-', '=', '<', '>', ',', '.', '/', '\\', "'", '"', '_', '@', '#', '$', '%', '^', '&', '*', '?', '!', '~', '\n']
# TODO: Edit the emulator_characters.bin file to include all of the
# characters in the order defined by the above list. CHARACTERS
# can have a maximum length of 256; one byte per character.

pygame.init()
screen = pygame.display.set_mode((256, 256), pygame.SCALED)
pygame.display.set_caption("ARC Screen Output")
screen.fill((0, 0, 0))
display_surface = pygame.Surface((256, 256))
clock = pygame.Clock()
pixel_buffer = np.zeros((256, 256), dtype=int)

def rgb_to_int_singular(c: tuple[float]) -> int:
    """Takes in 3 floats between 0 and 1 and returns the
    color ID associated with those RGB values.
        
    Works when taking in a tuple of floats."""
    c = np.clip(c, 0, 1)
    r = int(c[0] * 255)
    g = int(c[1] * 255)
    b = int(c[2] * 255)
    return (r << 16) | (g << 8) | b

def rgb_to_int_ndarray(c: tuple[np.ndarray]) -> np.ndarray:
    """Takes in 3 floats between 0 and 1 and returns the
    color ID associated with those RGB values.
    
    Works when taking in a tuple of Numpy NDArrays."""
    # Making constant inputs work
    c = tuple(
        np.full((256, 256), item)
        if not isinstance(item, np.ndarray)
        else item
        for item in c
    )
    # Scaling the RGB values from in between 0 and 1
    # to an integer between 0 and 255
    r = (np.clip(c[0], 0, 1) * 255).astype(np.uint32)
    g = (np.clip(c[1], 0, 1) * 255).astype(np.uint32)
    b = (np.clip(c[2], 0, 1) * 255).astype(np.uint32)
    return (r << 16) | (g << 8) | b

def draw_character(
    pixels_array: np.ndarray,
    idx: int | str,
    pos: tuple[int, int]
) -> None:
    """ A black magic function that is used in the console program to
    draw characters from the emulator_characters.bin file.
    
    Edits pixels_array in-place."""

    with open("emulator_characters.bin", "rb") as file:
        data = np.fromfile(file, dtype=np.uint8)
    if data.size == 0 or data.size % 15 != 0:
        raise ValueError(
            f"emulator_characters.bin must contain complete "
            f"15-byte-long characters; found {data.size} bytes"
        )
    characters = data.reshape(-1, 5, 3)
    character: np.ndarray = np.rot90(characters[idx], k=3, axes=(0, 1))

    # Allowing for strings to be passed into draw_character
    if isinstance(idx, str):
        if not idx in CHARACTERS:
            raise ValueError(f"Invalid character: {idx}")
        idx = CHARACTERS.index(idx)
    
    rgb = character.astype(np.uint32)
    # Converts the grayscale brightness values found in
    # emulator_characters.py into rgb values
    packed_colors = ((rgb << 16) | (rgb << 8) | rgb)
    # I don't really know how the mask works tbh
    mask = np.any(character != BLACK, axis=-1)
    row, column = pos

    # This alters pixels_array in-place using array slicing, so there is
    # no need to return anything.
    character_pixels_roi = pixels_array[
        row : row + 3,
        column : column + 5
    ]
    character_pixels_roi[mask] = packed_colors[mask]

def main() -> None: 
    program_start_time = time.time()
    frame_start_time = program_start_time
    frame_idx = -1
    running = True
    
    while running:
        # Initialization
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        pixel_buffer = np.zeros((256, 256), dtype=int)
        
        delta_t = time.time() - frame_start_time
        frame_start_time = time.time()
        TIME = time.time() - program_start_time
        frame_idx += 1

        class Programs:
            @staticmethod
            def shader_program():
                x, y = np.indices((256, 256))
                pixels = rgb_to_int_ndarray(
                    (
                        (x % 4 == 0) | (y % 6 == 0), # R
                        0, # G
                        0 # B
                    )
                )
                pixels[(x == 180) & (y == 76)] = rgb_to_int_singular((0, 0, 0))
                return pixels
            
            @staticmethod
            def console_program():
                pixels = np.zeros((256, 256), dtype=np.uint32)
                # TODO: Finish this so that it just types a character
                # on the screen at a position index automatically
                #def type_characters(pix_array, string: str, )
                draw_character(pixels, 3, (1, 250))
                draw_character(pixels, 1, (3, 248))
                return pixels

        # Computing the color of the pixels
        #pixel_buffer = Programs.console_program()
        pixel_buffer = Programs.shader_program()

        # Flipping the array vertically so that (0, 0) is in the bottom-left
        pixel_buffer = np.flip(pixel_buffer, axis=1)

        r = (pixel_buffer >> 16) & 0xFF # Leftmost (largest) 8 bits
        g = (pixel_buffer >> 8) & 0xFF
        b = pixel_buffer & 0xFF # Rightmost (smallest) 8 bits
        rgb_buffer = np.stack([r, g, b], axis=-1).astype(np.uint8)
        pygame.surfarray.blit_array(display_surface, rgb_buffer)
        scaled_surface = pygame.transform.scale(display_surface, screen.get_size())
        screen.blit(scaled_surface, (0, 0))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
