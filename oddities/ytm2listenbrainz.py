#!/usr/bin/env python3

from datetime import datetime
import argparse
import requests
import json
import time
import re

RED = "\033[91m"
RESET = "\033[0m"

MEDIA_PLAYER = "ytm2listenbrainz"
SUBMISSION_CLIENT = "https://github.com/TheAirBlow/AeroScripts/blob/main/oddities/ytm2listenbrainz.py"
LISTENBRAINZ_URL = "https://api.listenbrainz.org/1/submit-listens"

parser = argparse.ArgumentParser(prog="ytm2listenbrainz", description="Imports a YouTube Music watch-history.json export into ListenBrainz")
parser.add_argument("history", help="Path to the watch-history.json file")
parser.add_argument("-t", "--token", help="ListenBrainz user token", required=True)
parser.add_argument("-m", "--min-timestamp", help="Earliest unix timestamp to submit from (default: 0)", type=int, default=0)
args = parser.parse_args()

# https://github.com/MorpheApp/morphe-patches/blob/main/extensions/music/src/main/java/app/morphe/extension/music/patches/scrobbling/ScrobbleManager.java
TITLE_SUFFIXES = [
    r"\s*[(|\[]official(.*?)[)|\]]",
    r"\s*[(|\[]((lyrics?|visualizer|audio)\s*(video)?)[)|\]]",
    r"\s*[(|\[](performance video)[)|\]]",
    r"\s*[(|\[](clip official)[)|\]]",
    r"\s*[(|\[](video version)[)|\]]",
    r"\s*[(|\[](HD|HQ)\s*?(?:audio)?[)|\]]$",
    r"\s*[(|\[](live)[)|\]]$",
    r"\s*[(|\[]4K\s*?(?:upgrade)?[)|\]]$",
    r"\s*[(|\[](\d{4}\s+)?remaster(ed)?(\s+\d{4})?[)|\]]",
    r"\s*[(|\[](mono|stereo)[)|\]]",
]
ARTIST_SUFFIXES = [r"\s*(- topic)$", r"\s*vevo$"]

def apply_suffixes(name, suffixes):
    for pattern in suffixes:
        name = re.sub(pattern, "", name, count=1, flags=re.IGNORECASE)
    return name

def cleanup_title(name):
    return apply_suffixes(re.sub(r"^Watched\s", "", name), TITLE_SUFFIXES)

def cleanup_artist(name):
    return apply_suffixes(name, ARTIST_SUFFIXES)

def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]

def build_listens(data, min_timestamp):
    listens = []
    for entry in data:
        timestamp = entry["time"].replace("Z", "+00:00")
        listened_at = int(datetime.fromisoformat(timestamp).timestamp())
        if listened_at < min_timestamp:
            continue
        if entry["header"] == "YouTube":
            continue
        if "subtitles" not in entry:
            continue

        artist_name = cleanup_artist(entry["subtitles"][0]["name"])
        if not artist_name:
            continue

        track_metadata = {
            "artist_name": artist_name,
            "track_name": cleanup_title(entry["title"]),
            "additional_info": {
                "media_player": MEDIA_PLAYER,
                "music_service": "music.youtube.com",
                "origin_url": entry["titleUrl"],
                "submission_client": SUBMISSION_CLIENT,
            }
        }
        listens.append({
            "listened_at": listened_at,
            "track_metadata": track_metadata
        })
    return listens

def submit_to_listenbrainz(listens, token):
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

    total = len(listens)
    done = 0
    for listen_batch in batch(listens, 1000):
        payload = {
            "listen_type": "import",
            "payload": listen_batch
        }
        response = requests.post(LISTENBRAINZ_URL, headers=headers, data=json.dumps(payload))
        done += len(listen_batch)
        if not response.ok:
            print(f"{RED}[ytm2listenbrainz] Batch failed ({response.status_code}): {response.text}{RESET}")
            continue

        print(f"[ytm2listenbrainz] Submitted {done}/{total} listens")
        reset_in = response.headers.get("X-RateLimit-Reset-In")
        if reset_in:
            time.sleep(int(reset_in))

with open(args.history, "r", encoding="utf-8") as file:
    json_data = json.load(file)

print(f"[ytm2listenbrainz] Loaded {len(json_data)} watch-history entries")
listens = build_listens(json_data, args.min_timestamp)
print(f"[ytm2listenbrainz] {len(listens)} entries eligible for submission")
submit_to_listenbrainz(listens, args.token)
print("[ytm2listenbrainz] Import completed")
