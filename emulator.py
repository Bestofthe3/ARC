import pygame
import numpy as np


class Bit_String(list):
    def __init__(self, num: list | tuple | int | str):
        if isinstance(num, list):
            self.value = #TODO: continue here!


pygame.init()

screen = pygame.display.set_mode((256, 256), pygame.SCALED)
pygame.display.set_caption("ARC Screen Output")

screen.fill((0, 0, 0))

def draw_pixel(col: np.int8, pos: np.int16):
    screen.set_at((100, 50), (255, 255, 255))

# 5. Refresh the display to show your changes
pygame.display.flip()

# 6. Keep the window open until you close it
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

pygame.quit()

