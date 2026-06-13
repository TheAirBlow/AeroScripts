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

from tqdm.utils import CallbackIOWrapper
from pathlib import Path
from adbutils import adb
from tqdm import tqdm
import argparse

def shorten(name):
    if len(name) < 18:
        return name
    return f"{name[:9]}^{name[-8:]}"

parser = argparse.ArgumentParser(prog="adbsync", description="Syncs directory with a remove ADB device")
parser.add_argument("source", help="Target directory on local device (required)", default=".")
parser.add_argument("target", help="Target directory on remote device (required)")
parser.add_argument("-d", "--device", help="Serial identifier of ADB device (default: first connected device)", default=None)
args = parser.parse_args()

d = adb.device(serial=args.device)
print('ADB device:', d.serial)

source = Path(args.source)
target = Path(args.target)
print('Source:', source)
print('Target:', target)

d.shell(["mkdir", "-p", args.target])
remote = d.shell(["find", args.target, "-type", "f"]).split('\n')
local = source.rglob("*")

delete = list()
for rpath in remote:
    if not rpath:
        continue
    lpath = source / Path(rpath).relative_to(target)
    if lpath.is_file():
        continue
    delete.append(rpath)

if len(delete) > 0:
    print("Deleting", len(delete), "files...")
    for arr in tqdm([delete[i:i + 250] for i in range(0, len(delete), 250)], desc="Deleting files", unit="batch", position=0, leave=False):
        d.shell(['rm'] + arr)
else:
    print("No files to delete, skipping...")

push = list()
for lpath in local:
    if not lpath:
        continue
    rpath = target / lpath.relative_to(source)
    if str(rpath) in remote:
        continue
    push.append((lpath, rpath))

if len(push) > 0:
    print("Pushing", len(push), "files...")
    progress = tqdm(unit="B", unit_scale=True, position=1, leave=False)
    for lpath, rpath in tqdm(push, desc="Transferring files", unit="file", position=0, leave=False):
        if not lpath.exists():
            continue
        with lpath.open("rb") as f:
            progress.reset(lpath.stat().st_size)
            progress.set_description(f"{shorten(lpath.name):<18}")
            wrapper = CallbackIOWrapper(progress.update, f, "read")
            d.sync.push(wrapper, str(rpath))
    progress.close()
else:
    print("No files to push, skipping...")
