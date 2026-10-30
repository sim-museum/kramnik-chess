"""Chessmaster opening books (*.OBK), read from the player's installation (EPIC CM, sprint CM-10).

A book is a tree of moves, each with a weight from 0 to 3 (CM-27 adds the generic style books). A move of
weight 0 is followed when the opponent plays it but never chosen.
Kramnik chess has no castling, so a line is cut at its first castling move (it stays legal Kramnik chess up to there).
Result: {moves so far (SAN, space separated): {next move: summed weight of the book lines through it}}, Kramnik
chess's book format; a move that is only ever met (weight 0) stays in the book with 0 and is never chosen.
"""
import os
import struct

from . import engine as E
from .game import strip_checks


def _square(s):                      # Chessmaster a1=0 -> Kramnik chess index (rank 8 first)
    return (7 - s // 8) * 8 + s % 8


def read_obk(path, max_plies=24):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] == b"BOO!":
        n, off = struct.unpack_from("<I", data, 4)[0], 12
    elif data[:4] == b"UGWS":
        n, off = struct.unpack_from("<H", data, 4)[0], 8
    else:
        return None
    if off + 2 * n > len(data):
        return None
    book = {}

    def count(line):                  # one more book line passes through every move of this line, by its weight
        for k in range(len(line)):
            node = book.setdefault(" ".join(san for san, _ in line[:k]), {})
            san, w = line[k]
            node[san] = node.get(san, 0) + w
    start = (E.init_board(), "w", None, [], False)
    cur, pending = start, []
    for i in range(n):
        b0, b1 = data[off + 2 * i], data[off + 1 + 2 * i]
        board, turn, ep, line, dead = cur
        if not b0 & 0x40:
            pending.append(cur)
        frm, to = _square(b0 & 63), _square(b1 & 63)
        if not dead and len(line) < max_plies:
            m = next((m for m in E.legal_moves(board, turn, ep) if m.frm == frm and m.to == to and m.kind != "self"
                      and m.promo in (None, "q")), None)
            if m is None:                # a castling move (illegal in Kramnik chess): the rest of this line is cut
                cur = (board, turn, ep, line, True)
            else:
                san = strip_checks(E.san_of(board, m, ep))
                cur = (E.apply_move(board, m), E.opp(turn), E.ep_after(m), line + [(san, b1 >> 6)], False)
        else:
            cur = (board, turn, ep, line, True)
        if b0 & 0x80:
            count(cur[3])                # the line as played (cut at castling)
            if not pending:
                break
            cur = pending.pop()
    return book


def find_book(directory, name):
    """The book file named in a personality (case-insensitive, as Windows found it), or None."""
    d = os.path.join(directory, "Data", "Opening Books")
    if not name or not os.path.isdir(d):
        return None
    for f in os.listdir(d):
        if f.lower() == name.lower():
            return os.path.join(d, f)
    return None
