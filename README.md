# Kramnik Chess

Kramnik's chess variant: **no castling, and you may capture your own pieces** (anything but your own king; a king
may take its own pieces too). It's Wednesday's game in Serious Games Week ([serious-games-week](https://github.com/sim-museum/serious-games-week)).

    ./run.sh          # the desktop app (needs python3 and PyQt6: sudo apt install python3-pyqt6)
    ./browser.sh      # the same game in your web browser (kramnik_chess.html)

- **Vs Computer, hotseat, or Computer vs Computer.** Choose your computer opponent by rating and playing style, as in
  Chessmaster. With Chessmaster installed (point `KRAMNIK_CHESSMASTER` at its folder), its 188 personalities are offered (read
  from your installation); otherwise the app's own eight, from 800 to full strength. The opponents play Kramnik chess properly
  and never hand material back. They need the personality engine, built once with `engine/build_engine.sh`
  (Fairy-Stockfish with a self-capture patch); without it, the HTML game's engine plays at full strength.
  Each personality has weights for your side
  and the opponent's, a trade attitude, contempt for draws that fades as material comes off, and randomness as a
  fixed preference per move for each search.
  **Ratings are measured, not labels:** strength is set by search size on a ladder calibrated by matches, the weakest
  opponents (below 1163) by measured evaluation noise (the same misjudgement for the same
  position, so a weak opponent plays plausible moves, not random ones), and each style's cost in strength (an attacker,
  a materialist, a random player) is paid back, so a 1600-rated attacker plays at 1600. The "Choose…" button
  lists all opponents with filters and biographies. Opponents take a player's thinking time on the clock.
- **Rated games**, as in Chessmaster's ranked play: tick "Rated game". Your rating starts from your experience,
  moves quickly for the first 20 games (a performance average, then Elo with K = 32), and each
  game shows what a loss, draw or win would do to it. No take-backs
  and no advice (no book hints) during a rated game. A rated game can be adjourned and resumed later.
  Your history is kept in `~/.local/share/kramnikChess/profile.json`.
- **Learning what self-capture changes.** Kramnik chess looks like ordinary chess, and most moves
  are ordinary moves, which is what makes it deceptive. Kramnik Chess shows where it differs:
  - **Self-capture specialists**: eight opponents from 950 to 2600 (Hal, Rosa, Felix, Mirela, Corin, Ada, Selim,
    Kestrel), each playing for one self-capture idea, with a biography that says what to watch for. They choose,
    among near-best moves, the ones that gain most from Kramnik rules, and self-capture 3–4 times as often as
    ordinary engines. Their ratings are measured: 120 games each against a neutral opponent of the same rating
   . A specialist's biography names the Academy lesson for their
    idea, and New tournament can fill an event with specialists only.
  - **Academy → Kramnik Academy**: eight lessons from beginner to advanced (the king that escapes through its own
    army, promotion through your own piece, opening a file in one move, the quiet threat, ...) with 24 positions to
    solve on the board, from the AlphaZero/Kramnik paper and from strong engine games. Every solution is checked by
    a deep search, and Leela agrees on 22 of 24. Each lesson ends with a game against its
    specialist.
  - **Academy → Getting started**: five minutes for a first-time player, offered on the first launch: the two rules,
    four boards to solve, what the app shows, then an unrated game against Hal with the coach on.
  - **Academy → Self-capture puzzles**: 172 puzzles. 93 are mined from strong engine games, checked by both engines and rated
    1163–2600 by the search strength that finds them. 79 beginner puzzles (660–1100) teach that self-capture is
    legal at all: mates in one that need it, and checks it alone escapes. All are served near your own puzzle rating. Each puzzle's rating
    also moves with players' first attempts (`puzzle_ratings.json`).
  - **The coach** (unrated games, on by default): on your turn, a warning when the natural ordinary-chess move fails
    to a self-capture, or a nudge when a strong self-capture is there. It never names the move, and is silent in
    rated games.
  - **Post-Game Analysis → Self-capture moments**: after each game, the moments where Kramnik rules mattered: self-captures
    played, strong ones missed, and ordinary-chess moves that lost. Click one to see the position, or practise the
    ones you missed as quizzes. During unrated play, a self-capture is named in the status line as it happens.
  - It matters in about 5% of positions in strong games; the motifs, from the AlphaZero / Kramnik paper:
    `docs/SELF_CAPTURE_MOTIFS.md`.
- **The strongest opponent, Leela T40** (with the GPU build): a large network adapted to Kramnik chess here; at
  3000 nodes it scored 14/20 against full-strength Fairy-Stockfish at a second a move. Fairy-Stockfish, which can switch self-capture on and off, does the explaining
  (specialists, coach, analysis, puzzles); Leela brings the judgement.
- **Coach** menu (practice games only; never in rated or network games): the self-capture coach above, and from
  Chessmaster's own coach: the board shows danger zones (a move there
  loses material once the exchanges on that square are played out) and safe zones, and a blunder alert stops the
  clock and offers a take-back when your move throws away more than a threshold you set (3 pawns by default).
  Move hints as arrows: captures in red (thick when the capture wins material once the exchanges are played out;
  one that loses material is not shown), the defenders of your attacked pieces in green, pin and skewer moves
  dotted red, check and checkmate moves in mauve; "other side" (Ctrl+Tab) shows the same for your opponent. The
  pawn hint draws isolated and passed pawns faint. A board coverage overlay shades the squares your pieces cover
  green, your opponent's red, and both amber.
- After each game against the computer, the **Post-Game Analysis** reads the game: its type, the costliest moves, a
  comment that weighs the result against the rating gap, the evaluation chart and a suggested next opponent.
- **Time controls:** Fischer 10+3 (and 5+3, 15+10, 3+2), 30 minutes per game, 40 moves in 90 minutes, or untimed.
  Rated games are always timed. Running out of time loses, unless the other side cannot mate.
- **Opening helper** from 25,072 grandmaster games, each legal Kramnik chess up to its first castling move: blue
  marks show what the grandmasters played here, and the panel lists their moves with how often each was chosen.
  The computer opens as they did, in proportion, and never the same way twice running.
- **Network play** (Network menu). Host a game, or join one. With a Serious Games Week matchmaker set up
  (`sgw url http://<matchmaker>:8090`), a hosted game is listed while it waits for an opponent, and the join dialog
  lists open games. Without one, enter the host's address. TCP port 47810 by default.
- Undo, draw offers both ways, resignation, review (⏮ ◀ ▶ ⏭), PGN save and load.

## Analysis in Nibbler, with a Kramnik neural network
`./nibbler.sh [game.pgn]` opens Nibbler with Leela (lc0) playing Kramnik chess (no castling, self-captures)
and a Kramnik-chess network: put one in `engine/nets/` (`kramnik-sp1.pb.gz`, trained by self-play under Kramnik rules)
or set `KRAMNIK_NET=<file>`; no network is included in this repository. The first run builds the Kramnik lc0 and Nibbler
(`engine/build_lc0.sh`, `engine/make_nibbler.sh`). For about 100x the speed on an NVIDIA GPU, build once with
`engine/build_lc0_gpu.sh` (no system CUDA install needed); the launcher and Kramnik chess's Leela opponent then use it.
Its settings live in `~/.config/kramnik-nibbler`, so your normal Nibbler is untouched.
It plays far above club strength: use it to go over your games, not as an opponent at your level.

