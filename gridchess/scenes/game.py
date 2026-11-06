"""The game: the player types every move against the CPU, racing the turn clock."""
import math
import random
import threading
import time

import pygame

from .. import art, storage
from ..ai import Searcher
from ..app import Scene, W, H
from ..chess import Board, WHITE, BLACK, parse_square, square_name
from ..i18n import t, piece_name
from ..ui import Button, TextField, Popups, Particles

POINTS = {"P": 100, "N": 200, "B": 300, "R": 400, "Q": 500}
MATE_BONUS = 1000
START_POINTS = 1000
TIMEOUT_PENALTY = 500
TIMEOUT_BONUS_SECONDS = 10
TURN_SECONDS = {"easy": 60, "medium": 60, "hard": 30}
ANIM_SECONDS = 0.26
CPU_MIN_SECONDS = 0.7
MOVE_CHARS = set("abcdefghABCDEFGH12345678NBRQKnbrqkxX+#=-oO0 :")


class GameScene(Scene):
    music = "game"

    def __init__(self, app, difficulty="easy", timed=True, player_color=None, seed=None):
        super().__init__(app)
        self.rng = random.Random(seed)
        self.difficulty = difficulty
        self.timed = timed
        self.player = player_color or self.rng.choice((WHITE, BLACK))
        self.cpu = BLACK if self.player == WHITE else WHITE
        self.board = Board()
        self.view = art.BoardView((68, 56, 608, 608), flipped=self.player == BLACK)
        self.searcher = Searcher(difficulty, random.Random(seed))
        self.score = START_POINTS
        self.turn_limit = TURN_SECONDS[difficulty]
        self.time_left = self.turn_limit
        self.turn_elapsed = 0.0
        self.stats = {"valid": 0, "invalid": 0, "timeouts": 0, "move_times": []}
        self.won, self.lost = [], []          # pieces captured by / from the player
        self.field = TextField((712, 548, 538, 70), 10, t("type_move"), 38, "mono", MOVE_CHARS)
        self.message = ("", art.INK, 0.0)
        # Movement guide (highlighted piece, destination dots, move arrow) on Easy only
        self.guide = difficulty == "easy"
        self.preview_from = None
        self.preview_dests = []
        self.preview_move = None
        self.last_move = None
        self.anim = None
        self.thinking = None
        self.cpu_started = 0.0
        self.over = None
        self.leave_confirm = False
        self.banner = 2.6
        self.popups = Popups()
        self.particles = Particles()
        self.last_tick = None
        self.name_field = None
        self.saved_rank = None
        self.recorded = False
        self.hover_sq = None
        self.check_flash = 0.0
        self.pieces = app.settings["pieces"]
        self.theme = app.settings["board"]
        art.warm_pieces(self.pieces, self.view.size)
        bx = 712
        self.buttons = [
            Button((bx, 664, 260, 42), lambda: f"♪ {t('music')}: {t('on') if self.app.settings['bgm'] else t('off')}",
                   self.app.toggle_bgm, 19, art.GREEN),
            Button((bx + 278, 664, 260, 42), lambda: t("menu"), self.ask_leave, 19, art.RED),
        ]
        self.leave_buttons = [
            Button((440, 390, 190, 50), lambda: t("leave_yes"), self.quit_game, 22, art.RED),
            Button((650, 390, 190, 50), lambda: t("leave_no"), self.cancel_leave, 22, art.GREEN),
        ]
        self.over_buttons = [
            Button((420, 560, 210, 52), lambda: t("play_again"), self.play_again, 22, art.GOLD),
            Button((650, 560, 210, 52), lambda: t("to_title"), self.to_title, 22, art.CYAN),
        ]

    # ---------------------------------------------------------- lifecycle
    def enter(self):
        self.app.audio.play("start")
        self.say(t("you_are_white") if self.player == WHITE else t("you_are_black"), art.GOLD, 5)
        if self.board.turn == self.player:
            self.begin_player_turn()

    def leave(self):
        self.thinking = None

    # ---------------------------------------------------------- helpers
    def say(self, text, color=art.INK, seconds=4.0):
        self.message = (text, color, seconds)

    def player_turn(self):
        return self.board.turn == self.player and not self.anim and not self.over

    def begin_player_turn(self):
        self.time_left = self.turn_limit
        self.turn_elapsed = 0.0
        self.field.active = True
        self.last_tick = None
        if self.board.in_check():
            self.say(t("you_in_check"), art.RED, 5)

    def sq_center(self, sq):
        return self.view.square_rect(sq).center

    # ---------------------------------------------------------- input preview
    def update_preview(self):
        text = self.field.value.strip()
        self.preview_from, self.preview_dests, self.preview_move = None, [], None
        if not text or not self.guide:
            return
        low = text.lower()
        frm = parse_square(low[:2]) if len(low) >= 2 else None
        if frm is not None and self.board.sq[frm] != "." and (self.board.sq[frm].isupper() == (self.player == WHITE)):
            self.preview_from = frm
            self.preview_dests = sorted({m[1] for m in self.board.piece_moves_from(frm)})
            if len(low) == 2:
                p = piece_name(self.board.sq[frm])
                if self.preview_dests:
                    self.say(t("selected", piece=p, sq=square_name(frm),
                               list=", ".join(square_name(s) for s in self.preview_dests)), art.CYAN, 6)
                else:
                    self.say(t("selected_none", piece=p, sq=square_name(frm)), art.INK_DIM, 4)
        if len(text) >= 2:
            move, _err = self.board.parse(text)
            if move:
                self.preview_move = move

    def submit(self):
        text = self.field.value.strip()
        move, err = self.board.parse(text)
        if move is None:
            self.stats["invalid"] += 1
            self.field.error()
            self.app.audio.play("error")
            hint = ""
            if self.preview_from is not None and err == "illegal":
                dests = self.preview_dests
                hint = t("hint_from", piece=piece_name(self.board.sq[self.preview_from]),
                         sq=square_name(self.preview_from),
                         list=", ".join(square_name(s) for s in dests) or "—")
            color_name = t("white") if self.player == WHITE else t("black")
            self.say(t("err_" + err, t=text, hint=hint, c=color_name), art.RED, 6)
            return
        self.stats["valid"] += 1
        self.stats["move_times"].append(self.turn_elapsed)
        self.field.ok()
        self.field.value = ""
        self.field.active = False
        self.update_preview()
        promo_tip = move[2] == "q" and not text.lower().rstrip("+#!? ").endswith("q")
        self.play_move(move, by_player=True)
        if move[2]:
            self.say(t("promoted", p=piece_name(move[2])) + ("  " + t("auto_queen") if promo_tip else ""), art.GOLD, 6)

    # ---------------------------------------------------------- moves
    def play_move(self, move, by_player):
        piece = self.board.sq[move[0]]
        ep_capture = piece.upper() == "P" and move[1] == self.board.ep and self.board.sq[move[1]] == "."
        cap_sq = (move[1] - 8 if piece == "P" else move[1] + 8) if ep_capture else move[1]
        info = self.board.push(move)
        rook = None
        if info["castle"]:
            if move[1] > move[0]:
                rook = (move[0] + 3, move[0] + 1)
            else:
                rook = (move[0] - 4, move[0] - 1)
        self.anim = {"piece": piece, "from": move[0], "to": move[1], "t": 0.0, "rook": rook,
                     "captured": info["captured"], "cap_sq": cap_sq, "by_player": by_player, "info": info}
        self.last_move = move
        audio = self.app.audio
        if info["check"]:
            audio.play("check")
        elif info["promotion"]:
            audio.play("promote")
        elif info["captured"] != ".":
            audio.play("capture")
        elif info["castle"]:
            audio.play("castle")
        else:
            audio.play("move" if by_player else "cpu")
        if info["captured"] != ".":
            kind = info["captured"].upper()
            if by_player:
                self.won.append(info["captured"])
                pts = POINTS.get(kind, 0)
                self.score += pts
                self.popups.add(f"+{pts}", self.sq_center(cap_sq), art.GOLD, 36)
                self.particles.burst(self.sq_center(cap_sq), art.GOLD)
            else:
                self.lost.append(info["captured"])
                self.particles.burst(self.sq_center(cap_sq), (255, 120, 120), 18, 160)

    def finish_animation(self):
        info = self.anim["info"]
        self.anim = None
        if info["check"]:
            self.check_flash = 1.2
        outcome = self.board.outcome()
        if outcome:
            result, reason = outcome
            if result == "draw":
                self.end_game("draw", reason)
            elif result == ("white" if self.player == WHITE else "black"):
                self.score += MATE_BONUS
                self.popups.add(f"+{MATE_BONUS}", self.sq_center(self.board.kings[self.cpu]), art.GOLD, 48, 2.2)
                for _ in range(4):
                    self.particles.burst((self.rng.randint(150, 600), self.rng.randint(120, 600)),
                                         self.rng.choice([art.GOLD, art.CYAN, art.GREEN]), 40, 300)
                self.end_game("win", reason)
            else:
                self.end_game("loss", reason)
            return
        if self.board.turn == self.player:
            self.begin_player_turn()
            if info["check"]:
                self.say(t("you_in_check"), art.RED, 5)
        else:
            self.field.active = False

    def start_cpu(self):
        holder = {"move": None, "done": False}
        board = self.board.copy()

        def work():
            try:
                holder["move"] = self.searcher.choose(board)
            finally:
                holder["done"] = True
        self.thinking = holder
        self.cpu_started = time.time()
        threading.Thread(target=work, daemon=True).start()

    def timeout(self):
        self.score -= TIMEOUT_PENALTY
        self.stats["timeouts"] += 1
        self.time_left = TIMEOUT_BONUS_SECONDS
        self.app.audio.play("timeout")
        self.popups.add(f"-{TIMEOUT_PENALTY}", (390, 360), art.RED, 54, 2.0)
        self.say(t("timeout_msg"), art.RED, 5)
        self.field.error()
        if self.score <= 0:
            self.end_game("points", "points")

    # ---------------------------------------------------------- end of game
    def end_game(self, result, reason):
        self.over = {"result": result, "reason": reason, "t": 0.0}
        self.field.active = False
        self.thinking = None
        audio = self.app.audio
        audio.play({"win": "win", "draw": "draw"}.get(result, "lose"))
        self.record(result, reason)
        if self.timed and result != "quit" and storage.qualifies(self.score):
            self.name_field = TextField((440, 476, 400, 60), 12, t("enter_save"), 30, "body")
            self.name_field.value = self.app.settings.get("last_name", "")

    def record(self, result, reason):
        if self.recorded:
            return
        self.recorded = True
        storage.record_game({
            "mode": "blitz" if self.timed else "free", "difficulty": self.difficulty,
            "color": self.player, "result": result, "reason": reason, "score": self.score,
            "moves": self.stats["valid"], "valid": self.stats["valid"], "invalid": self.stats["invalid"],
            "timeouts": self.stats["timeouts"], "move_times": self.stats["move_times"],
        })

    def save_name(self):
        name = self.name_field.value.strip() or "PLAYER"
        self.app.settings["last_name"] = name
        self.app.save()
        rank = storage.add_score(name, self.score, self.difficulty, self.over["result"])
        self.saved_rank = rank + 1 if rank >= 0 else None
        self.name_field = None
        self.app.audio.play("new_record")

    def ask_leave(self):
        if not self.over:
            self.leave_confirm = True

    def cancel_leave(self):
        self.leave_confirm = False

    def quit_game(self):
        if not self.over and not self.recorded:
            self.record("quit", "quit")
        self.thinking = None
        self.to_title()

    def play_again(self):
        if self.name_field:
            self.save_name()
        self.app.switch(GameScene(self.app, self.difficulty, self.timed))

    def to_title(self):
        if self.name_field:
            self.save_name()
        self.thinking = None
        from .title import TitleScene
        self.app.switch(TitleScene(self.app))

    # ---------------------------------------------------------- events
    def handle(self, event):
        audio = self.app.audio
        if self.over:
            if self.name_field:
                res = self.name_field.handle(event, audio)
                if res == "submit":
                    self.save_name()
                    return
                if event.type == pygame.KEYDOWN:
                    return
            for b in self.over_buttons:
                if b.handle(event, audio):
                    return
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE) and self.over["t"] > 1:
                self.to_title()
            return
        if self.leave_confirm:
            for b in self.leave_buttons:
                if b.handle(event, audio):
                    return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.cancel_leave()
                elif event.key == pygame.K_RETURN:
                    self.quit_game()
            return
        for b in self.buttons:
            if b.handle(event, audio):
                return
        if event.type == pygame.MOUSEMOTION:
            self.hover_sq = self.view.square_at(event.pos)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.ask_leave()
            return
        if self.banner > 0.4:
            if event.type == pygame.KEYDOWN or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                self.banner = 0.4      # any key or click skips the intro banner
            return
        if self.player_turn():
            res = self.field.handle(event, audio)
            if res == "submit":
                self.submit()
            elif res == "changed":
                self.update_preview()

    # ---------------------------------------------------------- update
    def update(self, dt):
        self.field.update(dt)
        self.popups.update(dt)
        self.particles.update(dt)
        self.banner = max(0.0, self.banner - dt)
        self.check_flash = max(0.0, self.check_flash - dt)
        for b in self.buttons + self.leave_buttons + self.over_buttons:
            b.update(dt)
        text, color, left = self.message
        if left > 0:
            self.message = (text, color, left - dt)
        if self.name_field:
            self.name_field.update(dt)
        if self.over:
            self.over["t"] += dt
            return
        if self.anim:
            self.anim["t"] += dt / ANIM_SECONDS
            if self.anim["t"] >= 1:
                self.finish_animation()
            return
        if self.board.turn == self.player:
            if self.banner <= 0:
                self.turn_elapsed += dt
            if self.timed and self.banner <= 0:
                self.time_left -= dt
                sec = math.ceil(self.time_left)
                if self.time_left <= 10 and sec != self.last_tick and sec > 0:
                    self.last_tick = sec
                    self.app.audio.play("tick")
                if self.time_left <= 0:
                    self.timeout()
        else:
            if self.thinking is None:
                if self.banner < 1.6:
                    self.start_cpu()
            elif self.thinking["done"] and time.time() - self.cpu_started >= CPU_MIN_SECONDS:
                move = self.thinking["move"]
                self.thinking = None
                if move:
                    self.play_move(move, by_player=False)

    # ---------------------------------------------------------- drawing
    def draw(self, surface):
        app = self.app
        app.backdrop.draw(surface, app.time)
        v = self.view
        v.draw_frame(surface, self.theme)
        v.draw_squares(surface, self.theme, app.settings.get("coords", True))
        if self.last_move:
            v.tint(surface, self.last_move[0], (255, 214, 64), 80)
            v.tint(surface, self.last_move[1], (255, 214, 64), 120)
        if self.board.in_check() and not self.anim:
            k = self.board.kings[self.board.turn]
            pulse = 0.6 + 0.4 * math.sin(app.time * 6)
            v.tint(surface, k, (255, 40, 40), int(90 + 60 * pulse))
        if self.preview_from is not None:
            v.tint(surface, self.preview_from, (60, 200, 255), 120)
            v.ring(surface, self.preview_from, (90, 220, 255))
        if self.preview_move:
            v.tint(surface, self.preview_move[1], (90, 230, 120), 120)
        # pieces
        hidden = set()
        if self.anim:
            hidden.add(self.anim["to"])
            if self.anim["rook"]:
                hidden.add(self.anim["rook"][1])
        size = v.size
        for i, p in enumerate(self.board.sq):
            if p != "." and i not in hidden:
                surface.blit(art.piece_image(self.pieces, p, size), v.square_rect(i))
        for sq in self.preview_dests:
            v.dot(surface, sq, (40, 190, 255), capture=self.board.sq[sq] != ".")
        if self.anim:
            a = self.anim
            k = 1 - (1 - min(1.0, a["t"])) ** 3
            if a["captured"] != ".":
                img = art.piece_image(self.pieces, a["captured"], size).copy()
                img.set_alpha(int(255 * (1 - k)))
                surface.blit(img, v.square_rect(a["cap_sq"]))
            moving = [(a["piece"] if not a["info"]["promotion"] or k < 0.9 else self.board.sq[a["to"]], a["from"], a["to"])]
            if a["rook"]:
                moving.append((self.board.sq[a["rook"][1]], a["rook"][0], a["rook"][1]))
            for p, f, to in moving:
                r1, r2 = v.square_rect(f), v.square_rect(to)
                x = r1.x + (r2.x - r1.x) * k
                y = r1.y + (r2.y - r1.y) * k - math.sin(k * math.pi) * size * 0.25
                sh = pygame.Surface((size, size // 3), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect().inflate(-size // 3, 0))
                surface.blit(sh, (r1.x + (r2.x - r1.x) * k, r1.y + (r2.y - r1.y) * k + size * 0.72))
                surface.blit(art.piece_image(self.pieces, p, size), (x, y))
        if self.preview_move and not self.anim:
            v.arrow(surface, self.preview_move[0], self.preview_move[1], (90, 230, 120), 170)
        if not self.timed and self.hover_sq is not None and not self.over:
            r = v.square_rect(self.hover_sq)
            art.panel(surface, (r.centerx - 28, r.y - 30, 56, 28), (10, 14, 30), 230, 8, art.CYAN, 2)
            art.text(surface, square_name(self.hover_sq), (r.centerx, r.y - 16), 18, art.CYAN, True, "mono", "center")
        self.particles.draw(surface)
        self.popups.draw(surface)
        self.draw_panel(surface)
        if self.banner > 0 and not self.over:
            self.draw_banner(surface)
        if self.leave_confirm:
            self.draw_leave(surface)
        if self.over:
            self.draw_over(surface)

    def draw_panel(self, surface):
        app = self.app
        x0, w = 712, 538
        # header
        art.panel(surface, (x0, 24, w, 52), (22, 30, 56), 230, 14)
        mode = t("mode_blitz") if self.timed else t("mode_free")
        art.text(surface, f"{mode} · {t(self.difficulty)}", (x0 + 18, 50), 20,
                 art.GOLD if self.timed else art.GREEN, True, anchor="midleft")
        icon = art.piece_image(self.pieces, "K" if self.player == WHITE else "k", 40)
        cname = t("white") if self.player == WHITE else t("black")
        r = art.text(surface, f"{t('you_play')} {cname}", (x0 + w - 18, 50), 20, art.INK, True, anchor="midright")
        surface.blit(icon, icon.get_rect(midright=(r.left - 6, 50)))

        # clock
        cx, cy, rad = x0 + 82, 162, 64
        art.panel(surface, (x0, 86, w, 152), (22, 30, 56), 230, 14)
        pygame.draw.circle(surface, (12, 16, 32), (cx, cy), rad)
        if self.timed:
            frac = max(0.0, min(1.0, self.time_left / self.turn_limit))
            col = art.GREEN if self.time_left > 20 else (art.GOLD if self.time_left > 10 else art.RED)
            if self.board.turn != self.player:
                col = (90, 100, 130)
            if self.time_left <= 10 and self.board.turn == self.player and not self.over:
                art.blit_glow(surface, (cx, cy), rad + 30, (90, 20, 20), 0.6 + 0.4 * math.sin(app.time * 8))
            rect = pygame.Rect(0, 0, rad * 2, rad * 2)
            rect.center = (cx, cy)
            pygame.draw.circle(surface, (40, 48, 76), (cx, cy), rad, 9)
            if frac > 0:
                start = math.pi / 2
                pygame.draw.arc(surface, col, rect, start, start + frac * 2 * math.pi, 9)
            secs = max(0, math.ceil(self.time_left)) if self.board.turn == self.player else self.turn_limit
            art.text(surface, str(secs), (cx, cy - 4), 46, col, True, "num", "center")
            art.text(surface, t("time"), (cx, cy + 32), 13, art.INK_DIM, anchor="center")
        else:
            pygame.draw.circle(surface, (40, 48, 76), (cx, cy), rad, 9)
            art.text(surface, "∞", (cx, cy - 6), 60, art.GREEN, True, "glyph", "center")
            art.text(surface, t("no_limit"), (cx, cy + 34), 13, art.INK_DIM, anchor="center")
        # score
        sx = x0 + 170
        art.text(surface, t("score"), (sx, 98), 16, art.INK_DIM, True)
        scol = art.GOLD if self.score > TIMEOUT_PENALTY or not self.timed else art.RED
        art.text(surface, f"{self.score:,}", (sx, 112), 46, scol, True, "num")
        # captured pieces
        art.text(surface, t("captured"), (sx, 176), 14, art.INK_DIM)
        art.text(surface, t("lost"), (sx, 206), 14, art.INK_DIM)
        order = "QRBNP"
        for row, (items, y) in enumerate(((self.won, 170), (self.lost, 200))):
            items = sorted(items, key=lambda p: order.index(p.upper()))
            px = sx + 92
            for p in items:
                surface.blit(art.piece_image(self.pieces, p, 28), (px, y))
                px += 18
        # move list
        box = pygame.Rect(x0, 248, w, 256)
        art.panel(surface, box, (16, 22, 44), 235, 14)
        art.text(surface, t("moves"), (box.x + 18, box.y + 10), 16, art.INK_DIM, True)
        hist = self.board.history
        rows = [(i // 2 + 1, hist[i][1], hist[i + 1][1] if i + 1 < len(hist) else "") for i in range(0, len(hist), 2)]
        visible = rows[-8:]
        for k, (n, wm, bm) in enumerate(visible):
            y = box.y + 40 + k * 26
            art.text(surface, f"{n}.", (box.x + 44, y), 19, art.INK_DIM, True, "mono", "topright")
            last = (k == len(visible) - 1)
            wcol = art.GOLD if last and not bm else art.INK
            bcol = art.GOLD if last and bm else art.INK
            art.text(surface, wm, (box.x + 56, y), 19, wcol, True, "mono")
            art.text(surface, bm, (box.x + 176, y), 19, bcol, True, "mono")
        # live coordinates helper
        hx = box.x + 316
        art.text(surface, "a b c d e f g h", (hx, box.y + 40), 15, (120, 140, 180), True, "mono")
        art.text(surface, "1 → 8", (hx, box.y + 62), 15, (120, 140, 180), True, "mono")
        notes = ["e2e4  g1f3", "Nf3  exd5", "O-O  O-O-O", "e7e8q  e8=Q"]
        for i, n in enumerate(notes):
            art.text(surface, n, (hx, box.y + 100 + i * 24), 15, (150, 170, 210), False, "mono")
        # status line
        if self.over:
            status, scol = "", art.INK
        elif self.board.turn == self.player and not self.anim:
            status, scol = t("your_turn"), art.CYAN
        else:
            dots = "." * (1 + int(app.time * 3) % 3)
            status, scol = t("cpu_thinking").rstrip("…") + dots, art.INK_DIM
        art.text(surface, status, (x0 + 4, 520), 17, scol, True)
        self.field.draw(surface)
        # message
        text, color, left = self.message
        if left > 0 and text:
            alpha_col = color if left > 0.5 else tuple(int(c * left / 0.5) for c in color)
            y = 624
            for line in art.wrap(text, w - 8, 15, True)[:2]:
                art.text(surface, line, (x0 + 4, y), 15, alpha_col, True)
                y += 19
        for b in self.buttons:
            b.draw(surface)

    def draw_banner(self, surface):
        k = min(1.0, self.banner / 0.5, (2.6 - self.banner) / 0.4)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(120 * k)))
        surface.blit(shade, (0, 0))
        r = pygame.Rect(0, 0, 680, 180)
        r.center = (W // 2, H // 2)
        art.panel(surface, r, (20, 26, 50), int(240 * k), 20, art.GOLD, 3)
        icon = art.piece_image(self.pieces, "K" if self.player == WHITE else "k", 110)
        icon.set_alpha(int(255 * k))
        surface.blit(icon, (r.x + 24, r.centery - 55))
        msg = t("you_are_white") if self.player == WHITE else t("you_are_black")
        art.text(surface, msg, (r.x + 150, r.y + 56), 26, art.GOLD, True)
        art.text(surface, t("flip_hint"), (r.x + 150, r.y + 104), 18, art.INK)
        if self.timed:
            art.text(surface, t("secs_turn", n=self.turn_limit), (r.x + 150, r.y + 134), 18, art.CYAN, True)

    def draw_leave(self, surface):
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surface.blit(shade, (0, 0))
        r = pygame.Rect(400, 240, 480, 230)
        art.panel(surface, r, (24, 30, 58), 250, 18, art.RED, 3)
        art.text(surface, t("leave_title"), (r.centerx, r.y + 50), 30, art.INK, True, anchor="center")
        art.text(surface, t("leave_body"), (r.centerx, r.y + 100), 20, art.INK_DIM, anchor="center")
        for b in self.leave_buttons:
            b.draw(surface)

    def draw_over(self, surface):
        o = self.over
        k = min(1.0, o["t"] / 0.6)
        shade = pygame.Surface((W, H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, int(160 * k)))
        surface.blit(shade, (0, 0))
        r = pygame.Rect(330, 110, 620, 520)
        result = o["result"]
        edge = {"win": art.GOLD, "draw": art.CYAN}.get(result, art.RED)
        art.panel(surface, r, (20, 26, 52), int(248 * k), 22, edge, 3)
        if result == "win":
            title = t("win_mate")
        elif result == "loss":
            title = t("lose_mate")
        elif result == "draw":
            title = t("draw_" + o["reason"])
        elif result == "points":
            title = t("out_of_points")
        else:
            title = t("resigned")
        art.blit_glow(surface, (r.centerx, r.y + 60), 200, tuple(int(c * 0.25) for c in edge), k)
        art.text(surface, title, (r.centerx, r.y + 56), 32, edge, True, anchor="center")
        art.text(surface, t("final_score"), (r.centerx, r.y + 110), 18, art.INK_DIM, anchor="center")
        art.text(surface, f"{self.score:,}", (r.centerx, r.y + 152), 60, art.GOLD, True, "num", "center")
        times = self.stats["move_times"]
        avg = f"{sum(times) / len(times):.1f}" if times else "—"
        typed = self.stats["valid"] + self.stats["invalid"]
        acc = f"{round(100 * self.stats['valid'] / typed)}%" if typed else "—"
        rows = [(t("stat_moves"), str(self.stats["valid"])), (t("stat_avg"), t("sec", n=avg)),
                (t("stat_acc"), acc)]
        if self.timed:
            rows.append((t("stat_timeouts"), str(self.stats["timeouts"])))
        for i, (a, b) in enumerate(rows):
            y = r.y + 200 + i * 30
            art.text(surface, a, (r.x + 150, y), 19, art.INK_DIM)
            art.text(surface, b, (r.right - 150, y), 19, art.INK, True, anchor="topright")
        if self.name_field:
            art.text(surface, t("new_high"), (r.centerx, r.y + 340), 20, art.GOLD, True, anchor="center")
            self.name_field.draw(surface)
        elif self.saved_rank:
            art.text(surface, t("saved_rank", n=self.saved_rank), (r.centerx, r.y + 380), 24, art.GOLD, True,
                     anchor="center")
        for b in self.over_buttons:
            b.draw(surface)
