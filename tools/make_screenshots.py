#!/usr/bin/env python3
"""Render the website screenshots (1280x720) into a folder: python3 tools/make_screenshots.py <out_dir>

Uses a temporary save folder filled with sample scores and progress, so your own
records are never touched.
"""
import os
import random
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["GRIDCHESS_DATA"] = tempfile.mkdtemp(prefix="gridchess-shots-")

import pygame  # noqa: E402

from gridchess import storage  # noqa: E402
from gridchess.app import App  # noqa: E402
from gridchess.scenes import game as game_module  # noqa: E402
from gridchess.scenes.game import GameScene  # noqa: E402
from gridchess.scenes.parents import ParentsScene  # noqa: E402
from gridchess.scenes.style import StyleScene  # noqa: E402
from gridchess.scenes.title import TitleScene  # noqa: E402
from gridchess.scenes.tutorial import TutorialScene  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "shots")
os.makedirs(OUT, exist_ok=True)
rng = random.Random(4)

# Sample records for the title screen and the Parents screen
for name, score, diff, res in [("Hana", 4300, "hard", "win"), ("Leo", 3800, "medium", "win"), ("Sora", 3100, "easy", "win"),
                               ("Mia", 2600, "medium", "draw"), ("Kenji", 2200, "easy", "loss"), ("Ava", 1900, "hard", "loss"),
                               ("Ryo", 1700, "easy", "draw"), ("Noah", 1500, "medium", "loss")]:
    storage.add_score(name, score, diff, res)
for i in range(12):
    res = rng.choice(["win", "win", "loss", "draw", "loss", "win", "points"])
    moves = rng.randint(14, 42)
    speed = max(4.0, 24 - i * 1.5 + rng.uniform(-3, 3))
    storage.record_game({"mode": "blitz" if i % 4 else "free", "difficulty": ["easy", "easy", "medium", "hard"][i % 4],
                         "color": rng.choice("wb"), "result": res, "reason": "checkmate", "score": rng.randint(8, 40) * 100,
                         "moves": moves, "valid": moves, "invalid": rng.randint(0, 6), "timeouts": rng.randint(0, 2),
                         "move_times": [max(1.5, rng.gauss(speed, 4)) for _ in range(moves)]})

game_module.CPU_MIN_SECONDS = 0.0
app = App(windowed=True, smoke=True)
app.audio.ok = False


def frames(scene, n=8, dt=1 / 60):
    for _ in range(n):
        scene.update(dt)
    scene.draw(app.canvas)


def save(name):
    pygame.image.save(app.canvas, os.path.join(OUT, f"gridchess-{name}.png"))
    print("saved", name)


def key(scene, text):
    for ch in text:
        scene.handle(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch, mod=0))


def setup_game(diff, colour, sans, pieces="classic", board="walnut", timed=True):
    app.settings["pieces"], app.settings["board"] = pieces, board
    g = GameScene(app, diff, timed=timed, player_color=colour, seed=3)
    app.switch(g)
    g.banner = 0
    g.message = ("", (0, 0, 0), 0)
    for s in sans:
        mover_is_player = g.board.turn == colour
        move = g.board.parse(s)[0]
        info = g.board.push(move)
        g.last_move = move
        if info["captured"] != ".":
            (g.won if mover_is_player else g.lost).append(info["captured"])
            if mover_is_player:
                g.score += game_module.POINTS.get(info["captured"].upper(), 0)
    g.begin_player_turn()
    return g


app.set_language("en")
# 1. Typing a move on Easy, with the movement guide
g = setup_game("easy", "w", ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d4", "exd4", "cxd4", "Bb4+", "Nc3", "Nxe4", "O-O", "Nxc3"])
g.time_left = 41.3
key(g, "b2")
frames(g)
save("typing-a-move")

# 2. Title screen
app.settings["pieces"], app.settings["board"] = "classic", "walnut"
t = TitleScene(app)
app.switch(t)
for _ in range(9):
    t.demo_timer = 0
    t.update(1 / 60)
frames(t)
save("title")

# 3. Playing Black on Medium: board turned around, no movement guide
g = setup_game("medium", "b", ["d4", "Nf6", "c4", "e6", "Nc3", "Bb4", "Qc2", "O-O", "a3", "Bxc3+", "Qxc3", "b6", "Bg5", "Bb7"],
               pieces="neon", board="midnight")
g.board.push(g.board.parse("f3")[0])
g.last_move = g.board.history[-1][0]
g.begin_player_turn()
g.time_left = 23.6
key(g, "h7h6")
frames(g)
save("playing-black")

# 4. Tutorial: the knight
tut = TutorialScene(app)
app.switch(tut)
tut.page = 9
frames(tut)
save("how-to-play")

# 5. Checkmate win with name entry
g = setup_game("easy", "w", ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"], pieces="wood", board="walnut")
g.time_left = 52
g.field.value = ""
g.play_move(g.board.parse("Qxf7#")[0], by_player=True)
for _ in range(40):
    g.update(1 / 60)
g.over["t"] = 2
g.stats.update(valid=4, invalid=1, move_times=[4.8, 6.2, 3.9, 5.1])
g.name_field.value = "Hana"
g.particles.items.clear()
frames(g, 2)
save("checkmate")

# 6. Pieces and boards
app.settings["pieces"], app.settings["board"] = "modern", "marble"
s = StyleScene(app)
app.switch(s)
frames(s)
save("pieces-and-boards")

# 7. Parents screen
p = ParentsScene(app)
app.switch(p)
frames(p)
save("for-parents")

# 8. Japanese: a refused move explained, on Hard (30 seconds, no movement guide)
app.set_language("ja")
g = setup_game("hard", "w", ["e4", "c5", "Nf3", "d6", "d4", "cxd4", "Nxd4", "Nf6"], pieces="tournament", board="tournament")
g.time_left = 8.4
key(g, "f1f5")
g.submit()
frames(g)
save("gameplay-japanese")

# 9. Japanese Grid Drill
tut = TutorialScene(app)
app.switch(tut)
tut.page = tut.count - 1
tut.drill_target = 36
tut.drill_right, tut.drill_tries = 7, 8
tut.drill_msg = ("正解！ c6", (110, 226, 140))
key(tut, "e")
frames(tut)
save("grid-drill-japanese")
app.set_language("en")
pygame.quit()
