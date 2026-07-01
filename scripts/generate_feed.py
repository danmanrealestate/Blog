import os
import json
import re
import html
import math
import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from email.utils import format_datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

SITE_NAME = "Real Estate Blog"
SITE_URL = "https://danmanrealestate.github.io/Blog"
MAIN_WEBSITE = "https://dmsellsre.com"
AUTHOR = "Dan Marovich, RE/MAX Ace Realty"
CONTACT_EMAIL = "danmarovich@remax.net"
CONTACT_PHONE = "610-613-9148"
CONTACT_PHONE_TEL = "tel:6106139148"
TIMEZONE = "America/New_York"

POSTS_FILE = "posts.json"
FEED_FILE = "feed.xml"
POSTS_DIR = "posts"
MAX_POSTS_IN_FEED = 100

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

RESIDENTIAL_IMAGES = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1592595896551-12b371d546d5?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=1800&q=80",
]

COMMERCIAL_IMAGES = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1554469384-e58fac16e23a?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1568992688065-536aad8a12f6?auto=format&fit=crop&w=1800&q=80",
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
    "How to evaluate school districts, taxes, and commute needs",
    "What homeowners should know before renovating to sell",
    "How buyers can stay organized during a home search",
    "Why pricing strategy matters when selling a home",
    "How to prepare for a home appraisal",
    "What sellers should know about buyer financing",
    "How to choose between a starter home and a long-term home",
    "What to consider before buying new construction",
    "How to prepare a rental property for quality tenants",
    "Questions landlords should ask before listing a rental",
    "How to compare suburban and small-town living in Southeastern PA",
    "What homeowners should know about timing a sale",
    "How to avoid common buyer mistakes in a competitive market",
    "How to create a home search strategy that saves time",
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
    "How commercial property owners can reduce vacancy risk",
    "What to know before purchasing land for development",
    "How investors can think about cash flow and resale value",
    "Commercial property marketing tips for owners",
    "How business owners can plan for future space needs",
    "What investors should know about lease structure",
    "How to compare owner-user and investment commercial properties",
    "Why visibility and access matter for retail space",
    "How to evaluate parking, zoning, and utility needs",
    "What to consider before buying a warehouse or flex building",
    "How commercial tenants can prepare before touring space",
    "How landlords can improve tenant retention",
    "What to know about buying multifamily properties",
    "Commercial property management planning for investors",
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
        print(f"{category} post already exists for {today_key}. Rebuilding with Version 5 template.")
        rebuild_all()
        return

    topic = pick_next_topic(posts, category, topics)
    image_url = pick_image(posts, category, images, offset=0)
    inline_image_url = pick_image(posts, category, images, offset=1)
    sidebar_image_url = pick_image(posts, category, images, offset=2)

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
        "faq": article.get("faq", []),
        "keywords": article.get("keywords", []),
        "image_url": image_url,
        "inline_image_url": inline_image_url,
        "sidebar_image_url": sidebar_image_url,
        "filename": filename,
        "link": post_url,
        "author": AUTHOR,
        "reading_time": estimate_reading_time(article["content"]),
    }

    posts.append(post)
    save_posts(posts)
    rebuild_all()

    print(f"Created Version 5 article page: {post_url}")


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


def pick_image(posts, category, images, offset=0):
    count = len([p for p in posts if p.get("category") == category])
    return images[(count + offset) % len(images)]


def generate_article(category, topic, local_now):
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY repository secret.")

    prompt = f"""
Write an original, polished, professional, SEO-friendly real estate blog article for {SITE_NAME}.

Category: {category}
Topic: {topic}
Date: {local_now.strftime('%B %d, %Y')}
Author: {AUTHOR}

Business contact:
- Dan Marovich
- RE/MAX Ace Realty
- Phone: {CONTACT_PHONE}
- Email: {CONTACT_EMAIL}
- Website: {MAIN_WEBSITE}

Local markets to naturally reference when relevant:
- Downingtown, PA
- Chester County, PA
- Montgomery County, PA
- Berks County, PA
- Lancaster County, PA
- Bucks County, PA
- Delaware County, PA
- Southeastern Pennsylvania

Return valid JSON only with these exact fields:
{{
  "title": "",
  "description": "",
  "content": "",
  "faq": [
    {{
      "question": "",
      "answer": ""
    }}
  ],
  "keywords": []
}}

Article requirements:
- Title under 70 characters.
- Description between 140 and 160 characters.
- Content between 1400 and 2000 words.
- Use HTML formatting only inside content.
- Use <p>, <h2>, <h3>, <ul>, and <li> where helpful.
- Add a short "Key Takeaways" section in the content.
- Add a short "Local Market Perspective" section in the content.
- Add a "Questions to Ask Before You Move Forward" section.
- Add practical advice for buyers, sellers, renters, landlords, business owners, or investors depending on the topic.
- Make the article useful, attractive, and educational for real estate visitors.
- Do not invent exact market statistics, interest rates, sales numbers, tax rules, legal advice, or financial guarantees.
- Do not say the article was AI-generated.
- Use a professional, approachable, confident tone.
- Include internal links naturally inside the article:
  <a href="{MAIN_WEBSITE}">DMSellsRE.com</a>
  <a href="{MAIN_WEBSITE}/contact">contact Dan Marovich</a>
- End the content with a natural call to contact Dan Marovich at {CONTACT_PHONE} or {CONTACT_EMAIL}.
- FAQ must include 4 questions and answers.
- Keywords must include 8 to 12 SEO keyword phrases.
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
        timeout=180,
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

    if not isinstance(article.get("faq"), list):
        article["faq"] = []

    if not isinstance(article.get("keywords"), list):
        article["keywords"] = []

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
    posts = normalize_posts(load_posts())
    os.makedirs(POSTS_DIR, exist_ok=True)

    for post in posts:
        write_article_page(post)

    write_index(posts)
    write_feed(posts)
    save_posts(posts)


def normalize_posts(posts):
    normalized = []

    for index, post in enumerate(posts):
        category = post.get("category", "Residential Real Estate")
        is_commercial = "Commercial" in category
        image_pool = COMMERCIAL_IMAGES if is_commercial else RESIDENTIAL_IMAGES

        post.setdefault("image_url", image_pool[index % len(image_pool)])
        post.setdefault("inline_image_url", image_pool[(index + 1) % len(image_pool)])
        post.setdefault("sidebar_image_url", image_pool[(index + 2) % len(image_pool)])
        post.setdefault("faq", [])
        post.setdefault("keywords", [])
        post.setdefault("facebook_post", "")
        post.setdefault("linkedin_post", "")
        post.setdefault("x_post", "")
        post.setdefault("author", AUTHOR)
        post.setdefault("reading_time", estimate_reading_time(post.get("content", "")))

        if not post.get("filename"):
            date_key = post.get("date_key") or datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
            post["filename"] = f"{date_key}-{slugify(post.get('title', 'real-estate-article'))}.html"

        post["link"] = f"{SITE_URL}/posts/{post['filename']}"

        normalized.append(post)

    return normalized


def write_article_page(post):
    faq_html = build_faq_html(post)
    schema_json = build_schema_json(post)
    keyword_string = ", ".join(str(k) for k in post.get("keywords", [])[:12])
    share_url = escape_attr(post["link"])
    share_title = escape_attr(post["title"])

    category_class = "commercial" if "Commercial" in post.get("category", "") else "residential"

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_attr(post["title"])}</title>
  <meta name="description" content="{escape_attr(post["description"])}">
  <meta name="keywords" content="{escape_attr(keyword_string)}">
  <meta name="author" content="Dan Marovich">

  <meta property="og:title" content="{escape_attr(post["title"])}">
  <meta property="og:description" content="{escape_attr(post["description"])}">
  <meta property="og:image" content="{escape_attr(post["image_url"])}">
  <meta property="og:url" content="{share_url}">
  <meta property="og:type" content="article">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape_attr(post["title"])}">
  <meta name="twitter:description" content="{escape_attr(post["description"])}">
  <meta name="twitter:image" content="{escape_attr(post["image_url"])}">

  <script type="application/ld+json">
{schema_json}
  </script>

  <style>
    :root {{
      --navy: #061b36;
      --red: #b5121b;
      --gold: #c7a45a;
      --light: #f5f7fb;
      --white: #ffffff;
      --text: #172033;
      --muted: #667085;
      --border: #e4e8f0;
      --shadow: 0 18px 45px rgba(15,23,42,.14);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--light);
      color: var(--text);
      line-height: 1.7;
    }}

    a {{ color: var(--red); font-weight: 800; }}

    .topbar {{
      background: #030d1b;
      color: #cbd7e8;
      padding: 14px 6%;
      font-size: .92rem;
      display: flex;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
    }}

    .topbar a {{ color: #f0dba1; text-decoration: none; }}

    .hero {{
      background:
        linear-gradient(90deg, rgba(6,27,54,.95), rgba(6,27,54,.60)),
        url('{escape_attr(post["image_url"])}') center/cover;
      color: white;
      padding: 98px 6%;
    }}

    .hero-inner {{ max-width: 1160px; margin: auto; }}

    .eyebrow {{
      color: #f0dba1;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 2px;
      font-size: .85rem;
      margin-bottom: 14px;
    }}

    h1 {{
      font-size: clamp(2.2rem, 5vw, 4.9rem);
      line-height: 1.02;
      margin: 0;
      max-width: 1060px;
      letter-spacing: -1px;
    }}

    .meta {{ margin-top: 18px; color: #dbe6f3; font-weight: 700; }}

    .sharebar {{ margin-top: 24px; display: flex; flex-wrap: wrap; gap: 10px; }}

    .sharebar a,
    .sharebar button {{
      background: rgba(255,255,255,.14);
      border: 1px solid rgba(255,255,255,.24);
      color: white;
      border-radius: 999px;
      padding: 10px 14px;
      text-decoration: none;
      font-weight: 800;
      cursor: pointer;
      font: inherit;
    }}

    main {{ max-width: 1160px; margin: -46px auto 0; padding: 0 6% 80px; }}

    article {{
      background: white;
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
      border: 1px solid var(--border);
    }}

    .featured {{ width: 100%; height: 410px; object-fit: cover; display: block; }}

    .content-wrap {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 300px;
      gap: 34px;
      padding: 46px;
    }}

    .summary {{
      font-size: 1.2rem;
      color: #344054;
      border-left: 6px solid var(--red);
      padding-left: 20px;
      margin: 0 0 32px;
      font-weight: 700;
    }}

    .article-body h2 {{ color: var(--navy); font-size: 1.95rem; line-height: 1.15; margin-top: 36px; }}
    .article-body h3 {{ color: var(--navy); margin-top: 24px; }}
    .article-body p, .article-body li {{ color: #344054; }}
    .article-body ul {{ padding-left: 24px; }}
    .article-body li {{ margin-bottom: 8px; }}

    .article-image {{
      margin: 34px 0;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 14px 32px rgba(15,23,42,.12);
    }}

    .article-image img {{ width: 100%; height: 320px; object-fit: cover; display: block; }}
    .article-image figcaption {{ font-size: .9rem; color: var(--muted); padding: 12px 16px; background: #f8fafc; }}

    .info-box {{
      margin: 34px 0;
      background: #f5f7fb;
      border: 1px solid var(--border);
      border-left: 6px solid var(--gold);
      border-radius: 18px;
      padding: 24px;
    }}

    .info-box h2 {{ margin-top: 0; font-size: 1.55rem; }}

    .sidebar {{ align-self: start; display: grid; gap: 18px; position: sticky; top: 20px; }}

    .side-card {{
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 22px;
      background: #f8fafc;
    }}

    .side-card.dark {{ background: var(--navy); color: white; border: 0; }}
    .side-card.dark p {{ color: #dbe6f3; }}
    .side-card h3 {{ margin-top: 0; color: var(--navy); }}
    .side-card.dark h3 {{ color: white; }}
    .side-card img {{ width: 100%; height: 165px; object-fit: cover; border-radius: 14px; margin-bottom: 14px; }}

    .contact-list {{ list-style: none; padding: 0; margin: 0; }}
    .contact-list li {{ margin-bottom: 8px; color: inherit; }}
    .contact-list a {{ color: #f0dba1; text-decoration: none; }}

    .faq {{
      margin-top: 42px;
      background: #f8fafc;
      border-radius: 20px;
      padding: 28px;
      border: 1px solid var(--border);
    }}

    .faq h2 {{ margin-top: 0; }}
    .faq-item {{ border-top: 1px solid var(--border); padding-top: 18px; margin-top: 18px; }}
    .faq-item h3 {{ margin: 0 0 8px; color: var(--navy); }}

    .cta {{
      margin-top: 42px;
      background: linear-gradient(135deg, var(--red), var(--navy));
      color: white;
      border-radius: 20px;
      padding: 32px;
    }}

    .cta h2 {{ color: white; margin-top: 0; }}
    .cta p {{ color: #e4edf8; margin-bottom: 18px; }}

    .btn {{
      display: inline-block;
      background: white;
      color: var(--navy);
      padding: 14px 20px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 900;
      text-transform: uppercase;
      font-size: .9rem;
      margin-right: 8px;
      margin-bottom: 8px;
    }}

    .btn-red {{ background: var(--red); color: white; }}

    footer {{ text-align: center; padding: 36px 6%; color: var(--muted); }}
    footer a {{ color: var(--red); text-decoration: none; }}

    @media (max-width: 900px) {{
      .content-wrap {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; }}
    }}

    @media (max-width: 760px) {{
      .content-wrap {{ padding: 28px; }}
      .featured, .article-image img {{ height: 240px; }}
      .topbar {{ display: block; }}
    }}
  </style>
</head>
<body>
  <div class="topbar">
    <div>Dan Marovich · RE/MAX Ace Realty</div>
    <div><a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> · <a href="{MAIN_WEBSITE}">DMSellsRE.com</a></div>
  </div>

  <section class="hero">
    <div class="hero-inner">
      <div class="eyebrow">{escape_html(post["category"])}</div>
      <h1>{escape_html(post["title"])}</h1>
      <div class="meta">By {escape_html(post["author"])} · {display_date(post["date"])} · {escape_html(str(post.get("reading_time", "5")))} min read</div>
      <div class="sharebar">
        <a href="https://www.facebook.com/sharer/sharer.php?u={share_url}" target="_blank" rel="noopener">Share on Facebook</a>
        <a href="https://www.linkedin.com/sharing/share-offsite/?url={share_url}" target="_blank" rel="noopener">Share on LinkedIn</a>
        <a href="https://twitter.com/intent/tweet?url={share_url}&text={share_title}" target="_blank" rel="noopener">Share on X</a>
        <button onclick="window.print()">Print Article</button>
      </div>
    </div>
  </section>

  <main>
    <article>
      <img class="featured" src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}">

      <div class="content-wrap">
        <div class="article-body">
          <p class="summary">{escape_html(post["description"])}</p>

          {post["content"]}

          <figure class="article-image">
            <img src="{escape_attr(post["inline_image_url"])}" alt="Real estate planning in Southeastern Pennsylvania">
            <figcaption>Thoughtful real estate planning helps buyers, sellers, landlords, business owners, and investors make better decisions.</figcaption>
          </figure>

          <div class="info-box">
            <h2>Local Real Estate Guidance Matters</h2>
            <p>Real estate decisions are rarely one-size-fits-all. Property condition, location, timing, financing, lease terms, management needs, and long-term goals can all influence the right strategy. A local conversation can help clarify the next best step.</p>
          </div>

          {faq_html}

          <div class="cta">
            <h2>Ready to Talk Real Estate?</h2>
            <p>Whether you are buying, selling, renting, leasing, investing, or exploring property management, Dan Marovich can help you understand your options in Southeastern Pennsylvania.</p>
            <a class="btn" href="{MAIN_WEBSITE}/contact">Contact Dan</a>
          </div>
        </div>

        <aside class="sidebar">
          <div class="side-card dark">
            <h3>Contact Dan Marovich</h3>
            <p>RE/MAX Ace Realty</p>
            <ul class="contact-list">
              <li><strong>Email:</strong> <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></li>
              <li><strong>Website:</strong> <a href="{MAIN_WEBSITE}">DMSellsRE.com</a></li>
            </ul>
          </div>

          <div class="side-card">
            <img src="{escape_attr(post["sidebar_image_url"])}" alt="Real estate services">
            <h3>Real Estate Services</h3>
            <p>Residential, commercial, leasing, investment properties, new construction, land, and property management support across Southeastern Pennsylvania.</p>
          </div>

          <div class="side-card">
            <h3>Helpful Next Step</h3>
            <p>Have a question about this topic? Start with a quick conversation about your goals, timing, and property needs.</p>
            <a class="btn btn-red" href="{MAIN_WEBSITE}/contact">Ask Dan</a>
          </div>
        </aside>
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


def build_faq_html(post):
    faq_items = post.get("faq", [])

    if not faq_items:
        faq_items = [
            {
                "question": "When should I speak with a real estate professional?",
                "answer": "It is helpful to speak with a real estate professional early so you can understand timing, pricing, preparation, financing, leasing, or investment considerations before making a major decision.",
            },
            {
                "question": "Does local market knowledge matter?",
                "answer": "Yes. Local pricing, property condition, taxes, demand, inventory, lease terms, and neighborhood trends can all affect real estate strategy.",
            },
            {
                "question": "How can I get started?",
                "answer": f"You can contact Dan Marovich at {CONTACT_EMAIL} to discuss your goals and the best next step.",
            },
        ]

    html_parts = ['<section class="faq"><h2>Frequently Asked Questions</h2>']

    for item in faq_items[:4]:
        question = escape_html(item.get("question", "Real estate question"))
        answer = escape_html(item.get("answer", "Contact Dan Marovich to discuss your options."))
        html_parts.append(f'<div class="faq-item"><h3>{question}</h3><p>{answer}</p></div>')

    html_parts.append("</section>")
    return "\n".join(html_parts)


def build_schema_json(post):
    faq_entities = []

    for item in post.get("faq", [])[:4]:
        faq_entities.append(
            {
                "@type": "Question",
                "name": str(item.get("question", "")),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": str(item.get("answer", "")),
                },
            }
        )

    schema = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.get("title", ""),
        "description": post.get("description", ""),
        "image": post.get("image_url", ""),
        "datePublished": post.get("date", ""),
        "dateModified": post.get("date", ""),
        "author": {
            "@type": "Person",
            "name": "Dan Marovich",
        },
        "publisher": {
            "@type": "Organization",
            "name": "RE/MAX Ace Realty",
        },
        "mainEntityOfPage": post.get("link", ""),
    }

    if faq_entities:
        schema["mainEntity"] = faq_entities

    return json.dumps(schema, indent=2)


def write_index(posts):
    posts = sorted(posts, key=lambda p: p.get("date", ""), reverse=True)

    featured_html = ""
    cards = ""

    if posts:
        featured = posts[0]
        featured_class = "commercial" if "Commercial" in featured.get("category", "") else "residential"
        featured_html = f"""
        <section class="featured-post">
          <a class="featured-image" href="posts/{escape_attr(featured["filename"])}">
            <img src="{escape_attr(featured["image_url"])}" alt="{escape_attr(featured["title"])}">
          </a>
          <div class="featured-body">
            <div class="topline">
              <span class="date">{display_date(featured["date"])}</span>
              <span class="badge {featured_class}">{escape_html(featured["category"].replace(" Real Estate", ""))}</span>
            </div>
            <h2><a href="posts/{escape_attr(featured["filename"])}">{escape_html(featured["title"])}</a></h2>
            <p>{escape_html(featured["description"])}</p>
            <div class="card-meta">{escape_html(str(featured.get("reading_time", "5")))} min read · By Dan Marovich · RE/MAX Ace Realty</div>
            <a class="read {featured_class}" href="posts/{escape_attr(featured["filename"])}">Read Featured Article →</a>
          </div>
        </section>
"""

    for post in posts[1:]:
        category_class = "commercial" if "Commercial" in post.get("category", "") else "residential"
        cards += f"""
        <article class="card">
          <a class="image-link" href="posts/{escape_attr(post["filename"])}">
            <img src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}">
          </a>
          <div class="body">
            <div class="topline">
              <span class="date">{display_date(post["date"])}</span>
              <span class="badge {category_class}">{escape_html(post["category"].replace(" Real Estate", ""))}</span>
            </div>
            <h2><a href="posts/{escape_attr(post["filename"])}">{escape_html(post["title"])}</a></h2>
            <p>{escape_html(post["description"])}</p>
            <div class="card-meta">{escape_html(str(post.get("reading_time", "5")))} min read · By Dan Marovich · RE/MAX Ace Realty</div>
            <a class="read {category_class}" href="posts/{escape_attr(post["filename"])}">Continue Reading →</a>
          </div>
        </article>
"""

    if not posts:
        cards = """
        <div class="empty">
          <h2>Articles Coming Soon</h2>
          <p>Residential articles are scheduled for Mondays and commercial articles are scheduled for Fridays.</p>
        </div>
"""

    social_rows = ""
    for post in posts[:4]:
        if post.get("facebook_post") or post.get("linkedin_post") or post.get("x_post"):
            social_rows += f"""
            <div class="social-card">
              <h3>{escape_html(post["title"])}</h3>
              <p><strong>Facebook:</strong> {escape_html(post.get("facebook_post", ""))}</p>
              <p><strong>LinkedIn:</strong> {escape_html(post.get("linkedin_post", ""))}</p>
              <p><strong>X:</strong> {escape_html(post.get("x_post", ""))}</p>
            </div>
"""

    if not social_rows:
        social_rows = """
            <div class="social-card">
              <h3>Social Media Drafts</h3>
              <p>New articles will automatically include Facebook, LinkedIn, and X post drafts going forward.</p>
            </div>
"""

    index = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Real Estate Blog</title>
  <meta name="description" content="Residential and commercial real estate insights from Dan Marovich, RE/MAX Ace Realty.">
  <style>
    :root {{
      --navy: #061b36;
      --red: #b5121b;
      --gold: #c7a45a;
      --light: #f7f9fc;
      --text: #172033;
      --muted: #667085;
      --border: #e4e8f0;
      --shadow: 0 16px 38px rgba(15,23,42,.10);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: white;
      color: var(--text);
      line-height: 1.6;
    }}

    header {{
      padding: 44px 6% 18px;
      background: white;
    }}

    .header-inner {{
      max-width: 1180px;
      margin: 0 auto;
    }}

    h1 {{
      margin: 0;
      color: var(--navy);
      font-size: clamp(2.1rem, 4vw, 3.8rem);
      line-height: 1;
      letter-spacing: -1px;
    }}

    main {{
      padding: 28px 6% 70px;
      max-width: 1180px;
      margin: auto;
    }}

    .featured-post {{
      display: grid;
      grid-template-columns: 52% 1fr;
      gap: 34px;
      align-items: center;
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 24px;
      margin-bottom: 42px;
      box-shadow: var(--shadow);
    }}

    .featured-image {{
      display: block;
      border-radius: 18px;
      overflow: hidden;
      background: #eef2f7;
    }}

    .featured-image img {{
      width: 100%;
      height: 390px;
      object-fit: cover;
      display: block;
    }}

    .featured-body h2 {{
      margin: 0 0 14px;
      font-size: clamp(2rem, 3.6vw, 3.2rem);
      line-height: 1.04;
      color: var(--navy);
    }}

    .grid {{
      display: grid;
      gap: 34px;
    }}

    .card {{
      display: grid;
      grid-template-columns: 40% 1fr;
      gap: 34px;
      align-items: center;
      padding: 0 0 34px;
      border-bottom: 1px solid var(--border);
    }}

    .image-link {{
      display: block;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: var(--shadow);
      background: #eef2f7;
    }}

    .card img {{
      width: 100%;
      height: 310px;
      object-fit: cover;
      display: block;
      transition: transform .25s ease;
    }}

    .card:hover img,
    .featured-post:hover img {{
      transform: scale(1.03);
    }}

    .body {{
      padding: 8px 0;
    }}

    .topline {{
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: .95rem;
    }}

    .badge {{
      display: inline-block;
      color: white;
      border-radius: 6px;
      padding: 5px 10px;
      font-size: .78rem;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: .4px;
    }}

    .badge.commercial, .read.commercial {{
      background: var(--navy);
    }}

    .badge.residential, .read.residential {{
      background: var(--red);
    }}

    h2 {{
      margin: 0 0 14px;
      font-size: clamp(1.65rem, 3vw, 2.65rem);
      line-height: 1.08;
      color: var(--navy);
    }}

    h2 a {{
      color: inherit;
      text-decoration: none;
    }}

    p {{
      margin: 0 0 16px;
      font-size: 1.08rem;
      color: #344054;
    }}

    .card-meta {{
      color: var(--muted);
      font-size: .95rem;
      margin: 16px 0 20px;
    }}

    .read {{
      display: inline-block;
      color: white;
      text-decoration: none;
      border-radius: 8px;
      padding: 13px 18px;
      font-weight: 900;
    }}

    .marketing-tools {{
      margin-top: 50px;
      background: var(--light);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 28px;
    }}

    .marketing-tools h2 {{
      margin-top: 0;
      font-size: 2rem;
    }}

    .social-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 18px;
    }}

    .social-card {{
      background: white;
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 20px;
    }}

    .social-card h3 {{
      margin-top: 0;
      color: var(--navy);
    }}

    .social-card p {{
      font-size: .96rem;
    }}

    .empty {{
      background: var(--light);
      border-radius: 20px;
      padding: 32px;
      border: 1px solid var(--border);
    }}

    @media (max-width: 900px) {{
      .featured-post,
      .card {{
        grid-template-columns: 1fr;
        gap: 18px;
      }}

      .featured-image img,
      .card img {{
        height: 270px;
      }}

      .social-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <h1>Real Estate Blog</h1>
    </div>
  </header>

  <main>
    {featured_html}

    <div class="grid">
      {cards}
    </div>

    <section class="marketing-tools">
      <h2>Social Media Post Drafts</h2>
      <p>These draft posts are automatically generated with new articles and can be copied into Facebook, LinkedIn, or X.</p>
      <div class="social-grid">
        {social_rows}
      </div>
    </section>
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
    add_text(channel, "description", "Residential and commercial real estate articles from Dan Marovich, RE/MAX Ace Realty.")
    add_text(channel, "language", "en-us")
    add_text(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc), usegmt=True))

    for post in posts:
        item = ET.SubElement(channel, "item")
        category_label = post.get("category", "Real Estate")
        read_time = str(post.get("reading_time", estimate_reading_time(post.get("content", ""))))
        clean_description = build_feed_preview(post)

        add_text(item, "title", post["title"])
        add_text(item, "link", post["link"])

        guid = add_text(item, "guid", post["link"])
        guid.set("isPermaLink", "false")

        add_text(item, "pubDate", format_datetime(datetime.fromisoformat(post["date"]), usegmt=True))
        add_text(item, "category", category_label)
        add_text(item, "description", clean_description)

        content_text = f"""
{post["title"]}

{clean_description}

Category: {category_label}
Estimated reading time: {read_time} minutes

Read the complete article:
{post["link"]}

Contact Dan Marovich, RE/MAX Ace Realty:
Email: {CONTACT_EMAIL}
Website: {MAIN_WEBSITE}
"""

        content_node = ET.SubElement(item, "content:encoded")
        content_node.text = f"__CDATA_START__{content_text}__CDATA_END__"

    rough = ET.tostring(rss, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
    pretty = pretty.replace("__CDATA_START__", "<![CDATA[")
    pretty = pretty.replace("__CDATA_END__", "]]>")

    with open(FEED_FILE, "w", encoding="utf-8") as file:
        file.write(pretty)


def build_feed_preview(post):
    category = post.get("category", "Real Estate")
    description = strip_html(post.get("description", ""))
    content_text = strip_html(post.get("content", ""))

    if len(description) < 120 and content_text:
        extra = content_text[:260].strip()
        description = f"{description} {extra}".strip()

    description = re.sub(r"\s+", " ", description).strip()

    if len(description) > 420:
        description = description[:417].rsplit(" ", 1)[0] + "..."

    if "Commercial" in category:
        lead = "Commercial Real Estate Insight:"
    elif "Residential" in category:
        lead = "Residential Real Estate Insight:"
    else:
        lead = "Real Estate Insight:"

    return (
        f"{lead} {description} "
        f"Click Continue Reading for the full article with photos, local guidance, key takeaways, and next steps from Dan Marovich."
    )


def strip_html(value):
    text = str(value or "")
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def estimate_reading_time(content):
    text = re.sub(r"<[^>]+>", " ", str(content or ""))
    words = len(re.findall(r"\w+", text))
    minutes = max(3, math.ceil(words / 225))
    return minutes


if __name__ == "__main__":
    main()

