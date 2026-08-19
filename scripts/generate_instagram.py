#!/usr/bin/env python3
from __future__ import annotations

import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
TOPICS_FILE = ROOT / "instagram_topics.json"
STATE_FILE = ROOT / "instagram" / "state.json"
OUTPUT_ROOT = ROOT / "instagram"
W, H, FOOTER_TOP = 1080, 1350, 1230
NAVY=(6,27,54); BLUE=(19,66,134); RED=(190,24,35); WHITE=(255,255,255)
LIGHT=(244,247,251); LIGHT_BLUE=(231,239,250); GRAY=(60,67,75); BORDER=(210,215,220); GREEN=(44,135,80)
FONT_REGULAR="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

def get_font(size,bold=False): return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR,size)
def clean_text(v): return re.sub(r"\s+"," ",str(v or "")).strip()
def words(v,n): return " ".join(clean_text(v).split()[:n])
def text_width(d,t,f):
    b=d.textbbox((0,0),t,font=f); return b[2]-b[0]

def wrap_pixels(d,text,font,max_width):
    out=[]; cur=""
    for word in clean_text(text).split():
        test=word if not cur else cur+" "+word
        if text_width(d,test,font)<=max_width: cur=test
        else:
            if cur: out.append(cur)
            cur=word
    if cur: out.append(cur)
    return out or [""]

def fit_text(d,text,max_width,max_height,max_font,min_font=18,bold=False,line_gap=8,max_lines=None):
    for size in range(max_font,min_font-1,-1):
        f=get_font(size,bold); ls=wrap_pixels(d,text,f,max_width); lh=size+line_gap
        if (not max_lines or len(ls)<=max_lines) and len(ls)*lh<=max_height and all(text_width(d,x,f)<=max_width for x in ls):
            return f,ls,lh
    raise RuntimeError(f"Unsafe text layout blocked: {clean_text(text)}")

def draw_text_box(d,box,text,fill,max_font,min_font=18,bold=False,line_gap=8,max_lines=None,align="left",valign="top"):
    l,t,r,b=box; f,ls,lh=fit_text(d,text,r-l,b-t,max_font,min_font,bold,line_gap,max_lines)
    total=len(ls)*lh; y=t if valign=="top" else t+max(0,((b-t)-total)/2)
    for line in ls:
        w=text_width(d,line,f)
        x=l if align=="left" else (r-w if align=="right" else l+((r-l)-w)/2)
        d.text((x,y),line,font=f,fill=fill); y+=lh
    return y

def draw_centered_text(d,box,text,fill,max_font,min_font=18,bold=False,max_lines=3):
    return draw_text_box(d,box,text,fill,max_font,min_font,bold,6,max_lines,"center","center")

def canvas(): return Image.new("RGB",(W,H),WHITE)
def save(im,path): im.save(path,"JPEG",quality=94,optimize=True)

def footer(d):
    d.rectangle((0,FOOTER_TOP,W,H),fill=NAVY)
    d.text((48,FOOTER_TOP+25),"RE/MAX ACE REALTY",font=get_font(24,True),fill=WHITE)
    d.text((48,FOOTER_TOP+61),"COMMERCIAL DIVISION",font=get_font(21),fill=WHITE)
    site="dmsellscre.com"; f=get_font(24,True); w=text_width(d,site,f)
    d.text((W-48-w,FOOTER_TOP+44),site,font=f,fill=WHITE)

def header(d,n,title):
    d.rounded_rectangle((42,40,120,118),radius=14,fill=NAVY)
    draw_centered_text(d,(42,40,120,118),str(n),WHITE,38,28,True,1)
    # Keep every slide header on one line; shrink instead of spilling into content.
    draw_text_box(d,(150,42,1010,112),words(title,6).upper(),NAVY,36,20,True,4,1)
    d.rectangle((150,132,270,140),fill=RED)

def clean_json(text):
    text=re.sub(r"^```json\s*|^```\s*|\s*```$","",text.strip(),flags=re.I)
    return json.loads(text)

def state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {"last_index":-1,"last_lesson":7}

def prompt(lesson,topic):
    return f'''Create Commercial Investor Academy Lesson {lesson} about: {topic}.
Audience: commercial real estate investors, landlords, building owners, and business owners in Chester County and Montgomery County, Pennsylvania.
Return ONLY valid JSON with these exact keys: lesson_title, subtitle, definition, included_title, included_items, expenses_title, expense_items, not_included_title, not_included_items, local_example_title, local_example_intro, local_example_rows, why_title, why_items, caption, hashtags, engagement_question.
STRICT GRAPHIC LIMITS — never exceed them:
lesson_title max 6 words; subtitle max 10 words; definition max 36 words.
included_title, expenses_title, not_included_title, local_example_title, why_title max 5 words each.
included_items exactly 5, max 8 words each; expense_items exactly 5, max 8 words each; not_included_items exactly 4, max 8 words each.
local_example_intro max 18 words. local_example_rows exactly 3 objects with label and value; label max 5 words and value max 5 words. Keep each label and value separate; never combine multiple fields with pipes or semicolons.
why_items exactly 4, max 9 words each. engagement_question max 18 words.
caption approximately 700-1100 characters with natural CTA to dmsellscre.com/investors. hashtags exactly 15.
Use short, plain slide copy. No invented market statistics, property values, vacancy rates, rents, cap rates, or loan terms. Keep claims evergreen.'''

def generate(lesson,topic):
    r=OpenAI().responses.create(model=os.getenv("OPENAI_MODEL","gpt-5-mini"),input=prompt(lesson,topic))
    data=clean_json(r.output_text)
    # Hard caps protect the layout even if the model ignores instructions.
    data["lesson_title"]=words(data.get("lesson_title"),6)
    data["subtitle"]=words(data.get("subtitle"),10)
    data["definition"]=words(data.get("definition"),36)
    for k in ("included_title","expenses_title","not_included_title","local_example_title","why_title"):
        data[k]=words(data.get(k),5)
    data["local_example_intro"]=words(data.get("local_example_intro"),18)
    data["engagement_question"]=words(data.get("engagement_question"),18)
    for k,count,limit in (("included_items",5,8),("expense_items",5,8),("not_included_items",4,8),("why_items",4,9)):
        vals=list(data.get(k,[]))[:count]
        if len(vals)!=count: raise RuntimeError(f"{k} must contain exactly {count} items")
        data[k]=[words(x,limit) for x in vals]
    rows=list(data.get("local_example_rows",[]))[:3]
    if len(rows)!=3: raise RuntimeError("local_example_rows must contain exactly 3 rows")
    data["local_example_rows"]=[{"label":words(x.get("label"),5),"value":words(x.get("value"),5)} for x in rows]
    return data

def cover(lesson,data,path):
    im=canvas(); d=ImageDraw.Draw(im); d.rectangle((0,0,W,H),fill=NAVY); d.rectangle((0,820,W,FOOTER_TOP),fill=BLUE)
    d.rounded_rectangle((55,55,1025,145),radius=16,fill=WHITE)
    draw_centered_text(d,(75,65,1005,135),"COMMERCIAL INVESTOR ACADEMY",NAVY,38,28,True,1)
    d.rounded_rectangle((65,205,330,295),radius=16,fill=RED)
    draw_centered_text(d,(75,215,320,285),f"LESSON {lesson}",WHITE,36,26,True,1)
    draw_text_box(d,(65,345,1015,585),data["lesson_title"].upper(),WHITE,62,34,True,10,3)
    d.rectangle((65,610,225,619),fill=RED)
    draw_text_box(d,(65,650,1015,790),data["subtitle"],WHITE,32,23,False,8,3)
    buildings=[(75,1025,170,1190),(190,930,295,1190),(315,1000,415,1190),(440,870,560,1190),(585,960,685,1190),(710,905,825,1190),(850,1010,970,1190)]
    for x1,y1,x2,y2 in buildings:
        d.rounded_rectangle((x1,y1,x2,y2),radius=6,fill=(215,224,238))
        for wx in range(x1+16,x2-10,31):
            for wy in range(y1+22,y2-25,42): d.rectangle((wx,wy,wx+12,wy+19),fill=BLUE)
    footer(d); save(im,path)

def definition(data,path):
    im=canvas(); d=ImageDraw.Draw(im); header(d,2,"What Is It?")
    d.ellipse((425,190,655,420),fill=NAVY); draw_centered_text(d,(440,205,640,405),"$",WHITE,105,80,True,1)
    draw_text_box(d,(90,480,990,790),data["definition"],GRAY,34,24,False,10,7)
    d.rounded_rectangle((90,845,990,1165),radius=24,fill=LIGHT_BLUE)
    draw_text_box(d,(130,885,950,935),"INVESTOR TAKEAWAY",NAVY,26,22,True,5,1)
    draw_text_box(d,(130,970,950,1115),data["subtitle"],RED,28,21,True,8,3)
    footer(d); save(im,path)

def listslide(n,title,items,path,positive=True):
    im=canvas(); d=ImageDraw.Draw(im); header(d,n,title); items=list(items)
    top,bottom,gap=185,1185,18; ch=int((bottom-top-gap*(len(items)-1))/len(items)); y=top
    color=GREEN if positive else RED; symbol="✓" if positive else "×"
    for item in items:
        b=y+ch; d.rounded_rectangle((75,y,1005,b),radius=22,fill=LIGHT,outline=BORDER,width=2)
        cy=y+(ch-66)/2; d.ellipse((105,cy,171,cy+66),fill=color); draw_centered_text(d,(105,cy,171,cy+66),symbol,WHITE,38,27,True,1)
        draw_text_box(d,(205,y+24,960,b-20),item,GRAY,33,22,False,8,3,valign="center"); y=b+gap
    footer(d); save(im,path)

def example(data,path):
    im=canvas(); d=ImageDraw.Draw(im); header(d,6,data["local_example_title"])
    draw_text_box(d,(80,175,1000,305),data["local_example_intro"],GRAY,30,22,False,8,3)
    rows=data["local_example_rows"]; y=345; rh=240; gap=25
    for i,row in enumerate(rows):
        total=i==len(rows)-1; fill=NAVY if total else LIGHT; tf=WHITE if total else GRAY; vf=WHITE if total else RED
        d.rounded_rectangle((80,y,1000,y+rh),radius=20,fill=fill,outline=NAVY,width=2)
        # Stack label and value vertically. This removes the collision risk entirely.
        draw_text_box(d,(120,y+35,960,y+105),row["label"],tf,29,21,True,6,2)
        draw_text_box(d,(120,y+125,960,y+205),row["value"],vf,34,22,True,6,2)
        y+=rh+gap
    footer(d); save(im,path)

def why(data,path):
    im=canvas(); d=ImageDraw.Draw(im); header(d,7,data["why_title"]); y=185
    for item in data["why_items"]:
        d.rounded_rectangle((75,y,1005,y+150),radius=20,fill=LIGHT,outline=BORDER,width=2)
        d.ellipse((105,y+42,170,y+107),fill=NAVY); draw_centered_text(d,(105,y+42,170,y+107),"✓",WHITE,35,26,True,1)
        draw_text_box(d,(205,y+22,960,y+128),item,GRAY,30,21,False,8,3,valign="center"); y+=168
    d.rounded_rectangle((75,900,1005,1175),radius=24,fill=LIGHT_BLUE)
    draw_text_box(d,(115,935,965,980),"LOCAL INVESTOR QUESTION",NAVY,25,21,True,5,1)
    draw_text_box(d,(115,1005,965,1135),data["engagement_question"],GRAY,28,21,False,8,4)
    footer(d); save(im,path)

def write_lesson_files(lesson,topic,data,folder,update_latest):
    repo=os.getenv("GITHUB_REPOSITORY","danmanrealestate/Blog"); owner,name=repo.split("/",1); base=f"https://{owner}.github.io/{name}"
    urls=[f"{base}/instagram/lesson-{lesson:03d}/slide{i}.jpg" for i in range(1,8)]
    caption=data["caption"].rstrip()+"\n\n"+" ".join(data["hashtags"])
    manifest={"lesson":lesson,"topic":topic,"created_at":datetime.now(timezone.utc).isoformat(),"caption":caption,"engagement_question":data["engagement_question"],"files":[{"photo":u} for u in urls]}
    (folder/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8"); (folder/"caption.txt").write_text(caption,encoding="utf-8")
    if update_latest: (OUTPUT_ROOT/"latest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

def create_slides(lesson,topic,data,folder):
    folder.mkdir(parents=True,exist_ok=True)
    cover(lesson,data,folder/"slide1.jpg"); definition(data,folder/"slide2.jpg")
    listslide(3,data["included_title"],data["included_items"],folder/"slide3.jpg",True)
    listslide(4,data["expenses_title"],data["expense_items"],folder/"slide4.jpg",True)
    listslide(5,data["not_included_title"],data["not_included_items"],folder/"slide5.jpg",False)
    example(data,folder/"slide6.jpg"); why(data,folder/"slide7.jpg")

def repair_lesson(n):
    folder=OUTPUT_ROOT/f"lesson-{n:03d}"; mf=folder/"manifest.json"
    if not mf.exists(): raise RuntimeError(f"Cannot repair Lesson {n}: manifest not found")
    topic=json.loads(mf.read_text(encoding="utf-8"))["topic"]; data=generate(n,topic); create_slides(n,topic,data,folder)
    manifest=write_lesson_files(n,topic,data,folder,False); print(json.dumps(manifest,indent=2))

def generate_next_lesson():
    topics=json.loads(TOPICS_FILE.read_text(encoding="utf-8")); st=state(); idx=(st["last_index"]+1)%len(topics); lesson=st["last_lesson"]+1; topic=topics[idx]
    data=generate(lesson,topic); folder=OUTPUT_ROOT/f"lesson-{lesson:03d}"; create_slides(lesson,topic,data,folder); manifest=write_lesson_files(lesson,topic,data,folder,True)
    STATE_FILE.parent.mkdir(parents=True,exist_ok=True); STATE_FILE.write_text(json.dumps({"last_index":idx,"last_lesson":lesson},indent=2),encoding="utf-8"); print(json.dumps(manifest,indent=2))

def main():
    repair=os.getenv("REGENERATE_LESSON")
    repair_lesson(int(repair)) if repair else generate_next_lesson()

if __name__=="__main__": main()
