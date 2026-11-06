"""The CPU opponent: alpha-beta search with quiescence and piece-square tables.

Easy   - looks one move ahead and often picks a slightly worse move, so kids can win.
Medium - searches about two moves ahead with a little variety.
Hard   - iterative deepening for up to ~2.5 seconds per move.
"""
import random
import time

from .chess import WHITE, BLACK

VALUE = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0}
MATE = 100000

# Piece-square tables (from White's side, index a8..h8 first row, as written on paper)
_PST = {
    "P": [0, 0, 0, 0, 0, 0, 0, 0,
          50, 50, 50, 50, 50, 50, 50, 50,
          10, 10, 20, 30, 30, 20, 10, 10,
          5, 5, 10, 25, 25, 10, 5, 5,
          0, 0, 0, 20, 20, 0, 0, 0,
          5, -5, -10, 0, 0, -10, -5, 5,
          5, 10, 10, -20, -20, 10, 10, 5,
          0, 0, 0, 0, 0, 0, 0, 0],
    "N": [-50, -40, -30, -30, -30, -30, -40, -50,
          -40, -20, 0, 0, 0, 0, -20, -40,
          -30, 0, 10, 15, 15, 10, 0, -30,
          -30, 5, 15, 20, 20, 15, 5, -30,
          -30, 0, 15, 20, 20, 15, 0, -30,
          -30, 5, 10, 15, 15, 10, 5, -30,
          -40, -20, 0, 5, 5, 0, -20, -40,
          -50, -40, -30, -30, -30, -30, -40, -50],
    "B": [-20, -10, -10, -10, -10, -10, -10, -20,
          -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 10, 10, 5, 0, -10,
          -10, 5, 5, 10, 10, 5, 5, -10,
          -10, 0, 10, 10, 10, 10, 0, -10,
          -10, 10, 10, 10, 10, 10, 10, -10,
          -10, 5, 0, 0, 0, 0, 5, -10,
          -20, -10, -10, -10, -10, -10, -10, -20],
    "R": [0, 0, 0, 0, 0, 0, 0, 0,
          5, 10, 10, 10, 10, 10, 10, 5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          -5, 0, 0, 0, 0, 0, 0, -5,
          0, 0, 0, 5, 5, 0, 0, 0],
    "Q": [-20, -10, -10, -5, -5, -10, -10, -20,
          -10, 0, 0, 0, 0, 0, 0, -10,
          -10, 0, 5, 5, 5, 5, 0, -10,
          -5, 0, 5, 5, 5, 5, 0, -5,
          0, 0, 5, 5, 5, 5, 0, -5,
          -10, 5, 5, 5, 5, 5, 0, -10,
          -10, 0, 5, 0, 0, 0, 0, -10,
          -20, -10, -10, -5, -5, -10, -10, -20],
    "K": [-30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -30, -40, -40, -50, -50, -40, -40, -30,
          -20, -30, -30, -40, -40, -30, -30, -20,
          -10, -20, -20, -20, -20, -20, -20, -10,
          20, 20, 0, 0, 0, 0, 20, 20,
          20, 30, 10, 0, 0, 10, 30, 20],
    "KE": [-50, -40, -30, -20, -20, -30, -40, -50,
           -30, -20, -10, 0, 0, -10, -20, -30,
           -30, -10, 20, 30, 30, 20, -10, -30,
           -30, -10, 30, 40, 40, 30, -10, -30,
           -30, -10, 30, 40, 40, 30, -10, -30,
           -30, -10, 20, 30, 30, 20, -10, -30,
           -30, -30, 0, 0, 0, 0, -30, -30,
           -50, -30, -30, -30, -30, -30, -30, -50],
}
# Convert to a1-indexed tables per colour
PST = {}
for _k, _t in _PST.items():
    white = [0] * 64
    black = [0] * 64
    for sq in range(64):
        f, r = sq & 7, sq >> 3
        white[sq] = _t[(7 - r) * 8 + f]
        black[sq] = _t[r * 8 + f]
    PST[(_k, WHITE)] = white
    PST[(_k, BLACK)] = black

LEVELS = {
    "easy": {"depth": 1, "time": 0.6, "noise": 220, "blunder": 0.22},
    "medium": {"depth": 2, "time": 1.2, "noise": 35, "blunder": 0.0},
    "hard": {"depth": 5, "time": 2.5, "noise": 0, "blunder": 0.0},
}


def evaluate(board):
    """Score from the side to move's point of view, in centipawns."""
    s = board.sq
    score = 0
    queens = s.count("Q") + s.count("q")
    minor = sum(1 for p in s if p in "NBRnbr")
    endgame = queens == 0 or (queens <= 2 and minor <= 2)
    bishops_w = bishops_b = 0
    for i, p in enumerate(s):
        if p == ".":
            continue
        k = p.upper()
        if p.isupper():
            score += VALUE[k] + PST[("KE" if k == "K" and endgame else k, WHITE)][i]
            bishops_w += k == "B"
        else:
            score -= VALUE[k] + PST[("KE" if k == "K" and endgame else k, BLACK)][i]
            bishops_b += k == "B"
    if bishops_w >= 2:
        score += 30
    if bishops_b >= 2:
        score -= 30
    return score if board.turn == WHITE else -score


class Searcher:
    def __init__(self, level="medium", rng=None):
        self.cfg = LEVELS[level]
        self.rng = rng or random.Random()
        self.nodes = 0
        self.deadline = 0
        self.stopped = False
        self.killers = {}

    def _order(self, board, moves, ply, best=None):
        s = board.sq
        killers = self.killers.get(ply, ())

        def key(m):
            if m == best:
                return -100000
            victim = s[m[1]]
            score = 0
            if victim != ".":
                score -= 10 * VALUE[victim.upper()] - VALUE[s[m[0]].upper()] + 1000
            if m[2]:
                score -= 800
            if m in killers:
                score -= 500
            return score
        moves.sort(key=key)
        return moves

    def quiesce(self, board, alpha, beta, depth=0):
        self.nodes += 1
        stand = evaluate(board)
        if stand >= beta:
            return beta
        if alpha < stand:
            alpha = stand
        if depth > 5:
            return alpha
        us = board.turn
        for m in self._order(board, board.pseudo_moves(captures_only=True), 99):
            board.make(m)
            if board.attacked(board.kings[us], board.turn):
                board.unmake()
                continue
            score = -self.quiesce(board, -beta, -alpha, depth + 1)
            board.unmake()
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    def negamax(self, board, depth, alpha, beta, ply):
        if self.nodes & 1023 == 0 and time.time() > self.deadline:
            self.stopped = True
        if self.stopped:
            return 0
        if ply and (board.halfmove >= 100):
            return 0
        if depth <= 0:
            return self.quiesce(board, alpha, beta)
        self.nodes += 1
        us = board.turn
        in_check = board.in_check()
        if in_check:
            depth += 1
        legal_found = False
        for m in self._order(board, board.pseudo_moves(), ply):
            board.make(m)
            if board.attacked(board.kings[us], board.turn):
                board.unmake()
                continue
            legal_found = True
            score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.unmake()
            if self.stopped:
                return 0
            if score >= beta:
                if board.sq[m[1]] == ".":
                    k = self.killers.setdefault(ply, [])
                    if m not in k:
                        k.insert(0, m)
                        del k[2:]
                return beta
            if score > alpha:
                alpha = score
        if not legal_found:
            return -MATE + ply if in_check else 0
        return alpha

    def choose(self, board):
        """Pick a move for the side to move. The board is not changed."""
        board = board.copy()
        legal = board.legal_moves()
        if not legal:
            return None
        if len(legal) == 1:
            return legal[0]
        cfg = self.cfg
        if cfg["blunder"] and self.rng.random() < cfg["blunder"]:
            # a casual move: anything that doesn't simply hang the queen
            safe = [m for m in legal if board.sq[m[0]].upper() != "Q"] or legal
            return self.rng.choice(safe)
        self.deadline = time.time() + cfg["time"]
        self.stopped = False
        self.nodes = 0
        self.killers = {}
        seen = set(board.keys)
        scored = [(m, 0) for m in legal]
        best_order = legal[:]
        for depth in range(1, cfg["depth"] + 1):
            results = []
            alpha = -MATE * 2
            for m in best_order:
                board.make(m)
                score = -self.negamax(board, depth - 1, -MATE * 2, -alpha + cfg["noise"] + 1, 1)
                if board.position_key() in seen:
                    score -= 40 if score > 0 else 0   # don't drift into repeating when ahead
                board.unmake()
                if self.stopped:
                    break
                results.append((m, score))
                alpha = max(alpha, score)
            if self.stopped and depth > 1:
                break
            if results:
                # keep scores of moves not reached at this depth from the last iteration
                done = {m for m, _ in results}
                scored = results + [x for x in scored if x[0] not in done]
                scored.sort(key=lambda x: -x[1])
                best_order = [m for m, _ in scored]
                if scored[0][1] > MATE - 100:
                    break
            if time.time() > self.deadline:
                break
        noise = cfg["noise"]
        if noise:
            top = scored[0][1]
            pool = [m for m, sc in scored if sc >= top - noise]
            return self.rng.choice(pool)
        top = scored[0][1]
        return self.rng.choice([m for m, sc in scored if sc == top])
