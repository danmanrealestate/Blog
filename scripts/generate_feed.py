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
MAX_POSTS_IN_FEED = 75

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

RESIDENTIAL_IMAGES = [
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1592595896551-12b371d546d5?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=1800&q=80",
]

COMMERCIAL_IMAGES = [
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1800&q=80",
    "https://images.unsplash.com/photo-1554469384-e58fac16e23a?auto=format&fit=crop&w=1800&q=80",
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
        print(f"{category} post already exists for {today_key}. Rebuilding with Version 3 template.")
        rebuild_all()
        return

    topic = pick_next_topic(posts, category, topics)
    image_url = pick_image(posts, category, images)
    inline_image_url = pick_image(posts + [{"category": category}], category, images)

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
        "image_url": image_url,
        "inline_image_url": inline_image_url,
        "filename": filename,
        "link": post_url,
        "author": AUTHOR,
    }

    posts.append(post)
    save_posts(posts)
    rebuild_all()

    print(f"Created Version 3 article page: {post_url}")


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
Write an original, polished, professional, SEO-friendly real estate blog article for {SITE_NAME}.

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
  ]
}}

Article requirements:
- Title under 70 characters.
- Description between 140 and 160 characters.
- Content between 1200 and 1800 words.
- Use HTML formatting only inside content.
- Use <p>, <h2>, <h3>, <ul>, and <li> where helpful.
- Add one short "Key Takeaways" section in the content.
- Add one short "Local Market Perspective" section in the content.
- Make the article practical, attractive, and useful to real estate visitors.
- Do not invent exact market statistics, interest rates, sales numbers, tax rules, legal advice, or financial guarantees.
- Do not say the article was AI-generated.
- Use a professional but approachable tone.
- Include practical advice for buyers, sellers, renters, landlords, business owners, or investors depending on the topic.
- Include internal links naturally inside the article:
  <a href="{MAIN_WEBSITE}">DMSellsRE.com</a>
  <a href="{MAIN_WEBSITE}/contact">contact Dan Marovich</a>
- End the content with a natural call to contact Dan Marovich at {CONTACT_EMAIL}.
- FAQ must include 3 questions and answers.
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
        post.setdefault("faq", [])
        post.setdefault("author", AUTHOR)

        if not post.get("filename"):
            date_key = post.get("date_key") or datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d")
            post["filename"] = f"{date_key}-{slugify(post.get('title', 'real-estate-article'))}.html"

        post["link"] = f"{SITE_URL}/posts/{post['filename']}"

        normalized.append(post)

    return normalized


def write_article_page(post):
    faq_html = build_faq_html(post)
    schema_json = build_schema_json(post)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape_attr(post["title"])}</title>
  <meta name="description" content="{escape_attr(post["description"])}">
  <script type="application/ld+json">
{schema_json}
  </script>
  <style>
    :root {{
      --navy: #061b36;
      --blue: #0b3d75;
      --red: #b5121b;
      --gold: #c7a45a;
      --light: #f5f7fb;
      --white: #ffffff;
      --text: #172033;
      --muted: #667085;
      --border: #e4e8f0;
      --shadow: 0 18px 45px rgba(15,23,42,.14);
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

    .topbar a {{
      color: #f0dba1;
      text-decoration: none;
    }}

    .hero {{
      background:
        linear-gradient(90deg, rgba(6,27,54,.94), rgba(6,27,54,.58)),
        url('{escape_attr(post["image_url"])}') center/cover;
      color: white;
      padding: 96px 6%;
    }}

    .hero-inner {{
      max-width: 1120px;
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
      font-size: clamp(2.2rem, 5vw, 4.8rem);
      line-height: 1.02;
      margin: 0;
      max-width: 1040px;
      letter-spacing: -1px;
    }}

    .meta {{
      margin-top: 18px;
      color: #dbe6f3;
      font-weight: 700;
    }}

    main {{
      max-width: 1120px;
      margin: -46px auto 0;
      padding: 0 6% 78px;
    }}

    article {{
      background: white;
      border-radius: 24px;
      box-shadow: var(--shadow);
      overflow: hidden;
      border: 1px solid var(--border);
    }}

    .featured {{
      width: 100%;
      height: 390px;
      object-fit: cover;
      display: block;
    }}

    .content {{
      padding: 46px;
    }}

    .summary {{
      font-size: 1.2rem;
      color: #344054;
      border-left: 6px solid var(--red);
      padding-left: 20px;
      margin-bottom: 32px;
      font-weight: 700;
    }}

    .article-image {{
      margin: 34px 0;
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 14px 32px rgba(15,23,42,.12);
    }}

    .article-image img {{
      width: 100%;
      height: 320px;
      object-fit: cover;
      display: block;
    }}

    .article-image figcaption {{
      font-size: .9rem;
      color: var(--muted);
      padding: 12px 16px;
      background: #f8fafc;
    }}

    h2 {{
      color: var(--navy);
      font-size: 1.95rem;
      line-height: 1.15;
      margin-top: 36px;
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

    .info-box {{
      margin: 34px 0;
      background: #f5f7fb;
      border: 1px solid var(--border);
      border-left: 6px solid var(--gold);
      border-radius: 18px;
      padding: 24px;
    }}

    .info-box h2 {{
      margin-top: 0;
      font-size: 1.55rem;
    }}

    .faq {{
      margin-top: 42px;
      background: #f8fafc;
      border-radius: 20px;
      padding: 28px;
      border: 1px solid var(--border);
    }}

    .faq h2 {{
      margin-top: 0;
    }}

    .faq-item {{
      border-top: 1px solid var(--border);
      padding-top: 18px;
      margin-top: 18px;
    }}

    .faq-item h3 {{
      margin: 0 0 8px;
    }}

    .cta {{
      margin-top: 42px;
      background: linear-gradient(135deg, var(--red), var(--navy));
      color: white;
      border-radius: 20px;
      padding: 32px;
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
      padding: 14px 20px;
      border-radius: 999px;
      text-decoration: none;
      font-weight: 900;
      text-transform: uppercase;
      font-size: .9rem;
    }}

    footer {{
      text-align: center;
      padding: 36px 6%;
      color: var(--muted);
    }}

    footer a {{
      color: var(--red);
      text-decoration: none;
    }}

    @media (max-width: 760px) {{
      .content {{
        padding: 28px;
      }}

      .featured,
      .article-image img {{
        height: 240px;
      }}

      .topbar {{
        display: block;
      }}
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
      <div class="meta">By {escape_html(post["author"])} · {display_date(post["date"])}</div>
    </div>
  </section>

  <main>
    <article>
      <img class="featured" src="{escape_attr(post["image_url"])}" alt="{escape_attr(post["title"])}">
      <div class="content">
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
      background:
        linear-gradient(135deg, rgba(6,27,54,.96), rgba(181,18,27,.88));
      color: white;
      padding: 76px 6%;
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
      padding: 54px 6%;
      max-width: 1220px;
      margin: auto;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 28px;
    }}

    .card {{
      background: white;
      border-radius: 22px;
      overflow: hidden;
      box-shadow: 0 14px 35px rgba(15,23,42,.11);
      border: 1px solid #e4e8f0;
    }}

    .card img {{
      width: 100%;
      height: 270px;
      object-fit: cover;
      display: block;
    }}

    .body {{
      padding: 28px;
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
