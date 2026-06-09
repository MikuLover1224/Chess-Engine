"""
engine/opening_book.py
----------------------
Loads opening_book.json and provides move lookups for the bot.

The bot calls book.get_move(played_moves, color) which returns a
SAN move string from the book, or None if we're out of book.

Move selection: weighted random by (count * win_rate^2)
— prefers moves you played often AND won with.
"""

import json
import os
import random

BOOK_FILE = os.path.join(os.path.dirname(__file__), "opening_book.json")


class OpeningBook:

    def __init__(self):
        self.white_tree = {}
        self.black_tree = {}
        self.loaded     = False
        self._load()

    def _load(self):
        if not os.path.exists(BOOK_FILE):
            print("[Opening book] No book file found — run build_opening_book.py first.")
            return
        try:
            with open(BOOK_FILE) as f:
                data = json.load(f)
            self.white_tree = data.get("white", {})
            self.black_tree = data.get("black", {})
            self.loaded     = True
            built = data.get("built", "unknown")
            print(f"[Opening book] Loaded (built {built[:10]})")
        except Exception as e:
            print(f"[Opening book] Failed to load: {e}")

    def get_move(self, played_san_moves, bot_color):
        """
        played_san_moves : list of SAN strings already played this game
                           e.g. ["e4", "e5", "Nf3"]
        bot_color        : "white" or "black"

        Returns a SAN string (e.g. "Nf3") or None if out of book.
        """
        if not self.loaded:
            return None

        tree = self.white_tree if bot_color == "white" else self.black_tree

        # Walk down the tree following the moves played so far
        node = tree
        for move in played_san_moves:
            if move not in node:
                return None   # position not in our book
            node = node[move]

        # Collect candidate next moves
        candidates = []
        for move, data in node.items():
            if move.startswith("_"):
                continue
            count   = data.get("_count", 0)
            wins    = data.get("_wins", 0)
            win_rate = wins / count if count > 0 else 0.0
            # Weight: favour frequent moves and winning moves
            weight  = count * (win_rate ** 2 + 0.1)
            candidates.append((move, weight))

        if not candidates:
            return None

        # Weighted random selection
        total   = sum(w for _, w in candidates)
        r       = random.uniform(0, total)
        running = 0
        for move, weight in candidates:
            running += weight
            if running >= r:
                return move

        return candidates[-1][0]   # fallback


# Singleton instance
_book = None

def get_book():
    global _book
    if _book is None:
        _book = OpeningBook()
    return _book