"""Choose the piece set and board theme, with a live preview."""
import pygame

from .. import art
from ..app import Scene
from ..chess import Board
from ..i18n import t
from ..ui import Button, Segmented

PREVIEW_FEN = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 1"


class StyleScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        s = app.settings
        self.view = art.BoardView((70, 96, 512, 512))
        self.board = Board(PREVIEW_FEN)
        self.buttons = [Button((50, 646, 180, 48), lambda: t("back"), self.back, 20, art.RED)]
        x = 650
        for i, name in enumerate(art.PIECE_SETS):
            self.buttons.append(Button((x, 130 + i * 52, 270, 44), (lambda n=name: t("set_" + n)),
                                       (lambda n=name: self._set("pieces", n)), 18,
                                       art.GOLD))
        for i, name in enumerate(art.BOARD_ORDER):
            self.buttons.append(Button((x + 300, 130 + i * 52, 270, 44), (lambda n=name: t("board_" + n)),
                                       (lambda n=name: self._set("board", n)), 18, art.CYAN))
        self.coords = Segmented((x, 520, 300, 42), [(True, lambda: t("on")), (False, lambda: t("off"))],
                                lambda: s.get("coords", True), lambda v: self._set("coords", v), accent=art.GREEN)

    def _set(self, key, value):
        self.app.settings[key] = value
        self.app.save()

    def back(self):
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        if self.coords.handle(event, self.app.audio):
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        app = self.app
        s = app.settings
        app.backdrop.draw(surface, app.time)
        art.text(surface, t("style_title"), (50, 26), 34, art.GOLD, True, "title")
        art.draw_position(surface, self.view, self.board.sq, s["board"], s["pieces"], hl=["c4", "f7"],
                          arrows=[("f3", "g5")], coords=s.get("coords", True))
        art.text(surface, t("piece_set"), (650, 98), 20, art.GOLD, True)
        art.text(surface, t("board_theme"), (950, 98), 20, art.CYAN, True)
        for b in self.buttons:
            b.draw(surface)
        # mark the chosen ones
        for b in self.buttons[1:]:
            name = None
            for n in art.PIECE_SETS:
                if b.text() == t("set_" + n) and s["pieces"] == n:
                    name = n
            for n in art.BOARD_ORDER:
                if b.text() == t("board_" + n) and s["board"] == n:
                    name = n
            if name:
                pygame.draw.rect(surface, art.GREEN, b.rect.inflate(6, 6), 3, border_radius=14)
                art.text(surface, "✓", (b.rect.right - 22, b.rect.centery), 22, art.GREEN, True, "glyph", "center")
        art.text(surface, t("show_coords"), (650, 490), 18, art.INK_DIM, True)
        self.coords.draw(surface)
        # mini row of every piece in the chosen set
        x = 650
        for i, p in enumerate("KQRBNPkqrbnp"):
            surface.blit(art.piece_image(s["pieces"], p, 46), (x + (i % 12) * 48, 590))
