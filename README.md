# Grid Chess: Blitz Edition v0.1.0

**Type your moves. Beat the clock. Master the grid.** · **手を入力して、時間と勝負。マス目をマスターしよう！**

Grid Chess: Blitz Edition is a high-speed chess notation trainer for **ages 10+**, in
**English and Japanese**. You play a full game of chess against the CPU, but there
is no dragging and no clicking on pieces: **every move is typed** using the real
chess board grid, either square to square (`e2e4`, `g1f3`) or in real chess
notation (`Nf3`, `exd5`, `O-O`, `e8=Q`). With only **60 seconds per turn** (30 on
Hard) you must think fast and type faster.

- Creator: **Shawn Rapaz**, with **Claude Code**
- Website: <https://shoukugames.org/> · Email: <info@shoukugames.org>
- Release: v0.1.0, 2026-11-07
- License: **GNU GPL v3.0** (see [LICENSE](LICENSE))
- Recommended ages: **10+**

## Features

- **100% real chess rules**: legal move checking, check, checkmate, stalemate,
  castling (with all its conditions), en passant, promotion to any piece,
  threefold repetition, the fifty-move rule and insufficient material. The move
  generator is verified against standard perft counts.
- **A real 8×8 board**: 64 squares (32 light, 32 dark), a1 dark, files a–h and
  ranks 1–8 labelled around the edge, with optional labels on every square.
- **You always play from the bottom.** White or Black is chosen at random each
  game. When you are Black the board turns around (rank 8 nearest you, files
  h→a), exactly like sitting on Black's side of a real board. White always moves
  first.
- **Typing trainer**: every mistake gets a clear explanation ("there's no piece
  of yours on e3", "that would leave your king in check", "two knights can go
  there, write Nbd2").
- **Movement guide on Easy only**: on Easy, typing the first square lights up
  that piece and every square it can legally reach, a complete move shows a
  green arrow before you press Enter, and a refused move lists where that piece
  can go. On **Medium and Hard there is no movement guide**: no dots, no arrow,
  no list of squares. You have to read the board yourself.
- **Blitz Play**: 60 seconds per turn on Easy and Medium, 30 on Hard.
- **Free Play**: any difficulty, no clock (the movement guide still follows the
  difficulty). Hovering over a square shows its name.
- **Three difficulty levels**:

  | Level | Blitz clock | Movement guide | CPU |
  |---|---|---|---|
  | Easy | 60 s per turn | yes | makes kid-friendly mistakes |
  | Medium | 60 s per turn | no | looks about two moves ahead |
  | Hard | 30 s per turn | no | searches several moves ahead |
- **How to Play tutorial**: 16 illustrated pages covering the board and square
  names, setting up, both ways of typing moves, how each piece moves (with every
  reachable square labelled), castling, en passant, promotion, check, checkmate
  and draws, opening strategy, tactics (forks, pins), scoring, and an
  interactive **Grid Drill** that asks you to name highlighted squares from both
  White's and Black's side.
- **Parents** section (behind a quick multiplication question): games played,
  wins, losses, draws, average and fastest move time, typing accuracy, moves
  typed, timeouts, best score, a move-speed chart and a table of recent games.
- **Top 10 high scores** with name entry, shown on the title screen.
- **Five piece sets** (Classic Staunton, Tournament, Carved Wood, Modern, Neon)
  and **six boards** (Walnut, Tournament Green, Marble, Midnight, Sakura,
  Ocean), all drawn in code.
- **Relaxing ambient music** (original, synthesised for this game) that can be
  turned on or off on the title screen and in the game. Wooden piece sounds,
  capture chimes, check bells, and a ticking clock for the last 10 seconds.
- English / 日本語 toggle on the title screen; full screen with **F11**.

## Scoring

| Event | Points |
|---|---|
| Start of game | 1,000 |
| Capture a pawn | +100 |
| Capture a knight | +200 |
| Capture a bishop | +300 |
| Capture a rook | +400 |
| Capture a queen | +500 |
| Checkmate the CPU | +1,000 |
| Run out of time on your turn | −500, and you get 10 more seconds |

The game ends with **checkmate** (either side), any **draw**, or when your points
reach **zero or less**. Every finished game, including leaving early, is
recorded in the Parents section. Blitz games can enter the Top 10.

## How to type moves

| You type | Meaning |
|---|---|
| `e2e4` | the piece on e2 moves to e4 (also `e2-e4`) |
| `e4` | a pawn moves to e4 |
| `Nf3` | a knight moves to f3 (K king, Q queen, R rook, B bishop, N knight) |
| `exd5`, `Nxe5` | captures (`x` is optional in square-to-square form) |
| `O-O` / `O-O-O` | castle short / long (or move the king: `e1g1`, `e1c1`); `0-0` works too |
| `e7e8q`, `e8=Q` | promote (q, r, b or n); with no letter a pawn becomes a queen |
| `Nbd2`, `R1e3` | say which piece when two of the same kind can reach the square |

Lower case piece letters (`nf3`) are understood too. `+` and `#` are optional.

## Install

- **Windows**: run `GridChess-v0.1.0.exe` (a single file, nothing to install).
- **Debian / Ubuntu**: `sudo apt install ./gridchess_v0.1.0_amd64.deb`, then start
  *Grid Chess: Blitz Edition* from the menu or run `gridchess`.
- **From source** (Python 3.10+):

  ```
  pip install -r requirements.txt
  python3 run_game.py            # add --windowed to start in a window
  ```

Saved settings, scores and progress live in `%APPDATA%\GridChess` on Windows and
`~/.local/share/gridchess` on Linux.

## Building the installers

```
./build.sh                       # both
packaging/build_linux.sh         # dist/gridchess_v0.1.0_amd64.deb
packaging/build_windows.sh       # dist/GridChess-v0.1.0.exe (built under Wine)
```

The Linux build needs `python3-venv` and `dpkg-deb`. The Windows build runs
Windows Python and PyInstaller under Wine and `xvfb-run`; the first run
downloads Python from python.org into a private Wine prefix in `build/`. Both
scripts finish by running the packaged game's built-in self-test.

## Development

```
pip install -r requirements-dev.txt
python3 -m pytest                # rules engine (perft), CPU and save-file tests
python3 run_game.py --smoke-test result.txt   # plays real games through the UI
python3 tools/make_audio.py      # regenerate music and sounds (needs numpy)
python3 tools/make_icon.py       # regenerate the icon (needs Pillow)
```

| Path | What it is |
|---|---|
| `gridchess/chess.py` | complete rules engine, SAN and move parsing |
| `gridchess/ai.py` | CPU opponent (alpha-beta search) |
| `gridchess/art.py` | piece sets, boards and drawing helpers |
| `gridchess/i18n.py` | all English and Japanese text, tutorial pages |
| `gridchess/scenes/` | title, game, tutorial, parents, style and credits screens |
| `gridchess/storage.py` | settings, Top 10 and progress files |

## Credits

- Created by Shawn Rapaz, made with Claude Code.
- Fonts: M PLUS 1p and Orbitron (SIL Open Font License, see `assets/fonts/OFL-*.txt`),
  DejaVu Sans and DejaVu Sans Mono (Bitstream Vera license, see `assets/fonts/LICENSE-DejaVu.txt`).
- Music and sound effects: original, generated by `tools/make_audio.py`.

## License

Copyright © 2026 Shawn Rapaz. Grid Chess: Blitz Edition is free software: you can
redistribute it and/or modify it under the terms of the GNU General Public
License as published by the Free Software Foundation, version 3. It is
distributed WITHOUT ANY WARRANTY. See [LICENSE](LICENSE) for the full text.

Bug reports: see [BUGREPORT.md](BUGREPORT.md).
