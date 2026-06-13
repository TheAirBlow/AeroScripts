#!/usr/bin/env bash
""":"
if [ -L "$0" ]; then
    real_path=$(readlink -f "$0")
else
    real_path="$0"
fi

script_dir=$(dirname "$real_path")
venv_python="$script_dir/venv/bin/python"

if [ -x "$venv_python" ]; then
    exec "$venv_python" "$real_path" "$@"
else
    echo "[!] WARNING: venv does not exist, falling back to system Python installation." >&2
    echo "[!] Please run setup.sh in the Scripts directory to properly set everything up." >&2
    exec /usr/bin/env python3 "$real_path" "$@"
fi
"""

import argparse
import traceback
from pathlib import Path

parser = argparse.ArgumentParser(description="Convert files into a single LLM-friendly prompt")
parser.add_argument("paths", nargs="+", help="List of files and directories")
parser.add_argument("-e", "--exclude", nargs="+", help="Folder names to exclude", default=[])

args = parser.parse_args()

ignore_list = {'.git', '__pycache__', '.DS_Store', 'venv', '.venv', '.env', '.idea', 'LICENCE'}
if args.exclude:
    ignore_list.update(args.exclude)

for path_str in args.paths:
    root_path = Path(path_str)

    if not root_path.exists():
        print(f"[!] {path_str} does not exist")
        exit(1)

    files_to_process = root_path.rglob('*') if root_path.is_dir() else [root_path]

    for p in files_to_process:
        if p.is_dir() or any(part in ignore_list for part in p.parts):
            continue

        try:
            content = p.read_text(encoding='utf-8', errors='replace')

            safe_content = content.replace("```", "``\\`")

            print(f"`{p}`:")
            print("```")
            print(safe_content)
            print("```\n")
        except Exception as e:
            traceback.print_exc()
            exit(1)
