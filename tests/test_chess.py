"""Rules engine tests, including perft counts from the Chess Programming Wiki."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

from gridchess.chess import Board, parse_square, is_light, square_name  # noqa: E402


def perft(board, depth):
    if depth == 0:
        return 1
    total = 0
    for m in board.legal_moves():
        board.make(m)
        total += perft(board, depth - 1)
        board.unmake()
    return total


@pytest.mark.parametrize("fen,depth,expected", [
    ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 3, 8902),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),  # Kiwipete
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),
    ("r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 3, 9467),
    ("rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 2, 1486),
])
def test_perft(fen, depth, expected):
    board = Board(fen)
    before = board.fen()
    assert perft(board, depth) == expected
    assert board.fen() == before


def test_board_colours():
    assert not is_light(parse_square("a1"))
    assert is_light(parse_square("h1"))
    assert sum(is_light(s) for s in range(64)) == 32
    assert square_name(0) == "a1" and square_name(63) == "h8"


def test_parse_coordinate_and_san():
    b = Board()
    assert b.parse("e2e4") == ((12, 28, ""), None)
    assert b.parse("Nf3")[0] == (6, 21, "")
    assert b.parse("nf3")[0] == (6, 21, "")
    assert b.parse("g1-f3")[0] == (6, 21, "")
    assert b.parse("e4")[0] == (12, 28, "")
    assert b.parse("b4")[0] == (9, 25, "")
    assert b.parse("e2e5")[1] == "illegal"
    assert b.parse("e3e4")[1] == "no_piece"
    assert b.parse("e7e5")[1] == "not_yours"
    assert b.parse("hello")[1] == "format"
    assert b.parse("Bc4")[1] == "illegal"


def test_scholars_mate_and_san_suffix():
    b = Board()
    for text in ["e4", "e5", "Bc4", "Nc6", "Qh5", "Nf6"]:
        b.push(b.parse(text)[0])
    move = b.parse("Qxf7")[0]
    assert b.san(move) == "Qxf7#"
    b.push(move)
    assert b.outcome() == ("white", "checkmate")


def test_castling_rules():
    b = Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    assert b.parse("O-O")[0] == (4, 6, "")
    assert b.parse("0-0-0")[0] == (4, 2, "")
    assert b.parse("e1g1")[0] == (4, 6, "")
    # can't castle through an attacked square
    b = Board("r3k2r/8/8/8/8/8/5r2/R3K2R w KQkq - 0 1")
    assert b.parse("O-O")[0] is None
    # can't castle out of check
    b = Board("r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1")
    assert b.parse("O-O-O")[0] is None
    # rook moved -> right lost
    b = Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    b.push(b.parse("Rh2")[0])
    b.push(b.parse("Kd8")[0])
    b.push(b.parse("Rh1")[0])
    b.push(b.parse("Kd7")[0])
    assert b.parse("O-O")[0] is None
    assert b.parse("O-O-O")[0] is not None


def test_en_passant_and_promotion():
    b = Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1")
    info = b.push(b.parse("exd6")[0])
    assert info["en_passant"] and info["captured"] == "p"
    assert b.sq[parse_square("d5")] == "."
    b = Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    assert b.parse("a8=N")[0] == (48, 56, "n")
    assert b.parse("a7a8r")[0] == (48, 56, "r")
    assert b.parse("a8")[0] == (48, 56, "q")


def test_draws():
    assert Board("8/8/8/4k3/8/8/8/4K3 w - - 0 1").outcome() == ("draw", "insufficient")
    assert Board("8/8/8/4k3/8/8/8/3NK3 w - - 0 1").outcome() == ("draw", "insufficient")
    assert Board("8/8/8/4k3/8/8/8/3QK3 w - - 0 1").outcome() is None
    assert Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1").outcome() == ("draw", "stalemate")
    assert Board("4k3/8/8/8/8/8/8/R3K3 w - - 100 80").outcome() == ("draw", "fifty_moves")
    b = Board()
    for _ in range(2):
        for text in ["Nf3", "Nf6", "Ng1", "Ng8"]:
            b.push(b.parse(text)[0])
    assert b.outcome() == ("draw", "repetition")


def test_disambiguation():
    b = Board("4k3/8/8/8/8/8/4K3/R6R w - - 0 1")
    move = b.parse("Rad1")[0]
    assert move == (0, 3, "")
    assert b.san(move) == "Rad1"
    assert b.parse("Rd1")[1] == "ambiguous"


def test_self_check_reason():
    b = Board("4k3/4r3/8/8/8/8/4B3/4K3 w - - 0 1")
    assert b.parse("Bd3")[1] == "self_check"


def test_cpu_always_returns_legal_moves():
    import random
    from gridchess.ai import Searcher
    rng = random.Random(1)
    b = Board()
    cpu = Searcher("easy", rng)
    cpu.cfg = dict(cpu.cfg, time=0.02)
    for _ in range(60):
        if b.outcome():
            break
        move = cpu.choose(b)
        assert move in b.legal_moves()
        b.push(move)


def test_hard_cpu_finds_mate_in_one():
    from gridchess.ai import Searcher
    b = Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    assert b.san(Searcher("hard").choose(b)) == "Ra8#"
