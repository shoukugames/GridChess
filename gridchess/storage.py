"""Settings, the top 10 table and the parents' progress record, saved as JSON.

Files live in the per-user data folder, so they survive updates and the game
works from a read-only install. A damaged file is set aside, never fatal.
"""
import json
import os
import sys
import tempfile
import time

GAMES_KEPT = 500
TOP_N = 10
DIFFICULTIES = ("easy", "medium", "hard")


def data_dir():
    override = os.environ.get("GRIDCHESS_DATA")
    if override:
        path = override
    elif sys.platform == "win32":
        path = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GridChess")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        path = os.path.join(base, "gridchess")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        path = os.path.join(tempfile.gettempdir(), "gridchess")
        os.makedirs(path, exist_ok=True)
    return path


def _load(name, default):
    path = os.path.join(data_dir(), name)
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, type(default)):
            return data
        raise ValueError("unexpected structure")
    except FileNotFoundError:
        return default
    except (OSError, ValueError):
        try:
            os.replace(path, path + ".corrupt")
        except OSError:
            pass
        return default


def _save(name, data):
    path = os.path.join(data_dir(), name)
    temp = path + ".tmp"
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1, ensure_ascii=False)
        os.replace(temp, path)
    except OSError as error:
        print(f"Could not save {name}: {error}", file=sys.stderr)


DEFAULT_SETTINGS = {"bgm": True, "sfx": True, "language": "en", "difficulty": "easy",
                    "pieces": "classic", "board": "walnut", "fullscreen": False,
                    "last_name": "", "coords": True}


def load_settings():
    data = dict(DEFAULT_SETTINGS)
    data.update(_load("settings.json", {}))
    if data["difficulty"] not in DIFFICULTIES:
        data["difficulty"] = "easy"
    if data["language"] not in ("en", "ja"):
        data["language"] = "en"
    return data


def save_settings(settings):
    _save("settings.json", settings)


# ------------------------------------------------------------------ high scores
def load_scores():
    scores = [s for s in _load("scores.json", []) if isinstance(s, dict) and "score" in s]
    return sorted(scores, key=lambda s: -s["score"])[:TOP_N]


def qualifies(score):
    if score <= 0:
        return False
    scores = load_scores()
    return len(scores) < TOP_N or score > scores[-1]["score"]


def add_score(name, score, difficulty, result):
    scores = load_scores()
    entry = {"name": (name.strip() or "PLAYER")[:12], "score": int(score),
             "difficulty": difficulty, "result": result, "date": time.strftime("%Y-%m-%d")}
    scores.append(entry)
    scores = sorted(scores, key=lambda s: -s["score"])[:TOP_N]
    _save("scores.json", scores)
    return scores.index(entry) if entry in scores else -1


# ------------------------------------------------------------------ progress
def load_progress():
    data = _load("progress.json", {})
    data.setdefault("games", [])
    return data


def record_game(record):
    """record: dict with mode, difficulty, color, result (win/loss/draw/points/quit),
    reason, score, moves, valid, invalid, timeouts, move_times (list of seconds)."""
    data = load_progress()
    rec = dict(record)
    times = rec.pop("move_times", [])
    rec["when"] = time.strftime("%Y-%m-%d %H:%M")
    rec["avg_time"] = round(sum(times) / len(times), 1) if times else None
    rec["best_time"] = round(min(times), 1) if times else None
    data["games"].append(rec)
    data["games"] = data["games"][-GAMES_KEPT:]
    _save("progress.json", data)


def summary():
    games = load_progress()["games"]
    out = {"played": len(games), "wins": 0, "losses": 0, "draws": 0, "timeouts": 0,
           "moves": 0, "valid": 0, "invalid": 0, "avg_time": None, "best_time": None,
           "best_score": 0, "recent": games[-12:][::-1]}
    total_time = weighted = 0.0
    for g in games:
        r = g.get("result")
        if r == "win":
            out["wins"] += 1
        elif r == "draw":
            out["draws"] += 1
        elif r in ("loss", "points", "quit"):
            out["losses"] += 1
        out["timeouts"] += g.get("timeouts", 0)
        out["moves"] += g.get("moves", 0)
        out["valid"] += g.get("valid", 0)
        out["invalid"] += g.get("invalid", 0)
        out["best_score"] = max(out["best_score"], g.get("score", 0))
        if g.get("avg_time") is not None and g.get("moves"):
            total_time += g["avg_time"] * g["moves"]
            weighted += g["moves"]
        if g.get("best_time") is not None:
            out["best_time"] = g["best_time"] if out["best_time"] is None else min(out["best_time"], g["best_time"])
    if weighted:
        out["avg_time"] = round(total_time / weighted, 1)
    typed = out["valid"] + out["invalid"]
    out["accuracy"] = round(100 * out["valid"] / typed) if typed else None
    return out


def reset_progress():
    _save("progress.json", {"games": []})
    _save("scores.json", [])
