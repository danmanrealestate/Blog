import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]

API_VERSION = "v26.0"
GRAPH_URL = f"https://graph.instagram.com/{API_VERSION}"

INSTAGRAM_DIR = Path("instagram")
STATE_FILE = INSTAGRAM_DIR / "publish_state.json"


def post(endpoint, data):
    url = f"{GRAPH_URL}/{endpoint}"

    encoded = urllib.parse.urlencode(data).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
    )

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
        params = urllib.parse.urlencode(
            {
                "fields": "status_code",
                "access_token": ACCESS_TOKEN,
            }
        )

        url = f"{GRAPH_URL}/{container_id}?{params}"

        with urllib.request.urlopen(url, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        status = result.get("status_code")

        print(
            f"Container {container_id}: "
            f"{status} ({attempt + 1}/{attempts})"
        )

        if status == "FINISHED":
            return

        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(
                f"Instagram container failed with status: {status}"
            )

        time.sleep(5)

    raise TimeoutError(
        f"Timed out waiting for Instagram container {container_id}"
    )


def load_publish_state():
    if not STATE_FILE.exists():
        raise RuntimeError(
            f"Publish state file not found: {STATE_FILE}"
        )

    with STATE_FILE.open(encoding="utf-8") as f:
        state = json.load(f)

    if "last_published_lesson" not in state:
        raise RuntimeError(
            "publish_state.json does not contain "
            "'last_published_lesson'."
        )

    return state


def save_publish_state(lesson_number):
    state = {
        "last_published_lesson": lesson_number
    }

    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")

    print(
        f"Publish state updated: "
        f"last_published_lesson = {lesson_number}"
    )


def load_next_lesson():
    state = load_publish_state()

    last_published = int(
        state["last_published_lesson"]
    )

    next_lesson = last_published + 1

    lesson_folder = (
        INSTAGRAM_DIR /
        f"lesson-{next_lesson:03d}"
    )

    manifest_file = lesson_folder / "manifest.json"

    print(
        f"Last successfully published lesson: "
        f"{last_published}"
    )

    print(
        f"Next lesson to publish: "
        f"{next_lesson}"
    )

    if not lesson_folder.exists():
        raise RuntimeError(
            f"Lesson {next_lesson} has not been "
            f"generated yet. Expected folder: "
            f"{lesson_folder}"
        )

    if not manifest_file.exists():
        raise RuntimeError(
            f"Manifest not found for Lesson "
            f"{next_lesson}: {manifest_file}"
        )

    with manifest_file.open(encoding="utf-8") as f:
        lesson = json.load(f)

    actual_lesson_number = int(
        lesson.get("lesson", next_lesson)
    )

    if actual_lesson_number != next_lesson:
        raise RuntimeError(
            f"Expected Lesson {next_lesson}, "
            f"but manifest identifies itself as "
            f"Lesson {actual_lesson_number}."
        )

    return lesson, next_lesson


def get_image_url(item):
    if isinstance(item, dict):
        image_url = item.get("photo")

        if not image_url:
            raise RuntimeError(
                f"Slide dictionary does not contain "
                f"a photo URL: {item}"
            )

        return image_url

    if isinstance(item, str):
        return item

    raise RuntimeError(
        f"Unsupported slide entry: {item}"
    )


# -------------------------------------------------
# Determine the next unpublished lesson
# -------------------------------------------------

lesson, lesson_number = load_next_lesson()

caption = lesson["caption"]
files = lesson["files"]

if not files:
    raise RuntimeError(
        f"No slide images found for "
        f"Lesson {lesson_number}."
    )

if len(files) > 10:
    raise RuntimeError(
        f"Instagram carousel supports at most "
        f"10 items; found {len(files)}."
    )

print("")
print("----------------------------------------")
print(
    f'Publishing Lesson {lesson_number}: '
    f'{lesson["topic"]}'
)
print("----------------------------------------")
print("")

print(f"Found {len(files)} slides.")


# -------------------------------------------------
# Create Instagram container for every slide
# -------------------------------------------------

children = []

for number, item in enumerate(files, start=1):

    image_url = get_image_url(item)

    print(
        f"Creating slide {number}: "
        f"{image_url}"
    )

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


# -------------------------------------------------
# Create carousel
# -------------------------------------------------

print("")
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


# -------------------------------------------------
# Publish carousel
# -------------------------------------------------

print("")
print("Publishing carousel...")

published = post(
    f"{INSTAGRAM_USER_ID}/media_publish",
    {
        "creation_id": carousel_id,
        "access_token": ACCESS_TOKEN,
    },
)


# -------------------------------------------------
# IMPORTANT:
# Update state ONLY after successful publication
# -------------------------------------------------

save_publish_state(lesson_number)


# -------------------------------------------------
# Success
# -------------------------------------------------

print("")
print("========================================")
print("SUCCESS")
print("========================================")
print(
    f"Lesson {lesson_number} "
    f"published to Instagram."
)
print(
    f'Instagram media ID: '
    f'{published["id"]}'
)
print(
    f"Next scheduled publication will be "
    f"Lesson {lesson_number + 1}."
)
