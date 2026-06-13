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

import os
import re
import sys
import argparse
import tempfile
import shutil
from github import Github

parser = argparse.ArgumentParser(description="Scan GitHub repos for swear words across multiple users/orgs")
parser.add_argument("-t", "--targets", nargs="+", required=True, help="GitHub usernames or org names")
parser.add_argument("-c", "--context", type=int, default=3, help="Lines of context to show")
args = parser.parse_args()

token = os.environ.get("GITHUB_TOKEN")
if not token:
    sys.exit("Error: GitHub token required via GITHUB_TOKEN env var.")

g = Github(token)

KEYWORDS = [r"f[u*]ck", r"sh[i*]t", r"bitch", r"retard"]
RE_PATTERN = re.compile(r'\b(' + '|'.join(KEYWORDS) + r')\b', re.IGNORECASE)
IGNORE_EXT = ('.png', '.jpg', '.jpeg', '.zip', '.gz', '.exe', '.dll', '.pdf', '.mp4', '.pyc')

def get_repos(target_name):
    try:
        return g.get_organization(target_name).get_repos()
    except:
        try:
            return g.get_user(target_name).get_repos()
        except Exception as e:
            print(f"[-] Skipping {target_name}: {e}")
            return []

work_dir = tempfile.mkdtemp()

try:
    for target in args.targets:
        print(f"\n{'='*60}\nTARGET: {target}\n{'='*60}")

        for repo in get_repos(target):
            if repo.fork:
                continue

            print(f" -> Scanning: {repo.full_name}")
            repo_path = os.path.join(work_dir, repo.name)

            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)

            auth_url = repo.clone_url.replace("https://", f"https://{token}@")
            if os.system(f"git clone --depth 1 --quiet {auth_url} {repo_path}") != 0:
                continue

            for root, _, files in os.walk(repo_path):
                if '.git' in root: continue

                for file in files:
                    if file.lower().endswith(IGNORE_EXT): continue

                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                    except:
                        continue

                    for idx, line in enumerate(lines):
                        if RE_PATTERN.search(line):
                            rel_path = os.path.relpath(full_path, repo_path)
                            print(f"\n[!] MATCH: {repo.name}/{rel_path} (Line {idx+1})")
                            print("-" * 50)

                            start = max(0, idx - args.context)
                            end = min(len(lines), idx + args.context + 1)
                            for j in range(start, end):
                                marker = ">>> " if j == idx else "    "
                                print(f"{marker}{j+1}: {lines[j].rstrip()}")
                            print("-" * 50)
finally:
    shutil.rmtree(work_dir)
