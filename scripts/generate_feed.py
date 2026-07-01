import os
import json
import re
import html
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import format_datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

SITE_NAME = "DMSellsRE.com Real Estate Blog"
SITE_URL = "https://danmanrealestate.github.io/Blog"
MAIN_WEBSITE = "https://dmsellsre.com"
AUTHOR = "Dan Marovich, RE/MAX Ace Realty"
CONTACT_EMAIL = "danmarovich@remax.net"
TIMEZONE = "America/New_York"

POSTS_FILE = "posts.json"
FEED_FILE = "feed.xml"
POSTS_DIR = "posts"
MAX_POSTS_IN_FEED = 50

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


RESIDENTIAL_IMAGES = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1592595896551-12b371d546d5?auto=format&fit=crop&w=1600&q=80",
]

COMMERCIAL_IMAGES = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1600&q=80",
    "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1600&q=80",
]


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
    "A practical moving checklist for Pennsylvania home buyers",
    "How sellers can make their property stand out online",
    "Questions buyers should ask before touring homes",
    "How to plan a move to Downingtown or Chester County",
    "What renters should know before applying for a home",
    "How homeowners can prepare for a successful showing",
    "The importance of local guidance when buying a home",
    "How to evaluate a home beyond the listing photos",
    "What to expect from offer to closing in Pennsylvania",
    "How to decide when it is time to sell your home",
    "Residential real estate planning for growing families",
    "How to prepare financially before buying a home",
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
    "How to think about vacancy, expenses, and tenant quality",
    "What landlords should consider before leasing commercial space",
    "How to prepare a commercial property for market",
    "Commercial real estate planning for local business growth",
    "What investors should know about mixed-use properties",
    "How to compare office, retail, flex, and industrial space",
    "Why tenant quality matters in commercial investments",
    "How property condition affects commercial value",
    "Commercial leasing questions every business owner should ask",
    "How investors can evaluate long-term asset performance",
    "What to know before buying a small commercial building",
    "How management strategy supports investment returns",
]


def main():
    os.makedirs(POSTS_DIR, exist_ok=True)

    post_type = os.getenv("POST_TYPE", "auto").lower().strip()
    local_now = datetime.now(ZoneInfo(TIMEZONE))

    if post_type == "auto":
        if local_now.weekday() == 0 and local_now.hour == 8:
            post_type = "residential"
        elif local_now.weekday() == 4 and local_now.hour == 8:
            post_type = "commercial"
        else:
            print(f"No post scheduled now. Local time: {local_now.isoformat()}")
            rebuild_all()
            return

    if post_type not in ("residential", "commercial"):
        raise ValueError("POST_TYPE must be auto, residential, or commercial.")

    posts = load_posts()

    category = "Residential Real Estate" if post_type == "residential" else "Commercial Real Estate"
    topics = RESIDENTIAL_TOPICS if post_type == "residential" else COMMERCIAL_TOPICS
    images = RESIDENTIAL_IMAGES if post_type == "residential" else COMMERCIAL_IMAGES

    today_key = local_now.strftime("%Y-%m-%d")

    if any(p.get("date_key") == today_key and p.get("category") == category for p in posts):
        print(f"{category} post already exists for {today_key}. Rebuilding files only.")
        rebuild_all()
        return

    topic = pick_next_topic(posts, category, topics)
    image_url = pick_image(posts, category, images)

    article = generate_article(category, topic, local_now)

    slug = f"{today_key}-{slugify(article['title'])}"
    filename = f"{slug}.html"
    post_url = f"{SITE_URL}/posts/{filename}"

    post = {
        "date": datetime.now(timezone.utc).isoformat(),
        "date_key": today_key,
        "category": category,
        "topic": topic,
        "title": article["title"],
        "description": article["description"],
        "content": article["content"],
        "image_url": image_url,
        "filename": filename,
        "link": post_url,
        "author": AUTHOR,
    }

    posts.append(post)
    save_posts(posts)
    rebuild_all()

    print(f"Created full article page: {post_url}")


def load_posts():
    if not os.path.exists(POSTS_FILE):
        return []

    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def save_posts(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as file:
        json.dump(posts, file, indent=2, ensure_ascii=False)


def pick_next_topic(posts, category, topics):
    used_topics = [p.get("topic") for p in posts if p.get("category") == category]

    for topic in topics:
        if topic not in used_topics:
            return topic

    index = len(used_topics) % len(topics)
    return topics[index]


def pick_image(posts, category, images):
    count = len([p for p in posts if p.get("category") == category])
    return images[count % len(images)]


def generate_article(category, topic, local_now):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY repository secret.")

    prompt = f"""
Write an original, polished, SEO-friendly real estate blog article for {SITE_NAME}.

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
- Content between 1000 and 1400 words.
- Use HTML formatting only inside content.
- Use <p>, <h2>, <h3>, and <ul><li> where helpful.
- Make the article practical, attractive, and useful to real estate visitors.
- Do not invent exact market statistics, interest rates, sales numbers, tax rules, legal advice, or financial guarantees.
- Do not mention that the article was AI-generated.
- Write in a professional but approachable tone.
- Include practical advice for buyers, sellers, renters, landlords, business owners, or investors depending on the topic.
- Include internal links naturally inside the article:
  <a href="{MAIN_WEBSITE}">DMSellsRE.com</a>
  <a href="{MAIN_WEBSITE}/contact">contact Dan Marovich</a>
- End with a call to contact Dan Marovich at {CONTACT_EMAIL}.
"""

    payload = {
        "model": OPENAI_MODEL,
        "input": prompt,
        "text": {
            "format": {
                "type": "json_object"
            }
        },
    }

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    data = response.json()
    output_text = extract_output_text(data)

    article = parse_article_json(output_text)

    for key in ("title", "description", "content"):
        if key not in article or not article[key]:
            raise RuntimeError(f"OpenAI response missing required field: {key}")

    article["title"] = str(article["title"]).strip()[:70]
    article["description"] = str(article["description"]).strip()
    article["content"] = str(article["content"]).strip()

    return article


def extract_output_text(data):
    if data.get("output_text"):
        return data["output_text"]

    pieces = []

    for item in data.get("output", []):
        for content_item in item.get("content", []):
            if "text" in content_item:
                pieces.append(content_item["text"])

    output_text = "".join(pieces).strip()

    if not output_text:
        raise RuntimeError(f"No usable OpenAI output found: {json.dumps(data)[:1000]}")

    return output_text


def parse_article_json(text):
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = re.sub(r"^json", "", cleaned, flags=re.I).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if match:
            return json.loads(match.group(0))
        raise


def rebuild_all():
    posts = load_posts()
    os.makedirs(POSTS_DIR, exist_ok=True)

    for post in posts:
        write_article_page(post)

    write_index(posts)
    write_feed(posts)


def write_article_page(post):
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_attr(post["title"])}</title>
  <meta name="description" content="{escape_attr(post["description"])}">
  <style>
    :root {{
      --navy: #061b36;
      --red: #b5121b;
      --gold: #c7a45a;
      --light: #f5f7fb;
      --text: #172033;
      --muted: #667085;
      --border: #e4e8f0;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--light);
      color: var(--text);
      line-height: 1.7;
    }}

    a {{
      color: var(--red);
      font-weight: 800;
    }}

    .hero {{
      background:
        linear-gradient(90deg, rgba(6,27,54,.92), rgba(6,27,54,.55)),
        url('{escape_attr(post["image_url"])}') center/cover;
      color: white;
      padding: 92px 6%;
    }}

    .hero-inner {{
      max-width: 1080px;
      margin: auto;
    }}

    .eyebrow {{
      color: #f0dba1;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 2px;
      font-size: .85rem;
      margin-bottom: 14px;
    }}

    h1 {{
      font-size: clamp(2.2rem, 5vw, 4.6rem);
      line-height: 1.02;
      margin: 0;
      max-width: 980px;
      letter-spacing: -1px;
    }}

    .meta {{
      margin-top: 18px;
      color: #dbe6f3;
      font-weight: 700;
    }}

    main {{
      max-width: 1080px;
      margin: -42px auto 0;
      padding: 0 6% 74px;
    }}

    article {{
      background: white;
      border-radius: 24px;
      box-shadow: 0 18px 45px rgba(15,23,42,.14);
      overflow: hidden;
      border: 1px solid var(--border);
    }}

    .featured {{
      width: 100%;
      height: 380px;
      object-fit: cover;
      display: block;
    }}

    .content {{
      padding: 44px;
    }}

    .summary {{
      font-size: 1.18rem;
      color: #344054;
      border-left: 5px solid var(--red);
      padding-left: 18px;
      margin-bottom: 30px;
      font-weight: 700;
    }}

    h2 {{
      color: var(--navy);
      font-size: 1.9rem;
      line-height: 1.15;
      margin-top: 34px;
    }}

    h3 {{
      color: var(--navy);
      margin-top: 24px;
    }}

    p,
    li {{
      color: #344054;
    }}

    ul {{
      padding-left: 24px;
    }}

    li {{
      margin-bottom: 8px;
    }}

    .cta {{
      margin-top: 40px;
      background: linear-gradient(135deg, var(--red), var(--navy));
      color: white;
      border-radius: 18px;
      padding: 30px;
    }}

    .cta h2 {{
      color: white;
      margin-top: 0;
    }}

    .cta p {{
      color: #e4edf8;
      margin-bottom: 18px;
    }}

    .btn {{
      display: inline-block;
      background: white;
      color: var(--navy);
      padding: 13px 18px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 900;
      text-transform: uppercase;
      font-size: .9rem;
    }}

    footer {{
      text-align: center;
      padding: 34px 6%;
      color: var(--muted);
    }}

    @media (max-width: 760px) {{
      .content {{
        padding: 26px;
      }}

      .featured {{
        height: 240px;
      }}
    }}
  </style>
</head>
<body>
  <section class="hero">
    <div class="hero-inner">
      <div class="eyebrow">{escape_html(post["category"])}</div>
      <h1>{escape_html(post["title"])}</h1>
      <div class="meta">By {escape_html(post["author"])} · {display_date(post["date"])}</div>
    </div>
  </section>

  <main>
    <article>
      <img class="featured" src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}">
      <div class="content">
        <p class="summary">{escape_html(post["description"])}</p>

        {post["content"]}

        <div class="cta">
          <h2>Ready to Talk Real Estate?</h2>
          <p>Whether you are buying, selling, renting, leasing, investing, or exploring property management, Dan Marovich can help you understand your options.</p>
          <a class="btn" href="{MAIN_WEBSITE}/contact">Contact Dan</a>
        </div>
      </div>
    </article>
  </main>

  <footer>
    Dan Marovich · RE/MAX Ace Realty · <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a><br>
    <a href="{MAIN_WEBSITE}">Visit DMSellsRE.com</a>
  </footer>
</body>
</html>
"""

    output_path = os.path.join(POSTS_DIR, post["filename"])

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(page)


def write_index(posts):
    posts = sorted(posts, key=lambda p: p.get("date", ""), reverse=True)

    cards = ""

    for post in posts:
        cards += f"""
        <article class="card">
          <img src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}">
          <div class="body">
            <div class="category">{escape_html(post["category"])}</div>
            <h2><a href="posts/{escape_attr(post["filename"])}">{escape_html(post["title"])}</a></h2>
            <p>{escape_html(post["description"])}</p>
            <a class="read" href="posts/{escape_attr(post["filename"])}">Read Article →</a>
          </div>
        </article>
"""

    if not cards:
        cards = """
        <div class="empty">
          <h2>Articles Coming Soon</h2>
          <p>Residential articles are scheduled for Mondays and commercial articles are scheduled for Fridays.</p>
        </div>
"""

    index = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DMSellsRE Real Estate Blog</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: #f5f7fb;
      color: #172033;
      line-height: 1.6;
    }}

    header {{
      background: #061b36;
      color: white;
      padding: 72px 6%;
      text-align: center;
    }}

    header h1 {{
      margin: 0;
      font-size: clamp(2rem, 4vw, 4rem);
    }}

    header p {{
      color: #dbe6f3;
      max-width: 850px;
      margin: 14px auto 0;
    }}

    main {{
      padding: 50px 6%;
      max-width: 1200px;
      margin: auto;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 26px;
    }}

    .card {{
      background: white;
      border-radius: 20px;
      overflow: hidden;
      box-shadow: 0 14px 35px rgba(15,23,42,.10);
    }}

    .card img {{
      width: 100%;
      height: 260px;
      object-fit: cover;
      display: block;
    }}

    .body {{
      padding: 26px;
    }}

    .category {{
      color: #b5121b;
      text-transform: uppercase;
      font-size: .8rem;
      letter-spacing: 1px;
      font-weight: 900;
    }}

    h2 {{
      margin: 8px 0 10px;
      line-height: 1.15;
    }}

    a {{
      color: #061b36;
      text-decoration: none;
    }}

    .read {{
      color: #b5121b;
      font-weight: 900;
      text-transform: uppercase;
      font-size: .9rem;
    }}

    .empty {{
      background: white;
      border-radius: 20px;
      padding: 32px;
      box-shadow: 0 14px 35px rgba(15,23,42,.10);
    }}

    @media (max-width: 800px) {{
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>DMSellsRE Real Estate Blog</h1>
    <p>Residential, commercial, leasing, property management, and investment real estate insights from Dan Marovich.</p>
  </header>

  <main>
    <div class="grid">
      {cards}
    </div>
  </main>
</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as file:
        file.write(index)


def write_feed(posts):
    posts = sorted(posts, key=lambda p: p.get("date", ""), reverse=True)[:MAX_POSTS_IN_FEED]

    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
        },
    )

    channel = ET.SubElement(rss, "channel")

    add_text(channel, "title", SITE_NAME)
    add_text(channel, "link", SITE_URL + "/")
    add_text(
        channel,
        "description",
        "Residential, commercial, leasing, property management, and investment real estate insights from Dan Marovich.",
    )
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

        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", post["image_url"])
        enclosure.set("type", "image/jpeg")

        content_html = f"""
<img src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}" style="width:100%;max-width:900px;height:auto;" />
<p><strong>{escape_html(post["description"])}</strong></p>
{post["content"]}
<p><strong>Contact Dan Marovich, RE/MAX Ace Realty:</strong> <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p>
<p><a href="{post["link"]}">Read the full article</a></p>
"""

        content_node = ET.SubElement(item, "content:encoded")
        content_node.text = f"__CDATA_START__{content_html}__CDATA_END__"

    rough = ET.tostring(rss, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")

    pretty = pretty.replace("__CDATA_START__", "<![CDATA[")
    pretty = pretty.replace("__CDATA_END__", "]]>")

    with open(FEED_FILE, "w", encoding="utf-8") as file:
        file.write(pretty)


def add_text(parent, tag, text):
    node = ET.SubElement(parent, tag)
    node.text = str(text)
    return node


def slugify(text):
    slug = str(text).lower()
    slug = slug.replace("&", " and ")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"^-+|-+$", "", slug)
    return slug[:80] or "real-estate-article"


def escape_html(value):
    return html.escape(str(value or ""), quote=False)


def escape_attr(value):
    return html.escape(str(value or ""), quote=True)


def display_date(value):
    try:
        return datetime.fromisoformat(value).strftime("%B %d, %Y")
    except Exception:
        return ""


if __name__ == "__main__":
    main()
