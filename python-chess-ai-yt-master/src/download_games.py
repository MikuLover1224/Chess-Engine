"""
download_games.py
-----------------
Downloads all games for a chess.com username and saves them as a
single PGN file: games.pgn

Usage:
    python download_games.py taibbbbbbb
"""

import sys
import time
import json
import urllib.request
import urllib.error

USERNAME = sys.argv[1] if len(sys.argv) > 1 else "taibbbbbbb"
OUTPUT   = "games.pgn"
HEADERS  = {"User-Agent": f"chess-bot-trainer/1.0 (studying {USERNAME})"}


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def main():
    print(f"Fetching archive list for '{USERNAME}' ...")
    archives_url = f"https://api.chess.com/pub/player/{USERNAME}/games/archives"
    try:
        data     = json.loads(get(archives_url))
        archives = data.get("archives", [])
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure the username is correct and you have internet access.")
        sys.exit(1)

    if not archives:
        print("No games found.")
        sys.exit(0)

    print(f"Found {len(archives)} month(s) of games. Downloading...")

    total = 0
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for archive_url in archives:
            pgn_url   = archive_url + "/pgn"
            month_tag = "/".join(archive_url.split("/")[-2:])
            try:
                pgn_text = get(pgn_url)
                games_in_month = pgn_text.count("[Event ")
                f.write(pgn_text)
                f.write("\n\n")
                total += games_in_month
                print(f"  {month_tag}: {games_in_month} games")
                time.sleep(0.5)   # be polite to the API
            except urllib.error.HTTPError as e:
                print(f"  {month_tag}: HTTP {e.code} — skipping")
            except Exception as e:
                print(f"  {month_tag}: {e} — skipping")

    print(f"\nDone! {total} games saved to '{OUTPUT}'")


if __name__ == "__main__":
    main()