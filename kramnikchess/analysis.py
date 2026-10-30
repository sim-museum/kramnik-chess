"""Post-game analysis, as Chessmaster's Post-Game Analysis window (EPIC CM, CM-19).

After a game: the evaluation after every move (Fairy-Stockfish, Kramnik rules, a fixed search per position so the
same game always reads the same), the game's type as the manual defines it, the moves that threw the game, how long
the game followed grandmaster practice, and a suggested next opponent.

The manual names the types but gives no numbers; these are Kramnik chess's (from White's point of view, centipawns):
  ADV = 100     an advantage (a pawn)
  EVEN = 50     "about even"
  BLUNDER = 300 one move that costs three pawns or more
  * Blunder   -- a decisive game where one move by the loser turned a roughly level game (|eval| <= ADV) into a lost
                 one (a swing of BLUNDER or more) and the loser never got back to level;
  * Dominated -- a decisive game where the winner was never at a disadvantage (never below -ADV);
  * Disputed  -- the advantage went to both sides at some point;
  * Balanced  -- more than 40% of the game was about even (and none of the above).
  Precedence when several fit: Blunder, Dominated, Disputed, Balanced.
"""
import os
import subprocess
import zlib

from . import engine as E
from .game import book, strip_checks

ADV, EVEN, BLUNDER = 100, 50, 300
MATE = 10000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BINARY = os.path.join(ROOT, "engine", "fairy-stockfish-kramnik")
VARIANTS = os.path.join(ROOT, "engine", "kramnik.ini")


def available():
    return os.access(BINARY, os.X_OK) and os.path.exists(VARIANTS)


def _uci(m):
    return E.sqname(m.frm) + E.sqname(m.to) + (m.promo or "")


def evaluate_game(uci_moves, nodes=50000, progress=None, cancel=None):
    """White-point-of-view centipawns after 0..n plies (n + 1 values). Mates are +-MATE (less the distance)."""
    p = subprocess.Popen([BINARY], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, bufsize=1)

    def send(s):
        p.stdin.write(s + "\n"); p.stdin.flush()

    def wait(tok):
        for line in p.stdout:
            if line.startswith(tok):
                return line
        raise RuntimeError("engine ended")
    try:
        for c in ("uci", "setoption name VariantPath value " + VARIANTS, "setoption name UCI_Variant value kramnik",
                  "isready"):
            send(c)
        wait("readyok")
        b, turn, ep, out = E.init_board(), "w", None, []
        for i in range(len(uci_moves) + 1):
            if cancel and cancel():
                return None
            if not E.legal_moves(b, turn, ep):            # game over on the board: mate or stalemate
                v = (-MATE if turn == "w" else MATE) if E.in_check(b, turn) else 0
            else:
                send("position startpos" + (" moves " + " ".join(uci_moves[:i]) if i else ""))
                send("go nodes %d" % nodes)
                score = 0
                for line in p.stdout:
                    if line.startswith("info") and " score " in line:
                        t = line.split()
                        k = t.index("score")
                        if t[k + 1] == "cp":
                            score = int(t[k + 2])
                        elif t[k + 1] == "mate":
                            n = int(t[k + 2])
                            score = (MATE - abs(n)) * (1 if n > 0 else -1)
                    elif line.startswith("bestmove"):
                        break
                v = score if turn == "w" else -score
            out.append(v)
            if progress:
                progress(i, len(uci_moves))
            if i < len(uci_moves):
                m = next(m for m in E.legal_moves(b, turn, ep) if _uci(m) == uci_moves[i])
                b, ep, turn = E.apply_move(b, m), E.ep_after(m), E.opp(turn)
        return out
    finally:
        try:
            send("quit"); p.wait(timeout=3)
        except Exception:
            p.kill()
        for f in (p.stdin, p.stdout):
            try:
                f.close()
            except Exception:
                pass


DECIDED = 1000                     # beyond ten pawns (or a mate) the game is decided: no move there "throws" it


def blunders(evals):
    """[(ply, swing)]: moves (ply = 1-based move index into the game) that cost their side BLUNDER or more, while
    the game was still undecided; swings are measured on evaluations clipped to +-DECIDED."""
    out = []
    for i in range(1, len(evals)):
        mover_white = (i % 2 == 1)                         # ply i was played by White if odd
        before, after = (max(-DECIDED, min(DECIDED, v)) for v in (evals[i - 1], evals[i]))
        loss = (before - after) if mover_white else (after - before)
        if loss >= BLUNDER and abs(before) < DECIDED:
            out.append((i, loss))
    return out


def classify(evals, result):
    """result: 1.0 White won, 0.0 Black won, 0.5 draw. Returns one of Blunder, Dominated, Disputed, Balanced."""
    even = sum(1 for v in evals if abs(v) < EVEN) / max(1, len(evals))
    white_adv, black_adv = any(v >= ADV for v in evals), any(v <= -ADV for v in evals)
    if result in (0.0, 1.0):
        sign = 1 if result == 1.0 else -1
        w = [sign * v for v in evals]                      # the winner's point of view
        for ply, _ in blunders(evals):
            loser_moved = (ply % 2 == 1) != (result == 1.0)
            if loser_moved and abs(w[ply - 1]) <= ADV and all(x > ADV for x in w[ply:]):
                return "Blunder"
        if min(w) > -ADV:
            return "Dominated"
    if white_adv and black_adv:
        return "Disputed"
    return "Balanced" if even > 0.4 else "Dominated" if result in (0.0, 1.0) else "Balanced"


def gm_plies(sans):
    """How many plies the game followed moves played in the grandmaster games (the opening helper's book)."""
    bk, n = book(), 0
    for i, san in enumerate(sans):
        key = " ".join(strip_checks(s) for s in sans[:i])
        if strip_checks(san) in bk.get(key, {}):
            n += 1
        else:
            break
    return n


def suggest_opponent(people, current, my_rating, score):
    """Chessmaster suggests a next opponent: a little stronger after a win, a little weaker after a loss, the same
    level after a draw -- the nearest rated opponent to that target, other than the one just played."""
    target = my_rating + (100 if score == 1.0 else -100 if score == 0.0 else 0)
    cands = [p for p in people if p.name != current]
    return min(cands, key=lambda p: abs(p.rating - target)) if cands else None


# The post-game comment (CM-26, as Chessmaster does it): Chessmaster crosses the game's shape
# with the rating gap in five bands and keeps three phrasings for each. The texts here are Kramnik chess's own.
def band(my_rating, opp_rating):
    """The opponent relative to you: much weaker (300 or more below), weaker (100 or more), even (within 100),
    stronger (100 or more above) or much stronger (300 or more)."""
    gap = opp_rating - my_rating
    return ("much weaker" if gap <= -300 else "weaker" if gap <= -100 else "even" if gap < 100 else
            "stronger" if gap < 300 else "much stronger")


VERDICT = {      # [band][outcome]: what the result means against that opponent
    "much weaker":   {"win": "the result your rating expects", "draw": "a costly draw for you",
                      "loss": "a real setback"},
    "weaker":        {"win": "a sound win", "draw": "half a point dropped", "loss": "an upset against you"},
    "even":          {"win": "a good win against an equal", "draw": "a fair share of the point",
                      "loss": "a loss to an equal"},
    "stronger":      {"win": "a win above your rating", "draw": "a useful draw", "loss": "no shame against a stronger player"},
    "much stronger": {"win": "an upset in your favour", "draw": "an excellent draw", "loss": "the expected result"},
}
COMMENT = {      # [(game type, outcome)]: three phrasings; {opp} is the opponent's name, {verdict} from VERDICT
    ("Blunder", "win"): ("{opp} let the game slip with one bad move and you took it: {verdict}.",
                         "One mistake by {opp} decided it, and you made it count: {verdict}.",
                         "The game turned on a single error by {opp}; you converted it. {Verdict}."),
    ("Blunder", "loss"): ("One move threw away a level game against {opp}: {verdict}.",
                          "You held {opp} until a single error; it was enough. {Verdict}.",
                          "A level game, lost to one bad move against {opp}: {verdict}."),
    ("Dominated", "win"): ("You were never worse against {opp}: {verdict}.",
                           "From the opening on you had the better of {opp}: {verdict}.",
                           "A clean game: {opp} never got a foothold. {Verdict}."),
    ("Dominated", "loss"): ("{opp} kept the upper hand from start to finish: {verdict}.",
                            "You never got level against {opp}: {verdict}.",
                            "{opp} controlled the whole game: {verdict}."),
    ("Disputed", "win"): ("The advantage changed hands, and you had it last: {verdict}.",
                          "A fight in which {opp} was ahead at times; you came out on top. {Verdict}.",
                          "Both sides had their chances against {opp}; yours counted. {Verdict}."),
    ("Disputed", "draw"): ("Both sides were ahead at some point, and it ended level: {verdict}.",
                           "A swinging game against {opp} that came back to equality: {verdict}.",
                           "Chances for both, and a draw at the end: {verdict}."),
    ("Disputed", "loss"): ("You were ahead against {opp} at one point, but not at the end: {verdict}.",
                           "A game of swings that {opp} won: {verdict}.",
                           "Chances for both, and {opp} took the last one: {verdict}."),
    ("Balanced", "win"): ("A long, even game against {opp}, decided late in your favour: {verdict}.",
                          "Little separated you and {opp} for most of the game; you found the difference. {Verdict}.",
                          "A quiet game that you edged: {verdict}."),
    ("Balanced", "draw"): ("An even game against {opp} from start to finish: {verdict}.",
                           "Neither side got much against {opp}: {verdict}.",
                           "A quiet, level game: {verdict}."),
    ("Balanced", "loss"): ("A mostly even game against {opp} that slipped away late: {verdict}.",
                           "Little separated you and {opp} until the end; it went their way. {Verdict}.",
                           "A quiet game that {opp} edged: {verdict}."),
}


def comment(kind, my_score, my_rating, opp_rating, opp, sans):
    """The comment for the player, one of three phrasings chosen from the moves (the same game reads the same)."""
    outcome = {1.0: "win", 0.5: "draw", 0.0: "loss"}[my_score]
    if (kind, outcome) not in COMMENT:                 # a decisive game is never typed Balanced with no shape; guard
        kind = "Balanced"
    verdict = VERDICT[band(my_rating, opp_rating)][outcome]
    text = COMMENT[(kind, outcome)][zlib.crc32(" ".join(sans).encode()) % 3]
    return text.format(opp=opp, verdict=verdict, Verdict=verdict[:1].upper() + verdict[1:])


def summary(evals, result, sans, white, black):
    """The Post-Game Analysis text, as plain sentences."""
    kind = classify(evals, result)
    who = {1.0: "%s won" % white, 0.0: "%s won" % black, 0.5: "Drawn"}[result]
    lines = ["%s in %d moves. Game type: %s." % (who, (len(sans) + 1) // 2, kind)]
    bl = blunders(evals)
    if bl:
        worst = sorted(bl, key=lambda x: -x[1])[:3]
        lines.append("Costliest moves: " + ", ".join(
            "%d%s %s (-%.1f)" % ((ply + 1) // 2, "." if ply % 2 else "...", sans[ply - 1], loss / 100)
            for ply, loss in sorted(worst)) + ".")
    g = gm_plies(sans)
    lines.append("Opening: followed grandmaster games for %d plies." % g if g else "Opening: left grandmaster practice "
                 "at once.")
    return kind, " ".join(lines)
