import os
import json
import html
import re
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import format_datetime
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

SITE_NAME = "DMSellsRE.com Real Estate Blog"
SITE_URL = "https://dmsellsre.com"
AUTHOR = "Dan Marovich, RE/MAX Ace Realty"
CONTACT_EMAIL = "danmarovich@remax.net"
TIMEZONE = "America/New_York"
POSTS_FILE = "posts.json"
FEED_FILE = "feed.xml"
MAX_POSTS_IN_FEED = 50

# Change this if you prefer a different current OpenAI model.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

RESIDENTIAL_TOPICS = [
    "Chester County housing market tips for buyers",
    "How to prepare your Downingtown home for sale",
    "First-time home buyer guide for Southeastern Pennsylvania",
    "Should you buy or rent in Chester County?",
    "What sellers should know before listing a home",
    "How inspections and contingencies affect buyers",
    "Best ways to improve curb appeal before selling",
    "Understanding closing costs for Pennsylvania home buyers",
    "How to price a home competitively in today's market",
    "Residential leasing tips for tenants and landlords",
    "How buyers can compare neighborhoods in Southeastern Pennsylvania",
    "What homeowners should know before downsizing",
    "How to make a strong offer without overpaying",
    "Why local market knowledge matters when selling a home",
    "A practical moving checklist for Pennsylvania home buyers"
]

COMMERCIAL_TOPICS = [
    "Commercial real estate opportunities in Chester County",
    "What investors should know about income-producing properties",
    "Office and flex-space leasing considerations in Southeastern Pennsylvania",
    "Retail property trends for local business owners",
    "How to evaluate a commercial investment property",
    "Multifamily investment basics for real estate investors",
    "Commercial leasing terms every tenant should understand",
    "Property management considerations for landlords",
    "How location affects commercial property value",
    "Land and building lot opportunities for developers",
    "What small business owners should know before leasing space",
    "How investors can compare commercial property types",
    "Why property management matters for long-term asset performance",
    "Commercial due diligence basics for Pennsylvania buyers",
    "How to think about vacancy, expenses, and tenant quality"
]

def main():
    post_type = os.getenv("POST_TYPE", "auto").lower().strip()
    local_now = datetime.now(ZoneInfo(TIMEZONE))

    if post_type == "auto":
        if local_now.weekday() == 0 and local_now.hour == 8:
            post_type = "residential"
        elif local_now.weekday() == 4 and local_now.hour == 8:
            post_type = "commercial"
        else:
            print(f"No post scheduled now. Local time: {local_now.isoformat()}")
            rebuild_feed()
            return

    if post_type not in ("residential", "commercial"):
        raise ValueError("POST_TYPE must be auto, residential, or commercial.")

    posts = load_posts()
    category = "Residential Real Estate" if post_type == "residential" else "Commercial Real Estate"

    # Prevent duplicate same-day posts for the same category.
    today_key = local_now.strftime("%Y-%m-%d")
    if any(p.get("date_key") == today_key and p.get("category") == category for p in posts):
        print(f"{category} post already exists for {today_key}. Rebuilding feed only.")
        rebuild_feed()
        return

    topics = RESIDENTIAL_TOPICS if post_type == "residential" else COMMERCIAL_TOPICS
    topic = pick_next_topic(posts, category, topics)

    article = generate_article(category, topic, local_now)
    slug = slugify(article["title"])

    post = {
        "date": datetime.now(timezone.utc).isoformat(),
        "date_key": today_key,
        "category": category,
        "topic": topic,
        "title": article["title"],
        "description": article["description"],
        "content": article["content"],
        "link": f"{SITE_URL}/blog/{slug}",
        "author": AUTHOR
    }

    posts.append(post)
    save_posts(posts)
    rebuild_feed()
    print(f"Created post: {post['title']}")

def load_posts():
    if not os.path.exists(POSTS_FILE):
        return []
    with open(POSTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

def pick_next_topic(posts, category, topics):
    used = [p.get("topic") for p in posts if p.get("category") == category]
    for topic in topics:
        if topic not in used:
            return topic
    count = len([p for p in posts if p.get("category") == category])
    return topics[count % len(topics)]

def generate_article(category, topic, local_now):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY repository secret.")

    prompt = f"""
Write an original SEO-friendly blog article for {SITE_NAME}.

Category: {category}
Topic: {topic}
Date: {local_now.strftime('%B %d, %Y')}
Author: {AUTHOR}

Local markets to naturally reference when relevant:
- Downingtown, PA
- Chester County, PA
- Montgomery County, PA
- Berks County, PA
- Lancaster County, PA
- Bucks County, PA
- Delaware County, PA

Return valid JSON only with these exact fields:
{{
  "title": "",
  "description": "",
  "content": ""
}}

Requirements:
- Title under 70 characters.
- Description between 140 and 160 characters.
- Content between 900 and 1200 words.
- Use HTML formatting only inside content.
- Use <p>, <h2>, and <ul><li> where helpful.
- Do not invent exact market statistics, interest rates, sales numbers, tax rules, or legal advice.
- Keep the tone professional, helpful, and local.
- Include practical information for buyers, sellers, renters, landlords, or investors.
- End with a call to contact Dan Marovich at {CONTACT_EMAIL}.
"""

    payload = {
        "model": OPENAI_MODEL,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_object"
            }
        }
    }

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=120
    )

    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    data = response.json()
    output_text = extract_output_text(data)

    try:
        article = json.loads(output_text)
    except json.JSONDecodeError:
        cleaned = output_text.strip().strip("`")
        cleaned = re.sub(r"^json", "", cleaned, flags=re.I).strip()
        article = json.loads(cleaned)

    for key in ("title", "description", "content"):
        if key not in article or not article[key]:
            raise RuntimeError(f"OpenAI response missing {key}: {article}")

    return article

def extract_output_text(data):
    if "output_text" in data and data["output_text"]:
        return data["output_text"]

    pieces = []
    for item in data.get("output", []):
        for content_item in item.get("content", []):
            if "text" in content_item:
                pieces.append(content_item["text"])

    if not pieces:
        raise RuntimeError(f"No output text found in OpenAI response: {json.dumps(data)[:1000]}")
    return "".join(pieces)

def rebuild_feed():
    posts = load_posts()
    posts = sorted(posts, key=lambda p: p.get("date", ""), reverse=True)[:MAX_POSTS_IN_FEED]

    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
    })

    channel = ET.SubElement(rss, "channel")
    add_text(channel, "title", SITE_NAME)
    add_text(channel, "link", SITE_URL)
    add_text(channel, "description", "Residential, commercial, leasing, property management, and investment real estate insights from Dan Marovich.")
    add_text(channel, "language", "en-us")
    add_text(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc), usegmt=True))

    for post in posts:
        item = ET.SubElement(channel, "item")
        add_text(item, "title", post["title"])
        add_text(item, "link", post["link"])
        guid = add_text(item, "guid", post["link"])
        guid.set("isPermaLink", "false")
        add_text(item, "pubDate", format_datetime(datetime.fromisoformat(post["date"]), usegmt=True))
        add_text(item, "category", post["category"])
        add_text(item, "description", post["description"])
        content_node = ET.SubElement(item, "content:encoded")
        content_node.text = f"<![CDATA[{post['content']}]]>"

    rough = ET.tostring(rss, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    pretty = reparsed.toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

    # minidom escapes CDATA marker text; restore it for RSS readers.
    pretty = pretty.replace("&lt;![CDATA[", "<![CDATA[").replace("]]&gt;", "]]>")

    with open(FEED_FILE, "w", encoding="utf-8") as f:
        f.write(pretty)

def add_text(parent, tag, text):
    node = ET.SubElement(parent, tag)
    node.text = str(text)
    return node

def slugify(text):
    slug = text.lower()
    slug = slug.replace("&", " and ")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug[:80] or "real-estate-article"

if __name__ == "__main__":
    main()
