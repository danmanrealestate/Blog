#!/usr/bin/env python3
from __future__ import annotations

import json, os, re, textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TOPICS_FILE = ROOT / "instagram_topics.json"
STATE_FILE = ROOT / "instagram" / "state.json"
OUTPUT_ROOT = ROOT / "instagram"

W, H = 1080, 1350
NAVY=(6,27,54); BLUE=(19,66,134); RED=(190,24,35); WHITE=(255,255,255)
LIGHT=(244,247,251); GRAY=(60,67,75); GREEN=(44,135,80)

def get_font(size:int,bold:bool=False):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(p,size)

F_TITLE=get_font(64,True); F_H1=get_font(54,True); F_H2=get_font(40,True)
F_BODY=get_font(34); F_BODY_B=get_font(34,True); F_SMALL=get_font(25); F_SMALL_B=get_font(25,True)

def lines(text:str,width:int):
    return textwrap.wrap(text,width=width,break_long_words=False)

def draw_wrap(d,xy,text,font,fill,width,gap=12):
    x,y=xy
    for line in lines(text,width):
        d.text((x,y),line,font=font,fill=fill)
        y += font.size+gap
    return y

def footer(d):
    d.rectangle((0,H-118,W,H),fill=NAVY)
    d.text((48,H-91),"RE/MAX ACE REALTY",font=F_SMALL_B,fill=WHITE)
    d.text((48,H-56),"COMMERCIAL DIVISION",font=F_SMALL,fill=WHITE)
    d.text((770,H-72),"dmsellscre.com",font=F_SMALL_B,fill=WHITE)

def header(d,n,title):
    d.rounded_rectangle((42,42,118,118),radius=12,fill=NAVY)
    d.text((66,53),str(n),font=F_H2,fill=WHITE)
    d.text((150,52),title.upper(),font=F_H2,fill=NAVY)
    d.rectangle((150,116,260,124),fill=RED)

def clean_json(text):
    text=re.sub(r"^```json\s*","",text.strip())
    text=re.sub(r"\s*```$","",text)
    return json.loads(text)

def state():
    return json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"last_index":-1,"last_lesson":7}

def prompt(lesson,topic):
    return f'''Create Commercial Investor Academy Lesson {lesson} about: {topic}.
Audience: commercial real estate investors, landlords, building owners, and business owners in Chester County and Montgomery County, Pennsylvania.
Return ONLY valid JSON with keys: lesson_title, subtitle, definition, included_title, included_items (5), expenses_title, expense_items (5), not_included_title, not_included_items (4), local_example_title, local_example_intro, local_example_rows (3 objects with label and value), why_title, why_items (4), caption (900-1400 characters with CTA to dmsellscre.com/investors), hashtags (15), engagement_question.
Keep claims evergreen. Do not invent market statistics.'''

def generate(lesson,topic):
    r=OpenAI().responses.create(
        model=os.getenv("OPENAI_MODEL","gpt-5-mini"),
        input=prompt(lesson,topic)
    )
    return clean_json(r.output_text)

def save(img,path):
    img.save(path,"JPEG",quality=94,optimize=True)

def canvas():
    return Image.new("RGB",(W,H),WHITE)

def cover(lesson,data,path):
    im=canvas()
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,H),fill=NAVY)
    d.rectangle((0,700,W,H),fill=BLUE)
    d.rectangle((55,58,1025,140),fill=WHITE)
    d.text((90,75),"COMMERCIAL INVESTOR ACADEMY",font=F_H2,fill=NAVY)
    d.rounded_rectangle((65,205,315,290),radius=14,fill=RED)
    d.text((95,220),f"LESSON {lesson}",font=F_H2,fill=WHITE)
    y=draw_wrap(d,(65,350),data["lesson_title"].upper(),F_TITLE,WHITE,22,14)
    d.rectangle((65,y+16,220,y+25),fill=RED)
    draw_wrap(d,(65,y+65),data["subtitle"],F_BODY,WHITE,38)
    for i,h in enumerate([210,320,250,390,285,350,230]):
        x=80+i*135
        d.rectangle((x,920-h,x+95,920),fill=(215,224,238))
        for wx in range(x+14,x+80,28):
            for wy in range(940-h,900,38):
                d.rectangle((wx,wy,wx+12,wy+18),fill=BLUE)
    footer(d)
    save(im,path)

def definition(data,path):
    im=canvas()
    d=ImageDraw.Draw(im)
    header(d,2,"What Is It?")
    d.ellipse((365,190,715,540),fill=NAVY)
    d.text((470,290),"$",font=get_font(130,True),fill=WHITE)
    draw_wrap(d,(95,620),data["definition"],F_BODY,GRAY,45,14)
    d.rounded_rectangle((95,960,985,1110),radius=24,fill=(231,239,250))
    d.text((135,1000),"Investor takeaway:",font=F_BODY_B,fill=NAVY)
    draw_wrap(d,(465,1000),data["subtitle"],F_SMALL_B,RED,36,9)
    footer(d)
    save(im,path)

def listslide(n,title,items,path,pos=True):
    im=canvas()
    d=ImageDraw.Draw(im)
    header(d,n,title)
    y=210
    c=GREEN if pos else RED
    s="✓" if pos else "×"
    for item in items:
        d.ellipse((85,y,145,y+60),fill=c)
        d.text((101,y+4),s,font=F_H2,fill=WHITE)
        d.text((185,y+8),item,font=F_BODY,fill=GRAY)
        d.line((185,y+72,960,y+72),fill=(210,215,220),width=2)
        y+=145
    footer(d)
    save(im,path)

def example(data,path):
    im=canvas()
    d=ImageDraw.Draw(im)
    header(d,6,data["local_example_title"])
    draw_wrap(d,(80,190),data["local_example_intro"],F_BODY,GRAY,46)
    y=410
    for i,row in enumerate(data["local_example_rows"]):
        fill=NAVY if i==2 else LIGHT
        tf=WHITE if i==2 else GRAY
        d.rounded_rectangle((80,y,1000,y+150),radius=18,fill=fill,outline=NAVY,width=3)
        d.text((125,y+50),row["label"],font=F_BODY_B,fill=tf)
        b=d.textbbox((0,0),row["value"],font=F_H2)
        d.text((950-(b[2]-b[0]),y+44),row["value"],font=F_H2,fill=WHITE if i==2 else RED)
        y+=180
    footer(d)
    save(im,path)

def why(data,path):
    im=canvas()
    d=ImageDraw.Draw(im)
    header(d,7,data["why_title"])
    y=210
    for item in data["why_items"]:
        d.ellipse((85,y,155,y+70),fill=NAVY)
        d.text((108,y+8),"✓",font=F_H2,fill=WHITE)
        draw_wrap(d,(195,y+8),item,F_BODY,GRAY,40)
        y+=160
    d.rounded_rectangle((75,930,1005,1135),radius=24,fill=(231,239,250))
    d.text((115,965),"LOCAL INVESTOR QUESTION",font=F_SMALL_B,fill=NAVY)
    draw_wrap(d,(115,1015),data["engagement_question"],F_SMALL,GRAY,62,8)
    footer(d)
    save(im,path)

def main():
    topics=json.loads(TOPICS_FILE.read_text())
    st=state()
    idx=(st["last_index"]+1)%len(topics)
    lesson=st["last_lesson"]+1

    data=generate(lesson,topics[idx])

    folder=OUTPUT_ROOT/f"lesson-{lesson:03d}"
    folder.mkdir(parents=True,exist_ok=True)

    cover(lesson,data,folder/"slide1.jpg")
    definition(data,folder/"slide2.jpg")
    listslide(3,data["included_title"],data["included_items"],folder/"slide3.jpg",True)
    listslide(4,data["expenses_title"],data["expense_items"],folder/"slide4.jpg",True)
    listslide(5,data["not_included_title"],data["not_included_items"],folder/"slide5.jpg",False)
    example(data,folder/"slide6.jpg")
    why(data,folder/"slide7.jpg")

    repo=os.getenv("GITHUB_REPOSITORY","danmanrealestate/Blog")
    owner,name=repo.split("/",1)
    base=f"https://{owner}.github.io/{name}"

    urls=[
        f"{base}/instagram/lesson-{lesson:03d}/slide{i}.jpg"
        for i in range(1,8)
    ]

    caption=data["caption"].rstrip()+"\n\n"+" ".join(data["hashtags"])

    manifest={
        "lesson":lesson,
        "topic":topics[idx],
        "created_at":datetime.now(timezone.utc).isoformat(),
        "caption":caption,
        "engagement_question":data["engagement_question"],

        # CHANGED FOR MAKE / INSTAGRAM
        "files":[
            {"photo":url}
            for url in urls
        ]
    }

    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2))
    (folder/"caption.txt").write_text(caption)
    (OUTPUT_ROOT/"latest.json").write_text(json.dumps(manifest,indent=2))

    STATE_FILE.parent.mkdir(parents=True,exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "last_index":idx,
        "last_lesson":lesson
    },indent=2))

    print(json.dumps(manifest,indent=2))

if __name__=="__main__":
    main()
