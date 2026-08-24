#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTAGRAM_DIR = ROOT / "instagram"
PUBLISH_STATE_FILE = INSTAGRAM_DIR / "publish_state.json"


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_image_url(item):
    if isinstance(item, dict):
        return item.get("photo")
    if isinstance(item, str):
        return item
    return None


def image_is_ready(url: str) -> tuple[bool, str]:
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 GitHub-Actions-Instagram-Publisher",
                "Cache-Control": "no-cache",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            status = getattr(response, "status", 200)
            sample = response.read(32)
            if status == 200 and content_type.lower().startswith("image/") and sample:
                return True, f"HTTP {status}, {content_type}"
            return False, f"HTTP {status}, {content_type or 'unknown content type'}"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def wait_for_images(urls, attempts=36, delay=10):
    # Up to six minutes. GitHub Pages deployment time can vary, so a fixed
    # sleep is unreliable. We only publish once every slide is publicly served.
    for attempt in range(1, attempts + 1):
        not_ready = []
        for url in urls:
            ok, detail = image_is_ready(url)
            if not ok:
                not_ready.append((url, detail))

        if not not_ready:
            print(f"All {len(urls)} slide images are publicly available.")
            return

        print(
            f"Image readiness check {attempt}/{attempts}: "
            f"{len(not_ready)} of {len(urls)} not ready yet."
        )
        for url, detail in not_ready[:3]:
            print(f"  {detail}: {url}")

        if attempt < attempts:
            time.sleep(delay)

    raise RuntimeError(
        "GitHub Pages did not make all Instagram slide images available within six minutes. "
        "Publishing was safely stopped before contacting Instagram."
    )


def main():
    state = load_json(PUBLISH_STATE_FILE)
    next_lesson = int(state["last_published_lesson"]) + 1
    manifest_file = INSTAGRAM_DIR / f"lesson-{next_lesson:03d}" / "manifest.json"

    if not manifest_file.exists():
        raise RuntimeError(
            f"Lesson {next_lesson} is not generated. Missing: {manifest_file}"
        )

    lesson = load_json(manifest_file)
    files = lesson.get("files") or []
    urls = [get_image_url(item) for item in files]

    if not urls or any(not url for url in urls):
        raise RuntimeError(f"Lesson {next_lesson} manifest contains invalid slide URLs")

    print(f"Preparing to publish Lesson {next_lesson}: {lesson.get('topic', '')}")
    print("Waiting for GitHub Pages to serve every slide image...")
    wait_for_images(urls)

    # Once images are verified, use the established publisher. We intentionally
    # invoke it only once to avoid any possibility of duplicate public posts.
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "publish_instagram.py")],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
