"""How to Play: illustrated pages on the board, the grid, each piece, special rules,
strategy and scoring, ending with an interactive Grid Drill."""
import random

import pygame

from .. import art, i18n
from ..app import Scene
from ..chess import Board, parse_square, square_name
from ..i18n import TUTORIAL, t
from ..ui import Button, TextField


class TutorialScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        self.page = 0
        self.count = len(TUTORIAL) + 1
        self.view = art.BoardView((76, 112, 448, 448))
        self.buttons = [
            Button((560, 640, 180, 48), lambda: "◀ " + t("prev"), self.prev, 20, art.CYAN),
            Button((1050, 640, 180, 48), lambda: t("next") + " ▶", self.next, 20, art.GOLD),
            Button((50, 640, 180, 48), lambda: t("back"), self.back, 20, art.RED),
        ]
        self.rng = random.Random()
        self.drill_field = TextField((620, 330, 300, 70), 2, "e4", 40, "mono", set("abcdefghABCDEFGH12345678"))
        self.drill_target = None
        self.drill_right = 0
        self.drill_tries = 0
        self.drill_msg = ("", art.INK)
        self.drill_flip = False
        self._new_target()

    def _new_target(self):
        prev = self.drill_target
        while self.drill_target == prev:
            self.drill_target = self.rng.randrange(64)
        self.drill_flip = (self.drill_tries // 5) % 2 == 1

    def prev(self):
        self.page = (self.page - 1) % self.count

    def next(self):
        self.page = (self.page + 1) % self.count

    def back(self):
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.back()
            return
        if self.page == self.count - 1:
            res = self.drill_field.handle(event, self.app.audio)
            if res == "submit" and self.drill_field.value:
                guess = parse_square(self.drill_field.value.lower())
                self.drill_tries += 1
                name = square_name(self.drill_target)
                if guess == self.drill_target:
                    self.drill_right += 1
                    self.drill_msg = (t("drill_right", sq=name), art.GREEN)
                    self.drill_field.ok()
                    self.app.audio.play("move")
                else:
                    self.drill_msg = (t("drill_wrong", sq=name), art.RED)
                    self.drill_field.error()
                    self.app.audio.play("error")
                self.drill_field.value = ""
                self._new_target()
            if res:
                return
        if event.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
            self.next()
        elif event.key in (pygame.K_LEFT, pygame.K_PAGEUP):
            self.prev()

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)
        self.drill_field.update(dt)

    def draw(self, surface):
        app = self.app
        app.backdrop.draw(surface, app.time)
        art.text(surface, t("tut_title"), (50, 30), 34, art.GOLD, True, "title")
        art.text(surface, t("page_of", a=self.page + 1, b=self.count), (1230, 44), 18, art.INK_DIM,
                 anchor="topright")
        # progress dots
        for i in range(self.count):
            x = 760 + i * 15
            col = art.GOLD if i == self.page else (70, 80, 110)
            pygame.draw.circle(surface, col, (x, 664), 5 if i == self.page else 4)
        pieces, theme = app.settings["pieces"], app.settings["board"]
        if self.page < len(TUTORIAL):
            title_en, title_ja, lines_en, lines_ja, diag = TUTORIAL[self.page]
            title = title_ja if i18n.ja() else title_en
            lines = lines_ja if i18n.ja() else lines_en
            self.draw_diagram(surface, diag, pieces, theme)
            r = pygame.Rect(570, 100, 666, 520)
            art.panel(surface, r)
            art.text(surface, title, (r.x + 28, r.y + 22), 30, art.GOLD, True)
            y = r.y + 84
            size = 21 if len(lines) <= 5 else 19
            for line in lines:
                pygame.draw.circle(surface, art.CYAN, (r.x + 34, y + size // 2 + 3), 4)
                y = art.text_block(surface, line, (r.x + 50, y, r.w - 80, 200), size, art.INK) + 10
        else:
            self.draw_drill(surface, pieces, theme)
        for b in self.buttons:
            b.draw(surface)

    def draw_diagram(self, surface, diag, pieces, theme):
        board = Board(diag["fen"]) if diag.get("fen") else None
        sq = board.sq if board else ["."] * 64
        marks = list(diag.get("marks", []))
        if diag.get("moves_of"):
            frm = parse_square(diag["moves_of"])
            board.turn = "w" if sq[frm].isupper() else "b"
            marks += [square_name(m[1]) for m in board.pseudo_moves() if m[0] == frm]
        hl = list(diag.get("hl", []))
        if diag.get("moves_of"):
            hl.append(diag["moves_of"])
        art.draw_position(surface, self.view, sq, theme, pieces, hl=hl, marks=marks,
                          arrows=diag.get("arrows", []), label_all=diag.get("label_all", False),
                          label_marks=diag.get("label_marks", False))
        if diag.get("big_label"):
            r = self.view.square_rect(parse_square(diag["big_label"]))
            art.text(surface, diag["big_label"], r.center, 30, (30, 20, 0), True, "mono", "center", shadow=False)
        if diag.get("caption"):
            art.text(surface, diag["caption"], (self.view.rect.centerx, self.view.rect.bottom + 46), 28, art.GOLD,
                     True, "mono", "center")

    def draw_drill(self, surface, pieces, theme):
        self.view.flipped = self.drill_flip
        self.view.draw_frame(surface, theme)
        self.view.draw_squares(surface, theme)
        r = self.view.square_rect(self.drill_target)
        pulse = 0.5 + 0.5 * abs(((self.app.time * 1.4) % 2) - 1)
        self.view.tint(surface, self.drill_target, (255, 214, 64), int(120 + 100 * pulse))
        pygame.draw.rect(surface, art.GOLD, r, 4)
        self.view.flipped = False
        p = pygame.Rect(570, 100, 666, 520)
        art.panel(surface, p)
        art.text(surface, t("drill_title"), (p.x + 28, p.y + 22), 30, art.GOLD, True)
        art.text_block(surface, t("drill_prompt"), (p.x + 30, p.y + 90, p.w - 60, 80), 21, art.INK)
        view_txt = t("black") if self.drill_flip else t("white")
        art.text(surface, f"{t('you_play')}: {view_txt}", (p.x + 30, p.y + 160), 18, art.CYAN, True)
        self.drill_field.rect.topleft = (p.x + 30, p.y + 210)
        self.drill_field.draw(surface)
        msg, col = self.drill_msg
        if msg:
            art.text(surface, msg, (p.x + 30, p.y + 310), 24, col, True)
        art.text(surface, t("drill_score", r=self.drill_right, t=self.drill_tries), (p.x + 30, p.y + 360), 20,
                 art.INK_DIM, True)
