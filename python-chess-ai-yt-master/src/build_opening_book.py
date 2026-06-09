"""
build_opening_book.py
---------------------
Builds engine/opening_book.json from your downloaded games.
Only uses games where you played well (high accuracy or won).
"""

import json
import os
import re
import datetime

OUTPUT_FILE = os.path.join("engine", "opening_book.json")
PGN_FILE = "games.pgn"
USERNAME = "taibbbbbbb"
MIN_ACCURACY = 75.0       # Only use games where you played well
MAX_BOOK_DEPTH = 12       # 6 moves per side
MIN_MOVE_FREQ = 2         # Move must appear in at least 2 games

def parse_header(pgn_text, tag):
    m = re.search(rf'\[{tag}\s+"([^"]+)"\]', pgn_text)
    return m.group(1) if m else None

def parse_moves(pgn_text, max_halfmoves):
    body = re.sub(r'\[[^\]]*\]', '', pgn_text)
    body = re.sub(r'\{[^}]*\}', '', body)
    body = re.sub(r'\d+\.+', '', body)
    body = re.sub(r'(1-0|0-1|1/2-1/2|\*)\s*$', '', body)
    tokens = body.split()
    return tokens[:max_halfmoves]

def split_games(pgn_text):
    games = re.split(r'(?=\[Event )', pgn_text)
    return [g.strip() for g in games if g.strip()]

def build_tree():
    return {}

def insert_line(tree, moves, won):
    node = tree
    for move in moves:
        if move not in node:
            node[move] = {"_count": 0, "_wins": 0}
        node[move]["_count"] += 1
        if won:
            node[move]["_wins"] += 1
        node = node[move]

def prune_tree(node, min_freq, depth, max_depth):
    if depth >= max_depth:
        return {}
    pruned = {}
    for key, val in node.items():
        if key.startswith("_"):
            pruned[key] = val
            continue
        if val.get("_count", 0) >= min_freq:
            pruned[key] = prune_tree(val, min_freq, depth + 1, max_depth)
    return pruned

def tree_stats(node, depth=0):
    moves = 0
    for key, val in node.items():
        if key.startswith("_"): continue
        moves += 1
        moves += tree_stats(val, depth + 1)
    return moves

def main():
    if not os.path.exists(PGN_FILE):
        print(f"ERROR: {PGN_FILE} not found. Run download_games.py first.")
        return

    with open(PGN_FILE, encoding="utf-8", errors="ignore") as f:
        pgn_text = f.read()

    games = split_games(pgn_text)
    print(f"Found {len(games)} games")

    tree_white = build_tree()
    tree_black = build_tree()
    used = skipped = 0

    for pgn in games:
        white = (parse_header(pgn, "White") or "").lower()
        black = (parse_header(pgn, "Black") or "").lower()
        uname = USERNAME.lower()

        if white == uname:
            color = "white"
        elif black == uname:
            color = "black"
        else:
            skipped += 1
            continue

        # Only use games you won or played well
        accuracy = parse_header(pgn, f"{'White' if color == 'white' else 'Black'}Accuracy")
        if accuracy:
            try:
                acc = float(accuracy)
                if acc < MIN_ACCURACY:
                    skipped += 1
                    continue
            except ValueError:
                pass

        result = parse_header(pgn, "Result") or "*"
        won = (color == "white" and result == "1-0") or (color == "black" and result == "0-1")

        moves = parse_moves(pgn, MAX_BOOK_DEPTH)
        if not moves:
            skipped += 1
            continue

        tree = tree_white if color == "white" else tree_black
        insert_line(tree, moves, won)
        used += 1

    print(f"Games used: {used}")
    print(f"Skipped: {skipped}")

    tree_white = prune_tree(tree_white, MIN_MOVE_FREQ, 0, MAX_BOOK_DEPTH)
    tree_black = prune_tree(tree_black, MIN_MOVE_FREQ, 0, MAX_BOOK_DEPTH)

    book = {
        "username": USERNAME,
        "built": datetime.datetime.now().isoformat(),
        "white": tree_white,
        "black": tree_black,
    }

    os.makedirs("engine", exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(book, f, indent=2)

    total = tree_stats(tree_white) + tree_stats(tree_black)
    print(f"\nBook saved! {total} total moves")
    print(f"White: {tree_stats(tree_white)} moves")
    print(f"Black: {tree_stats(tree_black)} moves")

    # Show your top 3 openings
    print("\nYour most common openings:")
    for color_name, tree in [("White", tree_white), ("Black", tree_black)]:
        print(f"\n  As {color_name}:")
        sorted_moves = sorted(
            [(k, v) for k, v in tree.items() if not k.startswith("_")],
            key=lambda x: x[1].get("_count", 0),
            reverse=True
        )[:3]
        for move, data in sorted_moves:
            count = data.get("_count", 0)
            wins = data.get("_wins", 0)
            wp = wins / count * 100 if count else 0
            print(f"    {move:8s}  {count:3d} games  {wp:.0f}% win")

if __name__ == "__main__":
    main()