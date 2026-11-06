"""Parents section: a simple multiplication gate, then the player's progress record."""
import random

import pygame

from .. import art, storage
from ..app import Scene
from ..i18n import t
from ..ui import Button, TextField


class ParentGateScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        rng = random.Random()
        self.a, self.b = rng.randint(6, 12), rng.randint(6, 12)
        self.field = TextField((490, 360, 300, 70), 3, "?", 40, "mono", set("0123456789"))
        self.wrong = False
        self.buttons = [Button((50, 640, 180, 48), lambda: t("back"), self.back, 20, art.RED)]

    def back(self):
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    def handle(self, event):
        for b in self.buttons:
            if b.handle(event, self.app.audio):
                return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.back()
            return
        if self.field.handle(event, self.app.audio) == "submit":
            if self.field.value == str(self.a * self.b):
                self.app.audio.play("click")
                self.app.switch(ParentsScene(self.app))
            else:
                self.wrong = True
                self.field.error()
                self.field.value = ""
                self.app.audio.play("error")

    def update(self, dt):
        self.field.update(dt)
        for b in self.buttons:
            b.update(dt)

    def draw(self, surface):
        self.app.backdrop.draw(surface, self.app.time)
        r = pygame.Rect(340, 170, 600, 360)
        art.panel(surface, r)
        art.text(surface, t("gate_title"), (r.centerx, r.y + 50), 34, art.GOLD, True, anchor="center")
        art.text(surface, t("gate_q", a=self.a, b=self.b), (r.centerx, r.y + 130), 22, art.INK, True,
                 anchor="center")
        self.field.draw(surface)
        if self.wrong:
            art.text(surface, t("gate_wrong"), (r.centerx, r.y + 300), 20, art.RED, True, anchor="center")
        for b in self.buttons:
            b.draw(surface)


class ParentsScene(Scene):
    music = "title"

    def __init__(self, app):
        super().__init__(app)
        self.data = storage.summary()
        self.armed = False
        self.buttons = [Button((50, 650, 180, 46), lambda: t("back"), self.back, 20, art.RED),
                        Button((1000, 650, 240, 46), lambda: t("reset_confirm") if self.armed else t("reset"),
                               self.reset, 16, art.RED)]

    def back(self):
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    def reset(self):
        if not self.armed:
            self.armed = True
            return
        storage.reset_progress()
        self.data = storage.summary()
        self.armed = False

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
        self.app.backdrop.draw(surface, self.app.time)
        d = self.data
        art.text(surface, t("progress_title"), (50, 26), 34, art.GOLD, True, "title")
        dash = "—"
        tiles = [
            (t("games_played"), str(d["played"]), art.INK),
            (t("wins"), str(d["wins"]), art.GREEN),
            (t("losses"), str(d["losses"]), art.RED),
            (t("draws"), str(d["draws"]), art.CYAN),
            (t("avg_move"), t("sec", n=d["avg_time"]) if d["avg_time"] is not None else dash, art.GOLD),
            (t("best_move"), t("sec", n=d["best_time"]) if d["best_time"] is not None else dash, art.GOLD),
            (t("accuracy"), f"{d['accuracy']}%" if d["accuracy"] is not None else dash, art.CYAN),
            (t("total_moves"), str(d["valid"]), art.INK),
            (t("timeouts"), str(d["timeouts"]), art.RED),
            (t("best_score"), f"{d['best_score']:,}", art.GOLD),
        ]
        tw, th = 230, 84
        for i, (label, value, col) in enumerate(tiles):
            x = 50 + (i % 5) * (tw + 13)
            y = 84 + (i // 5) * (th + 12)
            art.panel(surface, (x, y, tw, th), radius=12)
            art.text(surface, label, (x + 14, y + 10), 15, art.INK_DIM, True)
            art.text(surface, value, (x + 14, y + 30), 32, col, True, "num")

        # speed chart (oldest to newest, last 12 games)
        games = list(reversed(d["recent"]))
        chart = pygame.Rect(50, 290, 520, 340)
        art.panel(surface, chart)
        art.text_block(surface, t("speed_chart"), (chart.x + 18, chart.y + 12, chart.w - 36, 50), 15, art.INK_DIM)
        plot = pygame.Rect(chart.x + 50, chart.y + 70, chart.w - 74, chart.h - 110)
        times = [g.get("avg_time") for g in games]
        valid = [x for x in times if x is not None]
        if not valid:
            art.text(surface, t("no_games"), plot.center, 18, art.INK_DIM, anchor="center")
        else:
            top = max(10, int(max(valid) / 10 + 1) * 10)
            for k in range(0, top + 1, max(5, top // 4)):
                y = plot.bottom - plot.h * k / top
                pygame.draw.line(surface, (50, 64, 100), (plot.x, y), (plot.right, y), 1)
                art.text(surface, str(k), (plot.x - 8, y), 13, art.INK_DIM, anchor="midright", shadow=False)
            n = len(times)
            bw = plot.w / max(n, 1)
            for i, (g, v) in enumerate(zip(games, times)):
                if v is None:
                    continue
                h = plot.h * v / top
                col = {"win": art.GREEN, "draw": art.CYAN}.get(g.get("result"), art.RED)
                bar = pygame.Rect(int(plot.x + i * bw + bw * 0.2), int(plot.bottom - h), max(4, int(bw * 0.6)), int(h))
                pygame.draw.rect(surface, col, bar, border_radius=4)
                art.text(surface, f"{v:.0f}", (bar.centerx, bar.y - 4), 12, art.INK, anchor="midbottom", shadow=False)
            pygame.draw.line(surface, art.INK_DIM, (plot.x, plot.bottom), (plot.right, plot.bottom), 2)
            for i, (label, col) in enumerate(((t("res_win"), art.GREEN), (t("res_draw"), art.CYAN),
                                               (t("res_loss"), art.RED))):
                x = plot.x + i * 110
                pygame.draw.rect(surface, col, (x, chart.bottom - 26, 14, 14), border_radius=3)
                art.text(surface, label, (x + 20, chart.bottom - 28), 14, art.INK_DIM, shadow=False)

        # recent games table
        tbl = pygame.Rect(590, 290, 650, 340)
        art.panel(surface, tbl)
        art.text(surface, t("recent_games"), (tbl.x + 18, tbl.y + 12), 18, art.GOLD, True)
        cols = [(t("col_date"), 18), (t("col_mode"), 170), (t("col_result"), 330), (t("col_score"), 430),
                (t("col_moves"), 520), (t("col_avg"), 590)]
        for label, x in cols:
            art.text(surface, label, (tbl.x + x, tbl.y + 46), 14, art.INK_DIM, True, shadow=False)
        if not d["recent"]:
            art.text(surface, t("no_games"), tbl.center, 18, art.INK_DIM, anchor="center")
        for i, g in enumerate(d["recent"][:10]):
            y = tbl.y + 72 + i * 26
            res = g.get("result", "quit")
            col = {"win": art.GREEN, "draw": art.CYAN}.get(res, art.RED)
            mode = (t("mode_blitz") if g.get("mode") == "blitz" else t("mode_free")) + " " + t(g.get("difficulty", "easy"))
            cells = [(g.get("when", ""), art.INK, 18), (mode, art.INK, 170), (t("res_" + res), col, 330),
                     (f"{g.get('score', 0):,}", art.GOLD, 430), (str(g.get("moves", 0)), art.INK, 520),
                     (str(g.get("avg_time") if g.get("avg_time") is not None else "—"), art.INK, 590)]
            for value, c, x in cells:
                art.text(surface, value, (tbl.x + x, y), 14, c, shadow=False)
        for b in self.buttons:
            b.draw(surface)
