#!/usr/bin/env python3
import json
import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = "dms_leaderboard"
CHUNK_SIZE = 25
ROW_HEIGHT = 45
HEADER_HEIGHT = 70
PADDING = 40
COLUMN_SPACING = 40

BG_COLOR = (49, 51, 56)
HEADER_BG = (30, 31, 34)
TEXT_COLOR = (219, 222, 225)
ACCENT_COLOR = (88, 101, 242)
ALT_ROW_COLOR = (43, 45, 49)

COL_TEXT_COLORS = {
    "#": ACCENT_COLOR,
    "Username": (255, 255, 255),     # White
    "Display Name": (180, 180, 180), # Light Grey
    "Me": (255, 165, 0),             # Orange
    "Them": (0, 255, 255),           # Cyan
    "Total": (255, 215, 0)           # Gold
}

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

if not os.path.exists("dms_leaderboard.json"):
    print(f"Error: dms_leaderboard.json not found.")
    exit()

with open("dms_leaderboard.json", "r", encoding="utf-8") as f:
    data = json.load(f)

font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 20)
header_font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 22)

cols_keys = ["#", "Username", "Display Name", "Me", "Them", "Total"]
col_widths = {k: header_font.getlength(k) for k in cols_keys}

for i, entry in enumerate(data):
    rank = str(i + 1)
    username = str(entry.get('username', 'N/A'))
    display_name = str(entry.get('display_name', 'N/A'))
    me = f"{entry.get('me', 0):,}"
    them = f"{entry.get('them', 0):,}"
    total = f"{entry.get('total', 0):,}"

    col_widths["#"] = max(col_widths["#"], font.getlength(rank))
    col_widths["Username"] = max(col_widths["Username"], font.getlength(username))
    col_widths["Display Name"] = max(col_widths["Display Name"], font.getlength(display_name))
    col_widths["Me"] = max(col_widths["Me"], font.getlength(me))
    col_widths["Them"] = max(col_widths["Them"], font.getlength(them))
    col_widths["Total"] = max(col_widths["Total"], font.getlength(total))

for k in col_widths:
    col_widths[k] += COLUMN_SPACING

IMG_WIDTH = int(sum(col_widths.values()) + (PADDING * 2))

for i in range(0, len(data), CHUNK_SIZE):
    chunk = data[i:i + CHUNK_SIZE]
    part_num = (i // CHUNK_SIZE) + 1

    img_height = HEADER_HEIGHT + (len(chunk) * ROW_HEIGHT)
    img = Image.new('RGB', (IMG_WIDTH, img_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, IMG_WIDTH, HEADER_HEIGHT], fill=HEADER_BG)
    curr_x = PADDING
    for title in cols_keys:
        draw.text((curr_x, 20), title, font=header_font, fill=ACCENT_COLOR)
        curr_x += col_widths[title]

    for row_idx, entry in enumerate(chunk):
        rank = i + row_idx + 1
        y_pos = HEADER_HEIGHT + (row_idx * ROW_HEIGHT)

        if row_idx % 2 == 0:
            draw.rectangle([0, y_pos, IMG_WIDTH, y_pos + ROW_HEIGHT], fill=ALT_ROW_COLOR)

        row_data = [
            ("#", str(rank)),
            ("Username", str(entry.get('username', 'N/A'))),
            ("Display Name", str(entry.get('display_name', 'N/A'))),
            ("Me", f"{entry.get('me', 0):,}"),
            ("Them", f"{entry.get('them', 0):,}"),
            ("Total", f"{entry.get('total', 0):,}")
        ]

        curr_x = PADDING
        for col_name, val in row_data:
            text_color = COL_TEXT_COLORS.get(col_name, TEXT_COLOR)
            draw.text((curr_x, y_pos + 10), val, font=font, fill=text_color)
            curr_x += col_widths[col_name]

    save_path = os.path.join(OUTPUT_DIR, f"dms_leaderboard_{part_num}.png")
    img.save(save_path)
    print(f"Exported: {save_path}")

print(f"\nDone! All images are in the '{OUTPUT_DIR}' folder.")
