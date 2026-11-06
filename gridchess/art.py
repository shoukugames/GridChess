"""All drawing: fonts, panels, glows, the five piece sets and the six board themes.

Everything is drawn in code at start-up (supersampled, then smoothed) and cached,
so there are no image files to ship apart from the fonts.
"""
import math
import random

import pygame

from . import i18n
from .chess import FILES, RANKS, is_light, parse_square
from .paths import asset

# ---------------------------------------------------------------- palette
BG_TOP = (14, 20, 40)
BG_BOTTOM = (30, 22, 52)
INK = (236, 240, 250)
INK_DIM = (160, 172, 200)
GOLD = (246, 196, 82)
CYAN = (90, 210, 255)
GREEN = (110, 226, 140)
RED = (255, 98, 98)
PANEL = (22, 30, 56)
PANEL_EDGE = (70, 92, 150)

_fonts = {}


def font(size, bold=False, kind="body"):
    """kind: body (M PLUS 1p, has Japanese), title (Orbitron, or M PLUS bold in Japanese),
    mono (DejaVu Sans Mono for typed moves), glyph (DejaVu Sans for chess symbols)."""
    if kind == "num" or (kind == "title" and i18n.ja()):
        kind, bold = "body", True     # Orbitron's slashed zero is easy to misread
    key = (size, bold, kind)
    if key not in _fonts:
        name = {"title": "Orbitron.ttf", "mono": "DejaVuSansMono-Bold.ttf", "glyph": "DejaVuSans.ttf"}.get(kind)
        if name is None:
            name = "MPLUS1p-Bold.ttf" if bold else "MPLUS1p-Regular.ttf"
        try:
            _fonts[key] = pygame.font.Font(asset("fonts", name), size)
        except (FileNotFoundError, pygame.error):
            _fonts[key] = pygame.font.Font(None, size)
    return _fonts[key]


def text(surface, s, pos, size=24, color=INK, bold=False, kind="body", anchor="topleft", shadow=True):
    f = font(size, bold, kind)
    img = f.render(str(s), True, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        sh = f.render(str(s), True, (0, 0, 0))
        sh.set_alpha(110)
        surface.blit(sh, rect.move(2, 2))
    surface.blit(img, rect)
    return rect


def wrap(s, width, size=22, bold=False):
    """Word wrap that also breaks Japanese text between characters."""
    f = font(size, bold)
    lines = []
    for para in str(s).split("\n"):
        tokens = para.split(" ") if " " in para and not _has_cjk(para) else list(para)
        joiner = " " if " " in para and not _has_cjk(para) else ""
        line = ""
        for tok in tokens:
            trial = line + (joiner if line else "") + tok
            if f.size(trial)[0] <= width or not line:
                line = trial
            else:
                lines.append(line)
                line = tok
        lines.append(line)
    return lines


def _has_cjk(s):
    return any(ord(c) > 0x2E80 for c in s)


def text_block(surface, s, rect, size=22, color=INK, bold=False, spacing=1.35):
    rect = pygame.Rect(rect)
    y = rect.y
    for line in wrap(s, rect.width, size, bold):
        text(surface, line, (rect.x, y), size, color, bold, shadow=False)
        y += int(size * spacing)
    return y


# ---------------------------------------------------------------- shapes
def gradient(size, top, bottom, horizontal=False):
    w, h = size
    surf = pygame.Surface((2, 256) if not horizontal else (256, 2))
    for i in range(256):
        k = i / 255
        c = [int(top[j] + (bottom[j] - top[j]) * k) for j in range(3)]
        if horizontal:
            surf.set_at((i, 0), c)
            surf.set_at((i, 1), c)
        else:
            surf.set_at((0, i), c)
            surf.set_at((1, i), c)
    return pygame.transform.smoothscale(surf, (max(1, w), max(1, h)))


def panel(surface, rect, color=PANEL, alpha=225, radius=16, border=PANEL_EDGE, width=2):
    rect = pygame.Rect(rect)
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
    sheen_h = min(rect.h // 2, 60)
    sheen = pygame.Surface(rect.size, pygame.SRCALPHA)
    for y in range(sheen_h):
        a = int(18 * (1 - y / sheen_h))
        inset = max(0, radius - int((radius * radius - (radius - y) ** 2) ** 0.5)) if y < radius else 0
        pygame.draw.line(sheen, (255, 255, 255, a), (inset + 2, y + 2), (rect.w - inset - 3, y + 2))
    s.blit(sheen, (0, 0))
    if border:
        pygame.draw.rect(s, (*border, 255), s.get_rect(), width, border_radius=radius)
    surface.blit(s, rect)


_glow_cache = {}


def glow_sprite(radius):
    """A soft white disc, premultiplied, because glows are added onto the scene."""
    if radius not in _glow_cache:
        size = radius * 2
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(radius, 0, -1):
            v = int(255 * (1 - i / radius) ** 2)
            pygame.draw.circle(s, (v, v, v, v), (radius, radius), i)
        _glow_cache[radius] = s
    return _glow_cache[radius]


def blit_glow(surface, pos, radius, color, strength=1.0):
    radius = max(2, int(radius))
    k = max(0.0, min(1.0, strength))
    g = glow_sprite(radius).copy()
    g.fill((int(color[0] * k), int(color[1] * k), int(color[2] * k), 255), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(g, (pos[0] - radius, pos[1] - radius), special_flags=pygame.BLEND_RGB_ADD)


def blur(surf, factor=4):
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


_bg_cache = {}


def background(size):
    if size not in _bg_cache:
        surf = gradient(size, BG_TOP, BG_BOTTOM)
        vignette = pygame.Surface(size, pygame.SRCALPHA)
        w, h = size
        for i in range(40):
            pygame.draw.rect(vignette, (0, 0, 0, 5), (-i * 4, -i * 4, w + i * 8, h + i * 8), 8,
                             border_radius=200)
        surf.blit(vignette, (0, 0))
        _bg_cache[size] = surf.convert()
    return _bg_cache[size]


# ---------------------------------------------------------------- textures
def _wood_texture(size, base, dark, seed, vertical=False):
    rng = random.Random(seed)
    w, h = size
    surf = pygame.Surface((w, h))
    surf.fill(base)
    lines = pygame.Surface((w, h), pygame.SRCALPHA)
    count = max(6, h // 3)
    phase = rng.uniform(0, 6)
    for i in range(count):
        y0 = rng.uniform(-h * 0.1, h * 1.1)
        amp = rng.uniform(1, h * 0.05)
        freq = rng.uniform(0.6, 2.2) / w * math.pi * 2
        a = rng.randint(14, 44)
        col = (*dark, a)
        pts = [(x, y0 + math.sin(x * freq + phase + i * 0.3) * amp + math.sin(x * freq * 3.1) * amp * 0.25)
               for x in range(0, w + 6, 6)]
        pygame.draw.lines(lines, col, False, pts, rng.choice((1, 1, 2, 3)))
    # occasional knot
    if rng.random() < 0.35:
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        for r in range(int(min(w, h) * 0.18), 2, -3):
            pygame.draw.ellipse(lines, (*dark, 22), (cx - r * 1.6, cy - r * 0.7, r * 3.2, r * 1.4), 1)
    lines = blur(lines, 2)
    surf.blit(lines, (0, 0))
    if vertical:
        surf = pygame.transform.rotate(surf, 90)
        surf = pygame.transform.smoothscale(surf, size)
    sheen = gradient(size, (255, 255, 255), (0, 0, 0))
    sheen.set_alpha(18)
    surf.blit(sheen, (0, 0))
    return surf


def _marble_texture(size, base, vein, seed):
    rng = random.Random(seed)
    w, h = size
    surf = pygame.Surface((w, h))
    surf.fill(base)
    clouds = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(14):
        r = rng.uniform(w * 0.15, w * 0.5)
        tone = rng.randint(-18, 18)
        c = tuple(max(0, min(255, base[i] + tone)) for i in range(3))
        pygame.draw.circle(clouds, (*c, 60), (rng.uniform(0, w), rng.uniform(0, h)), r)
    surf.blit(blur(clouds, 6), (0, 0))
    veins = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(3):
        x, y = rng.uniform(-w * 0.2, w * 0.3), rng.uniform(0, h)
        ang = rng.uniform(-0.6, 0.6)
        pts = []
        for _s in range(40):
            pts.append((x, y))
            ang += rng.uniform(-0.35, 0.35)
            x += math.cos(ang) * w / 26
            y += math.sin(ang) * h / 26
        pygame.draw.lines(veins, (*vein, rng.randint(60, 130)), False, pts, rng.choice((1, 2)))
    surf.blit(blur(veins, 2), (0, 0))
    return surf


# ---------------------------------------------------------------- boards
BOARDS = {
    "walnut": {"light": (232, 202, 156), "dark": (150, 98, 58), "frame": (66, 40, 24), "style": "wood",
               "label": (250, 232, 200), "grain_l": (176, 130, 82), "grain_d": (82, 48, 24)},
    "tournament": {"light": (238, 238, 210), "dark": (118, 150, 86), "frame": (48, 64, 38), "style": "flat",
                   "label": (238, 238, 210)},
    "marble": {"light": (232, 232, 226), "dark": (104, 132, 124), "frame": (52, 58, 60), "style": "marble",
               "label": (232, 236, 236), "vein_l": (150, 150, 160), "vein_d": (40, 60, 56)},
    "midnight": {"light": (148, 166, 204), "dark": (58, 72, 112), "frame": (24, 30, 52), "style": "glass",
                 "label": (196, 210, 240)},
    "sakura": {"light": (250, 232, 236), "dark": (214, 140, 160), "frame": (110, 60, 78), "style": "flat",
               "label": (255, 236, 242)},
    "ocean": {"light": (214, 236, 244), "dark": (76, 132, 168), "frame": (24, 58, 84), "style": "glass",
              "label": (214, 236, 244)},
}
BOARD_ORDER = list(BOARDS)

_square_cache = {}


def square_surface(theme, light, size, sq):
    """Texture for one square. Wood and marble vary per square so the board looks natural."""
    th = BOARDS[theme]
    style = th["style"]
    key = (theme, light, size, sq if style in ("wood", "marble") else 0)
    if key in _square_cache:
        return _square_cache[key]
    base = th["light"] if light else th["dark"]
    if style == "wood":
        s = _wood_texture((size, size), base, th["grain_l"] if light else th["grain_d"], seed=sq * 7 + light,
                          vertical=(sq + (sq >> 3)) % 2 == 0)
    elif style == "marble":
        s = _marble_texture((size, size), base, th["vein_l"] if light else th["vein_d"], seed=sq * 13 + light)
    elif style == "glass":
        hi = tuple(min(255, c + 22) for c in base)
        s = gradient((size, size), hi, base)
        pygame.draw.rect(s, tuple(min(255, c + 34) for c in base), (0, 0, size, size), 1)
    else:
        s = pygame.Surface((size, size))
        s.fill(base)
    s = s.convert()
    _square_cache[key] = s
    return s


class BoardView:
    """Draws the 8x8 board at a given rectangle, oriented for the human player."""

    def __init__(self, rect, flipped=False):
        self.rect = pygame.Rect(rect)
        self.size = self.rect.w // 8
        self.flipped = flipped

    def square_rect(self, sq):
        f, r = sq & 7, sq >> 3
        col = 7 - f if self.flipped else f
        row = r if self.flipped else 7 - r
        return pygame.Rect(self.rect.x + col * self.size, self.rect.y + row * self.size, self.size, self.size)

    def square_at(self, pos):
        if not self.rect.collidepoint(pos):
            return None
        col = (pos[0] - self.rect.x) // self.size
        row = (pos[1] - self.rect.y) // self.size
        f = 7 - col if self.flipped else col
        r = row if self.flipped else 7 - row
        return r * 8 + f

    def draw_frame(self, surface, theme, labels=True):
        th = BOARDS[theme]
        pad = max(9, int(self.size * 0.37))
        outer = self.rect.inflate(pad * 2, pad * 2)
        shadow = pygame.Surface(outer.inflate(30, 30).size, pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 120), shadow.get_rect().inflate(-24, -24), border_radius=18)
        surface.blit(blur(shadow, 6), outer.inflate(30, 30).move(4, 10))
        if th["style"] == "wood":
            frame = _wood_texture(outer.size, th["frame"], (30, 16, 8), seed=99)
        else:
            frame = gradient(outer.size, tuple(min(255, c + 30) for c in th["frame"]), th["frame"])
        mask = pygame.Surface(outer.size, pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=14)
        frame = frame.convert_alpha()
        frame.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surface.blit(frame, outer)
        pygame.draw.rect(surface, tuple(min(255, c + 60) for c in th["frame"]), outer, 2, border_radius=14)
        pygame.draw.rect(surface, (0, 0, 0), self.rect.inflate(4, 4), 2)
        if labels:
            files = FILES[::-1] if self.flipped else FILES
            ranks = RANKS if self.flipped else RANKS[::-1]
            size = max(14, self.size // 4)
            for i in range(8):
                cx = self.rect.x + i * self.size + self.size // 2
                cy = self.rect.y + i * self.size + self.size // 2
                for y in (self.rect.top - 15, self.rect.bottom + 14):
                    text(surface, files[i], (cx, y), size, th["label"], True, "mono", "center")
                for x in (self.rect.left - 15, self.rect.right + 15):
                    text(surface, ranks[i], (x, cy), size, th["label"], True, "mono", "center")

    def draw_squares(self, surface, theme, coords=False):
        th = BOARDS[theme]
        for sq in range(64):
            r = self.square_rect(sq)
            light = is_light(sq)
            surface.blit(square_surface(theme, light, self.size, sq), r)
            if coords:
                col = th["dark"] if light else th["light"]
                f = font(max(10, self.size // 5), True, "mono")
                img = f.render(FILES[sq & 7] + RANKS[sq >> 3], True, col)
                img.set_alpha(150)
                surface.blit(img, (r.x + 3, r.bottom - img.get_height()))

    def tint(self, surface, sq, color, alpha=110):
        r = self.square_rect(sq)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        s.fill((*color, alpha))
        surface.blit(s, r)

    def ring(self, surface, sq, color, width=4):
        r = self.square_rect(sq).inflate(-width, -width)
        pygame.draw.rect(surface, color, r, width, border_radius=4)

    def dot(self, surface, sq, color, capture=False):
        r = self.square_rect(sq)
        s = pygame.Surface(r.size, pygame.SRCALPHA)
        if capture:
            pygame.draw.circle(s, (*color, 150), (r.w // 2, r.h // 2), r.w // 2 - 3, max(3, r.w // 12))
        else:
            pygame.draw.circle(s, (*color, 150), (r.w // 2, r.h // 2), r.w // 7)
        surface.blit(s, r)

    def arrow(self, surface, a, b, color=(255, 170, 40), alpha=200):
        ra, rb = self.square_rect(a), self.square_rect(b)
        s = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        p, q = pygame.Vector2(ra.center), pygame.Vector2(rb.center)
        d = q - p
        if d.length() == 0:
            return
        u = d.normalize()
        n = pygame.Vector2(-u.y, u.x)
        w = self.size * 0.11
        head = self.size * 0.36
        end = q - u * head
        pts = [p + n * w, end + n * w, end + n * w * 2.6, q, end - n * w * 2.6, end - n * w, p - n * w]
        pygame.draw.polygon(s, (*color, alpha), pts)
        surface.blit(s, (0, 0))


# ---------------------------------------------------------------- pieces
PIECE_SETS = ["classic", "tournament", "wood", "modern", "neon"]
GLYPH_OUTLINE = {"K": "♔", "Q": "♕", "R": "♖", "B": "♗", "N": "♘", "P": "♙"}
GLYPH_SOLID = {"K": "♚", "Q": "♛", "R": "♜", "B": "♝", "N": "♞", "P": "♟"}
_piece_cache = {}
SS = 3  # supersampling factor


def _mask_surface(mask, color=(255, 255, 255, 255)):
    return mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))


def _glyph_masks(kind, size):
    """Returns (silhouette, strokes, solid) masks for a glyph piece, all size x size."""
    f = font(int(size * 0.97), False, "glyph")
    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    outline = f.render(GLYPH_OUTLINE[kind], True, (255, 255, 255))
    solid = f.render(GLYPH_SOLID[kind], True, (255, 255, 255))
    bound = outline.get_bounding_rect()
    off = (size // 2 - bound.centerx, int(size * 0.53) - bound.centery)
    c1 = canvas.copy()
    c1.blit(outline, off)
    c2 = canvas.copy()
    c2.blit(solid, off)
    strokes = pygame.mask.from_surface(c1, 100)
    solid_m = pygame.mask.from_surface(c2, 100)
    outside = strokes.copy()
    outside.invert()
    outside = outside.connected_component((0, 0))
    sil = outside.copy()
    sil.invert()
    return sil, strokes, solid_m


def _dilate(mask, radius):
    disc = pygame.mask.Mask((radius * 2 + 1, radius * 2 + 1))
    for x in range(radius * 2 + 1):
        for y in range(radius * 2 + 1):
            if (x - radius) ** 2 + (y - radius) ** 2 <= radius * radius:
                disc.set_at((x, y))
    return mask.convolve(disc, None, (-radius, -radius))


def _fill(mask, fill_surface):
    s = fill_surface.copy().convert_alpha()
    s.blit(_mask_surface(mask), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s


def _modern_masks(kind, size):
    u = size / 100.0
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    det = pygame.Surface((size, size), pygame.SRCALPHA)
    W = (255, 255, 255)

    def P(pts):
        return [(x * u, y * u) for x, y in pts]

    def R(x, y, w, h):
        return pygame.Rect(x * u, y * u, w * u, h * u)

    pygame.draw.rect(surf, W, R(22, 80, 56, 11), border_radius=int(4 * u))
    pygame.draw.rect(surf, W, R(27, 73, 46, 9), border_radius=int(3 * u))
    lw = max(1, int(2.6 * u))
    if kind == "P":
        pygame.draw.polygon(surf, W, P([(39, 52), (61, 52), (67, 75), (33, 75)]))
        pygame.draw.ellipse(surf, W, R(33, 45, 34, 10))
        pygame.draw.circle(surf, W, (50 * u, 32 * u), 13 * u)
    elif kind == "R":
        pygame.draw.polygon(surf, W, P([(34, 40), (66, 40), (70, 75), (30, 75)]))
        pygame.draw.polygon(surf, W, P([(27, 16), (38, 16), (38, 25), (45, 25), (45, 16), (55, 16), (55, 25),
                                        (62, 25), (62, 16), (73, 16), (73, 40), (27, 40)]))
        pygame.draw.line(det, W, (31 * u, 40 * u), (69 * u, 40 * u), lw)
    elif kind == "B":
        pygame.draw.polygon(surf, W, P([(41, 56), (59, 56), (68, 75), (32, 75)]))
        pygame.draw.ellipse(surf, W, R(33, 50, 34, 10))
        pygame.draw.ellipse(surf, W, R(35, 16, 30, 40))
        pygame.draw.polygon(surf, W, P([(40, 26), (50, 8), (60, 26)]))
        pygame.draw.circle(surf, W, (50 * u, 11 * u), 5.5 * u)
        pygame.draw.line(det, W, (56 * u, 25 * u), (46 * u, 38 * u), lw)
    elif kind == "N":
        pygame.draw.polygon(surf, W, P([(30, 75), (70, 75), (69, 58), (71, 40), (67, 26), (59, 17), (53, 15),
                                        (51, 6), (45, 13), (41, 10), (39, 18), (29, 26), (21, 40), (19, 48),
                                        (23, 55), (31, 55), (39, 48), (47, 46), (41, 58), (33, 67)]))
        pygame.draw.circle(det, W, (45 * u, 27 * u), 3.2 * u)
        pygame.draw.lines(det, W, False, P([(59, 22), (65, 34), (66, 50), (64, 66)]), lw)
    elif kind == "Q":
        pygame.draw.polygon(surf, W, P([(38, 50), (62, 50), (70, 75), (30, 75)]))
        pygame.draw.ellipse(surf, W, R(31, 43, 38, 11))
        pygame.draw.polygon(surf, W, P([(31, 46), (22, 20), (38, 33), (50, 12), (62, 33), (78, 20), (69, 46)]))
        for x, y in ((22, 18), (50, 10), (78, 18), (36, 28), (64, 28)):
            pygame.draw.circle(surf, W, (x * u, y * u), 4.6 * u)
        pygame.draw.line(det, W, (33 * u, 48 * u), (67 * u, 48 * u), lw)
    elif kind == "K":
        pygame.draw.polygon(surf, W, P([(38, 50), (62, 50), (70, 75), (30, 75)]))
        pygame.draw.ellipse(surf, W, R(31, 43, 38, 11))
        pygame.draw.polygon(surf, W, P([(32, 46), (26, 26), (74, 26), (68, 46)]))
        pygame.draw.ellipse(surf, W, R(26, 20, 48, 12))
        pygame.draw.rect(surf, W, R(45.5, 3, 9, 22), border_radius=int(2 * u))
        pygame.draw.rect(surf, W, R(39, 8, 22, 8), border_radius=int(2 * u))
        pygame.draw.line(det, W, (33 * u, 48 * u), (67 * u, 48 * u), lw)
        pygame.draw.line(det, W, (30 * u, 32 * u), (70 * u, 32 * u), lw)
    return pygame.mask.from_surface(surf, 100), pygame.mask.from_surface(det, 100)


def _compose(set_name, piece, size):
    kind = piece.upper()
    white = piece.isupper()
    hi = size * SS
    out = pygame.Surface((hi, hi), pygame.SRCALPHA)

    if set_name == "modern":
        sil, det = _modern_masks(kind, hi)
        strokes = None
        details = det
    else:
        sil, strokes, solid = _glyph_masks(kind, hi)
        details = sil.copy()
        details.erase(solid, (0, 0))    # the light lines inside a black glyph

    # soft drop shadow
    shadow = _mask_surface(sil, (0, 0, 0, 120))
    out.blit(blur(shadow, 6), (int(hi * 0.025), int(hi * 0.05)))

    if set_name == "neon":
        col = (80, 230, 255) if white else (255, 90, 200)
        body = _fill(sil, gradient((hi, hi), (34, 40, 70), (12, 14, 28)))
        body.set_alpha(225)
        out.blit(body, (0, 0))
        line_mask = strokes if white else _dilate(sil, max(1, hi // 70))
        if not white:
            line_mask.erase(sil, (0, 0))
            line_mask.draw(details, (0, 0))
        glow = _mask_surface(_dilate(line_mask, max(2, hi // 45)), (*col, 255))
        g = blur(glow, 5)
        out.blit(g, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        out.blit(_mask_surface(line_mask, (*[min(255, c + 90) for c in col], 255)), (0, 0))
        return pygame.transform.smoothscale(out, (size, size))

    rim = _dilate(sil, max(2, hi // 48))
    if set_name == "classic":
        if white:
            fill = gradient((hi, hi), (255, 251, 238), (214, 196, 160))
            edge, line = (48, 34, 24), (60, 44, 30)
        else:
            fill = gradient((hi, hi), (78, 66, 60), (18, 14, 14))
            edge, line = (10, 8, 8), (214, 196, 168)
    elif set_name == "wood":
        if white:
            fill = _wood_texture((hi, hi), (226, 190, 136), (160, 112, 62), seed=ord(kind), vertical=True)
            edge, line = (76, 46, 22), (110, 70, 34)
        else:
            fill = _wood_texture((hi, hi), (104, 52, 34), (40, 16, 8), seed=ord(kind) + 50, vertical=True)
            edge, line = (26, 10, 4), (206, 150, 108)
    elif set_name == "tournament":
        if white:
            fill = pygame.Surface((hi, hi))
            fill.fill((252, 252, 252))
            edge, line = (10, 10, 10), (10, 10, 10)
        else:
            fill = pygame.Surface((hi, hi))
            fill.fill((28, 28, 30))
            edge, line = (8, 8, 8), (236, 236, 236)
    else:  # modern
        if white:
            fill = gradient((hi, hi), (255, 255, 255), (200, 208, 222))
            edge, line = (30, 34, 46), (60, 68, 90)
        else:
            fill = gradient((hi, hi), (84, 92, 116), (22, 24, 34))
            edge, line = (6, 8, 12), (170, 190, 230)

    out.blit(_mask_surface(rim, (*edge, 255)), (0, 0))
    out.blit(_fill(sil, fill), (0, 0))
    if set_name in ("classic", "wood", "modern"):
        # a soft highlight on the upper-left of the body
        k = 34 if white else 46
        shine = _fill(sil, gradient((hi, hi), (k, k, k), (0, 0, 0), horizontal=True))
        out.blit(shine, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    if white and strokes is not None:
        out.blit(_mask_surface(strokes, (*line, 255)), (0, 0))
    elif white:
        out.blit(_mask_surface(details, (*line, 255)), (0, 0))
    else:
        out.blit(_mask_surface(details, (*line, 255)), (0, 0))
    return pygame.transform.smoothscale(out, (size, size))


def piece_image(set_name, piece, size):
    key = (set_name, piece, size)
    if key not in _piece_cache:
        _piece_cache[key] = _compose(set_name, piece, size)
    return _piece_cache[key]


def warm_pieces(set_name, size):
    for p in "PNBRQKpnbrqk":
        piece_image(set_name, p, size)


# ---------------------------------------------------------------- diagrams
def draw_position(surface, view, board_sq, theme, pieces, hl=(), marks=(), arrows=(), label_all=False,
                  label_marks=False, coords=False):
    """Draw a static position (used by the tutorial and the style preview)."""
    view.draw_frame(surface, theme)
    view.draw_squares(surface, theme, coords)
    for name in hl:
        view.tint(surface, parse_square(name), (255, 214, 64), 120)
    for i, p in enumerate(board_sq):
        if p != ".":
            surface.blit(piece_image(pieces, p, view.size), view.square_rect(i))
    for name in marks:
        sq = parse_square(name)
        view.dot(surface, sq, (40, 170, 90), capture=board_sq[sq] != ".")
    for a, b in arrows:
        view.arrow(surface, parse_square(a), parse_square(b))
    size = max(11, view.size // 4)
    for sq in range(64):
        name = FILES[sq & 7] + RANKS[sq >> 3]
        if label_all or (label_marks and name in marks):
            r = view.square_rect(sq)
            col = (20, 20, 20) if is_light(sq) else (250, 250, 250)
            if label_marks and not label_all:
                col = (10, 70, 30) if is_light(sq) else (220, 255, 230)
            text(surface, name, r.center, size, col, True, "mono", "center", shadow=False)
