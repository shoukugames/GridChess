"""Title screen: main menu, language / difficulty / music toggles, a live demo board and the top 10."""
import math
import random

import pygame

from .. import __version__, art, storage
from ..app import Scene, W, H
from ..chess import Board
from ..i18n import t
from ..ui import Button, Segmented

TURN_SECONDS = {"easy": 60, "medium": 60, "hard": 30}


class TitleScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        s = app.settings
        x, y, w, h, gap = 70, 222, 330, 50, 9
        entries = [
            (lambda: t("play_blitz"), self.play_blitz, art.GOLD),
            (lambda: t("free_play"), self.play_free, art.GREEN),
            (lambda: t("tutorial"), self.tutorial, art.CYAN),
            (lambda: t("parents"), self.parents, art.CYAN),
            (lambda: t("style"), self.style, art.CYAN),
            (lambda: t("credits"), self.credits, art.CYAN),
            (lambda: t("quit"), self.quit, art.RED),
        ]
        self.buttons = [Button((x, y + i * (h + gap), w, h), label, action, 24, accent)
                        for i, (label, action, accent) in enumerate(entries)]
        cx = 450
        self.lang = Segmented((cx, 248, 360, 42), [("en", "English"), ("ja", "日本語")],
                              lambda: s["language"], self._set_lang)
        self.diff = Segmented((cx, 334, 360, 42), [(d, (lambda d=d: t(d))) for d in storage.DIFFICULTIES],
                              lambda: s["difficulty"], self._set_diff)
        self.bgm = Segmented((cx, 440, 360, 42), [(True, lambda: t("on")), (False, lambda: t("off"))],
                             lambda: s["bgm"], self._set_bgm, accent=art.GREEN)
        self.widgets = [self.lang, self.diff, self.bgm]
        self.scores = storage.load_scores()
        self.demo = Board()
        self.demo_timer = 1.0
        self.demo_last = None
        self.rng = random.Random()
        self.demo_view = art.BoardView((cx + 40, 505, 192, 192))

    def enter(self):
        self.scores = storage.load_scores()

    # ---------------------------------------------------------- actions
    def _set_lang(self, code):
        self.app.set_language(code)

    def _set_diff(self, d):
        self.app.settings["difficulty"] = d
        self.app.save()

    def _set_bgm(self, on):
        if self.app.settings["bgm"] != on:
            self.app.toggle_bgm()

    def play_blitz(self):
        from .game import GameScene
        self.app.switch(GameScene(self.app, self.app.settings["difficulty"], timed=True))

    def play_free(self):
        from .game import GameScene
        self.app.switch(GameScene(self.app, self.app.settings["difficulty"], timed=False))

    def tutorial(self):
        from .tutorial import TutorialScene
        self.app.switch(TutorialScene(self.app))

    def parents(self):
        from .parents import ParentGateScene
        self.app.switch(ParentGateScene(self.app))

    def style(self):
        from .style import StyleScene
        self.app.switch(StyleScene(self.app))

    def credits(self):
        from .credits import CreditsScene
        self.app.switch(CreditsScene(self.app))

    def quit(self):
        self.app.running = False

    # ---------------------------------------------------------- loop
    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        for wdg in self.widgets:
            if wdg.handle(event, self.app.audio):
                return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.quit()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.play_blitz()

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)
        self.demo_timer -= dt
        if self.demo_timer <= 0:
            self.demo_timer = 1.3
            if self.demo.outcome() or len(self.demo.history) > 120:
                self.demo = Board()
                self.demo_last = None
                return
            moves = self.demo.legal_moves()
            caps = [m for m in moves if self.demo.sq[m[1]] != "."]
            centre = [m for m in moves if m[1] in (27, 28, 35, 36, 19, 20, 21, 42, 43, 44, 45, 18)]
            pool = caps if caps and self.rng.random() < 0.8 else (centre if centre and self.rng.random() < 0.6 else moves)
            m = self.rng.choice(pool)
            self.demo.push(m)
            self.demo_last = m

    def draw(self, surface):
        app = self.app
        app.backdrop.draw(surface, app.time)
        # logo
        pulse = 0.75 + 0.25 * math.sin(app.time * 1.5)
        art.blit_glow(surface, (300, 92), 260, (60, 50, 10), pulse)
        king = art.piece_image(app.settings["pieces"], "K", 104)
        surface.blit(king, (52, 42))
        art.text(surface, "GRID CHESS", (160, 52), 70, art.GOLD, True, "title")
        art.text(surface, t("subtitle"), (166, 132), 30, art.CYAN, True, "title")
        art.text(surface, t("tagline"), (72, 174), 19, art.INK_DIM)

        # settings column
        cx = 450
        art.text(surface, t("language"), (cx + 4, 220), 19, art.INK_DIM, True)
        self.lang.draw(surface)
        art.text(surface, t("difficulty"), (cx + 4, 306), 19, art.INK_DIM, True)
        self.diff.draw(surface)
        d = app.settings["difficulty"]
        art.text(surface, f"{t('play_blitz')}: {t('secs_turn', n=TURN_SECONDS[d])}   ·   {t('free_play')}: {t('free_desc')}",
                 (cx + 4, 382), 15, art.INK_DIM)
        art.text(surface, t("music"), (cx + 4, 412), 19, art.INK_DIM, True)
        self.bgm.draw(surface)

        # live demo board
        v = self.demo_view
        v.draw_frame(surface, app.settings["board"], labels=False)
        v.draw_squares(surface, app.settings["board"])
        if self.demo_last:
            v.tint(surface, self.demo_last[0], (255, 220, 80), 90)
            v.tint(surface, self.demo_last[1], (255, 220, 80), 120)
        for i, p in enumerate(self.demo.sq):
            if p != ".":
                surface.blit(art.piece_image(app.settings["pieces"], p, v.size), v.square_rect(i))
        if self.demo.history:
            art.text(surface, self.demo.history[-1][1], (v.rect.right + 30, v.rect.y + 8), 22, art.GOLD, True, "mono")
            for k, (_m, san) in enumerate(self.demo.history[-6:-1][::-1]):
                art.text(surface, san, (v.rect.right + 30, v.rect.y + 40 + k * 26), 17,
                         art.INK_DIM, True, "mono")

        for b in self.buttons:
            b.draw(surface)

        # top 10
        r = pygame.Rect(860, 40, 380, 590)
        art.panel(surface, r)
        art.text(surface, t("top10"), (r.centerx, r.y + 30), 24, art.GOLD, True, anchor="center")
        pygame.draw.line(surface, art.PANEL_EDGE, (r.x + 20, r.y + 56), (r.right - 20, r.y + 56), 1)
        if not self.scores:
            art.text_block(surface, t("no_scores"), (r.x + 30, r.y + 90, r.w - 60, 200), 19, art.INK_DIM)
        medals = [(255, 210, 80), (210, 220, 235), (220, 150, 90)]
        for i, sc in enumerate(self.scores):
            y = r.y + 76 + i * 51
            if i % 2 == 0:
                band = pygame.Surface((r.w - 24, 46), pygame.SRCALPHA)
                band.fill((255, 255, 255, 10))
                surface.blit(band, (r.x + 12, y - 4))
            col = medals[i] if i < 3 else art.INK
            art.text(surface, f"{i + 1:>2}", (r.x + 26, y + 2), 22, col, True, "mono")
            art.text(surface, sc["name"], (r.x + 72, y - 1), 21, col, True)
            art.text(surface, f"{t(sc.get('difficulty', 'easy'))} · {sc.get('date', '')}", (r.x + 72, y + 23), 13,
                     art.INK_DIM)
            art.text(surface, f"{sc['score']:,}", (r.right - 24, y + 4), 23, art.GOLD, True, "mono", "topright")

        # footer
        art.text(surface, t("ages"), (r.centerx, 660), 20, art.GREEN, True, anchor="center")
        art.text(surface, t("version", v=__version__) + "  ·  shoukugames.org  ·  GPL-3.0", (r.centerx, 690), 14,
                 art.INK_DIM, anchor="center")
        art.text(surface, "F11: full screen", (W - 16, H - 8), 12, (110, 120, 150), anchor="bottomright")
