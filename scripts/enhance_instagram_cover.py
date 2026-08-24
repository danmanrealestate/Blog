#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INSTAGRAM_DIR = ROOT / "instagram"
PUBLISH_STATE = INSTAGRAM_DIR / "publish_state.json"
W, H = 1080, 1350
NAVY = (6, 27, 54)
BLUE = (19, 66, 134)
RED = (190, 24, 35)
GOLD = (218, 163, 43)
WHITE = (255, 255, 255)
LIGHT = (235, 241, 249)
MUTED = (182, 195, 214)
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def width(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[2] - b[0]


def wrap(draw, text, f, max_width):
    lines, cur = [], ""
    for word in str(text).split():
        test = word if not cur else cur + " " + word
        if width(draw, test, f) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, max_width, max_lines, max_size, min_size, bold=True):
    for size in range(max_size, min_size - 1, -1):
        f = font(size, bold)
        lines = wrap(draw, text, f, max_width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(min_size, bold)
    return f, wrap(draw, text, f, max_width)[:max_lines]


def draw_lines(draw, x, y, text, max_width, max_lines, max_size, min_size, color, bold=True, gap=8):
    f, lines = fit(draw, text, max_width, max_lines, max_size, min_size, bold)
    for line in lines:
        draw.text((x, y), line, font=f, fill=color)
        y += f.size + gap
    return y


def topic_hook(topic: str):
    t = topic.lower()
    if "due diligence" in t:
        return "BEFORE YOU BUY...", "DON'T SKIP THE CHECKLIST"
    if "tenant" in t or "lease strength" in t:
        return "GOOD TENANT... OR BIG RISK?", "KNOW WHAT TO VERIFY"
    if "rent roll" in t:
        return "WHAT IS THE RENT ROLL REALLY TELLING YOU?", "READ BEYOND THE TOTAL"
    if "cap rate" in t:
        return "IS THE CAP RATE TELLING THE WHOLE STORY?", "LOOK PAST ONE NUMBER"
    if "financ" in t or "loan" in t or "debt" in t:
        return "CAN THE PROPERTY SUPPORT THE DEBT?", "RUN THE NUMBERS FIRST"
    if "expense" in t or "noi" in t:
        return "WHERE IS THE CASH FLOW REALLY GOING?", "FIND THE LEAKS"
    if "zoning" in t or "use" in t:
        return "CAN YOU ACTUALLY USE IT THAT WAY?", "CHECK BEFORE YOU COMMIT"
    return "WOULD YOU KNOW WHAT TO CHECK?", "LEARN THE INVESTOR VIEW"


def footer(draw):
    draw.rectangle((0, 1230, W, H), fill=(4, 18, 38))
    draw.text((50, 1260), "RE/MAX ACE REALTY", font=font(24, True), fill=WHITE)
    draw.text((50, 1295), "COMMERCIAL DIVISION", font=font(20), fill=WHITE)
    site = "dmsellscre.com"
    f = font(24, True)
    draw.text((W - 50 - width(draw, site, f), 1280), site, font=f, fill=WHITE)


def draw_checklist(draw, x, y, box_w=360, rows=5):
    draw.rounded_rectangle((x, y, x + box_w, y + 410), radius=28, fill=WHITE)
    draw.rounded_rectangle((x + 110, y - 22, x + 250, y + 35), radius=14, fill=GOLD)
    for i in range(rows):
        yy = y + 78 + i * 60
        draw.rounded_rectangle((x + 36, yy, x + 74, yy + 38), radius=7, outline=NAVY, width=4)
        draw.line((x + 45, yy + 20, x + 56, yy + 31), fill=RED, width=5)
        draw.line((x + 56, yy + 31, x + 69, yy + 10), fill=RED, width=5)
        draw.rounded_rectangle((x + 95, yy + 7, x + box_w - 32, yy + 18), radius=5, fill=MUTED)
        draw.rounded_rectangle((x + 95, yy + 27, x + box_w - 80, yy + 36), radius=4, fill=LIGHT)


def cover_style_a(lesson, topic, hook, subhook, out):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 185), fill=WHITE)
    d.text((58, 54), "COMMERCIAL INVESTOR", font=font(36, True), fill=NAVY)
    d.text((58, 99), "ACADEMY", font=font(36, True), fill=RED)
    d.rounded_rectangle((805, 48, 1018, 137), radius=18, fill=RED)
    d.text((846, 72), f"LESSON {lesson}", font=font(28, True), fill=WHITE)

    d.rounded_rectangle((55, 238, 615, 332), radius=20, fill=RED)
    d.text((86, 259), hook, font=font(42, True), fill=WHITE)
    y = draw_lines(d, 62, 390, topic.upper(), 660, 3, 61, 38, WHITE, True, 10)
    d.rectangle((63, y + 18, 250, y + 28), fill=GOLD)
    draw_lines(d, 63, y + 60, subhook, 650, 2, 32, 24, GOLD, True)
    draw_checklist(d, 665, 395, 350, 5)

    d.rounded_rectangle((60, 950, 1020, 1165), radius=28, fill=(12, 44, 82))
    d.text((95, 987), "THE INVESTOR QUESTION:", font=font(25, True), fill=GOLD)
    question = "What could you miss if you only looked at the asking price?"
    draw_lines(d, 95, 1032, question, 850, 3, 36, 26, WHITE, True, 7)
    footer(d)
    im.save(out, "JPEG", quality=95, optimize=True)


def cover_style_b(lesson, topic, hook, subhook, out):
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 400, 1230), fill=NAVY)
    d.rectangle((400, 0, W, 1230), fill=LIGHT)
    d.rounded_rectangle((55, 55, 330, 135), radius=18, fill=RED)
    d.text((88, 78), f"LESSON {lesson}", font=font(30, True), fill=WHITE)
    draw_lines(d, 55, 210, hook, 305, 4, 52, 33, GOLD, True, 8)
    draw_lines(d, 55, 515, subhook, 300, 3, 30, 22, WHITE, True, 7)
    d.text((455, 75), "COMMERCIAL INVESTOR ACADEMY", font=font(31, True), fill=NAVY)
    y = draw_lines(d, 455, 195, topic.upper(), 560, 4, 54, 34, NAVY, True, 10)
    d.rectangle((455, y + 20, 650, y + 30), fill=RED)
    draw_checklist(d, 525, 640, 405, 5)
    footer(d)
    im.save(out, "JPEG", quality=95, optimize=True)


def cover_style_c(lesson, topic, hook, subhook, out):
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 310), fill=BLUE)
    d.text((55, 48), "COMMERCIAL INVESTOR ACADEMY", font=font(34, True), fill=WHITE)
    d.text((55, 118), f"LESSON {lesson}", font=font(28, True), fill=GOLD)
    draw_lines(d, 55, 180, hook, 920, 2, 58, 38, WHITE, True, 8)
    y = draw_lines(d, 60, 380, topic.upper(), 940, 3, 62, 38, WHITE, True, 10)
    d.rectangle((60, y + 18, 290, y + 28), fill=RED)
    draw_lines(d, 60, y + 58, subhook, 900, 2, 34, 24, GOLD, True)
    # Visual risk meter
    base_y = 850
    d.text((62, base_y - 68), "DEAL RISK", font=font(25, True), fill=WHITE)
    colors = [(57, 147, 88), (218, 163, 43), (225, 115, 41), RED]
    for i, c in enumerate(colors):
        d.rounded_rectangle((65 + i*235, base_y, 255 + i*235, base_y + 120), radius=18, fill=c)
    d.polygon([(780, base_y-20),(820, base_y-20),(800, base_y+18)], fill=WHITE)
    d.rounded_rectangle((60, 1020, 1020, 1160), radius=24, fill=(12, 44, 82))
    d.text((92, 1053), "THE SMALL DETAILS CAN CHANGE THE DEAL.", font=font(31, True), fill=WHITE)
    footer(d)
    im.save(out, "JPEG", quality=95, optimize=True)


def main():
    if not PUBLISH_STATE.exists():
        raise SystemExit("publish_state.json not found")
    state = json.loads(PUBLISH_STATE.read_text(encoding="utf-8"))
    lesson = int(state["last_published_lesson"]) + 1
    folder = INSTAGRAM_DIR / f"lesson-{lesson:03d}"
    manifest_path = folder / "manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Next unpublished lesson {lesson} is not generated yet")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    topic = str(manifest.get("topic", f"Lesson {lesson}"))
    hook, subhook = topic_hook(topic)
    out = folder / "slide1.jpg"
    style = lesson % 3
    if style == 0:
        cover_style_a(lesson, topic, hook, subhook, out)
    elif style == 1:
        cover_style_b(lesson, topic, hook, subhook, out)
    else:
        cover_style_c(lesson, topic, hook, subhook, out)
    print(f"Enhanced cover for Lesson {lesson}: {topic}")
    print(f"Hook: {hook} / {subhook}")
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
