"""A complete chess rules engine.

Squares are numbered 0..63 with a1 = 0, b1 = 1 ... h8 = 63 (index = rank * 8 + file).
Pieces are single letters: upper case for White (PNBRQK), lower case for Black, '.' empty.
A move is a tuple (from_square, to_square, promotion) where promotion is '' or one of
'q', 'r', 'b', 'n'.

Implements every rule of chess: castling (with all its conditions), en passant,
promotion to any piece, check, checkmate, stalemate, threefold repetition, the
fifty-move rule and insufficient material. Moves can be read in coordinate form
(e2e4, e7e8q) or in Standard Algebraic Notation (Nf3, exd5, O-O, e8=Q+).
"""

FILES = "abcdefgh"
RANKS = "12345678"
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
WHITE, BLACK = "w", "b"
PIECE_NAMES = {"P": "pawn", "N": "knight", "B": "bishop", "R": "rook", "Q": "queen", "K": "king"}


def square_name(sq):
    return FILES[sq & 7] + RANKS[sq >> 3]


def parse_square(text):
    if len(text) != 2 or text[0] not in FILES or text[1] not in RANKS:
        return None
    return RANKS.index(text[1]) * 8 + FILES.index(text[0])


def is_light(sq):
    """a1 is a dark square; h1 is light."""
    return ((sq & 7) + (sq >> 3)) % 2 == 1


def color_of(piece):
    if piece == ".":
        return None
    return WHITE if piece.isupper() else BLACK


def other(color):
    return BLACK if color == WHITE else WHITE


# ---------------------------------------------------------------- lookup tables
def _build_tables():
    knight, king = [], []
    rays = []  # rays[sq][dir] -> list of squares outward
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    for sq in range(64):
        f, r = sq & 7, sq >> 3
        knight.append([(r + dr) * 8 + f + df for df, dr in
                       ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
                       if 0 <= f + df < 8 and 0 <= r + dr < 8])
        king.append([(r + dr) * 8 + f + df for df, dr in dirs
                     if 0 <= f + df < 8 and 0 <= r + dr < 8])
        sq_rays = []
        for df, dr in dirs:
            ray, nf, nr = [], f + df, r + dr
            while 0 <= nf < 8 and 0 <= nr < 8:
                ray.append(nr * 8 + nf)
                nf += df
                nr += dr
            sq_rays.append(ray)
        rays.append(sq_rays)
    return knight, king, rays


KNIGHT, KING, RAYS = _build_tables()
ROOK_DIRS = (0, 1, 2, 3)
BISHOP_DIRS = (4, 5, 6, 7)
QUEEN_DIRS = (0, 1, 2, 3, 4, 5, 6, 7)
# Castling rights lost when anything moves from or to these squares
CASTLE_MASK = {0: "Q", 4: "KQ", 7: "K", 56: "q", 60: "kq", 63: "k"}


class Board:
    def __init__(self, fen=START_FEN):
        self.set_fen(fen)

    # ------------------------------------------------------------ setup
    def set_fen(self, fen):
        parts = fen.split()
        self.sq = ["."] * 64
        rows = parts[0].split("/")
        for i, row in enumerate(rows):
            rank = 7 - i
            f = 0
            for ch in row:
                if ch.isdigit():
                    f += int(ch)
                else:
                    self.sq[rank * 8 + f] = ch
                    f += 1
        self.turn = parts[1] if len(parts) > 1 else WHITE
        self.castling = "" if len(parts) < 3 or parts[2] == "-" else parts[2]
        self.ep = None if len(parts) < 4 or parts[3] == "-" else parse_square(parts[3])
        self.halfmove = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove = int(parts[5]) if len(parts) > 5 else 1
        # A real game always has both kings; tutorial diagrams may not.
        self.kings = {WHITE: self.sq.index("K") if "K" in self.sq else None,
                      BLACK: self.sq.index("k") if "k" in self.sq else None}
        self.stack = []
        self.history = []        # list of (move, san) played with push()
        self.keys = [self.position_key()]

    def fen(self):
        rows = []
        for rank in range(7, -1, -1):
            row, empty = "", 0
            for f in range(8):
                p = self.sq[rank * 8 + f]
                if p == ".":
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += p
            if empty:
                row += str(empty)
            rows.append(row)
        ep = square_name(self.ep) if self.ep is not None else "-"
        return f"{'/'.join(rows)} {self.turn} {self.castling or '-'} {ep} {self.halfmove} {self.fullmove}"

    def copy(self):
        b = Board.__new__(Board)
        b.sq = self.sq[:]
        b.turn, b.castling, b.ep = self.turn, self.castling, self.ep
        b.halfmove, b.fullmove = self.halfmove, self.fullmove
        b.kings = dict(self.kings)
        b.stack = []
        b.history = list(self.history)
        b.keys = list(self.keys)
        return b

    def position_key(self):
        """Identity of a position for the repetition rule. The en passant square only
        counts when an en passant capture is actually possible."""
        ep = "-"
        if self.ep is not None:
            pawn = "P" if self.turn == WHITE else "p"
            if any(self.sq[s] == pawn for s in self._ep_attackers(self.ep, self.turn)):
                ep = str(self.ep)
        return "".join(self.sq) + self.turn + self.castling + ep

    def _ep_attackers(self, ep, color):
        f = ep & 7
        r = (ep >> 3) - 1 if color == WHITE else (ep >> 3) + 1
        return [r * 8 + f + d for d in (-1, 1) if 0 <= f + d < 8 and 0 <= r < 8]

    # ------------------------------------------------------------ attacks
    def attacked(self, sq, by):
        """Is square sq attacked by side `by`?"""
        s = self.sq
        if by == WHITE:
            pawn, knight, bishop, rook, queen, king = "P", "N", "B", "R", "Q", "K"
            f, r = sq & 7, sq >> 3
            if r > 0:
                if f > 0 and s[sq - 9] == pawn:
                    return True
                if f < 7 and s[sq - 7] == pawn:
                    return True
        else:
            pawn, knight, bishop, rook, queen, king = "p", "n", "b", "r", "q", "k"
            f, r = sq & 7, sq >> 3
            if r < 7:
                if f > 0 and s[sq + 7] == pawn:
                    return True
                if f < 7 and s[sq + 9] == pawn:
                    return True
        for t in KNIGHT[sq]:
            if s[t] == knight:
                return True
        for t in KING[sq]:
            if s[t] == king:
                return True
        rays = RAYS[sq]
        for d in ROOK_DIRS:
            for t in rays[d]:
                p = s[t]
                if p != ".":
                    if p == rook or p == queen:
                        return True
                    break
        for d in BISHOP_DIRS:
            for t in rays[d]:
                p = s[t]
                if p != ".":
                    if p == bishop or p == queen:
                        return True
                    break
        return False

    def in_check(self, color=None):
        color = color or self.turn
        return self.attacked(self.kings[color], other(color))

    # ------------------------------------------------------------ move generation
    def pseudo_moves(self, captures_only=False):
        s = self.sq
        us = self.turn
        moves = []
        add = moves.append
        white = us == WHITE
        for frm in range(64):
            p = s[frm]
            if p == "." or p.isupper() != white:
                continue
            kind = p.upper()
            if kind == "P":
                step = 8 if white else -8
                start_rank = 1 if white else 6
                promo_rank = 7 if white else 0
                f, r = frm & 7, frm >> 3
                to = frm + step
                if not captures_only and s[to] == ".":
                    if to >> 3 == promo_rank:
                        for pr in "qrbn":
                            add((frm, to, pr))
                    else:
                        add((frm, to, ""))
                        if r == start_rank and s[to + step] == ".":
                            add((frm, to + step, ""))
                elif captures_only and s[to] == "." and to >> 3 == promo_rank:
                    add((frm, to, "q"))
                for df in (-1, 1):
                    if 0 <= f + df < 8:
                        t = to + df
                        q = s[t]
                        if (q != "." and q.isupper() != white) or t == self.ep:
                            if t >> 3 == promo_rank:
                                for pr in ("qrbn" if not captures_only else "q"):
                                    add((frm, t, pr))
                            else:
                                add((frm, t, ""))
            elif kind == "N" or kind == "K":
                for t in (KNIGHT if kind == "N" else KING)[frm]:
                    q = s[t]
                    if q == ".":
                        if not captures_only:
                            add((frm, t, ""))
                    elif q.isupper() != white:
                        add((frm, t, ""))
                if kind == "K" and not captures_only:
                    self._castle_moves(frm, add)
            else:
                dirs = ROOK_DIRS if kind == "R" else BISHOP_DIRS if kind == "B" else QUEEN_DIRS
                rays = RAYS[frm]
                for d in dirs:
                    for t in rays[d]:
                        q = s[t]
                        if q == ".":
                            if not captures_only:
                                add((frm, t, ""))
                        else:
                            if q.isupper() != white:
                                add((frm, t, ""))
                            break
        return moves

    def _castle_moves(self, frm, add):
        s, c = self.sq, self.castling
        if self.turn == WHITE and frm == 4:
            if ("K" in c and s[5] == s[6] == "." and s[7] == "R" and not self.attacked(4, BLACK)
                    and not self.attacked(5, BLACK) and not self.attacked(6, BLACK)):
                add((4, 6, ""))
            if ("Q" in c and s[3] == s[2] == s[1] == "." and s[0] == "R" and not self.attacked(4, BLACK)
                    and not self.attacked(3, BLACK) and not self.attacked(2, BLACK)):
                add((4, 2, ""))
        elif self.turn == BLACK and frm == 60:
            if ("k" in c and s[61] == s[62] == "." and s[63] == "r" and not self.attacked(60, WHITE)
                    and not self.attacked(61, WHITE) and not self.attacked(62, WHITE)):
                add((60, 62, ""))
            if ("q" in c and s[59] == s[58] == s[57] == "." and s[56] == "r" and not self.attacked(60, WHITE)
                    and not self.attacked(59, WHITE) and not self.attacked(58, WHITE)):
                add((60, 58, ""))

    def legal_moves(self):
        us = self.turn
        legal = []
        for m in self.pseudo_moves():
            self.make(m)
            if not self.attacked(self.kings[us], self.turn):
                legal.append(m)
            self.unmake()
        return legal

    def is_legal(self, move):
        return move in self.legal_moves()

    # ------------------------------------------------------------ make / unmake
    def make(self, move):
        frm, to, promo = move
        s = self.sq
        piece = s[frm]
        captured = s[to]
        cap_sq = to
        undo = (move, piece, captured, to, self.castling, self.ep, self.halfmove, self.fullmove)
        kind = piece.upper()
        if kind == "P" and to == self.ep and captured == ".":
            cap_sq = to - 8 if piece == "P" else to + 8
            captured = s[cap_sq]
            s[cap_sq] = "."
            undo = (move, piece, captured, cap_sq, self.castling, self.ep, self.halfmove, self.fullmove)
        s[to] = (promo.upper() if piece.isupper() else promo) if promo else piece
        s[frm] = "."
        if kind == "K":
            self.kings[self.turn] = to
            if to - frm == 2:          # king side castle
                s[frm + 1], s[frm + 3] = s[frm + 3], "."
            elif frm - to == 2:        # queen side castle
                s[frm - 1], s[frm - 4] = s[frm - 4], "."
        if self.castling:
            for k in (frm, to):
                lost = CASTLE_MASK.get(k)
                if lost:
                    for ch in lost:
                        self.castling = self.castling.replace(ch, "")
        self.ep = (frm + to) // 2 if kind == "P" and abs(to - frm) == 16 else None
        self.halfmove = 0 if kind == "P" or captured != "." else self.halfmove + 1
        if self.turn == BLACK:
            self.fullmove += 1
        self.turn = other(self.turn)
        self.stack.append(undo)
        return captured

    def unmake(self):
        move, piece, captured, cap_sq, castling, ep, halfmove, fullmove = self.stack.pop()
        frm, to, promo = move
        s = self.sq
        self.turn = other(self.turn)
        s[frm] = piece
        s[to] = "."
        s[cap_sq] = captured
        if piece.upper() == "K":
            self.kings[self.turn] = frm
            if to - frm == 2:
                s[frm + 3], s[frm + 1] = s[frm + 1], "."
            elif frm - to == 2:
                s[frm - 4], s[frm - 1] = s[frm - 1], "."
        self.castling, self.ep, self.halfmove, self.fullmove = castling, ep, halfmove, fullmove

    # ------------------------------------------------------------ game level
    def push(self, move):
        """Play a legal move in the real game. Returns a dict describing it."""
        san = self.san(move)
        piece = self.sq[move[0]]
        castle = piece.upper() == "K" and abs(move[1] - move[0]) == 2
        en_passant = piece.upper() == "P" and move[1] == self.ep and self.sq[move[1]] == "."
        captured = self.make(move)
        self.history.append((move, san))
        self.keys.append(self.position_key())
        return {"move": move, "san": san, "piece": piece, "captured": captured,
                "castle": castle, "en_passant": en_passant, "promotion": move[2],
                "check": self.in_check()}

    def outcome(self):
        """None while the game goes on, else (result, reason) with result in
        'white', 'black', 'draw' and reason in checkmate, stalemate, repetition,
        fifty_moves, insufficient."""
        if not self.legal_moves():
            if self.in_check():
                return ("black" if self.turn == WHITE else "white", "checkmate")
            return ("draw", "stalemate")
        if self.insufficient_material():
            return ("draw", "insufficient")
        if self.halfmove >= 100:
            return ("draw", "fifty_moves")
        if self.keys.count(self.keys[-1]) >= 3:
            return ("draw", "repetition")
        return None

    def insufficient_material(self):
        minors = []
        for i, p in enumerate(self.sq):
            if p in ".Kk":
                continue
            if p in "PpRrQq":
                return False
            minors.append((p, i))
        if len(minors) <= 1:
            return True     # K v K, K+B v K, K+N v K
        if all(p in "Bb" for p, _ in minors):
            # any number of bishops, all on the same colour, can never mate
            return len({is_light(i) for _, i in minors}) == 1
        return False

    # ------------------------------------------------------------ notation
    def san(self, move):
        """Standard Algebraic Notation for a legal move in the current position."""
        frm, to, promo = move
        piece = self.sq[frm]
        kind = piece.upper()
        if kind == "K" and to - frm == 2:
            text = "O-O"
        elif kind == "K" and frm - to == 2:
            text = "O-O-O"
        else:
            capture = self.sq[to] != "." or (kind == "P" and to == self.ep)
            if kind == "P":
                text = (FILES[frm & 7] + "x" if capture else "") + square_name(to)
                if promo:
                    text += "=" + promo.upper()
            else:
                rivals = [m[0] for m in self.legal_moves()
                          if m[1] == to and m[0] != frm and self.sq[m[0]] == piece]
                dis = ""
                if rivals:
                    if all((r & 7) != (frm & 7) for r in rivals):
                        dis = FILES[frm & 7]
                    elif all((r >> 3) != (frm >> 3) for r in rivals):
                        dis = RANKS[frm >> 3]
                    else:
                        dis = square_name(frm)
                text = kind + dis + ("x" if capture else "") + square_name(to)
        self.make(move)
        if self.in_check():
            text += "#" if not self.legal_moves() else "+"
        self.unmake()
        return text

    def coord(self, move):
        return square_name(move[0]) + square_name(move[1]) + move[2]

    def parse(self, text):
        """Read a typed move. Returns (move, None) or (None, error_code).

        Error codes: empty, format, no_piece, not_yours, illegal, self_check,
        ambiguous, promote_needed.
        """
        raw = text.strip()
        if not raw:
            return None, "empty"
        t = raw.replace(" ", "").replace("0", "O").rstrip("+#!?")
        legal = self.legal_moves()
        if t in ("O-O", "OO", "o-o", "oo"):
            return self._castle(legal, kingside=True)
        if t in ("O-O-O", "OOO", "o-o-o", "ooo"):
            return self._castle(legal, kingside=False)
        # Coordinate form: e2e4, e2-e4, e2xe4, e7e8q, e7e8=Q
        low = t.lower().replace("-", "").replace("x", "").replace("=", "").replace(":", "")
        if len(low) in (4, 5) and parse_square(low[:2]) is not None and parse_square(low[2:4]) is not None:
            promo = low[4] if len(low) == 5 else ""
            if promo and promo not in "qrbn":
                return None, "format"
            return self._from_coords(parse_square(low[:2]), parse_square(low[2:4]), promo, legal)
        return self._from_san(t, legal)

    def _castle(self, legal, kingside):
        k = self.kings[self.turn]
        to = k + 2 if kingside else k - 2
        if (k, to, "") in legal:
            return (k, to, ""), None
        return None, "illegal"

    def _from_coords(self, frm, to, promo, legal):
        piece = self.sq[frm]
        if piece == ".":
            return None, "no_piece"
        if color_of(piece) != self.turn:
            return None, "not_yours"
        if piece.upper() == "P" and to >> 3 in (0, 7):
            promo = promo or "q"   # no letter typed: promote to a queen
        elif promo:
            return None, "format"
        move = (frm, to, promo)
        if move in legal:
            return move, None
        return None, self._why_illegal(move)

    def _why_illegal(self, move):
        """Tell apart 'that piece can't go there' from 'that would leave your king in check'."""
        if move in self.pseudo_moves():
            return "self_check"
        if self.sq[move[0]].upper() == "K" and abs(move[1] - move[0]) == 2:
            return "castle_blocked"
        return "illegal"

    def _from_san(self, t, legal):
        t = t.replace("=", "").replace("-", "")
        if not t:
            return None, "format"
        candidates = [t]
        # Friendly to beginners: lower case piece letters (nf3, qd1) are understood too.
        # 'b' is tried as a pawn on the b-file first, then as a bishop.
        if t[0] in "nrqk":
            candidates.append(t[0].upper() + t[1:])
        if t[0] == "b" and len(t) >= 3:
            candidates.append("B" + t[1:])
        if len(t) >= 2 and t[-1] in "qrbn" and t[-2] in "18":
            candidates.append(t[:-1] + t[-1].upper())
        error = "format"
        for cand in candidates:
            move, err = self._san_once(cand, legal)
            if move:
                return move, None
            if err != "format" and error == "format":
                error = err
        return None, error

    def _san_once(self, t, legal):
        promo = ""
        if len(t) >= 3 and t[-1] in "QRBN" and t[-2] in "18":
            promo = t[-1].lower()
            t = t[:-1]
        if not t:
            return None, "format"
        kind = "P"
        if t[0] in "NBRQK":
            kind = t[0]
            t = t[1:]
        capture = "x" in t
        t = t.replace("x", "")
        if len(t) < 2:
            return None, "format"
        to = parse_square(t[-2:])
        if to is None:
            return None, "format"
        dis = t[:-2]
        if len(dis) > 2 or any(c not in FILES + RANKS for c in dis):
            return None, "format"
        if kind == "P" and dis and (len(dis) != 1 or dis not in FILES):
            return None, "format"
        if kind == "P" and capture and not dis:
            return None, "format"
        if promo and kind != "P":
            return None, "format"
        want = kind if self.turn == WHITE else kind.lower()
        matches = []
        for m in legal:
            if m[1] != to or self.sq[m[0]] != want:
                continue
            if kind == "P":
                if (to >> 3) in (0, 7):
                    if m[2] != (promo or "q"):
                        continue
                elif promo:
                    continue
                if dis and FILES[m[0] & 7] != dis:
                    continue
                if not dis and (m[0] & 7) != (to & 7):
                    continue
            for c in dis:
                if c in FILES and FILES[m[0] & 7] != c:
                    break
                if c in RANKS and RANKS[m[0] >> 3] != c:
                    break
            else:
                matches.append(m)
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, "ambiguous"
        # Work out a helpful reason
        if not any(p == want for p in self.sq):
            return None, "no_piece"
        pseudo = [m for m in self.pseudo_moves() if m[1] == to and self.sq[m[0]] == want]
        if pseudo:
            return None, "self_check"
        return None, "illegal"

    def piece_moves_from(self, frm):
        return [m for m in self.legal_moves() if m[0] == frm]
