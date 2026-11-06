"""Saving scores and the parents' progress record."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_scores_and_progress(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIDCHESS_DATA", str(tmp_path))
    from gridchess import storage
    assert storage.load_scores() == []
    assert storage.qualifies(100)
    assert not storage.qualifies(0)
    for i in range(12):
        storage.add_score(f"P{i}", 1000 + i * 100, "easy", "win")
    scores = storage.load_scores()
    assert len(scores) == 10 and scores[0]["score"] == 2100
    assert not storage.qualifies(1000)
    storage.record_game({"mode": "blitz", "difficulty": "hard", "color": "w", "result": "win",
                         "reason": "checkmate", "score": 2500, "moves": 3, "valid": 3, "invalid": 1,
                         "timeouts": 1, "move_times": [4.0, 6.0, 2.0]})
    storage.record_game({"mode": "free", "difficulty": "easy", "color": "b", "result": "draw",
                         "reason": "stalemate", "score": 1000, "moves": 0, "valid": 0, "invalid": 0,
                         "timeouts": 0, "move_times": []})
    s = storage.summary()
    assert s["played"] == 2 and s["wins"] == 1 and s["draws"] == 1
    assert s["avg_time"] == 4.0 and s["best_time"] == 2.0 and s["accuracy"] == 75
    storage.reset_progress()
    assert storage.summary()["played"] == 0


def test_corrupt_file_is_set_aside(tmp_path, monkeypatch):
    monkeypatch.setenv("GRIDCHESS_DATA", str(tmp_path))
    from gridchess import storage
    (tmp_path / "scores.json").write_text("{not json")
    assert storage.load_scores() == []
    assert (tmp_path / "scores.json.corrupt").exists()
