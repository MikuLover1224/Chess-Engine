"""
train_from_games.py
-------------------
Reads games.pgn (your chess.com games), analyses which squares your pieces
performed well on (measured by game outcome), and prints updated
piece-square table values you can paste into engine/bot.py.

Usage:
    python train_from_games.py            # reads games.pgn by default
    python train_from_games.py my.pgn     # or specify a file

How it works:
  - Parses every game with a clear result (1-0, 0-1)
  - For each position in the game, records which squares each piece type
    occupied, tagged with whether the game was eventually won or lost
  - Accumulates a "score" per (piece_type, square): +1 for every move
    in a won game, -1 for every move in a lost game
  - Normalises those scores into centipawn bonuses/penalties
  - Blends them 70/30 with the existing PST values so the tables stay
    sane even with a small game sample
  - Prints the final tables ready to paste into bot.py

Requirements:
    pip install python-chess
"""

import sys
import re
import math
import collections

try:
    import chess
    import chess.pgn
except ImportError:
    print("ERROR: python-chess not installed.")
    print("Run:  pip install python-chess")
    sys.exit(1)

PGN_FILE = sys.argv[1] if len(sys.argv) > 1 else "games.pgn"
USERNAME = "taibbbbbbb"   # change if needed
BLEND    = 0.30           # how much weight to give your games vs the base PST

# ---------------------------------------------------------------------------
# Existing base PSTs (copied from bot.py so we can blend)
# ---------------------------------------------------------------------------

BASE_PST = {
    "pawn": [
         0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
         5,  5, 10, 25, 25, 10,  5,  5,
         0,  0,  0, 20, 20,  0,  0,  0,
         5, -5,-10,  0,  0,-10, -5,  5,
         5, 10, 10,-20,-20, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    "knight": [
       -50,-45,-35,-35,-35,-35,-45,-50,
       -45,-25,  0,  5,  5,  0,-25,-45,
       -35,  5, 15, 20, 20, 15,  5,-35,
       -35,  5, 20, 30, 30, 20,  5,-35,
       -35,  5, 20, 30, 30, 20,  5,-35,
       -35,  5, 15, 20, 20, 15,  5,-35,
       -45,-25,  0,  5,  5,  0,-25,-45,
       -50,-45,-35,-35,-35,-35,-45,-50,
    ],
    "bishop": [
       -20,-10,-10,-10,-10,-10,-10,-20,
       -10,  5,  0,  0,  0,  0,  5,-10,
       -10, 10, 10, 10, 10, 10, 10,-10,
       -10,  0, 10, 10, 10, 10,  0,-10,
       -10,  5,  5, 10, 10,  5,  5,-10,
       -10,  0,  5, 10, 10,  5,  0,-10,
       -10,  0,  0,  0,  0,  0,  0,-10,
       -20,-10,-10,-10,-10,-10,-10,-20,
    ],
    "rook": [
         0,  0,  0,  5,  5,  0,  0,  0,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         5, 10, 10, 10, 10, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0,
    ],
    "queen": [
       -20,-10,-10, -5, -5,-10,-10,-20,
       -10,  0,  5,  0,  0,  0,  0,-10,
       -10,  5,  5,  5,  5,  5,  0,-10,
         0,  0,  5,  5,  5,  5,  0, -5,
        -5,  0,  5,  5,  5,  5,  0, -5,
       -10,  0,  5,  5,  5,  5,  0,-10,
       -10,  0,  0,  0,  0,  0,  0,-10,
       -20,-10,-10, -5, -5,-10,-10,-20,
    ],
    "king": [
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -20,-30,-30,-40,-40,-30,-30,-20,
       -10,-20,-20,-30,-30,-20,-20,-10,
        20, 20,  0,-10,-10,  0, 20, 20,
        20, 30, 10,-10,  0,-10, 30, 20,
    ],
}

PIECE_NAMES = {
    chess.PAWN:   "pawn",
    chess.KNIGHT: "knight",
    chess.BISHOP: "bishop",
    chess.ROOK:   "rook",
    chess.QUEEN:  "queen",
    chess.KING:   "king",
}

# ---------------------------------------------------------------------------
# Accumulators: square_wins[piece_name][sq] and square_games[piece_name][sq]
# sq is 0-63, a1=0 .. h8=63 (python-chess convention)
# ---------------------------------------------------------------------------

square_score = {name: [0.0] * 64 for name in BASE_PST}
square_count = {name: [0]   * 64 for name in BASE_PST}


def process_game(game, player_color):
    """Walk through every position and accumulate square occupancy data."""
    result = game.headers.get("Result", "*")
    if result == "1-0":
        outcome = 1 if player_color == chess.WHITE else -1
    elif result == "0-1":
        outcome = -1 if player_color == chess.WHITE else 1
    else:
        return   # skip draws and unfinished games

    board = game.board()
    for node in game.mainline():
        board.push(node.move)
        # Record position from player's perspective
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece is None or piece.color != player_color:
                continue
            name = PIECE_NAMES.get(piece.piece_type)
            if name is None:
                continue
            # From player's perspective: if white, sq is already correct.
            # If black, flip the rank so the table is always "from our side".
            if player_color == chess.WHITE:
                idx = (7 - chess.square_rank(sq)) * 8 + chess.square_file(sq)
            else:
                idx = chess.square_rank(sq) * 8 + chess.square_file(sq)
            square_score[name][idx] += outcome
            square_count[name][idx] += 1


def normalise(scores, counts, max_bonus=40):
    """Convert raw win/loss tallies into centipawn bonuses, range ±max_bonus."""
    result = []
    for s, c in zip(scores, counts):
        if c < 5:
            result.append(None)   # not enough data — keep base value
        else:
            ratio = s / c         # -1..+1
            result.append(ratio * max_bonus)
    return result


def blend(base, learned, weight):
    """Blend learned values into base PST. None = no data, keep base."""
    out = []
    for b, l in zip(base, learned):
        if l is None:
            out.append(b)
        else:
            out.append(round(b * (1 - weight) + l * weight))
    return out


def format_table(values, name):
    lines = [f"{name.upper()}_TABLE = ["]
    for row in range(8):
        row_vals = values[row*8:(row+1)*8]
        line     = "   " + ",".join(f"{v:4d}" for v in row_vals) + ","
        lines.append(line)
    lines.append("]")
    return "\n".join(lines)


def main():
    print(f"Reading '{PGN_FILE}' ...")
    games_processed = 0
    games_skipped   = 0

    try:
        pgn = open(PGN_FILE, encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        print(f"ERROR: '{PGN_FILE}' not found.")
        print("Run download_games.py first to get your games.")
        sys.exit(1)

    while True:
        game = chess.pgn.read_game(pgn)
        if game is None:
            break

        white = game.headers.get("White", "").lower()
        black = game.headers.get("Black", "").lower()
        uname = USERNAME.lower()

        if white == uname:
            player_color = chess.WHITE
        elif black == uname:
            player_color = chess.BLACK
        else:
            games_skipped += 1
            continue

        try:
            process_game(game, player_color)
            games_processed += 1
        except Exception as e:
            games_skipped += 1

        if games_processed % 50 == 0 and games_processed > 0:
            print(f"  Processed {games_processed} games...")

    pgn.close()
    print(f"\nProcessed: {games_processed} games  |  Skipped: {games_skipped}")

    if games_processed == 0:
        print("No games found for your username. Check USERNAME in the script.")
        sys.exit(1)

    # Build final tables
    print(f"\nBlending learned values ({int(BLEND*100)}% your games, "
          f"{int((1-BLEND)*100)}% base PST) ...\n")

    print("=" * 60)
    print("Paste these into engine/bot.py, replacing the existing tables:")
    print("=" * 60 + "\n")

    for name, base in BASE_PST.items():
        raw      = normalise(square_score[name], square_count[name])
        final    = blend(base, raw, BLEND)
        print(format_table(final, name))
        print()

    # Also print stats on which squares you use most
    print("\n--- Your most used squares per piece (top 5) ---")
    for name in ["knight", "bishop", "queen"]:
        counts = square_count[name]
        top    = sorted(range(64), key=lambda i: counts[i], reverse=True)[:5]
        print(f"\n{name.capitalize()}:")
        for i in top:
            rank = 7 - (i // 8)
            file = i % 8
            sq   = "abcdefgh"[file] + str(rank + 1)
            print(f"  {sq}: {counts[i]} half-moves  (win bias: "
                  f"{square_score[name][i]/max(counts[i],1):+.2f})")


if __name__ == "__main__":
    main()