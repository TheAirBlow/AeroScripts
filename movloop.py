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

from skimage.metrics import structural_similarity as ssim
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
import subprocess
import datetime
import cv2
import os

def loop(path, out):
    process = subprocess.Popen([
        'ffmpeg', '-i', path, '-f', 'image2pipe', '-pix_fmt', 'rgb24', '-vcodec', 'rawvideo', '-'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    video = cv2.VideoCapture(path)
    width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video.get(cv2.CAP_PROP_FPS))
    video.release()

    best = None
    first = None
    frames = 0

    while True:
        image = process.stdout.read(width * height * 3)
        if len(image) != (width * height * 3):
            break
        if frames % (fps / 10) != 0:
            frames += 1
            continue
        if frames > fps * 5:
            break
        frame = np.frombuffer(image, dtype=np.uint8).reshape((height, width, 3))
        if first is None:
            first = frame
        elif frames > fps / 2:
            first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            score, _ = ssim(first_gray, frame_gray, full=True)
            if not best or score > best[1]:
                best = (frames, score)
        frames += 1

    process.terminate()
    if not best:
        print(f'[{path}] no best frame somehow')
        return
    end = datetime.timedelta(seconds=best[0] / fps)
    print(f'[{path}] score {score} at {end}')
    subprocess.call([
        'ffmpeg', '-i', path, '-filter:v', 'fps=30,scale=1080:-2,setsar=1:1', '-to', str(end), '-y', out
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def check(filename):
    path = Path(filename)
    if path.suffix not in [ '.mp4', '.mkv', '.wmv', '.mov' ]:
        return
    out = f'{path.stem}.gif'
    if os.path.isfile(out):
        return
    loop(filename, out)

with ThreadPoolExecutor(max_workers = 8) as executor:
    executor.map(check, os.listdir())
    executor.shutdown(wait=True)
