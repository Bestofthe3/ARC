import pygame
import numpy as np
import time
import math as m

SCREEN_SIZE = 256
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)

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
    idx: int,
    pos: tuple[int, int]
) -> np.ndarray:
    """ A black magic function that is used in the console program to
    dra characters from the emulator_characters.bin file."""

    with open("emulator_characters.bin", "rb") as file:
        data = np.fromfile(file, dtype=np.uint8)
    if data.size == 0 or data.size % 45 != 0:
        raise ValueError(
            f"emulator_characters.bin must contain complete "
            f"45-byte-long characters; found {data.size} bytes"
        )
    characters = data.reshape(-1, 5, 3, 3)
    character = np.rot90(characters[idx], k=3, axes=(0, 1))

    rgb = character.astype(np.uint32)
    packed_colors = (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]
    mask = np.any(character != BLACK, axis=-1)
    row, column = pos
    character_pixels_roi = pixels_array[
        row : row + 3,
        column : column + 5
    ]
    character_pixels_roi[mask] = packed_colors[mask]
    return pixels_array

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
            def shader_program(x, y):
                pixels = rgb_to_int_ndarray((x / SCREEN_SIZE, y / SCREEN_SIZE, m.sin(TIME) ** 2))
                pixels[(x == 180) & (y == 76)] = rgb_to_int_singular((0, 0, 0))
                return pixels
            
            def console_program():
                pixels = np.zeros((256, 256), dtype=np.uint32)
                pixels = draw_character(pixels, 0, (0, 0))
                return pixels

        # Computing the color of the pixels
        pixel_buffer = Programs.console_program()

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
