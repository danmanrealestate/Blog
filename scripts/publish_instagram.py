import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error


ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]

API_VERSION = "v26.0"
GRAPH_URL = f"https://graph.instagram.com/{API_VERSION}"


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


def wait_for_container(container_id, attempts=20):
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


with open("instagram/lesson-008/manifest.json", encoding="utf-8") as f:
    lesson = json.load(f)


caption = lesson["caption"]
files = lesson["files"]

if not files:
    raise RuntimeError("No slide images found in latest.json")

if len(files) > 10:
    raise RuntimeError(
        f"Instagram carousel supports at most 10 items; found {len(files)}"
    )


print(
    f'Publishing Lesson {lesson["lesson"]}: '
    f'{lesson["topic"]}'
)

print(f"Found {len(files)} slides.")


# -------------------------------------------------
# Create an Instagram container for each slide
# -------------------------------------------------

children = []

for number, item in enumerate(files, start=1):
   image_url = item if isinstance(item, str) else item["photo"]

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


# -------------------------------------------------
# Create carousel
# -------------------------------------------------

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

print("Publishing carousel...")

published = post(
    f"{INSTAGRAM_USER_ID}/media_publish",
    {
        "creation_id": carousel_id,
        "access_token": ACCESS_TOKEN,
    },
)

print("")
print("SUCCESS")
print(
    f'Lesson {lesson["lesson"]} published to Instagram.'
)
print(f'Instagram media ID: {published["id"]}')
