"""Window, main loop and screen switching.

The game draws onto a fixed 1280 x 720 canvas which is scaled to fit the window,
so it looks the same at any window size or in full screen (F11).
"""
import math
import os
import random
import sys
import traceback

import pygame

from . import TITLE, __version__, art, i18n, storage
from .audio import Audio
from .paths import asset

W, H = 1280, 720


class Scene:
    music = "title"

    def __init__(self, app):
        self.app = app

    def enter(self):
        pass

    def leave(self):
        pass

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surface):
        pass


class Backdrop:
    """Calm animated background: a faint perspective grid and drifting chess pieces."""

    def __init__(self, seed=3):
        rng = random.Random(seed)
        self.floaters = []
        for _ in range(14):
            self.floaters.append({
                "piece": rng.choice("KQRBNPkqrbnp"), "x": rng.uniform(0, W), "y": rng.uniform(0, H),
                "size": rng.choice((48, 64, 80, 96)), "speed": rng.uniform(6, 16),
                "phase": rng.uniform(0, 6.28), "alpha": rng.randint(18, 40)})
        self.base = None
        self.sprites = {}

    def _build(self):
        self.base = art.background((W, H)).copy()
        grid = pygame.Surface((W, H), pygame.SRCALPHA)
        horizon = 250
        for i in range(-12, 13):
            x = W / 2 + i * 120
            pygame.draw.line(grid, (90, 120, 200, 26), (W / 2 + i * 14, horizon), (x * 1.0 + (x - W / 2) * 1.6, H), 1)
        y, step = horizon, 6
        while y < H:
            pygame.draw.line(grid, (90, 120, 200, 22), (0, y), (W, y), 1)
            y += step
            step *= 1.22
        self.base.blit(grid, (0, 0))

    def draw(self, surface, t):
        if self.base is None:
            self._build()
        surface.blit(self.base, (0, 0))
        for f in self.floaters:
            key = (f["piece"], f["size"], f["alpha"])
            if key not in self.sprites:
                img = art.piece_image("neon", f["piece"], f["size"]).copy()
                img.set_alpha(f["alpha"])
                self.sprites[key] = img
            y = (f["y"] - t * f["speed"]) % (H + 120) - 60
            x = f["x"] + math.sin(t * 0.3 + f["phase"]) * 24
            surface.blit(self.sprites[key], (x, y))


class App:
    def __init__(self, windowed=False, smoke=False):
        os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
        pygame.mixer.pre_init(44100, -16, 2, 1024)
        pygame.init()
        pygame.key.set_repeat(400, 40)
        self.settings = storage.load_settings()
        i18n.LANG["current"] = self.settings["language"]
        self.smoke = smoke
        pygame.display.set_caption(f"{TITLE} v{__version__}")
        try:
            pygame.display.set_icon(pygame.image.load(asset("icon.png")))
        except (pygame.error, FileNotFoundError):
            pass
        self.fullscreen = self.settings.get("fullscreen", False) and not windowed and not smoke
        self._make_window()
        self.canvas = pygame.Surface((W, H)).convert()
        self.audio = Audio(self.settings)
        self.backdrop = Backdrop()
        self.time = 0.0
        self.scene = None
        self.running = True
        self.mouse = (0, 0)

    def _make_window(self):
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            info = pygame.display.Info()
            w, h = W, H
            if info.current_w and info.current_w < W + 40:
                scale = (info.current_w - 60) / W
                w, h = int(W * scale), int(H * scale)
            self.window = pygame.display.set_mode((w, h), pygame.RESIZABLE)

    def save(self):
        storage.save_settings(self.settings)

    def switch(self, scene):
        if self.scene:
            self.scene.leave()
        self.scene = scene
        self.audio.music(scene.music)
        scene.enter()

    def set_language(self, code):
        self.settings["language"] = code
        i18n.LANG["current"] = code
        self.save()

    def toggle_bgm(self):
        self.audio.toggle_bgm(self.scene.music if self.scene else "title")
        self.save()

    def _transform(self):
        ww, wh = self.window.get_size()
        scale = min(ww / W, wh / H)
        return scale, (ww - W * scale) / 2, (wh - H * scale) / 2

    def to_canvas(self, pos):
        scale, ox, oy = self._transform()
        return (int((pos[0] - ox) / scale), int((pos[1] - oy) / scale))

    def present(self):
        scale, ox, oy = self._transform()
        if abs(scale - 1) < 0.001 and ox == 0 and oy == 0:
            self.window.blit(self.canvas, (0, 0))
        else:
            self.window.fill((0, 0, 0))
            size = (int(W * scale), int(H * scale))
            self.window.blit(pygame.transform.smoothscale(self.canvas, size), (int(ox), int(oy)))
        pygame.display.flip()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.settings["fullscreen"] = self.fullscreen
        self.save()
        self._make_window()

    def run(self):
        from .scenes.title import TitleScene
        self.switch(TitleScene(self))
        clock = pygame.time.Clock()
        while self.running:
            dt = min(clock.tick(60) / 1000.0, 0.05)
            self.time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and event.mod & pygame.KMOD_ALT)):
                    self.toggle_fullscreen()
                    continue
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                    data = dict(event.dict)
                    data["pos"] = self.to_canvas(event.pos)
                    event = pygame.event.Event(event.type, data)
                self.scene.handle(event)
            self.mouse = self.to_canvas(pygame.mouse.get_pos())
            self.scene.update(dt)
            self.scene.draw(self.canvas)
            self.present()
        self.scene.leave()
        pygame.quit()


def _crash_log(error_text):
    try:
        path = os.path.join(storage.data_dir(), "crash.log")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(f"{TITLE} v{__version__}\n{error_text}")
        return path
    except OSError:
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--version" in argv:
        print(f"{TITLE} v{__version__}")
        return 0
    if "--smoke-test" in argv:
        from .smoke import smoke_test
        i = argv.index("--smoke-test")
        out = argv[i + 1] if i + 1 < len(argv) else None
        return smoke_test(out)
    try:
        App(windowed="--windowed" in argv).run()
    except Exception:  # noqa: BLE001 - last-chance crash report
        text = traceback.format_exc()
        print(text, file=sys.stderr)
        _crash_log(text)
        return 1
    return 0
