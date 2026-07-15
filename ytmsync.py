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

from yt_dlp.utils import DownloadError
from mutagen.id3 import ID3, TIT2, TPE1, APIC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3
from pathlib import Path
from PIL import Image
import argparse
import yt_dlp
import os
import io

parser = argparse.ArgumentParser(prog="ytmsync", description="Downloads youtube music playlist and appends metadata")
parser.add_argument("url", help="Playlist URL (default: liked music)", default="https://music.youtube.com/playlist?list=LL")
parser.add_argument("-o", "--output", help="Output folder (default: working directory)", default=".")
parser.add_argument("-x", "--proxy", help="Proxy to use when downloading", default=None)
parser.add_argument("--cookies-from-browser", help="Use cookies from browser", default=None)
parser.add_argument("-m", "--metadata", help="Add id3v2 metadata when possible", action='store_true')
parser.add_argument("-p", "--playlist", help="Generate m3u8 playlist for VLC", action='store_true')
parser.add_argument("-v", "--video", help="Download video instead of audio", action='store_true')
args = parser.parse_args()

def add_metadata(video_path, thumb_path, title, author):
    # uncomment if you want to add extra blank space instead
    # with Image.open(thumb_path) as img:
    #     max_dim = max(img.size)
    #     new_img = Image.new("RGB", (max_dim, max_dim), (0, 0, 0))
    #     y_offset = (max_dim - img.height) // 2
    #     new_img.paste(img, (0, y_offset))
    #     img_byte_arr = io.BytesIO()
    #     new_img.save(img_byte_arr, format='JPEG')
    #     img_byte_arr = img_byte_arr.getvalue()

    with Image.open(thumb_path) as img:
        width, height = img.size
        min_dimension = min(width, height)
        left = (width - min_dimension) / 2
        top = (height - min_dimension) / 2
        right = (width + min_dimension) / 2
        bottom = (height + min_dimension) / 2
        cropped_img = img.crop((left, top, right, bottom))
        img_byte_arr = io.BytesIO()
        cropped_img.convert('RGB').save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()

    if video_path.suffix == ".mp3":
        audio = MP3(video_path, ID3=ID3)
        audio['TIT2'] = TIT2(encoding=3, text=title)
        audio['TPE1'] = TPE1(encoding=3, text=author)
        audio['APIC'] = APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc=u'Cover',
            data=img_byte_arr
        )

        audio.save()
    elif video_path.suffix == ".mp4":
        video = MP4(video_path)
        video['\xa9nam'] = title
        video['\xa9ART'] = author
        video['covr'] = [MP4Cover(img_byte_arr, imageformat=MP4Cover.FORMAT_JPEG)]
        video.save()

os.makedirs(args.output, exist_ok=True)

ydl_opts = {
    'js_runtimes': {
        'deno': {},
    },
    'remote_components': {'ejs:github'},
    'extractor_args': {
        'youtube': {
            'player_client': ['web'],
            'po_token': ['web_music.gvs+MlvqPCdueogkg-oEPzMcTo_ovVZIxzZMATj3lLfYg8U8sUcbJwXLI6ZW8O4jhAn14QAmJBYtKfXe1QRg9vXuTheHwP1ckwvEQ8h0-Vj1e4M7HPTqkux0VehBly_Q'],
            'lang': ['en']
        }
    },
    'writethumbnail': args.metadata,
    'extract_flat': True,
    'quiet': True
}

if args.proxy:
    ydl_opts.update({
        'proxy': args.proxy
    })

if args.cookies_from_browser:
    ydl_opts.update({
        'cookiesfrombrowser': args.cookies_from_browser.split(',')
    })

if args.video:
    ydl_opts.update({
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': {
            'default': f'{args.output}/%(id)s.%(ext)s',
            'thumbnail': f'{args.output}/%(id)s.%(ext)s'
        },
        'postprocessors': [{
            'key': 'FFmpegThumbnailsConvertor',
            'format': 'png',
        }],
        'merge_output_format': 'mp4'
    })
else:
    ydl_opts.update({
        'format': 'bestaudio/best',
        'outtmpl': {
            'default': f'{args.output}/%(id)s.%(ext)s',
            'thumbnail': f'{args.output}/%(id)s.%(ext)s'
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': "mp3"
        }, {
            'key': 'FFmpegThumbnailsConvertor',
            'format': 'png',
        }]
    })

RED = "\033[91m"
RESET = "\033[0m"

ext = "mp4" if args.video else "mp3"
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    print(f"[ytmsync] Fetching playlist contents")
    info = ydl.extract_info(args.url, download=False)
    title = info.get('title', 'Unknown Title')
    entries = info['entries']
    print(f"[ytmsync] Found {len(entries)} songs in {title}")

    playlist = None
    if args.playlist:
        playlist = open(f'{args.output}/{title}.m3u8', 'w')
        playlist.write("#EXTM3U\n")

    done = 1
    for entry in entries:
        video_id = entry['id']
        video_url = entry['url']
        video_title = entry.get('title', 'Unknown Title')
        video_author = entry.get('uploader', 'Unknown Author')
        if "Private video" in video_title:
            print(f"[ytmsync] Skipping {video_id} as it has been privated ({done}/{len(entries)})")
            done += 1
            continue

        video_path = Path(args.output) / f'{video_id}.{ext}'
        if args.metadata:
            playlist.write(f"{video_path.name}\n")

        if video_path.exists():
            print(f"[ytmsync] Skipping {video_id} ({video_author} - {video_title}, {done}/{len(entries)})")
            done += 1
            continue

        print(f"[ytmsync] Downloading {video_id} ({video_author} - {video_title}, {done}/{len(entries)})")
        try:
            ydl.download([video_url])
        except DownloadError as e:
            print(f"{RED}[ytmsync] Failed to download {video_id}{RESET}")
            done += 1
            continue

        if not video_path.exists():
            print("[ytmsync] Failed to download the video, exiting...")
            if args.playlist:
                playlist.close()
            exit(-1)

        if args.metadata:
            thumb_path = Path(args.output) / f'{video_id}.png'
            if not thumb_path.exists():
                print("[ytmsync] Failed to download the thumbnail, exiting...")
                if args.playlist:
                    playlist.close()
                exit(-1)

            add_metadata(video_path, thumb_path, video_title, video_author)
            thumb_path.unlink()

        done += 1

    if args.playlist:
        playlist.close()

print("[ytmsync] Download completed")
