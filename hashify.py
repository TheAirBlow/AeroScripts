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
import hashlib
import os
import shutil

def compute_hash(file_path):
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
    except IOError as e:
        print(f"Error reading {file_path}: {e}")
        return None
    return hash_md5.hexdigest()

parser = argparse.ArgumentParser(description='Recursively renames files to their MD5 hash')
parser.add_argument('--skip-warning', action='store_true', help='Skip the initial warning prompt')
parser.add_argument('-f', '--flat', action='store_true', help='Flatten directory structure into current directory')
args = parser.parse_args()

if not args.skip_warning:
    print("This will recursively rename and move ALL files.")
    response = input("Do you want to continue? [y/N] ").strip().lower()
    if response != 'y':
        print("Cancelled by user")
        exit(1)

files = [os.path.join(dp, f) for dp, dn, filenames in os.walk(".") for f in filenames]
for path in files:
    if not os.path.exists(path):
        continue

    file_hash = compute_hash(path)
    if not file_hash:
        continue

    ext = os.path.splitext(path)[1]
    filename = f"sus_{file_hash}{ext}"

    if args.flat:
        new_path = os.path.join(os.getcwd(), filename)
    else:
        new_path = os.path.join(os.path.dirname(path), filename)

    if os.path.abspath(path) == os.path.abspath(new_path):
        print(f"skipping {path}")
        continue

    try:
        print(f"{path} -> {new_path}")
    except:
        print(f"INVALID -> {new_path}")

    try:
        shutil.move(path, new_path)
    except Exception as e:
        print(f"Error moving file: {e}")
