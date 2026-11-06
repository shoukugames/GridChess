"""Credits and the full GPL v3 license text."""
import pygame

from .. import TITLE, __version__, art
from ..app import Scene
from ..i18n import t
from ..paths import root
from ..ui import Button

RELEASE_DATE = "2026-11-07"


class CreditsScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        self.buttons = [Button((50, 646, 180, 48), lambda: t("back"), self.back, 20, art.RED),
                        Button((880, 646, 350, 48), lambda: t("view_license"), self.license, 18, art.CYAN)]

    def back(self):
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    def license(self):
        self.app.switch(LicenseScene(self.app))

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        app = self.app
        app.backdrop.draw(surface, app.time)
        r = pygame.Rect(140, 40, 1000, 586)
        art.panel(surface, r)
        art.text(surface, "GRID CHESS", (r.centerx, r.y + 46), 50, art.GOLD, True, "title", "center")
        art.text(surface, t("subtitle") + f"  ·  v{__version__}", (r.centerx, r.y + 94), 22, art.CYAN, True,
                 anchor="center")
        rows = [
            (t("release_date"), RELEASE_DATE),
            (t("created_by"), "Shawn Rapaz"),
            (t("made_with"), "Claude Code"),
            (t("website"), "https://shoukugames.org/"),
            (t("email"), "info@shoukugames.org"),
            (t("license"), "GNU General Public License v3.0 (GPL-3.0)"),
        ]
        for i, (a, b) in enumerate(rows):
            y = r.y + 140 + i * 42
            art.text(surface, a, (r.x + 360, y), 21, art.INK_DIM, True, anchor="topright")
            art.text(surface, b, (r.x + 390, y), 22, art.INK, True)
        y = r.y + 410
        y = art.text_block(surface, t("license_text"), (r.x + 80, y, r.w - 160, 80), 16, art.INK_DIM)
        y = art.text_block(surface, t("fonts_credit"), (r.x + 80, y + 8, r.w - 160, 60), 15, art.INK_DIM)
        art.text_block(surface, t("music_credit"), (r.x + 80, y + 4, r.w - 160, 40), 15, art.INK_DIM)
        art.text(surface, t("ages"), (r.centerx, r.bottom - 26), 20, art.GREEN, True, anchor="center")
        for b in self.buttons:
            b.draw(surface)


class LicenseScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        try:
            with open(f"{root()}/LICENSE", encoding="utf-8") as handle:
                raw = handle.read()
        except OSError:
            raw = "GNU GENERAL PUBLIC LICENSE Version 3 - https://www.gnu.org/licenses/gpl-3.0.html"
        self.lines = []
        for para in raw.split("\n"):
            self.lines.extend(art.wrap(para, 1080, 15) if para.strip() else [""])
        self.scroll = 0
        self.buttons = [Button((50, 656, 180, 44), lambda: t("back"), self.back, 20, art.RED)]

    def back(self):
        self.app.switch(CreditsScene(self.app))

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        if event.type == pygame.MOUSEWHEEL:
            self.scroll -= event.y * 3
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.back()
            elif event.key in (pygame.K_DOWN, pygame.K_j):
                self.scroll += 2
            elif event.key in (pygame.K_UP, pygame.K_k):
                self.scroll -= 2
            elif event.key in (pygame.K_PAGEDOWN, pygame.K_SPACE):
                self.scroll += 28
            elif event.key == pygame.K_PAGEUP:
                self.scroll -= 28
        self.scroll = max(0, min(self.scroll, len(self.lines) - 28))

    def update(self, dt):
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        self.app.backdrop.draw(surface, self.app.time)
        r = pygame.Rect(60, 30, 1160, 610)
        art.panel(surface, r)
        art.text(surface, f"{TITLE} — GPL-3.0", (r.x + 30, r.y + 14), 18, art.GOLD, True)
        clip = surface.get_clip()
        surface.set_clip(r.inflate(-20, -60).move(0, 20))
        for i, line in enumerate(self.lines[self.scroll:self.scroll + 30]):
            art.text(surface, line, (r.x + 40, r.y + 52 + i * 19), 15, art.INK, shadow=False)
        surface.set_clip(clip)
        frac = self.scroll / max(1, len(self.lines) - 28)
        pygame.draw.rect(surface, (50, 60, 90), (r.right - 14, r.y + 50, 6, r.h - 70), border_radius=3)
        pygame.draw.rect(surface, art.CYAN, (r.right - 14, r.y + 50 + (r.h - 110) * frac, 6, 40), border_radius=3)
        art.text(surface, "↑ ↓  PgUp PgDn", (r.right - 20, r.bottom + 30), 14, art.INK_DIM, anchor="topright")
        for b in self.buttons:
            b.draw(surface)
