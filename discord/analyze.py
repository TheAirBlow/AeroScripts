#!/usr/bin/env python3
import os, re, csv, glob, json, torch
from transformers.pipelines.pt_utils import KeyDataset
from collections import defaultdict, Counter
from transformers import pipeline
from rich.console import Console
from functools import lru_cache
from datasets import Dataset
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    TaskProgressColumn, MofNCompleteColumn,
    TimeRemainingColumn, TimeElapsedColumn
)

console = Console()
OUTFILE = "stats.json"

# ----------------------------
# Helper functions
# ----------------------------
REACTION_RE = re.compile(r"\s*(.+?)\s*\((\d+)\)\s*$")

@lru_cache(maxsize=10000)
def parse_reactions(raw: str):
    raw = raw.strip()
    if not raw:
        return []
    out = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        m = REACTION_RE.match(part)
        if m:
            out.append((m.group(1).strip(), int(m.group(2))))
        else:
            out.append((part.strip(), 1))
    return out

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

# ----------------------------
# Data containers
# ----------------------------
msgs_by_author = defaultdict(list)

rxn_counts = defaultdict(lambda: Counter())
rxn_presence = defaultdict(lambda: Counter())
rxn_max_per_msg = defaultdict(lambda: Counter())
rxn_top_msgs = defaultdict(list)

messages_per_day_global = Counter()
messages_per_day_author = defaultdict(Counter)

# ----------------------------
# Load and process CSVs
# ----------------------------
csv_files = glob.glob("*.csv")
if not csv_files:
    console.print("[red]❌ No CSV files found.")
    raise SystemExit()

with make_progress() as progress:
    task = progress.add_task("Reading CSV files...", total=len(csv_files))

    for path in csv_files:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for r in reader:
                author = (r.get("Author") or r.get("AuthorID") or "Unknown").strip()
                text = (r.get("Content") or "").strip()

                date_raw = (r.get("Date") or "").strip()
                date_key = ""
                if date_raw:
                    m = re.match(r"^(\d{4}-\d{2}-\d{2})", date_raw)
                    if m:
                        date_key = m.group(1)

                if text:
                    msgs_by_author[author].append(text)

                    if date_key:
                        messages_per_day_global[date_key] += 1
                        messages_per_day_author[author][date_key] += 1

                reactions = parse_reactions(r.get("Reactions") or "")
                if reactions:
                    labels_present = {lbl for lbl, _ in reactions}
                    for lbl in labels_present:
                        rxn_presence[lbl][author] += 1

                    for lbl, cnt in reactions:
                        rxn_counts[lbl][author] += cnt
                        rxn_max_per_msg[lbl][author] = max(
                            rxn_max_per_msg[lbl][author], cnt
                        )
                        rxn_top_msgs[lbl].append({
                            "author": author,
                            "count": cnt,
                            "date": date_raw,
                            "content": text,
                            "attachments": (
                                r.get("Attachments") or ""
                            ).split(",") if r.get("Attachments") else []
                        })

        progress.advance(task)

console.print(
    f"[green]Loaded {sum(len(v) for v in msgs_by_author.values()):,} messages "
    f"from {len(csv_files)} CSVs with {len(msgs_by_author):,} unique authors"
)

# ----------------------------
# Sentiment analysis
# ----------------------------
device = 0 if torch.cuda.is_available() else (
    "mps" if torch.backends.mps.is_available() else -1
)

sentiment_pipe = pipeline(
    "text-classification",
    model="tabularisai/multilingual-sentiment-analysis",
    device=device,
    truncation=True,
    padding=True,
    max_length=512
)

if device == 0:
    sentiment_pipe.model = sentiment_pipe.model.half()

console.print("[green]Sentiment model loaded successfully")

records = [
    {"author": a, "text": t}
    for a, texts in msgs_by_author.items()
    for t in texts
    if isinstance(t, str) and t.strip()
]

if not records:
    console.print("[red]No messages found for sentiment analysis.")
    raise SystemExit()

ds = Dataset.from_list(records)
sentiment_counter = defaultdict(lambda: Counter())
batch_size = 64 if device != -1 else 8

with make_progress() as progress:
    task = progress.add_task("Analyzing sentiment...", total=len(ds))

    for output, sample in zip(
        sentiment_pipe(
            KeyDataset(ds, "text"),
            batch_size=batch_size,
            truncation=True,
            padding=True
        ),
        ds
    ):
        sentiment_counter[sample["author"]][output["label"]] += 1
        progress.advance(task)

# ----------------------------
# Compile stats
# ----------------------------
stats = {}

for author, counts in sentiment_counter.items():
    total = sum(counts.values())
    pos = counts.get("Positive", 0) + counts.get("Very Positive", 0)
    neg = counts.get("Negative", 0) + counts.get("Very Negative", 0)
    neu = counts.get("Neutral", 0)

    stats[author] = {
        "messages_total": total,
        "sentiment": {
            "positive": pos,
            "neutral": neu,
            "negative": neg
        },
        "reactions": {},
        "messages_per_day": dict(messages_per_day_author.get(author, {}))
    }

for rxn, counts in rxn_counts.items():
    for author, total in counts.items():
        if author not in stats:
            continue

        unique_msgs = rxn_presence[rxn][author]
        stats[author]["reactions"][rxn] = {
            "total": total,
            "unique_msgs": unique_msgs
        }

for rxn, authors in rxn_max_per_msg.items():
    for author, max_cnt in authors.items():
        if author not in stats:
            continue

        stats[author]["reactions"].setdefault(rxn, {})
        stats[author]["reactions"][rxn]["max_in_single_message"] = max_cnt

reactions = {}
for rxn, messages in rxn_top_msgs.items():
    top_msgs = sorted(messages, key=lambda m: m["count"], reverse=True)[:50]
    reactions[rxn] = [
        {
            "count": m["count"],
            "date": m["date"],
            "author": m["author"],
            "content": m["content"],
            "attachments": m["attachments"]
        }
        for m in top_msgs
    ]

# ----------------------------
# Save JSON
# ----------------------------
output = {
    "messages_per_day": dict(messages_per_day_global),
    "reactions": reactions,
    "stats": stats
}

with open(OUTFILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

console.print(f"[cyan]Saved results to:[/cyan] [bold]{OUTFILE}[/bold]")
