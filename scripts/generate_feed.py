
import os, json, re, requests
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
 "https://images.unsplash.com/photo-1592595896551-12b371d546d5?auto=format&fit=crop&w=1600&q=80"
]
COMMERCIAL_IMAGES = [
 "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&q=80",
 "https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1600&q=80",
 "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1600&q=80",
 "https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=1600&q=80"
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
    if post_type not in ("residential","commercial"):
        raise ValueError("POST_TYPE must be auto, residential, or commercial.")
    posts = load_posts()
    category = "Residential Real Estate" if post_type == "residential" else "Commercial Real Estate"
    topics = RESIDENTIAL_TOPICS if post_type == "residential" else COMMERCIAL_TOPICS
    images = RESIDENTIAL_IMAGES if post_type == "residential" else COMMERCIAL_IMAGES
    today_key = local_now.strftime("%Y-%m-%d")
    if any(p.get("date_key")==today_key and p.get("category")==category for p in posts):
        print("Post already exists today. Rebuilding.")
        rebuild_all(); return
    topic = pick_next_topic(posts, category, topics)
    image_url = images[len([p for p in posts if p.get("category")==category]) % len(images)]
    article = generate_article(category, topic, local_now)
    slug = f"{today_key}-{slugify(article['title'])}"
    filename = f"{slug}.html"
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
        "link": f"{SITE_URL}/posts/{filename}",
        "author": AUTHOR
    }
    posts.append(post)
    save_posts(posts)
    rebuild_all()
    print(f"Created full article page: {post['link']}")

def load_posts():
    if not os.path.exists(POSTS_FILE): return []
    with open(POSTS_FILE,"r",encoding="utf-8") as f: return json.load(f)

def save_posts(posts):
    with open(POSTS_FILE,"w",encoding="utf-8") as f: json.dump(posts,f,indent=2,ensure_ascii=False)

def pick_next_topic(posts, category, topics):
    used = [p.get("topic") for p in posts if p.get("category")==category]
    for t in topics:
        if t not in used: return t
    return topics[len(used) % len(topics)]

def generate_article(category, topic, local_now):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: raise RuntimeError("Missing OPENAI_API_KEY repository secret.")
    prompt = f"""
Write an original, polished, SEO-friendly real estate blog article for {SITE_NAME}.

Category: {category}
Topic: {topic}
Date: {local_now.strftime('%B %d, %Y')}
Author: {AUTHOR}

Local markets to naturally reference when relevant:
Downingtown PA, Chester County PA, Montgomery County PA, Berks County PA, Lancaster County PA, Bucks County PA, Delaware County PA.

Return valid JSON only with these exact fields:
{{"title":"","description":"","content":""}}

Requirements:
- Title under 70 characters.
- Description between 140 and 160 characters.
- Content between 1000 and 1400 words.
- Use HTML formatting only inside content.
- Use <p>, <h2>, <h3>, and <ul><li>.
- Make it practical, helpful, and attractive for real estate visitors.
- Do not invent exact market statistics, interest rates, sales numbers, tax rules, or legal advice.
- Include internal links to <a href="{MAIN_WEBSITE}">DMSellsRE.com</a> and <a href="{MAIN_WEBSITE}/contact">contact Dan Marovich</a>.
- End with a contact line for Dan Marovich at {CONTACT_EMAIL}.
"""
    payload = {"model": OPENAI_MODEL, "input": prompt, "text":{"format":{"type":"json_object"}}}
    r = requests.post("https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type":"application/json"},
        json=payload, timeout=120)
    if r.status_code >= 400: raise RuntimeError(f"OpenAI API error {r.status_code}: {r.text}")
    data = r.json()
    text = data.get("output_text","")
    if not text:
        parts=[]
        for item in data.get("output",[]):
            for ci in item.get("content",[]):
                if "text" in ci: parts.append(ci["text"])
        text="".join(parts)
    if not text: raise RuntimeError("No OpenAI output text.")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = re.sub(r"^json", "", cleaned, flags=re.I).strip()
    return json.loads(cleaned)

def rebuild_all():
    posts = load_posts()
    os.makedirs(POSTS_DIR, exist_ok=True)
    for post in posts: write_article_page(post)
    write_index(posts)
    write_feed(posts)

def write_article_page(post):
    page = f\"\"\"<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(post['title'])}</title><meta name="description" content="{esc(post['description'])}">
<style>
:root{{--navy:#061b36;--red:#b5121b;--gold:#c7a45a;--light:#f5f7fb;--text:#172033;}}
*{{box-sizing:border-box}} body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:var(--light);color:var(--text);line-height:1.7}}
.hero{{background:linear-gradient(90deg,rgba(6,27,54,.90),rgba(6,27,54,.50)),url('{post['image_url']}') center/cover;color:white;padding:90px 6%}}
.hero-inner{{max-width:1050px;margin:auto}} .eyebrow{{color:#f0dba1;font-weight:900;text-transform:uppercase;letter-spacing:2px;font-size:.85rem;margin-bottom:14px}}
h1{{font-size:clamp(2.2rem,5vw,4.5rem);line-height:1.02;margin:0;max-width:950px}} .meta{{margin-top:18px;color:#dbe6f3;font-weight:700}}
main{{max-width:1050px;margin:-40px auto 0;padding:0 6% 70px}} article{{background:white;border-radius:24px;box-shadow:0 18px 45px rgba(15,23,42,.14);overflow:hidden}}
.featured{{width:100%;height:360px;object-fit:cover;display:block}} .content{{padding:42px}} .summary{{font-size:1.18rem;color:#344054;border-left:5px solid var(--red);padding-left:18px;margin-bottom:30px}}
h2{{color:var(--navy);font-size:1.9rem;line-height:1.15;margin-top:34px}} h3{{color:var(--navy);margin-top:24px}} p,li{{color:#344054}} a{{color:var(--red);font-weight:800}}
.cta{{margin-top:38px;background:linear-gradient(135deg,var(--red),var(--navy));color:white;border-radius:18px;padding:28px}} .cta p{{color:#e4edf8;margin:0 0 18px}}
.btn{{display:inline-block;background:white;color:var(--navy);padding:13px 18px;border-radius:999px;text-decoration:none;font-weight:900;text-transform:uppercase;font-size:.9rem}}
footer{{text-align:center;padding:34px 6%;color:#667085}} @media(max-width:760px){{.content{{padding:26px}}.featured{{height:240px}}}}
</style></head><body>
<section class="hero"><div class="hero-inner"><div class="eyebrow">{esc(post['category'])}</div><h1>{esc(post['title'])}</h1><div class="meta">By {esc(post['author'])} · {display_date(post['date'])}</div></div></section>
<main><article><img class="featured" src="{post['image_url']}" alt="{esc(post['title'])}"><div class="content"><p class="summary">{esc(post['description'])}</p>{post['content']}<div class="cta"><p>Thinking about buying, selling, leasing, investing, or managing property in Southeastern Pennsylvania?</p><a class="btn" href="{MAIN_WEBSITE}/contact">Contact Dan</a></div></div></article></main>
<footer>Dan Marovich · RE/MAX Ace Realty · <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a><br><a href="{MAIN_WEBSITE}">Visit DMSellsRE.com</a></footer>
</body></html>\"\"\"
    with open(os.path.join(POSTS_DIR,post["filename"]),"w",encoding="utf-8") as f: f.write(page)

def write_index(posts):
    posts = sorted(posts, key=lambda p:p.get("date",""), reverse=True)
    cards = ""
    for p in posts:
        cards += f\"\"\"<article class="card"><img src="{p['image_url']}" alt="{esc(p['title'])}"><div class="body"><div class="category">{esc(p['category'])}</div><h2><a href="posts/{p['filename']}">{esc(p['title'])}</a></h2><p>{esc(p['description'])}</p><a class="read" href="posts/{p['filename']}">Read Article →</a></div></article>\"\"\"
    if not cards: cards = "<p>No posts yet. New posts are scheduled Mondays and Fridays.</p>"
    html = f\"\"\"<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>DMSellsRE Real Estate Blog</title><style>
body{{margin:0;font-family:Arial,Helvetica,sans-serif;background:#f5f7fb;color:#172033;line-height:1.6}} header{{background:#061b36;color:white;padding:70px 6%;text-align:center}} header h1{{margin:0;font-size:clamp(2rem,4vw,4rem)}} header p{{color:#dbe6f3;max-width:800px;margin:14px auto 0}} main{{padding:50px 6%;max-width:1200px;margin:auto}} .grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:26px}} .card{{background:white;border-radius:20px;overflow:hidden;box-shadow:0 14px 35px rgba(15,23,42,.10)}} .card img{{width:100%;height:260px;object-fit:cover;display:block}} .body{{padding:26px}} .category{{color:#b5121b;text-transform:uppercase;font-size:.8rem;letter-spacing:1px;font-weight:900}} h2{{margin:8px 0 10px;line-height:1.15}} a{{color:#061b36;text-decoration:none}} .read{{color:#b5121b;font-weight:900;text-transform:uppercase;font-size:.9rem}} @media(max-width:800px){{.grid{{grid-template-columns:1fr}}}}</style></head><body><header><h1>DMSellsRE Real Estate Blog</h1><p>Residential, commercial, leasing, property management, and investment real estate insights from Dan Marovich.</p></header><main><div class="grid">{cards}</div></main></body></html>\"\"\"
    with open("index.html","w",encoding="utf-8") as f: f.write(html)

def write_feed(posts):
    posts = sorted(posts, key=lambda p:p.get("date",""), reverse=True)[:MAX_POSTS_IN_FEED]
    rss = ET.Element("rss", {"version":"2.0","xmlns:content":"http://purl.org/rss/1.0/modules/content/"})
    ch = ET.SubElement(rss,"channel")
    add(ch,"title",SITE_NAME); add(ch,"link",SITE_URL+"/"); add(ch,"description","Residential, commercial, leasing, property management, and investment real estate insights from Dan Marovich.")
    add(ch,"language","en-us"); add(ch,"lastBuildDate",format_datetime(datetime.now(timezone.utc), usegmt=True))
    for p in posts:
        it=ET.SubElement(ch,"item")
        add(it,"title",p["title"]); add(it,"link",p["link"]); g=add(it,"guid",p["link"]); g.set("isPermaLink","false")
        add(it,"pubDate",format_datetime(datetime.fromisoformat(p["date"]), usegmt=True)); add(it,"category",p["category"])
        add(it,"description",p["description"])
        enc=ET.SubElement(it,"enclosure"); enc.set("url",p["image_url"]); enc.set("type","image/jpeg")
        content = f\"\"\"<![CDATA[<img src="{p['image_url']}" alt="{esc(p['title'])}" style="width:100%;max-width:900px;height:auto;" /><p><strong>{esc(p['description'])}</strong></p>{p['content']}<p><strong>Contact Dan Marovich, RE/MAX Ace Realty:</strong> <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a></p><p><a href="{p['link']}">Read the full article</a></p>]]>\"\"\"
        ce=ET.SubElement(it,"content:encoded"); ce.text=content
    rough=ET.tostring(rss,encoding="utf-8")
    pretty=minidom.parseString(rough).toprettyxml(indent="  ",encoding="UTF-8").decode("utf-8")
    pretty=pretty.replace("&lt;![CDATA[","<![CDATA[").replace("]]&gt;","]]>")
    with open(FEED_FILE,"w",encoding="utf-8") as f: f.write(pretty)

def add(parent, tag, text):
    n=ET.SubElement(parent,tag); n.text=str(text); return n
def slugify(text):
    s=text.lower().replace("&"," and "); s=re.sub(r"[^a-z0-9]+","-",s); s=re.sub(r"^-+|-+$","",s); return s[:80] or "real-estate-article"
def esc(v):
    return str(v or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")
def display_date(v):
    try: return datetime.fromisoformat(v).strftime("%B %d, %Y")
    except Exception: return ""
if __name__ == "__main__": main()

