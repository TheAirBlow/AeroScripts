#!/usr/bin/env python3
import json
import os
import math
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = "dms_leaderboard"
CHUNK_SIZE = 25
ROW_HEIGHT = 45
HEADER_HEIGHT = 70
FOOTER_HEIGHT = 55
PADDING = 40
COLUMN_SPACING = 40
WILSON_Z = 12

BG_COLOR = (49, 51, 56)
HEADER_BG = (30, 31, 34)
FOOTER_BG = (20, 21, 24)
TEXT_COLOR = (219, 222, 225)
ACCENT_COLOR = (88, 101, 242)
ALT_ROW_COLOR = (43, 45, 49)
FOOTER_TEXT_COLOR = (219, 222, 225)
FOOTER_PAGE_COLOR = (140, 143, 150)

COL_TEXT_COLORS = {
    "#": ACCENT_COLOR,
    "Username": (255, 255, 255),     # White
    "Display Name": (180, 180, 180), # Light Grey
    "Me": (255, 165, 0),             # Orange
    "Them": (0, 255, 255),           # Cyan
    "Diff": (255, 105, 180),         # Pink
    "Total": (255, 215, 0),          # Gold
    "Score": (144, 238, 144)         # Light Green
}

MODE_DESCRIPTIONS = {
    "me_count": "DM Leaderboards (sorted by messages sent by me)",
    "they_count": "DM Leaderboards (sorted by messages sent by them)",
    "total_count": "DM Leaderboards (sorted by messages sent in total)",
    "msg_diff": "DM Leaderboards (sorted by 'yappiness score' with higher sample count being more trusted)"
}

if not os.path.exists("dms_leaderboard.json"):
    print(f"Error: dms_leaderboard.json not found.")
    exit()

with open("dms_leaderboard.json", "r", encoding="utf-8") as f:
    base_data = json.load(f)

def wilson_lower_bound(successes, total, z=WILSON_Z):
    if total <= 0:
        return 0.0
    phat = successes / total
    denom = 1 + z * z / total
    center = phat + z * z / (2 * total)
    adj = z * math.sqrt((phat * (1 - phat) + z * z / (4 * total)) / total)
    return (center - adj) / denom

def yappiness_score(entry):
    return wilson_lower_bound(entry.get("them", 0), entry.get("total", 0))

def yappiness_score_int(entry):
    return round(yappiness_score(entry) * 1000)

sorting_modes = {
    "me_count": sorted(base_data, key=lambda x: x.get('me', 0), reverse=True),
    "they_count": sorted(base_data, key=lambda x: x.get('them', 0), reverse=True),
    "total_count": sorted(base_data, key=lambda x: x.get('total', 0), reverse=True),
    "msg_diff": sorted(base_data, key=yappiness_score, reverse=True)
}

font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 20)
header_font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 22)
footer_font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 20)

cols_keys = ["#", "Username", "Display Name", "Me", "Them", "Diff", "Total", "Score"]

col_widths = {k: header_font.getlength(k) for k in cols_keys}

for mode, dataset in sorting_modes.items():
    for i, entry in enumerate(dataset):
        me_val = entry.get('me', 0)
        them_val = entry.get('them', 0)
        diff_val = me_val - them_val
        ratio = me_val / them_val if them_val > 0 else (0.0 if me_val == 0 else float('inf'))
        ratio_str = f"{ratio:.2f}x" if ratio != float('inf') else "∞x"
        diff_str = f"{diff_val:+,} ({ratio_str})"
        score_str = str(yappiness_score_int(entry))

        rank = str(i + 1)
        username = str(entry.get('username', 'N/A'))
        display_name = str(entry.get('display_name', 'N/A'))
        me = f"{me_val:,}"
        them = f"{them_val:,}"
        total = f"{entry.get('total', 0):,}"

        col_widths["#"] = max(col_widths["#"], font.getlength(rank))
        col_widths["Username"] = max(col_widths["Username"], font.getlength(username))
        col_widths["Display Name"] = max(col_widths["Display Name"], font.getlength(display_name))
        col_widths["Me"] = max(col_widths["Me"], font.getlength(me))
        col_widths["Them"] = max(col_widths["Them"], font.getlength(them))
        col_widths["Diff"] = max(col_widths["Diff"], font.getlength(diff_str))
        col_widths["Total"] = max(col_widths["Total"], font.getlength(total))
        col_widths["Score"] = max(col_widths["Score"], font.getlength(score_str))

padded_widths = {k: v + COLUMN_SPACING for k, v in col_widths.items()}
table_width = int(sum(padded_widths.values()) + (PADDING))

max_footer_width = 0
for mode in sorting_modes:
    desc_w = footer_font.getlength(MODE_DESCRIPTIONS[mode])
    page_w = footer_font.getlength(f"Page {math.ceil(len(sorting_modes[mode]) / CHUNK_SIZE)}/{math.ceil(len(sorting_modes[mode]) / CHUNK_SIZE)}")
    max_footer_width = max(max_footer_width, int(desc_w + page_w + COLUMN_SPACING + (PADDING * 2)))

IMG_WIDTH = max(table_width, max_footer_width)

for mode, dataset in sorting_modes.items():
    target_dir = os.path.join(OUTPUT_DIR, mode)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    print(f"\nGenerating leaderboard for folder: '{target_dir}'...")

    total_parts = math.ceil(len(dataset) / CHUNK_SIZE)

    for i in range(0, len(dataset), CHUNK_SIZE):
        chunk = dataset[i:i + CHUNK_SIZE]
        part_num = (i // CHUNK_SIZE) + 1

        img_height = HEADER_HEIGHT + (len(chunk) * ROW_HEIGHT) + FOOTER_HEIGHT
        img = Image.new('RGB', (IMG_WIDTH, img_height), color=BG_COLOR)
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, IMG_WIDTH, HEADER_HEIGHT], fill=HEADER_BG)
        curr_x = PADDING
        for title in cols_keys:
            draw.text((curr_x, 20), title, font=header_font, fill=ACCENT_COLOR)
            curr_x += padded_widths[title]

        for row_idx, entry in enumerate(chunk):
            rank = i + row_idx + 1
            y_pos = HEADER_HEIGHT + (row_idx * ROW_HEIGHT)

            if row_idx % 2 == 0:
                draw.rectangle([0, y_pos, IMG_WIDTH, y_pos + ROW_HEIGHT], fill=ALT_ROW_COLOR)

            me_val = entry.get('me', 0)
            them_val = entry.get('them', 0)
            diff_val = me_val - them_val
            ratio = me_val / them_val if them_val > 0 else (0.0 if me_val == 0 else float('inf'))
            ratio_str = f"{ratio:.2f}x" if ratio != float('inf') else "∞x"

            row_data = [
                ("#", str(rank)),
                ("Username", str(entry.get('username', 'N/A'))),
                ("Display Name", str(entry.get('display_name', 'N/A'))),
                ("Me", f"{me_val:,}"),
                ("Them", f"{them_val:,}"),
                ("Diff", f"{diff_val:+,} ({ratio_str})"),
                ("Total", f"{entry.get('total', 0):,}"),
                ("Score", str(yappiness_score_int(entry)))
            ]

            curr_x = PADDING
            for col_name, val in row_data:
                text_color = COL_TEXT_COLORS.get(col_name, TEXT_COLOR)
                draw.text((curr_x, y_pos + 10), val, font=font, fill=text_color)
                curr_x += padded_widths[col_name]

        footer_y = HEADER_HEIGHT + (len(chunk) * ROW_HEIGHT)
        draw.rectangle([0, footer_y, IMG_WIDTH, footer_y + FOOTER_HEIGHT], fill=FOOTER_BG)
        footer_text_y = footer_y + (FOOTER_HEIGHT - 16) // 2 - 10

        draw.text((PADDING, footer_text_y), MODE_DESCRIPTIONS[mode], font=footer_font, fill=FOOTER_TEXT_COLOR)

        page_text = f"Page {part_num}/{total_parts}"
        page_text_w = footer_font.getlength(page_text)
        draw.text((IMG_WIDTH - PADDING - page_text_w, footer_text_y), page_text, font=footer_font, fill=FOOTER_PAGE_COLOR)

        save_path = os.path.join(target_dir, f"leaderboard_{part_num}.png")
        img.save(save_path)
        print(f"  -> Exported: {save_path}")

print(f"\nDone! All sorted outputs are ready inside the '{OUTPUT_DIR}' directory.")
