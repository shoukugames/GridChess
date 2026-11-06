#!/usr/bin/env python3
"""Draw the game icon with the game's own art: assets/icon.png and assets/icon.ico.

Run this only when the design changes. Needs Pillow for the .ico file.
"""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

import pygame  # noqa: E402
from PIL import Image  # noqa: E402

from gridchess import art  # noqa: E402

pygame.init()
pygame.display.set_mode((16, 16))
SIZE = 512
canvas = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
mask = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=104)

# a 4x4 corner of a walnut board as the background
board = pygame.Surface((SIZE, SIZE))
cell = SIZE // 4
for r in range(4):
    for f in range(4):
        light = (r + f) % 2 == 0
        board.blit(art.square_surface("walnut", light, cell, r * 8 + f), (f * cell, r * cell))
shade = art.gradient((SIZE, SIZE), (40, 30, 60), (0, 0, 0))
shade.set_alpha(80)
board.blit(shade, (0, 0))
board = board.convert_alpha()
board.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
canvas.blit(board, (0, 0))

# glowing grid lines
for i in range(1, 4):
    pygame.draw.line(canvas, (90, 210, 255), (i * cell, 0), (i * cell, SIZE), 3)
    pygame.draw.line(canvas, (90, 210, 255), (0, i * cell), (SIZE, i * cell), 3)

art.blit_glow(canvas, (256, 250), 230, (90, 70, 20))
knight = art.piece_image("classic", "N", 400)
canvas.blit(knight, (56, 34))

# the "e4"-style label of a typed move
tag = pygame.Rect(276, 372, 210, 104)
art.panel(canvas, tag, (12, 16, 34), 240, 22, (246, 196, 82), 6)
f = art.font(74, True, "mono")
img = f.render("Nf3", True, (246, 196, 82))
canvas.blit(img, img.get_rect(center=tag.center))

canvas.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
pygame.draw.rect(canvas, (246, 196, 82), canvas.get_rect().inflate(-8, -8), 8, border_radius=100)

png = os.path.join(ROOT, "assets", "icon.png")
pygame.image.save(canvas, png)
Image.open(png).save(os.path.join(ROOT, "assets", "icon.ico"),
                     sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon written")
