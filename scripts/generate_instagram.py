#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont


# ============================================================
# PATHS / SETTINGS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

TOPICS_FILE = ROOT / "instagram_topics.json"
STATE_FILE = ROOT / "instagram" / "state.json"
OUTPUT_ROOT = ROOT / "instagram"

W = 1080
H = 1350

FOOTER_TOP = 1230

NAVY = (6, 27, 54)
BLUE = (19, 66, 134)
RED = (190, 24, 35)
WHITE = (255, 255, 255)
LIGHT = (244, 247, 251)
LIGHT_BLUE = (231, 239, 250)
GRAY = (60, 67, 75)
MID_GRAY = (120, 128, 138)
BORDER = (210, 215, 220)
GREEN = (44, 135, 80)


# ============================================================
# FONTS
# ============================================================

FONT_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
)

FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
)


def get_font(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(path, size)


# ============================================================
# TEXT HELPERS
# ============================================================

def clean_text(value) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_width(draw, text, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def wrap_pixels(draw, text, font, max_width):
    """
    Wrap text based on actual rendered pixel width rather than
    approximate character counts.
    """

    text = clean_text(text)

    if not text:
        return [""]

    words = text.split()
    result = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word

        if text_width(draw, test, font) <= max_width:
            current = test
        else:
            if current:
                result.append(current)

            current = word

    if current:
        result.append(current)

    return result


def fit_text(
    draw,
    text,
    max_width,
    max_height,
    max_font,
    min_font=20,
    bold=False,
    line_gap=10,
    max_lines=None,
):
    """
    Finds the largest font size that allows the text to fit
    inside the requested box.

    Raises an error instead of allowing unreadable overlap.
    """

    text = clean_text(text)

    for size in range(max_font, min_font - 1, -2):
        font = get_font(size, bold)
        lines = wrap_pixels(draw, text, font, max_width)

        if max_lines and len(lines) > max_lines:
            continue

        line_height = size + line_gap
        total_height = len(lines) * line_height

        if total_height <= max_height:
            return font, lines, line_height

    raise RuntimeError(
        f"Text cannot fit safely in layout: {text}"
    )


def draw_text_box(
    draw,
    box,
    text,
    fill,
    max_font,
    min_font=20,
    bold=False,
    line_gap=10,
    max_lines=None,
    align="left",
):
    """
    Draw text safely inside:
    (left, top, right, bottom)
    """

    left, top, right, bottom = box

    width = right - left
    height = bottom - top

    font, lines, line_height = fit_text(
        draw=draw,
        text=text,
        max_width=width,
        max_height=height,
        max_font=max_font,
        min_font=min_font,
        bold=bold,
        line_gap=line_gap,
        max_lines=max_lines,
    )

    y = top

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]

        if align == "center":
            x = left + (width - line_width) / 2
        elif align == "right":
            x = right - line_width
        else:
            x = left

        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
        )

        y += line_height

    return y


def draw_centered_text(
    draw,
    box,
    text,
    fill,
    max_font,
    min_font=18,
    bold=False,
):
    left, top, right, bottom = box

    font, lines, line_height = fit_text(
        draw,
        text,
        right - left,
        bottom - top,
        max_font,
        min_font,
        bold,
        line_gap=6,
        max_lines=3,
    )

    total_height = len(lines) * line_height
    y = top + ((bottom - top) - total_height) / 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)

        width = bbox[2] - bbox[0]

        x = left + ((right - left) - width) / 2

        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
        )

        y += line_height


# ============================================================
# IMAGE HELPERS
# ============================================================

def canvas():
    return Image.new(
        "RGB",
        (W, H),
        WHITE,
    )


def save(img, path):
    img.save(
        path,
        "JPEG",
        quality=94,
        optimize=True,
    )


def footer(draw):
    draw.rectangle(
        (0, FOOTER_TOP, W, H),
        fill=NAVY,
    )

    draw.text(
        (48, FOOTER_TOP + 25),
        "RE/MAX ACE REALTY",
        font=get_font(24, True),
        fill=WHITE,
    )

    draw.text(
        (48, FOOTER_TOP + 61),
        "COMMERCIAL DIVISION",
        font=get_font(21),
        fill=WHITE,
    )

    website = "dmsellscre.com"

    font = get_font(24, True)

    bbox = draw.textbbox(
        (0, 0),
        website,
        font=font,
    )

    width = bbox[2] - bbox[0]

    draw.text(
        (W - 48 - width, FOOTER_TOP + 44),
        website,
        font=font,
        fill=WHITE,
    )


def header(draw, number, title):
    """
    Header is deliberately allowed to use two lines so long
    AI-generated headings never overlap the page.
    """

    draw.rounded_rectangle(
        (42, 40, 120, 118),
        radius=14,
        fill=NAVY,
    )

    draw_centered_text(
        draw,
        (42, 40, 120, 118),
        str(number),
        WHITE,
        max_font=38,
        min_font=28,
        bold=True,
    )

    draw_text_box(
        draw,
        (150, 38, 1010, 123),
        clean_text(title).upper(),
        NAVY,
        max_font=38,
        min_font=24,
        bold=True,
        line_gap=5,
        max_lines=2,
    )

    draw.rectangle(
        (150, 136, 270, 144),
        fill=RED,
    )


# ============================================================
# JSON / STATE
# ============================================================

def clean_json(text):
    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    return json.loads(text)


def state():
    if STATE_FILE.exists():
        return json.loads(
            STATE_FILE.read_text(
                encoding="utf-8"
            )
        )

    return {
        "last_index": -1,
        "last_lesson": 7,
    }


# ============================================================
# AI CONTENT
# ============================================================

def prompt(lesson, topic):
    return f"""
Create Commercial Investor Academy Lesson {lesson}
about:

{topic}

Audience:
Commercial real estate investors, landlords,
building owners, and business owners in Chester
County and Montgomery County, Pennsylvania.

Return ONLY valid JSON.

Use these exact keys:

lesson_title
subtitle
definition
included_title
included_items
expenses_title
expense_items
not_included_title
not_included_items
local_example_title
local_example_intro
local_example_rows
why_title
why_items
caption
hashtags
engagement_question

STRICT LENGTH RULES FOR INSTAGRAM GRAPHICS:

lesson_title:
Maximum 8 words.

subtitle:
Maximum 16 words.

definition:
Maximum 48 words.

included_title:
Maximum 6 words.

included_items:
Exactly 5 items.
Maximum 10 words per item.

expenses_title:
Maximum 6 words.

expense_items:
Exactly 5 items.
Maximum 10 words per item.

not_included_title:
Maximum 6 words.

not_included_items:
Exactly 4 items.
Maximum 10 words per item.

local_example_title:
Maximum 6 words.

local_example_intro:
Maximum 24 words.

local_example_rows:
Exactly 3 objects.
Each object must contain "label" and "value".
Label maximum 8 words.
Value maximum 8 words.

why_title:
Maximum 6 words.

why_items:
Exactly 4 items.
Maximum 11 words per item.

engagement_question:
Maximum 22 words.

caption:
Approximately 700-1100 characters.
Include a natural CTA to:
dmsellscre.com/investors

hashtags:
Exactly 15 hashtags.

STYLE:
Clear.
Educational.
Professional.
Easy to skim.
Avoid jargon when simpler wording works.
No long sentences on the slides.
No invented market statistics.
Keep claims evergreen.
Do not make up local property values,
vacancy rates, rents, cap rates, or loan terms.
"""


def generate(lesson, topic):
    response = OpenAI().responses.create(
        model=os.getenv(
            "OPENAI_MODEL",
            "gpt-5-mini",
        ),
        input=prompt(
            lesson,
            topic,
        ),
    )

    return clean_json(
        response.output_text
    )


# ============================================================
# SLIDE 1 — COVER
# ============================================================

def cover(lesson, data, path):
    im = canvas()
    d = ImageDraw.Draw(im)

    d.rectangle(
        (0, 0, W, H),
        fill=NAVY,
    )

    d.rectangle(
        (0, 820, W, FOOTER_TOP),
        fill=BLUE,
    )

    d.rounded_rectangle(
        (55, 55, 1025, 145),
        radius=16,
        fill=WHITE,
    )

    draw_centered_text(
        d,
        (75, 65, 1005, 135),
        "COMMERCIAL INVESTOR ACADEMY",
        NAVY,
        max_font=38,
        min_font=28,
        bold=True,
    )

    d.rounded_rectangle(
        (65, 205, 330, 295),
        radius=16,
        fill=RED,
    )

    draw_centered_text(
        d,
        (75, 215, 320, 285),
        f"LESSON {lesson}",
        WHITE,
        max_font=36,
        min_font=26,
        bold=True,
    )

    draw_text_box(
        d,
        (65, 350, 1015, 610),
        data["lesson_title"].upper(),
        WHITE,
        max_font=66,
        min_font=40,
        bold=True,
        line_gap=10,
        max_lines=3,
    )

    d.rectangle(
        (65, 635, 225, 644),
        fill=RED,
    )

    draw_text_box(
        d,
        (65, 680, 1015, 795),
        data["subtitle"],
        WHITE,
        max_font=34,
        min_font=25,
        bold=False,
        line_gap=8,
        max_lines=3,
    )

    # Clean commercial skyline graphic.
    building_data = [
        (75, 1025, 170, 1190),
        (190, 930, 295, 1190),
        (315, 1000, 415, 1190),
        (440, 870, 560, 1190),
        (585, 960, 685, 1190),
        (710, 905, 825, 1190),
        (850, 1010, 970, 1190),
    ]

    for x1, y1, x2, y2 in building_data:
        d.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=6,
            fill=(215, 224, 238),
        )

        for wx in range(
            x1 + 16,
            x2 - 10,
            31,
        ):
            for wy in range(
                y1 + 22,
                y2 - 25,
                42,
            ):
                d.rectangle(
                    (
                        wx,
                        wy,
                        wx + 12,
                        wy + 19,
                    ),
                    fill=BLUE,
                )

    footer(d)
    save(im, path)


# ============================================================
# SLIDE 2 — DEFINITION
# ============================================================

def definition(data, path):
    im = canvas()
    d = ImageDraw.Draw(im)

    header(
        d,
        2,
        "What Is It?",
    )

    d.ellipse(
        (405, 205, 675, 475),
        fill=NAVY,
    )

    draw_centered_text(
        d,
        (420, 225, 660, 455),
        "$",
        WHITE,
        max_font=120,
        min_font=90,
        bold=True,
    )

    draw_text_box(
        d,
        (85, 545, 995, 845),
        data["definition"],
        GRAY,
        max_font=35,
        min_font=27,
        line_gap=12,
        max_lines=7,
    )

    d.rounded_rectangle(
        (85, 900, 995, 1165),
        radius=24,
        fill=LIGHT_BLUE,
    )

    draw_text_box(
        d,
        (125, 940, 955, 990),
        "INVESTOR TAKEAWAY",
        NAVY,
        max_font=27,
        min_font=23,
        bold=True,
        max_lines=1,
    )

    draw_text_box(
        d,
        (125, 1010, 955, 1125),
        data["subtitle"],
        RED,
        max_font=30,
        min_font=23,
        bold=True,
        line_gap=8,
        max_lines=3,
    )

    footer(d)
    save(im, path)


# ============================================================
# SLIDES 3 / 4 / 5 — LIST SLIDES
# ============================================================

def listslide(
    number,
    title,
    items,
    path,
    positive=True,
):
    im = canvas()
    d = ImageDraw.Draw(im)

    header(
        d,
        number,
        title,
    )

    items = list(items)

    if not items:
        raise RuntimeError(
            f"Slide {number} received no list items."
        )

    content_top = 190
    content_bottom = 1185

    available = content_bottom - content_top

    gap = 18

    card_height = int(
        (
            available
            - gap * (len(items) - 1)
        )
        / len(items)
    )

    color = GREEN if positive else RED
    symbol = "✓" if positive else "×"

    y = content_top

    for item in items:
        bottom = y + card_height

        d.rounded_rectangle(
            (
                75,
                y,
                1005,
                bottom,
            ),
            radius=22,
            fill=LIGHT,
            outline=BORDER,
            width=2,
        )

        circle_size = 66

        circle_y = (
            y
            + (card_height - circle_size) / 2
        )

        d.ellipse(
            (
                105,
                circle_y,
                105 + circle_size,
                circle_y + circle_size,
            ),
            fill=color,
        )

        draw_centered_text(
            d,
            (
                105,
                circle_y,
                105 + circle_size,
                circle_y + circle_size,
            ),
            symbol,
            WHITE,
            max_font=39,
            min_font=28,
            bold=True,
        )

        draw_text_box(
            d,
            (
                205,
                y + 25,
                960,
                bottom - 20,
            ),
            item,
            GRAY,
            max_font=34,
            min_font=23,
            bold=False,
            line_gap=8,
            max_lines=3,
        )

        y = bottom + gap

    footer(d)
    save(im, path)


# ============================================================
# SLIDE 6 — EXAMPLE
# ============================================================

def example(data, path):
    im = canvas()
    d = ImageDraw.Draw(im)

    header(
        d,
        6,
        data["local_example_title"],
    )

    draw_text_box(
        d,
        (80, 185, 1000, 340),
        data["local_example_intro"],
        GRAY,
        max_font=32,
        min_font=24,
        line_gap=9,
        max_lines=4,
    )

    rows = data["local_example_rows"]

    y = 390
    row_height = 205
    gap = 24

    for i, row in enumerate(rows):
        is_total = i == len(rows) - 1

        fill = NAVY if is_total else LIGHT
        text_fill = WHITE if is_total else GRAY
        value_fill = WHITE if is_total else RED

        d.rounded_rectangle(
            (
                80,
                y,
                1000,
                y + row_height,
            ),
            radius=20,
            fill=fill,
            outline=NAVY,
            width=2,
        )

        draw_text_box(
            d,
            (
                120,
                y + 35,
                645,
                y + row_height - 30,
            ),
            row["label"],
            text_fill,
            max_font=31,
            min_font=22,
            bold=True,
            line_gap=8,
            max_lines=3,
        )

        draw_text_box(
            d,
            (
                670,
                y + 35,
                950,
                y + row_height - 30,
            ),
            row["value"],
            value_fill,
            max_font=34,
            min_font=21,
            bold=True,
            line_gap=7,
            max_lines=3,
            align="right",
        )

        y += row_height + gap

    footer(d)
    save(im, path)


# ============================================================
# SLIDE 7 — WHY IT MATTERS
# ============================================================

def why(data, path):
    im = canvas()
    d = ImageDraw.Draw(im)

    header(
        d,
        7,
        data["why_title"],
    )

    items = data["why_items"]

    y = 190
    card_height = 155
    gap = 18

    for item in items:
        d.rounded_rectangle(
            (
                75,
                y,
                1005,
                y + card_height,
            ),
            radius=20,
            fill=LIGHT,
            outline=BORDER,
            width=2,
        )

        d.ellipse(
            (
                105,
                y + 43,
                170,
                y + 108,
            ),
            fill=NAVY,
        )

        draw_centered_text(
            d,
            (
                105,
                y + 43,
                170,
                y + 108,
            ),
            "✓",
            WHITE,
            max_font=36,
            min_font=27,
            bold=True,
        )

        draw_text_box(
            d,
            (
                205,
                y + 25,
                960,
                y + card_height - 20,
            ),
            item,
            GRAY,
            max_font=31,
            min_font=22,
            line_gap=8,
            max_lines=3,
        )

        y += card_height + gap

    d.rounded_rectangle(
        (
            75,
            900,
            1005,
            1175,
        ),
        radius=24,
        fill=LIGHT_BLUE,
    )

    draw_text_box(
        d,
        (
            115,
            935,
            965,
            980,
        ),
        "LOCAL INVESTOR QUESTION",
        NAVY,
        max_font=25,
        min_font=21,
        bold=True,
        max_lines=1,
    )

    draw_text_box(
        d,
        (
            115,
            1005,
            965,
            1135,
        ),
        data["engagement_question"],
        GRAY,
        max_font=29,
        min_font=22,
        line_gap=8,
        max_lines=4,
    )

    footer(d)
    save(im, path)


# ============================================================
# MANIFEST
# ============================================================

def write_lesson_files(
    lesson,
    topic,
    data,
    folder,
    update_latest,
):
    repo = os.getenv(
        "GITHUB_REPOSITORY",
        "danmanrealestate/Blog",
    )

    owner, name = repo.split("/", 1)

    base = (
        f"https://{owner}.github.io/{name}"
    )

    urls = [
        (
            f"{base}/instagram/"
            f"lesson-{lesson:03d}/"
            f"slide{i}.jpg"
        )
        for i in range(1, 8)
    ]

    caption = (
        data["caption"].rstrip()
        + "\n\n"
        + " ".join(data["hashtags"])
    )

    manifest = {
        "lesson": lesson,
        "topic": topic,
        "created_at": (
            datetime.now(timezone.utc)
            .isoformat()
        ),
        "caption": caption,
        "engagement_question": (
            data["engagement_question"]
        ),
        "files": [
            {
                "photo": url
            }
            for url in urls
        ],
    }

    (
        folder / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    (
        folder / "caption.txt"
    ).write_text(
        caption,
        encoding="utf-8",
    )

    if update_latest:
        (
            OUTPUT_ROOT / "latest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
            ),
            encoding="utf-8",
        )

    return manifest


# ============================================================
# CREATE SLIDES
# ============================================================

def create_slides(
    lesson,
    topic,
    data,
    folder,
):
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    cover(
        lesson,
        data,
        folder / "slide1.jpg",
    )

    definition(
        data,
        folder / "slide2.jpg",
    )

    listslide(
        3,
        data["included_title"],
        data["included_items"],
        folder / "slide3.jpg",
        True,
    )

    listslide(
        4,
        data["expenses_title"],
        data["expense_items"],
        folder / "slide4.jpg",
        True,
    )

    listslide(
        5,
        data["not_included_title"],
        data["not_included_items"],
        folder / "slide5.jpg",
        False,
    )

    example(
        data,
        folder / "slide6.jpg",
    )

    why(
        data,
        folder / "slide7.jpg",
    )


# ============================================================
# REPAIR AN EXISTING LESSON
# ============================================================

def repair_lesson(lesson_number):
    """
    Rebuild an existing lesson without advancing state.json
    and without replacing latest.json.

    Example:
    REGENERATE_LESSON=8
    """

    folder = (
        OUTPUT_ROOT
        / f"lesson-{lesson_number:03d}"
    )

    manifest_file = (
        folder / "manifest.json"
    )

    if not manifest_file.exists():
        raise RuntimeError(
            f"Cannot repair Lesson "
            f"{lesson_number}. "
            f"Manifest not found: "
            f"{manifest_file}"
        )

    old_manifest = json.loads(
        manifest_file.read_text(
            encoding="utf-8"
        )
    )

    topic = old_manifest["topic"]

    print(
        f"REPAIR MODE: rebuilding "
        f"Lesson {lesson_number}"
    )

    print(
        f"Topic: {topic}"
    )

    data = generate(
        lesson_number,
        topic,
    )

    create_slides(
        lesson_number,
        topic,
        data,
        folder,
    )

    manifest = write_lesson_files(
        lesson_number,
        topic,
        data,
        folder,
        update_latest=False,
    )

    print("")
    print(
        f"Lesson {lesson_number} "
        f"successfully rebuilt."
    )
    print(
        "Normal generation state "
        "was NOT changed."
    )
    print(
        "latest.json was NOT changed."
    )
    print("")

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


# ============================================================
# NORMAL GENERATION
# ============================================================

def generate_next_lesson():
    topics = json.loads(
        TOPICS_FILE.read_text(
            encoding="utf-8"
        )
    )

    st = state()

    idx = (
        st["last_index"] + 1
    ) % len(topics)

    lesson = (
        st["last_lesson"] + 1
    )

    topic = topics[idx]

    print(
        f"Generating new "
        f"Lesson {lesson}: {topic}"
    )

    data = generate(
        lesson,
        topic,
    )

    folder = (
        OUTPUT_ROOT
        / f"lesson-{lesson:03d}"
    )

    create_slides(
        lesson,
        topic,
        data,
        folder,
    )

    manifest = write_lesson_files(
        lesson,
        topic,
        data,
        folder,
        update_latest=True,
    )

    STATE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    STATE_FILE.write_text(
        json.dumps(
            {
                "last_index": idx,
                "last_lesson": lesson,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


# ============================================================
# MAIN
# ============================================================

def main():
    repair = os.getenv(
        "REGENERATE_LESSON"
    )

    if repair:
        repair_lesson(
            int(repair)
        )
    else:
        generate_next_lesson()


if __name__ == "__main__":
    main()
