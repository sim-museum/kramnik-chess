"""The coach (CM-26, as Chessmaster's coach works).

Board overlays. Chessmaster's coach marks the destinations of the player's legal moves as DANGER zones when the
opponent attacks them and SAFE zones when it does not; defenders are not counted. Kramnik chess goes one step further:
a destination is dangerous only if moving there LOSES material by static exchange -- the opponent captures with its
least valuable piece, you recapture with yours, and either side stops when going on would cost it -- so a defended
square attacked once is not marked. A self-capture's own cost is already shown by its purple ring and is not counted
again; only what the exchange on the square adds. With a piece selected the zones are that piece's; with none, a
square is dangerous only if every move there loses material.

The blunder alert. Chessmaster warns while you play: when your move is not the engine's expected move, the evaluation
falls by more than a threshold you set, and the game was not already decided (beyond five pawns), it stops the clock
and offers a take-back. `alert()` is that rule; the evaluations come from the analysis engine (Prober).
"""
import subprocess

from . import engine as E

VALUE = {"p": 1, "n": 3, "b": 3, "r": 5, "q": 9, "k": 100}
DECIDED = 500              # centipawns: beyond five pawns the game is decided and nothing is a blunder
THRESHOLD = 300            # the default alert threshold, as analysis.BLUNDER


def _see(b, turn, ep, sq):
    """What `turn` gains, at best, by starting an exchange on sq (0 if it should not), least valuable attacker first."""
    target = b[sq]
    if not target or target[0] == turn:
        return 0
    caps = [m for m in E.legal_moves(b, turn, ep) if m.to == sq]
    if not caps:
        return 0
    m = min(caps, key=lambda m: (VALUE[b[m.frm][1]], m.promo not in (None, "q")))
    return max(0, VALUE[target[1]] - _see(E.apply_move(b, m), E.opp(turn), E.ep_after(m), sq))


def move_outcome(b, turn, ep, m):
    """Material the mover ends up with from this move and the exchange on its square (pawns; < 0 = loses)."""
    victim = b[m.to]
    gained = VALUE[victim[1]] if victim and victim[0] != turn and m.kind != "self" else 0
    if m.kind == "ep":
        gained = 1
    after = E.apply_move(b, m)
    return gained - _see(after, E.opp(turn), E.ep_after(m), m.to)


def zones(b, turn, ep, moves):
    """{square: "danger" | "safe"} for the destinations of `moves` (legal moves of `turn`)."""
    best = {}
    for m in moves:
        v = move_outcome(b, turn, ep, m)
        best[m.to] = max(best.get(m.to, v), v)
    return {sq: "danger" if v < 0 else "safe" for sq, v in best.items()}


def naive_zones(b, turn, moves):
    """Chessmaster's own overlay, for comparison: danger = the opponent attacks the square, defenders not counted."""
    them = E.opp(turn)
    return {m.to: "danger" if E.attacked(b, m.to, them) else "safe" for m in moves}


def alert(expected, played, before, after, threshold=THRESHOLD, forced=False):
    """Chessmaster's blunder alert. before / after: the evaluation (centipawns) from the mover's side before and
    after the move. Returns the loss to report, or 0 for no alert."""
    if forced or played == expected or abs(before) >= DECIDED:
        return 0
    loss = before - after
    return loss if loss > threshold else 0


class Prober:
    """One analysis engine (neutral Kramnik Fairy-Stockfish), kept running: (best move, centipawns for the side to
    move) of a position, at a fixed search so the same position always answers the same."""
    def __init__(self, binary, variants, nodes=40000):
        self.nodes = nodes
        self.p = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, bufsize=1)
        for c in ("uci", "setoption name VariantPath value " + variants, "setoption name UCI_Variant value kramnik",
                  "isready"):
            self._send(c)
        self._wait("readyok")

    def _send(self, s):
        self.p.stdin.write(s + "\n"); self.p.stdin.flush()

    def _wait(self, tok):
        for line in self.p.stdout:
            if line.startswith(tok):
                return line
        raise RuntimeError("analysis engine ended")

    def probe(self, moves):
        self._send("position startpos" + (" moves " + " ".join(moves) if moves else ""))
        self._send("go nodes %d" % self.nodes)
        score = 0
        for line in self.p.stdout:
            if line.startswith("info") and " score " in line:
                t = line.split()
                k = t.index("score")
                score = int(t[k + 2]) if t[k + 1] == "cp" else (10000 if int(t[k + 2]) > 0 else -10000)
            elif line.startswith("bestmove"):
                return line.split()[1], score
        raise RuntimeError("analysis engine ended")

    def close(self):
        try:
            self._send("quit")
            self.p.wait(timeout=3)
        except Exception:
            self.p.kill()
        for f in (self.p.stdin, self.p.stdout):
            try:
                f.close()
            except Exception:
                pass


def prober():
    """A Prober on the Kramnik Fairy-Stockfish, or None if it is not built."""
    from . import analysis
    if not analysis.available():
        return None
    try:
        return Prober(analysis.BINARY, analysis.VARIANTS)
    except OSError:
        return None

