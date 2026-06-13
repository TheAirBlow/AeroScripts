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

from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import imagehash
import hashlib
import signal
import sys
import os

def term(signum, frame):
    print("Exiting...")
    sys.exit(-1)
signal.signal(signal.SIGINT, term)

def hash_file(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b""):
            hasher.update(block)
    return hasher.hexdigest()

def hash_image(file_path):
    try:
        with Image.open(file_path) as img:
            return "img_" + str(imagehash.phash(img, hash_size=32))
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")
        return hash_file(file_path)

hashes = list()
deleted = 0
unique = 0

def check_file(file_path):
    global hashes, deleted, unique
    file_hash = None
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
        file_hash = hash_image(file_path)
    else:
        file_hash = hash_file(file_path)
    if file_hash in hashes:
        print("[-]", file_path)
        os.remove(file_path)
        deleted += 1
    else:
        print("[+]", file_path)
        hashes.append(file_hash)
        unique += 1

with ThreadPoolExecutor(max_workers = 8) as executor:
    print("This will recursively DELETE duplicate files.")
    choice = input("Do you want to continue? [y/N] ").strip().lower()
    if choice != 'y':
        print("Cancelled by user")
        sys.exit(-1)

    for root, dirs, files in os.walk('.'):
        for name in files:
            file_path = os.path.join(root, name)
            executor.submit(check_file, file_path)

    executor.shutdown(wait=True)

print(f"{deleted} duplicates of {unique} unique files deleted")
