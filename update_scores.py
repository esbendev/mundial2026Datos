#!/usr/bin/env python3
import re
import subprocess
from datetime import date, timezone
from datetime import datetime as dt

DATOS_FILE = "datos.txt"

def parse_line(line):
    """Parse a CSV line, handling quoted fields with emoji."""
    # Match: "datetime","home","away",score1,score2,field6
    m = re.match(r'^"([^"]+)","([^"]+)","([^"]+)",(-?\d+),(-?\d+),(\d+)$', line.rstrip())
    if m:
        return {
            "datetime": m.group(1),
            "home": m.group(2),
            "away": m.group(3),
            "home_score": int(m.group(4)),
            "away_score": int(m.group(5)),
            "field6": m.group(6),
            "raw": line,
        }
    return None

def build_line(g):
    return f'"{g["datetime"]}","{g["home"]}","{g["away"]}",{g["home_score"]},{g["away_score"]},{g["field6"]}\n'

def local_dt(utc_str):
    """Parse a UTC ISO datetime string and return the local datetime."""
    utc_time = dt.fromisoformat(utc_str.replace("Z", "+00:00"))
    return utc_time.astimezone(tz=None)  # convert to local timezone

def main():
    today = date.today()  # local today
    today_str = today.isoformat()
    print(f"Today's date: {today_str}\n")

    with open(DATOS_FILE, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # Find games whose local time falls on today
    today_games = []
    for i, line in enumerate(all_lines):
        g = parse_line(line)
        if g:
            local = local_dt(g["datetime"])
            if local.date() == today:
                g["local_dt"] = local
                today_games.append((i, g))

    if not today_games:
        print("No games found for today.")
        return

    print(f"Games on {today_str} (local time):")
    print("-" * 60)
    for _, g in today_games:
        score_str = f"{g['home_score']} - {g['away_score']}" if g['home_score'] != -1 else "vs"
        time_str = g["local_dt"].strftime("%H:%M")
        print(f"  {time_str}  {g['home']}  {score_str}  {g['away']}")
    print("-" * 60)

    # Ask for scores
    changes = []
    for idx, (line_i, g) in enumerate(today_games):
        current = f"{g['home_score']} - {g['away_score']}" if g['home_score'] != -1 else "not set"
        print(f"\n[{idx+1}] {g['home']} vs {g['away']}  (current score: {current})")
        ans = input("  Update score? (y/N): ").strip().lower()
        if ans == "y":
            while True:
                try:
                    home_score = int(input(f"  {g['home']} goals: ").strip())
                    away_score = int(input(f"  {g['away']} goals: ").strip())
                    if home_score < 0 or away_score < 0:
                        print("  Scores must be 0 or positive.")
                        continue
                    break
                except ValueError:
                    print("  Please enter a valid integer.")
            changes.append((line_i, g, home_score, away_score))

    if not changes:
        print("\nNo changes entered. Exiting.")
        return

    # Show summary
    print("\n" + "=" * 60)
    print("Pending changes:")
    commit_details = []
    for line_i, g, hs, as_ in changes:
        time_str = local_dt(g["datetime"]).strftime("%H:%M")
        print(f"  {g['home']} {hs} - {as_} {g['away']}  ({time_str} local)")
        commit_details.append(f"{g['home']} {hs}-{as_} {g['away']}")
    print("=" * 60)

    confirm = input("\nApply these changes and commit+push? (y/N): ").strip().lower()
    if confirm != "y":
        print("Aborted. No changes made.")
        return

    # Apply changes to lines
    for line_i, g, hs, as_ in changes:
        g["home_score"] = hs
        g["away_score"] = as_
        all_lines[line_i] = build_line(g)

    with open(DATOS_FILE, "w", encoding="utf-8") as f:
        f.writelines(all_lines)
    print(f"\n{DATOS_FILE} updated.")

    # Git commit
    commit_msg = f"Scores {today}: {', '.join(commit_details)}"
    try:
        subprocess.run(["git", "add", DATOS_FILE], check=True)
        subprocess.run(["git", "commit", "-m", commit_msg], check=True)
        print(f"\nCommitted: {commit_msg}")
        subprocess.run(["git", "push"], check=True)
        print("Pushed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\nGit error: {e}")

if __name__ == "__main__":
    main()
