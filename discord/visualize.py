#!/usr/bin/env python3
import os, json, matplotlib.pyplot as plt
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TaskProgressColumn, MofNCompleteColumn,
    TimeRemainingColumn, TimeElapsedColumn
)
from matplotlib import font_manager as fm
import unicodedata
import re
import requests, mimetypes
from PIL import ImageFont, ImageDraw, Image
import textwrap
from io import BytesIO

console = Console()
IN_FILE = "stats.json"
OUT_DIR = "output"
MSG_DIR = os.path.join(OUT_DIR, "messages")

WHITELIST = {
    "✅", "💎", "🔥", "🥶"
}


os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(MSG_DIR, exist_ok=True)

# =============================================================================
# Helper functions
# =============================================================================
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

fm.fontManager.addfont("/home/theairblow/Tools/DiscordChatExporter/.obamacord/NotoEmoji-Regular.ttf")
plt.rcParams['font.family'] = ['Noto Sans', 'Noto Emoji']

def make_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None, complete_style="cyan"),
        TaskProgressColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    )

def plot_leaderboard(items, title, value_label="Count", annotate_extra=None, outfile="leaderboard.png", figsize=(9,6)):
    if not items:
        return
    items = sorted(items, key=lambda d: (-d["value"], d["name"]))
    names = [f"{i+1}. {d['name']}" for i, d in enumerate(items)]
    vals = [d["value"] for d in items]
    vmax = max(vals) or 1.0
    plt.figure(figsize=figsize, dpi=180)
    ax = plt.gca()
    bars = ax.barh(range(len(items)), vals)
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel(value_label)
    ax.set_title(title, loc="left", pad=12, fontsize=12, fontweight="bold")
    for i, (y, v) in enumerate(zip(range(len(items)), vals)):
        if isinstance(v, float):
            if v == 0:
                label_text = "0"
            elif abs(v) < 1:
                label_text = f"{v:.6f}".rstrip("0").rstrip(".")
            else:
                label_text = f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            label_text = f"{int(v)}"
        extra = f"  {annotate_extra(items[i])}" if annotate_extra else ""
        ax.text(v + vmax * 0.01, y, label_text + extra, va="center", fontsize=8)

    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", linestyle=":", alpha=0.35)
    ax.margins(y=0)
    plt.subplots_adjust(left=0.25, right=0.97, top=0.96, bottom=0.03)
    plt.savefig(outfile, bbox_inches="tight")
    plt.close()

def normalize_daily_counter(counter: dict, start=None, end=None):
    if not counter:
        return [], []

    parsed = {
        datetime.strptime(d, "%Y-%m-%d").date(): v
        for d, v in counter.items()
    }

    min_day = start or min(parsed)
    max_day = end or max(parsed)

    dates = []
    values = []

    cur = min_day
    while cur <= max_day:
        dates.append(datetime.combine(cur, datetime.min.time()))
        values.append(parsed.get(cur, 0))
        cur += timedelta(days=1)

    return dates, values

# =============================================================================
# Load JSON
# =============================================================================
if not os.path.exists(IN_FILE):
    console.print(f"[red]❌ stats.json not found. Run analyze.py first.[/red]")
    raise SystemExit()

with open(IN_FILE, "r", encoding="utf-8") as f:
    full_data = json.load(f)

stats = full_data.get("stats", {})
reactions_data = full_data.get("reactions", {})
messages_per_day_global = full_data.get("messages_per_day", {})

messages_per_day_author = {
    author: data.get("messages_per_day", {})
    for author, data in stats.items()
}


stats = {
    a: s
    for a, s in stats.items()
    if s.get("messages_total", 0) >= 200
}

stats_for_sentiment = {
    a: s
    for a, s in stats.items()
    if "#" not in a
}

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
console.rule(f"[bold green]Generating Visualizations ({timestamp})")

# =============================================================================
# Messages per author
# =============================================================================
def dynamic_figsize(items, base_width=9, row_height=0.3, min_height=4):
    return (base_width, max(min_height, row_height * len(items)))

msg_counts = {a: s["messages_total"] for a, s in stats.items()}
msg_items = [{"name": a, "value": v} for a, v in msg_counts.items()]
msg_items = sorted(msg_items, key=lambda d: -d["value"])
plot_leaderboard(
    msg_items,
    "Messages Sent",
    value_label="Messages",
    outfile=os.path.join(OUT_DIR, "messages_per_author.png"),
    figsize=dynamic_figsize(msg_items)
)

# =============================================================================
# Most reacted messages with box panels, attachments, and fixed width
# =============================================================================
import textwrap

reaction_messages_file = os.path.join(OUT_DIR, "reaction_messages.txt")

def create_box(content, width=80):
    if width < 4:
        raise ValueError("width must be at least 4")

    inner = width - 4
    border = "+" + "-" * (width - 2) + "+"

    wrapper = textwrap.TextWrapper(
        width=inner,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=True,
    )

    boxed_lines = [border]

    for original_line in content.split("\n"):
        line = original_line.expandtabs()

        wrapped = wrapper.wrap(line) or [""]
        for seg in wrapped:
            boxed_lines.append(f"| {seg.ljust(inner)} |")

    boxed_lines.append(border)
    return "\n".join(boxed_lines)

with open(reaction_messages_file, "w", encoding="utf-8") as f:
    for reaction in WHITELIST:
        f.write(f"Top 25 messages for reaction {reaction.ljust(50)}\n")

        reaction_list = reactions_data.get(reaction, [])
        reaction_list = sorted(reaction_list, key=lambda x: -x["count"])[:25]

        for idx, message in enumerate(reaction_list):
            count = message["count"]
            author = message["author"]
            content = message["content"]
            date = message["date"]
            attachments = message["attachments"]

            message_content = (
                f" #{idx + 1} {author} | {count} reactions | {date}\n{content}"
            )

            # List attachments if any
            if attachments:
                message_content += "\nAttachments:\n"
                for att in attachments:
                    message_content += f"- {att}\n"

            f.write(create_box(message_content.strip(), width=100))
            f.write("\n")

        f.write(f"\n")

# =============================================================================
# Most reacted messages with box panels, attachments, and fixed width
# =============================================================================
import textwrap

reaction_messages_file = os.path.join(OUT_DIR, "reaction_messages.txt")

def create_box(content, width=80):
    if width < 4:
        raise ValueError("width must be at least 4")

    inner = width - 4
    border = "+" + "-" * (width - 2) + "+"

    wrapper = textwrap.TextWrapper(
        width=inner,
        replace_whitespace=False,
        drop_whitespace=False,
        break_long_words=True,
        break_on_hyphens=True,
    )

    boxed_lines = [border]

    for original_line in content.split("\n"):
        line = original_line.expandtabs()

        wrapped = wrapper.wrap(line) or [""]
        for seg in wrapped:
            boxed_lines.append(f"| {seg.ljust(inner)} |")

    boxed_lines.append(border)
    return "\n".join(boxed_lines)

with open(reaction_messages_file, "w", encoding="utf-8") as f:
    for reaction in WHITELIST:
        f.write(f"Top 25 messages for reaction {reaction.ljust(50)}\n")

        reaction_list = reactions_data.get(reaction, [])
        reaction_list = sorted(reaction_list, key=lambda x: -x["count"])[:25]

        for idx, message in enumerate(reaction_list):
            count = message["count"]
            author = message["author"]
            content = message["content"]
            date = message["date"]
            attachments = message["attachments"]

            message_content = (
                f" #{idx + 1} {author} | {count} reactions | {date}\n{content}"
            )

            if attachments:
                message_content += "\nAttachments:\n"
                for att in attachments:
                    message_content += f"- {att}\n"

            f.write(create_box(message_content.strip(), width=100))
            f.write("\n")

        f.write(f"\n")

# =============================================================================
# Sentiment leaderboards
# =============================================================================
pos_pct = {}
neu_pct = {}
neg_pct = {}

for author, data in stats_for_sentiment.items():
    total = data["messages_total"] or 1
    s = data["sentiment"]
    pos_pct[author] = s["positive"] / total * 100
    neu_pct[author] = s["neutral"] / total * 100
    neg_pct[author] = s["negative"] / total * 100

def to_items(counter):
    return [{"name": a, "value": v} for a, v in counter.items()]

pos_items = sorted(to_items(pos_pct), key=lambda d: -d["value"])
neu_items = sorted(to_items(neu_pct), key=lambda d: -d["value"])
neg_items = sorted(to_items(neg_pct), key=lambda d: -d["value"])

plot_leaderboard(
    pos_items,
    "Positive Sentiment (%)",
    "Positive %",
    outfile=os.path.join(OUT_DIR, "sentiment_positive.png"),
    figsize=dynamic_figsize(pos_items),
)
plot_leaderboard(
    neu_items,
    "Neutral Sentiment (%)",
    "Neutral %",
    outfile=os.path.join(OUT_DIR, "sentiment_neutral.png"),
    figsize=dynamic_figsize(neu_items),
)
plot_leaderboard(
    neg_items,
    "Negative Sentiment (%)",
    "Negative %",
    outfile=os.path.join(OUT_DIR, "sentiment_negative.png"),
    figsize=dynamic_figsize(neg_items),
)

# =============================================================================
# Reaction leaderboards
# =============================================================================
from collections import defaultdict
import unicodedata
import re

rxn_dir = os.path.join(OUT_DIR, "reactions")
os.makedirs(rxn_dir, exist_ok=True)

def to_snake_case(name: str) -> str:
    if all(ord(ch) < 128 for ch in name):
        name = re.sub(r"[^0-9a-zA-Z]+", "_", name)
        name = re.sub(r"_+", "_", name)
        return name.strip("_").lower() or "unknown"

    names = []
    for ch in name:
        try:
            names.append(unicodedata.name(ch))
        except ValueError:
            names.append(ch)

    name = "_".join(n.lower().replace(" ", "_") for n in names)
    name = re.sub(r"_+", "_", name)
    return name.strip("_").lower() or "unknown"

reaction_totals = defaultdict(lambda: Counter())
reaction_rpm = defaultdict(lambda: Counter())
reaction_rpm_unique = defaultdict(lambda: Counter())
reaction_max = defaultdict(lambda: Counter())

with make_progress() as progress:
    task = progress.add_task("Generating reaction leaderboards...", total=len(stats))
    for author, data in stats.items():
        for rxn, rdata in data["reactions"].items():
            if rxn not in WHITELIST:
                continue
            total = rdata.get("total", 0)
            unique = rdata.get("unique_msgs", 0)
            max_one = rdata.get("max_in_single_message", 0)
            msg_total = data.get("messages_total", 1) or 1
            reaction_totals[rxn][author] += total
            reaction_max[rxn][author] = max(reaction_max[rxn][author], max_one)
            if author in stats_for_sentiment:
                reaction_rpm[rxn][author] += total / msg_total
                reaction_rpm_unique[rxn][author] += unique / msg_total
        progress.advance(task)

for rxn in sorted(reaction_totals.keys()):
    safe_name = to_snake_case(rxn)

    items_total = [{"name": a, "value": v} for a, v in reaction_totals[rxn].items()]
    items_rpm = [{"name": a, "value": v} for a, v in reaction_rpm[rxn].items()]
    items_rpm_unique = [{"name": a, "value": v} for a, v in reaction_rpm_unique[rxn].items()]
    items_max = [{"name": a, "value": v} for a, v in reaction_max[rxn].items()]

    items_total.sort(key=lambda d: -d["value"])
    items_rpm.sort(key=lambda d: -d["value"])
    items_rpm_unique.sort(key=lambda d: -d["value"])
    items_max.sort(key=lambda d: -d["value"])

    plot_leaderboard(
        items_total,
        f"{rxn} — Total Reactions",
        "Reactions",
        outfile=os.path.join(rxn_dir, f"{safe_name}_total.png"),
        figsize=(9, max(4, 0.34 * len(items_total) + 2))
    )
    plot_leaderboard(
        items_rpm,
        f"{rxn} — Reactions per message (RPM)",
        "RPM",
        outfile=os.path.join(rxn_dir, f"{safe_name}_rpm.png"),
        figsize=(9, max(4, 0.34 * len(items_rpm) + 2))
    )
    plot_leaderboard(
        items_rpm_unique,
        f"{rxn} — Reactions per unique message (RPM Unique)",
        "RPM Unique",
        outfile=os.path.join(rxn_dir, f"{safe_name}_rpm_unique.png"),
        figsize=(9, max(4, 0.34 * len(items_rpm_unique) + 2))
    )
    plot_leaderboard(
        items_max,
        f"{rxn} — Max Reactions on a single message",
        "Max Count",
        outfile=os.path.join(rxn_dir, f"{safe_name}_max.png"),
        figsize=(9, max(4, 0.34 * len(items_max) + 2))
    )

# =============================================================================
# Messages per day
# =============================================================================
dates, values = normalize_daily_counter(messages_per_day_global)

plt.figure(figsize=(15, 4), dpi=180)
plt.plot(dates, values, linewidth=2)
plt.title("Messages Sent Per Day (Global)", loc="left", fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Messages")
plt.grid(alpha=0.3, linestyle=":")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "messages_per_day.png"))
plt.close()

plt.figure(figsize=(15, 5), dpi=180)

for author, counter in messages_per_day_author.items():
    dates, values = normalize_daily_counter(counter)
    if dates:
        plt.plot(dates, values, alpha=0.25, linewidth=1)

g_dates, g_values = normalize_daily_counter(messages_per_day_global)
plt.plot(
    g_dates,
    g_values,
    linewidth=3,
    label="Global",
)

plt.title("Messages Per Day — All Users", loc="left", fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Messages")
plt.legend()
plt.grid(alpha=0.3, linestyle=":")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "messages_per_day_all.png"))
plt.close()

def plot_user_messages_per_day(username: str):
    counter = messages_per_day_author.get(username)
    if not counter:
        return

    dates, values = normalize_daily_counter(counter)
    if not dates:
        return

    plt.figure(figsize=(15, 4), dpi=180)
    plt.plot(dates, values, linewidth=2)
    plt.title(f"Messages Per Day — {username}", loc="left", fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("Messages")
    plt.grid(alpha=0.3, linestyle=":")
    plt.tight_layout()
    plt.savefig(os.path.join(MSG_DIR, f"{username}_per_day.png"))
    plt.close()

for author in messages_per_day_author:
    plot_user_messages_per_day(author)
