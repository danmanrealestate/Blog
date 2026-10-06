#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SYSTEM_USER_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
CONFIGURED_INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
LESSON_NUMBER = int(os.environ["LESSON_NUMBER"])

API_VERSION = "v26.0"
GRAPH_URL = f"https://graph.facebook.com/{API_VERSION}"
ROOT = Path(__file__).resolve().parents[1]


def get_json(endpoint, params):
    query = urllib.parse.urlencode(params)
    url = f"{GRAPH_URL}/{endpoint}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        print(f"Instagram API error {e.code}:")
        print(body)
        raise


def resolve_page_context():
    """Resolve the linked Instagram account and Page Access Token from the system-user token."""
    result = get_json(
        "me/accounts",
        {
            "fields": "id,name,access_token,tasks,instagram_business_account",
            "access_token": SYSTEM_USER_ACCESS_TOKEN,
        },
    )
    pages = result.get("data", [])
    for page in pages:
        ig = page.get("instagram_business_account") or {}
        ig_id = str(ig.get("id", ""))
        tasks = page.get("tasks") or []
        if ig_id == str(CONFIGURED_INSTAGRAM_USER_ID):
            if "CREATE_CONTENT" not in tasks:
                raise RuntimeError(
                    f"Linked Page {page.get('name')} does not grant CREATE_CONTENT to this token"
                )
            page_token = page.get("access_token")
            if not page_token:
                raise RuntimeError("Meta returned the linked Page but no Page Access Token")
            print(f"Using linked Page: {page.get('name')} ({page.get('id')})")
            print(f"Verified linked Instagram account: {ig_id}")
            return ig_id, page_token
    raise RuntimeError(
        "Could not find the configured Instagram account through /me/accounts. "
        "Check the Page/Instagram link and system-user Page permissions."
    )


INSTAGRAM_USER_ID, ACCESS_TOKEN = resolve_page_context()


def post(endpoint, data):
    url = f"{GRAPH_URL}/{endpoint}"
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(url, data=encoded, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode("utf-8")
            print(body)
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        print(f"Instagram API error {e.code}:")
        print(body)
        raise


def wait_for_container(container_id, attempts=30):
    print(f"Waiting for container {container_id}...")
    for attempt in range(attempts):
        params = urllib.parse.urlencode({
            "fields": "status_code",
            "access_token": ACCESS_TOKEN,
        })
        url = f"{GRAPH_URL}/{container_id}?{params}"
        with urllib.request.urlopen(url, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        status = result.get("status_code")
        print(f"Container {container_id}: {status} ({attempt + 1}/{attempts})")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram container failed with status: {status}")
        time.sleep(5)
    raise TimeoutError(f"Timed out waiting for Instagram container {container_id}")


def get_image_url(item):
    if isinstance(item, dict):
        url = item.get("photo")
    elif isinstance(item, str):
        url = item
    else:
        url = None
    if not url:
        raise RuntimeError(f"Invalid slide entry: {item}")
    return url


manifest_path = ROOT / "instagram" / f"lesson-{LESSON_NUMBER:03d}" / "manifest.json"
if not manifest_path.exists():
    raise RuntimeError(f"Lesson manifest not found: {manifest_path}")

lesson = json.loads(manifest_path.read_text(encoding="utf-8"))
if int(lesson.get("lesson", -1)) != LESSON_NUMBER:
    raise RuntimeError(
        f"Requested Lesson {LESSON_NUMBER}, but manifest identifies Lesson {lesson.get('lesson')}"
    )

caption = lesson["caption"]
files = lesson["files"]
if not files:
    raise RuntimeError("No slide images found in lesson manifest")
if len(files) > 10:
    raise RuntimeError(f"Instagram carousel supports at most 10 items; found {len(files)}")

print(f"Publishing specific Lesson {LESSON_NUMBER}: {lesson['topic']}")
print("This specific-lesson publisher does NOT update publish_state.json.")
print(f"Found {len(files)} slides.")

children = []
for number, item in enumerate(files, start=1):
    image_url = get_image_url(item)
    print(f"Creating slide {number}: {image_url}")
    result = post(
        f"{INSTAGRAM_USER_ID}/media",
        {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": ACCESS_TOKEN,
        },
    )
    container_id = result["id"]
    wait_for_container(container_id)
    children.append(container_id)

print("Creating carousel...")
carousel = post(
    f"{INSTAGRAM_USER_ID}/media",
    {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": ACCESS_TOKEN,
    },
)
carousel_id = carousel["id"]
wait_for_container(carousel_id)

print("Publishing carousel...")
published = post(
    f"{INSTAGRAM_USER_ID}/media_publish",
    {
        "creation_id": carousel_id,
        "access_token": ACCESS_TOKEN,
    },
)

print("SUCCESS")
print(f"Lesson {LESSON_NUMBER} published to Instagram.")
print(f"Instagram media ID: {published['id']}")
print("Sequential publish state was NOT changed.")
