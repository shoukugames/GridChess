"""Automatic self-test: visits every screen and plays real games by typing moves.

Used by the build scripts to prove a packaged game really starts and plays:
    gridchess --smoke-test result.txt
Set GRIDCHESS_SHOTS=<folder> to also save a screenshot of each screen.
"""
import os
import random
import sys
import tempfile
import time
import traceback


def smoke_test(out_path=None):
    os.environ.setdefault("GRIDCHESS_DATA", tempfile.mkdtemp(prefix="gridchess-smoke-"))
    shots = os.environ.get("GRIDCHESS_SHOTS")
    lines = []
    ok = True
    try:
        import pygame

        from . import ai, art, storage
        from .app import App
        from .chess import WHITE, BLACK
        from .scenes.credits import CreditsScene, LicenseScene
        from .scenes.game import GameScene
        from .scenes.parents import ParentGateScene, ParentsScene
        from .scenes.style import StyleScene
        from .scenes.title import TitleScene
        from .scenes.tutorial import TutorialScene

        from .scenes import game as game_module
        game_module.CPU_MIN_SECONDS = 0.0      # no artificial "thinking" pause while testing
        app = App(windowed=True, smoke=True)
        count = {"n": 0}

        def frames(scene, n=10, name=None, dt=1 / 60):
            for _ in range(n):
                pygame.event.pump()
                scene.update(dt)
                scene.draw(app.canvas)
                app.present()
            if shots and name:
                os.makedirs(shots, exist_ok=True)
                count["n"] += 1
                pygame.image.save(app.canvas, os.path.join(shots, f"{count['n']:02d}_{name}.png"))

        def type_text(scene, text):
            for ch in text:
                scene.handle(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch, mod=0))
            scene.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r", mod=0))

        # Every menu screen in both languages
        for language in ("en", "ja"):
            app.set_language(language)
            for cls in (TitleScene, CreditsScene, LicenseScene, ParentGateScene, ParentsScene, StyleScene):
                scene = cls(app)
                app.switch(scene)
                frames(scene, 6, f"{cls.__name__}_{language}")
            tut = TutorialScene(app)
            app.switch(tut)
            for page in range(tut.count):
                tut.page = page
                frames(tut, 2, f"tutorial_{page:02d}_{language}" if language == "en" or page in (0, 4, 15, 16) else None)
            type_text(tut, "e4")
            frames(tut, 2)
        lines.append("screens ok")
        app.set_language("en")

        # Every piece set and board renders
        for pieces in art.PIECE_SETS:
            for p in "KQRBNPkqrbnp":
                art.piece_image(pieces, p, 76)
        for theme in art.BOARD_ORDER:
            app.settings["board"] = theme
            frames(StyleScene(app), 1, f"board_{theme}")
        app.settings["board"], app.settings["pieces"] = "walnut", "classic"
        lines.append("styles ok")

        # Play real games by typing moves, as both colours
        rng = random.Random(5)
        results = []
        for game_no, (colour, diff, timed) in enumerate(((WHITE, "easy", True), (BLACK, "medium", True),
                                                          (WHITE, "hard", False))):
            app.settings["pieces"] = art.PIECE_SETS[game_no % len(art.PIECE_SETS)]
            game = GameScene(app, diff, timed=timed, player_color=colour, seed=game_no)
            game.searcher.cfg = dict(game.searcher.cfg, time=0.05, depth=min(2, game.searcher.cfg["depth"]))
            mover = ai.Searcher("medium", random.Random(game_no))
            mover.cfg = dict(mover.cfg, time=0.05)
            app.switch(game)
            game.banner = 0
            # a wrong entry first must be refused, counted, and leave the board unchanged
            frames(game, 2)
            while not game.player_turn():
                frames(game, 2, dt=0.1)
            if game.board.turn == colour:
                before = game.board.fen()
                type_text(game, "z9z9")
                assert game.board.fen() == before and game.stats["invalid"] == 1, "bad input accepted"
                # the movement guide appears on Easy only
                pawn_sq = "e2" if colour == WHITE else "e7"
                for ch in pawn_sq:
                    game.handle(pygame.event.Event(pygame.KEYDOWN, key=0, unicode=ch, mod=0))
                assert bool(game.preview_dests) == (diff == "easy"), f"movement guide wrong on {diff}"
                game.field.value = ""
                game.update_preview()
            plies, deadline = 0, time.time() + 90
            while not game.over and plies < 160 and time.time() < deadline:
                if game.player_turn():
                    move = mover.choose(game.board)
                    text = game.board.san(move) if rng.random() < 0.5 else game.board.coord(move)
                    type_text(game, text)
                    plies += 1
                    if plies == 6:
                        frames(game, 1, f"game_{game_no}_typing")
                frames(game, 3, dt=0.1)
            if not game.over:
                game.ask_leave()
                frames(game, 2, f"game_{game_no}_leave")
                game.quit_game()
                results.append("quit")
                continue
            results.append(game.over["result"])
            frames(game, 30, f"game_{game_no}_over")
            if game.name_field:
                game.name_field.value = f"SMOKE{game_no}"
                game.save_name()
                frames(game, 2, f"game_{game_no}_saved")
            game.to_title()
        lines.append("games: " + ", ".join(results))

        # The clock: running out costs 500 points and gives 10 more seconds; no points left ends it
        game = GameScene(app, "hard", timed=True, player_color=WHITE, seed=9)
        app.switch(game)
        game.banner = 0
        before = game.score
        game.time_left = 0.05
        frames(game, 2, dt=0.1)
        assert game.score == before - 500 and 9 < game.time_left <= 10, "timeout penalty wrong"
        frames(game, 1, "game_timeout")
        game.time_left = 0.05
        frames(game, 2, dt=0.1)
        assert game.over and game.over["result"] == "points", "out of points not detected"
        frames(game, 30, "game_out_of_points")
        game.to_title()
        lines.append("clock ok")
        summary = storage.summary()
        assert summary["played"] >= 3, "games were not recorded"
        frames(TitleScene(app), 4, "title_after")
        frames(ParentsScene(app), 4, "parents_after")
        lines.append(f"recorded {summary['played']} games")
        pygame.quit()
    except Exception:  # noqa: BLE001 - report every failure
        ok = False
        lines.append("FAILED\n" + traceback.format_exc())
    text = ("OK " if ok else "") + "; ".join(lines)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1
