#!/usr/bin/env python3
import json
import time
from curl_cffi import requests
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TaskProgressColumn, MofNCompleteColumn,
    TimeRemainingColumn, TimeElapsedColumn
)

MY_USER_ID = ""
AUTH_TOKEN = ""
INPUT_FILE = "all_dms.json"

console = Console()

try:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
except FileNotFoundError:
    console.print("[bold red]Error:[/bold red] all_dms.json not found.")
    exit()

session = requests.Session()
session.headers.update({
    "Authorization": AUTH_TOKEN,
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) discord/0.0.122 Chrome/138.0.7204.251 Electron/37.6.0 Safari/537.36"
})

leaderboard = []

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(bar_width=None, complete_style="cyan"),
    TaskProgressColumn(),
    MofNCompleteColumn(),
    TimeRemainingColumn(),
    TimeElapsedColumn(),
    console=console
) as progress:

    task = progress.add_task("[cyan]Scanning DMs...", total=len(users))

    for user in users:
        c_id = user.get("channel_id")
        u_id = user.get("user_id")
        username = user.get("username", "Unknown")
        display_name = user.get("display_name", "Unknown")

        if not c_id:
            progress.advance(task)
            continue

        counts = {}
        for target_id in [MY_USER_ID, u_id]:
            while True:
                url = f"https://discord.com/api/v9/channels/{c_id}/messages/search"
                resp = session.get(url, params={"author_id": target_id, "sort_by": "timestamp", "sort_order": "desc", "offset": 0})

                if resp.status_code == 200:
                    counts[target_id] = resp.json().get("total_results", 0)
                    break
                elif resp.status_code == 429:
                    retry = resp.json().get("retry_after", 5)
                    progress.console.print(f"[yellow]Rate limited! Sleeping {retry}s...[/yellow]")
                    time.sleep(retry)
                else:
                    counts[target_id] = 0
                    break

        total = counts.get(MY_USER_ID, 0) + counts.get(u_id, 0)
        if total > 0:
            leaderboard.append({
                "id": u_id,
                "username": username,
                "display_name": display_name,
                "me": counts.get(MY_USER_ID, 0),
                "them": counts.get(u_id, 0),
                "total": total
            })

        progress.advance(task)

leaderboard.sort(key=lambda x: x["total"], reverse=True)

with open("dms_leaderboard.json", "w", encoding="utf-8") as f:
    json.dump(leaderboard, f, ensure_ascii=False)

console.print(f"\n[bold green]Success![/bold green] Saved {len(leaderboard)} entries to dms_leaderboard.json")
