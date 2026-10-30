"""Your rating, as Chessmaster keeps it (EPIC CM, sprint CM-4).

The rule (CM-26):
  * provisional, the first 20 rated games: a running performance average,
        r' = (r x n + r_opp + 400 x (2S - 1)) / (n + 1)        (n = games played so far, S = 1 / 0.5 / 0)
    so the first game alone sets the rating to the opponent's +-400. This reproduces the manual's own example
    exactly ("loss -424, draw -24, win +376": a new player against an opponent 24 points lower);
  * established: Elo with K = 32 x n_opp / 20, n_opp the opponent's game count clamped to 3..20, so a result against
    a lightly played opponent counts less. Computer opponents count as established (K = 32).
  CM-4 used K = max(16, 800 / (games + 1)) before.
The starting rating is estimated from your experience, as Chessmaster's alter ego does from age and chess knowledge.

The profile is a small JSON file: $KRAMNIK_HOME/profile.json, else ~/.local/share/kramnikChess/profile.json.
"""
import json
import os
import time

PROVISIONAL = 20
LEVELS = [   # (label, starting rating)
    ("I know how the pieces move", 800),
    ("I play now and then", 1100),
    ("I play regularly, with a club or online", 1500),   # PO 10-08: SGW players are club strength; = Felix, the default opponent
    ("I am a strong club player", 1700),
    ("I am an expert or tournament player", 2000),
    ("I hold a master title", 2300),
]


def expected(r, opp):
    return 1 / (1 + 10 ** ((opp - r) / 400))


def k_factor(opp_games=PROVISIONAL):
    """Established play: K = 32 x the opponent's games (3..20) / 20."""
    return 32.0 * min(PROVISIONAL, max(3, opp_games)) / PROVISIONAL


def change(r, opp, games, score, opp_games=PROVISIONAL):
    """The exact rating change for one result (score 1, 0.5 or 0)."""
    if games < PROVISIONAL:
        return (r * games + opp + 400 * (2 * score - 1)) / (games + 1) - r
    return k_factor(opp_games) * (score - expected(r, opp))


def changes(r, opp, games, opp_games=PROVISIONAL):
    """The rating change for a loss, a draw and a win, rounded as shown before the game."""
    return tuple(round(change(r, opp, games, s, opp_games)) for s in (0.0, 0.5, 1.0))


def profile_path():
    base = os.environ.get("KRAMNIK_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share", "kramnikChess")
    return os.path.join(base, "profile.json")


class Profile:
    def __init__(self, name="Player", rating=1500, games=0, history=None, path=None):
        self.name, self.rating, self.games = name, rating, games
        self.history = history or []      # dicts: time, opponent, opponent_rating, result, before, after, colour, plies
        self.path = path or profile_path()

    @property
    def provisional(self):
        return self.games < PROVISIONAL

    def preview(self, opp_rating):
        return changes(self.rating, opp_rating, self.games)

    def record(self, opponent, opp_rating, score, colour="", plies=0, pgn=""):
        """score: 1 win, 0.5 draw, 0 loss. Returns the change applied."""
        delta = round(change(self.rating, opp_rating, self.games, score))
        before = self.rating
        self.rating = max(100, self.rating + delta)          # Chessmaster's floor is 1; Kramnik chess keeps 100
        self.games += 1
        self.history.append({"time": int(time.time()), "opponent": opponent, "opponent_rating": opp_rating,
                             "result": score, "before": before, "after": self.rating, "colour": colour, "plies": plies,
                             "pgn": pgn})
        self.save()
        return self.rating - before

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"name": self.name, "rating": self.rating, "games": self.games, "history": self.history}, f, indent=1)
        os.replace(tmp, self.path)

    @classmethod
    def load(cls, path=None):
        """The saved profile, or None if the player has never set one up."""
        p = path or profile_path()
        try:
            with open(p) as f:
                d = json.load(f)
            return cls(d.get("name", "Player"), int(d["rating"]), int(d.get("games", 0)), d.get("history", []), p)
        except (OSError, ValueError, KeyError):
            return None


# ---- adjourned rated games (CM-11): one at a time, as Chessmaster keeps them ----------------------------------------
def _adjourned_path():
    return os.path.join(os.path.dirname(profile_path()), "adjourned.json")


def save_adjourned(state):
    """state: opponent, rating, colour, sans (moves so far), clock (kind, args, left, moves)."""
    p = _adjourned_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w") as f:
        json.dump(state, f)
    os.replace(p + ".tmp", p)


def load_adjourned():
    try:
        with open(_adjourned_path()) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def clear_adjourned():
    try:
        os.remove(_adjourned_path())
    except OSError:
        pass
