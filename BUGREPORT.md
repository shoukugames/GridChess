# Reporting a bug in Grid Chess: Blitz Edition

Thank you for helping make Grid Chess better! A good bug report lets us find and
fix the problem quickly.

**Where to send it:** email **info@shoukugames.org** with the subject
`Grid Chess bug: <short summary>`, or open an issue on the project's repository.

## Before you report

1. Check you have the latest version (shown at the bottom of the title screen
   and in **Credits**).
2. Try to make the problem happen a second time and note the exact steps.

## Copy this template

```
Grid Chess version:    (e.g. v0.1.0, from the Credits screen)
Operating system:      (e.g. Windows 11, Ubuntu 24.04, Debian 12)
How installed:         (.exe / .deb / from source)
Language setting:      (English / 日本語)
Mode and difficulty:   (Blitz or Free Play; Easy / Medium / Hard)
Your colour:           (White / Black)
Moves so far:          (copy the move list from the right-hand panel)
What you typed:        (the exact text, e.g. "Nbd2")

What happened:

What I expected to happen:

Steps to make it happen again:
1.
2.
3.

How often:             (every time / sometimes / once)
```

## Rules questions

If you think a legal move was refused, or an illegal one allowed, the **move
list** is the most useful thing you can send: with it we can rebuild the exact
position. Before reporting, check the special rules in **How to Play**:

- You cannot castle out of, through, or into check, or after the king or that
  rook has moved.
- En passant is only allowed on the move right after the enemy pawn's
  two-square step.
- A move that leaves your own king attacked is always illegal.
- Draws are automatic: stalemate, threefold repetition, the fifty-move rule and
  insufficient material.

## Helpful extras

- **Screenshot or video** of the problem.
- **Crash log:** if the game closes unexpectedly it writes `crash.log` to its
  data folder. Please attach it.
  - Windows: `%APPDATA%\GridChess\crash.log`
  - Linux: `~/.local/share/gridchess/crash.log`
- **Progress file**, if the bug is about the Parents screen: `progress.json` in
  the same folder. It contains only dates, results, times and scores, no
  personal information.
- **From source:** run `python3 run_game.py --windowed` in a terminal and copy
  any error text it prints.
- **Self-test:** `gridchess --smoke-test result.txt` (or the .exe with the same
  option) runs the built-in check and writes the result to `result.txt`.

## Known limitations

- Draws are applied automatically (the fifty-move rule and threefold
  repetition are not offered as a claim).
- A promotion typed without a piece letter becomes a queen.
- No sound on a computer without a working audio device; the game still runs.
- Typing Japanese names on the Top 10 needs your system's input method (IME)
  to work with the game window.
