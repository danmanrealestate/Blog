#!/usr/bin/env python3
from __future__ import annotations

import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
IG=ROOT/'instagram'; PUB=IG/'publish_state.json'
W,H=1080,1350
NAVY=(6,27,54); BLUE=(19,66,134); RED=(190,24,35); GOLD=(218,163,43); WHITE=(255,255,255)
LIGHT=(244,247,251); PALE=(231,239,250); GRAY=(60,67,75); GREEN=(44,135,80); ORANGE=(224,124,52)
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FR='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def f(sz,b=False): return ImageFont.truetype(FB if b else FR,sz)
def clean(v): return re.sub(r'\s+',' ',str(v or '')).strip()
def words(v,n): return ' '.join(clean(v).split()[:n])
def tw(d,t,ff):
    b=d.textbbox((0,0),t,font=ff); return b[2]-b[0]
def wrap(d,t,ff,mw):
    out=[]; cur=''
    for w in clean(t).split():
        x=w if not cur else cur+' '+w
        if tw(d,x,ff)<=mw: cur=x
        else:
            if cur: out.append(cur)
            cur=w
    if cur: out.append(cur)
    return out or ['']
def box(d,rect,t,color,maxs,mins=18,b=False,ml=5,align='left'):
    l,tp,r,bt=rect
    for s in range(maxs,mins-1,-1):
        ff=f(s,b); ls=wrap(d,t,ff,r-l); lh=s+8
        if len(ls)<=ml and len(ls)*lh<=bt-tp: break
    else: raise RuntimeError('Text will not fit: '+clean(t))
    y=tp
    for line in ls:
        x=l if align=='left' else (l+(r-l-tw(d,line,ff))/2)
        d.text((x,y),line,font=ff,fill=color); y+=lh
    return y

def footer(d):
    d.rectangle((0,1230,W,H),fill=(4,18,38)); d.text((45,1252),'RE/MAX ACE REALTY',font=f(24,1),fill=WHITE); d.text((45,1288),'COMMERCIAL DIVISION',font=f(20),fill=WHITE)
    site='dmsellscre.com'; ff=f(24,1); d.text((W-45-tw(d,site,ff),1275),site,font=ff,fill=WHITE)
def header(d,n,title,dark=False):
    bg=WHITE if dark else NAVY; fg=NAVY if dark else WHITE
    d.rounded_rectangle((45,40,125,120),radius=16,fill=bg); box(d,(45,52,125,110),str(n),fg,35,26,1,1,'center')
    box(d,(155,45,1015,118),words(title,6).upper(),fg,38,22,1,1); d.rectangle((155,132,290,141),fill=GOLD if dark else RED)
def prompt(lesson,topic):
    return f'''Create Commercial Investor Academy Lesson {lesson} about: {topic}.
Audience: commercial real estate investors, landlords, building owners, and business owners in Chester and Montgomery Counties, Pennsylvania.
Return ONLY JSON with exact keys: lesson_title, subtitle, definition, included_title, included_items, expenses_title, expense_items, not_included_title, not_included_items, local_example_title, local_example_intro, local_example_rows, why_title, why_items, caption, hashtags, engagement_question.
Keep slide copy short: lesson_title 6 words max; subtitle 10; definition 34. List titles 5 words max. included_items 5 items, expense_items 5, not_included_items 4, why_items 4; each item 8 words max. local_example_intro 16 words max. local_example_rows exactly 3 objects with label and value, each 5 words max. engagement_question 16 words max. Caption 700-1100 characters with CTA to dmsellscre.com/investors. Exactly 15 hashtags. No invented market statistics or property-specific financial claims.'''
def generate(lesson,topic):
    r=OpenAI().responses.create(model=os.getenv('OPENAI_MODEL','gpt-5-mini'),input=prompt(lesson,topic))
    txt=re.sub(r'^```json\s*|^```\s*|\s*```$','',r.output_text.strip(),flags=re.I); a=json.loads(txt)
    a['lesson_title']=words(a.get('lesson_title'),6); a['subtitle']=words(a.get('subtitle'),10); a['definition']=words(a.get('definition'),34)
    for k in ('included_title','expenses_title','not_included_title','local_example_title','why_title'): a[k]=words(a.get(k),5)
    for k,c in [('included_items',5),('expense_items',5),('not_included_items',4),('why_items',4)]:
        vals=list(a.get(k,[]))[:c]
        if len(vals)!=c: raise RuntimeError(f'{k} must have {c} items')
        a[k]=[words(x,8) for x in vals]
    rows=list(a.get('local_example_rows',[]))[:3]
    if len(rows)!=3: raise RuntimeError('local_example_rows must have 3 rows')
    a['local_example_rows']=[{'label':words(x.get('label'),5),'value':words(x.get('value'),5)} for x in rows]
    a['local_example_intro']=words(a.get('local_example_intro'),16); a['engagement_question']=words(a.get('engagement_question'),16)
    return a

def save(im,p): im.save(p,'JPEG',quality=95,optimize=True)
def cover(lesson,topic,a,p):
    # Strong social hook, varied by lesson
    mode=lesson%3; im=Image.new('RGB',(W,H),NAVY if mode!=1 else WHITE); d=ImageDraw.Draw(im)
    hook='BEFORE YOU BUY...' if 'due diligence' in topic.lower() else ('WHAT WOULD YOU CHECK FIRST?' if mode==1 else 'DON’T JUST LOOK AT THE PRICE.')
    if mode==0:
        d.rectangle((0,0,W,250),fill=BLUE); d.rounded_rectangle((55,55,310,135),radius=16,fill=RED); box(d,(75,72,290,125),f'LESSON {lesson}',WHITE,30,24,1,1)
        box(d,(55,300,1000,450),hook,WHITE,62,34,1,2); y=box(d,(55,500,1000,720),a['lesson_title'].upper(),GOLD,58,34,1,3); box(d,(55,y+20,990,y+130),a['subtitle'],WHITE,30,22,0,3)
        for i in range(5):
            yy=850+i*60; d.rounded_rectangle((90,yy,135,yy+45),radius=7,outline=WHITE,width=3); d.line((102,yy+24,115,yy+35),fill=GOLD,width=5); d.line((115,yy+35,130,yy+12),fill=GOLD,width=5); d.rounded_rectangle((165,yy+12,870,yy+25),radius=6,fill=(58,82,118))
    elif mode==1:
        d.rectangle((0,0,420,1230),fill=NAVY); d.rounded_rectangle((55,55,330,135),radius=18,fill=RED); box(d,(75,72,310,126),f'LESSON {lesson}',WHITE,30,24,1,1)
        box(d,(55,225,350,470),hook,GOLD,50,30,1,4); box(d,(465,90,1010,330),'COMMERCIAL INVESTOR ACADEMY',NAVY,34,24,1,3)
        y=box(d,(465,400,1010,700),a['lesson_title'].upper(),NAVY,52,30,1,4); d.rectangle((465,y+10,700,y+20),fill=RED); box(d,(465,y+50,1010,y+175),a['subtitle'],GRAY,28,20,0,4)
        for i,h in enumerate([130,210,170,260,190]): d.rounded_rectangle((495+i*100,910-h,560+i*100,910),radius=8,fill=[BLUE,GOLD,RED,GREEN,ORANGE][i])
    else:
        d.rectangle((0,0,W,300),fill=BLUE); box(d,(55,55,1020,130),'COMMERCIAL INVESTOR ACADEMY',WHITE,36,25,1,1); box(d,(55,160,1020,270),hook,GOLD,54,32,1,2)
        box(d,(65,365,1010,620),a['lesson_title'].upper(),WHITE,60,34,1,3); box(d,(65,680,1010,800),a['subtitle'],WHITE,30,22,0,3)
        d.text((65,885),'DEAL RISK',font=f(26,1),fill=WHITE)
        for i,c in enumerate([GREEN,GOLD,ORANGE,RED]): d.rounded_rectangle((65+i*235,940,255+i*235,1060),radius=18,fill=c)
        d.polygon([(780,915),(825,915),(802,945)],fill=WHITE)
    footer(d); save(im,p)
def slide2(lesson,a,p):
    im=Image.new('RGB',(W,H),WHITE); d=ImageDraw.Draw(im); header(d,2,'The Big Idea')
    if lesson%2:
        d.rounded_rectangle((75,205,1005,520),radius=32,fill=NAVY); box(d,(115,250,965,470),a['definition'],WHITE,38,25,1,6)
        d.text((90,600),'WHY IT MATTERS',font=f(28,1),fill=RED); box(d,(90,655,990,840),a['subtitle'],NAVY,38,25,1,4)
        d.rounded_rectangle((90,910,990,1130),radius=25,fill=PALE); box(d,(135,960,945,1080),'Think like an investor: verify first, assume less.',GRAY,31,23,1,3,'center')
    else:
        d.ellipse((90,220,420,550),fill=NAVY); d.text((205,300),'?',font=f(150,1),fill=GOLD)
        box(d,(485,230,990,570),a['definition'],GRAY,34,24,0,7)
        d.rectangle((75,660,1005,675),fill=RED); d.text((85,725),'INVESTOR TAKEAWAY',font=f(26,1),fill=NAVY); box(d,(85,790,990,1040),a['subtitle'],RED,39,24,1,5)
    footer(d); save(im,p)
def cards(n,title,items,p,accent):
    im=Image.new('RGB',(W,H),WHITE); d=ImageDraw.Draw(im); header(d,n,title)
    # Alternating magazine-style cards instead of identical rows
    y=195
    for i,it in enumerate(items):
        left=75 if i%2==0 else 255; right=825 if i%2==0 else 1005
        d.rounded_rectangle((left,y,right,y+155),radius=24,fill=PALE if i%2==0 else LIGHT,outline=accent,width=3)
        d.rounded_rectangle((left+18,y+30,left+88,y+100),radius=16,fill=accent); box(d,(left+18,y+45,left+88,y+90),str(i+1),WHITE,30,24,1,1,'center')
        box(d,(left+115,y+35,right-30,y+125),it,GRAY,31,22,1,3)
        y+=185
    footer(d); save(im,p)
def stop_slide(a,p):
    im=Image.new('RGB',(W,H),NAVY); d=ImageDraw.Draw(im); header(d,5,a['not_included_title'],True)
    d.text((70,190),'DON’T ASSUME.',font=f(56,1),fill=GOLD); d.text((70,260),'VERIFY.',font=f(56,1),fill=WHITE)
    y=395
    for it in a['not_included_items']:
        d.rounded_rectangle((80,y,1000,y+160),radius=24,fill=(20,48,84)); d.ellipse((110,y+45,180,y+115),fill=RED); box(d,(110,y+58,180,y+105),'×',WHITE,34,26,1,1,'center'); box(d,(215,y+40,950,y+125),it,WHITE,31,22,1,3); y+=190
    footer(d); save(im,p)
def example(a,p):
    im=Image.new('RGB',(W,H),WHITE); d=ImageDraw.Draw(im); header(d,6,a['local_example_title']); box(d,(75,175,1005,280),a['local_example_intro'],GRAY,30,22,0,3)
    colors=[BLUE,GOLD,NAVY]; y=345
    for i,r in enumerate(a['local_example_rows']):
        d.rounded_rectangle((80,y,1000,y+220),radius=28,fill=colors[i]); box(d,(120,y+38,900,y+95),r['label'].upper(),WHITE,25,20,1,2); box(d,(120,y+120,940,y+190),r['value'],WHITE,36,24,1,2); y+=260
    footer(d); save(im,p)
def final(a,p):
    im=Image.new('RGB',(W,H),NAVY); d=ImageDraw.Draw(im); header(d,7,a['why_title'],True)
    d.text((70,185),'WHY INVESTORS CARE',font=f(44,1),fill=GOLD); y=285
    for i,it in enumerate(a['why_items']):
        d.line((95,y+38,155,y+38),fill=[GOLD,RED,BLUE,GREEN][i],width=8); box(d,(185,y,980,y+105),it,WHITE,31,22,1,3); y+=145
    d.rounded_rectangle((65,900,1015,1165),radius=30,fill=WHITE); d.text((105,945),'YOUR TURN',font=f(27,1),fill=RED); box(d,(105,1000,970,1125),a['engagement_question'],NAVY,34,23,1,4)
    footer(d); save(im,p)
def main():
    if not PUB.exists(): raise RuntimeError('publish_state.json missing')
    last=int(json.loads(PUB.read_text())['last_published_lesson']); lesson=last+1; folder=IG/f'lesson-{lesson:03d}'; mf=folder/'manifest.json'
    if not mf.exists(): raise RuntimeError(f'Lesson {lesson} not generated')
    old=json.loads(mf.read_text()); topic=old['topic']; a=generate(lesson,topic)
    cover(lesson,topic,a,folder/'slide1.jpg'); slide2(lesson,a,folder/'slide2.jpg'); cards(3,a['included_title'],a['included_items'],folder/'slide3.jpg',GREEN); cards(4,a['expenses_title'],a['expense_items'],folder/'slide4.jpg',GOLD); stop_slide(a,folder/'slide5.jpg'); example(a,folder/'slide6.jpg'); final(a,folder/'slide7.jpg')
    caption=a['caption'].rstrip()+'\n\n'+' '.join(a['hashtags']); old['caption']=caption; old['engagement_question']=a['engagement_question']; old['created_at']=datetime.now(timezone.utc).isoformat(); mf.write_text(json.dumps(old,indent=2),encoding='utf-8'); (folder/'caption.txt').write_text(caption,encoding='utf-8'); (folder/'enhanced_v2.json').write_text(json.dumps({'lesson':lesson,'visual_version':2,'topic':topic},indent=2),encoding='utf-8')
    print(f'Refreshed Lesson {lesson} with varied visual layouts.')
if __name__=='__main__': main()
