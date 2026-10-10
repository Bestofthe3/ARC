import pygame
import numpy as np
import time
import math as m

SCREEN_SIZE = 256

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

def main() -> None: 
    program_start_time = time.time()
    frame_start_time = program_start_time
    frame_idx = -1 # Only starts as -1
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

        # Computing the color of the pixels
        def shader_program(x, y):
            pixels = rgb_to_int_ndarray((x / SCREEN_SIZE, y / SCREEN_SIZE, abs(m.sin(TIME))))

            pixels[(x == 128) & (y == 128)] = rgb_to_int_singular((0, 0, 0))

            return pixels
        
        pixel_buffer = np.fromfunction(shader_program, (256, 256), dtype=int)

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
