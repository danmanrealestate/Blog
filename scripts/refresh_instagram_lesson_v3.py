#!/usr/bin/env python3
from __future__ import annotations

import base64, io, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

ROOT=Path(__file__).resolve().parents[1]
IG=ROOT/'instagram'; PUB=IG/'publish_state.json'; TOPICS=ROOT/'instagram_topics.json'
W,H=1080,1350
NAVY=(6,27,54); RED=(190,24,35); GOLD=(218,163,43); WHITE=(255,255,255); GRAY=(225,230,236)
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'; FR='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'

def font(sz,b=False): return ImageFont.truetype(FB if b else FR,sz)
def clean(x): return re.sub(r'\s+',' ',str(x or '')).strip()
def words(x,n): return ' '.join(clean(x).split()[:n])
def width(d,t,f): return d.textbbox((0,0),t,font=f)[2]
def wrap(d,t,f,mw):
    out=[]; cur=''
    for w in clean(t).split():
        test=w if not cur else cur+' '+w
        if width(d,test,f)<=mw: cur=test
        else:
            if cur: out.append(cur)
            cur=w
    if cur: out.append(cur)
    return out

def draw_text(d,rect,text,color,max_size,min_size=20,bold=False,max_lines=5):
    l,t,r,b=rect
    for s in range(max_size,min_size-1,-1):
        f=font(s,bold); lines=wrap(d,text,f,r-l); lh=s+8
        if len(lines)<=max_lines and len(lines)*lh<=b-t: break
    y=t
    for line in lines:
        d.text((l,y),line,font=f,fill=color); y+=lh
    return y

def photo_prompt(topic,scene):
    return f'''Photorealistic editorial commercial real estate photograph for an Instagram educational carousel. Topic: {topic}. Scene: {scene}. Chester County Pennsylvania suburban commercial real estate feel, believable architecture, natural daylight, professional real estate photography, strong depth, visually interesting, no people as the focal subject, no logos, no readable signs, no text, no watermarks. Vertical composition with useful negative space for headline overlays. This is an illustrative scene, not a depiction of a specific property.'''

def make_photo(client,topic,scene):
    try:
        r=client.images.generate(model=os.getenv('OPENAI_IMAGE_MODEL','gpt-image-1'),prompt=photo_prompt(topic,scene),size='1024x1536',quality='medium')
        raw=base64.b64decode(r.data[0].b64_json)
        im=Image.open(io.BytesIO(raw)).convert('RGB')
        # cover-crop to 1080x1350
        ratio=max(W/im.width,H/im.height); nw,nh=int(im.width*ratio),int(im.height*ratio)
        im=im.resize((nw,nh),Image.Resampling.LANCZOS)
        x=(nw-W)//2; y=(nh-H)//2
        return im.crop((x,y,x+W,y+H))
    except Exception as e:
        print('Image generation fallback:',e)
        # Fallback is intentionally visually different from old template.
        im=Image.new('RGB',(W,H),(28,38,50)); d=ImageDraw.Draw(im)
        for y in range(H):
            shade=int(28+35*y/H); d.line((0,y,W,y),fill=(shade,shade+8,shade+18))
        for i in range(7):
            x=40+i*155; bh=280+(i%4)*90
            d.rectangle((x,760-bh,x+125,1120),fill=(55+i*7,69+i*5,82+i*4))
            for wy in range(800-bh,1080,55):
                for wx in range(x+18,x+110,36): d.rectangle((wx,wy,wx+16,wy+24),fill=(190,168,105))
        return im

def overlay(im,lesson,kicker,title,subtitle='',dark=155):
    d=ImageDraw.Draw(im,'RGBA')
    d.rectangle((0,0,W,H),fill=(3,15,31,dark))
    d.rounded_rectangle((48,48,235,112),radius=14,fill=(*RED,245))
    draw_text(d,(66,62,220,104),f'LESSON {lesson}',WHITE,25,20,True,1)
    draw_text(d,(55,185,1015,250),kicker.upper(),GOLD,30,22,True,2)
    y=draw_text(d,(55,275,1015,650),title.upper(),WHITE,64,34,True,5)
    if subtitle: draw_text(d,(58,y+25,1000,min(y+180,910)),subtitle,GRAY,29,21,False,4)
    # compact brand footer
    d.rectangle((0,1218,W,H),fill=(3,15,31,225))
    d.text((45,1242),'COMMERCIAL INVESTOR ACADEMY',font=font(23,True),fill=WHITE)
    d.text((45,1278),'RE/MAX ACE REALTY • COMMERCIAL',font=font(18,True),fill=GRAY)
    site='dmsellscre.com'; f=font(21,True); d.text((W-45-width(d,site,f),1268),site,font=f,fill=WHITE)

def content_prompt(lesson,topic):
    return f'''Create concise Instagram carousel copy for Commercial Investor Academy Lesson {lesson}: {topic}.
Audience: newer commercial real estate investors, landlords and business owners in Chester and Montgomery Counties, Pennsylvania.
Return ONLY JSON with keys: cover_hook, cover_subtitle, slides, caption, hashtags.
slides must contain exactly 6 objects, each with kicker, title, body, visual_scene. Body maximum 26 words. Title maximum 7 words. Kicker maximum 4 words. visual_scene should describe a distinct photorealistic commercial-real-estate image that visually explains that slide (inspection, storefront, lease documents on desk, roof/HVAC, parking/access, mixed-use building, warehouse, office, retail etc as appropriate). Vary property types and camera angles across slides. Slide 6 should be a strong takeaway/engagement CTA, not a generic summary. cover_hook maximum 8 words and should create curiosity, tension, risk, or a question rather than repeat the lesson title. cover_subtitle maximum 12 words. Caption 700-1000 characters with CTA to dmsellscre.com/investors. Exactly 15 hashtags. No invented statistics, addresses, zoning approvals, financial claims, or claims about specific properties.'''

def generate_copy(client,lesson,topic):
    r=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5-mini'),input=content_prompt(lesson,topic))
    txt=re.sub(r'^```json\s*|^```\s*|\s*```$','',r.output_text.strip(),flags=re.I)
    a=json.loads(txt); slides=list(a.get('slides',[]))
    if len(slides)!=6: raise RuntimeError('Expected exactly 6 content slides')
    return a

def main():
    requested=os.getenv('LESSON_NUMBER','').strip()
    if requested: lesson=int(requested)
    else:
        last=int(json.loads(PUB.read_text())['last_published_lesson']); lesson=last+1
    folder=IG/f'lesson-{lesson:03d}'; mf=folder/'manifest.json'
    if not mf.exists(): raise RuntimeError(f'Lesson {lesson} is not generated: {mf}')
    old=json.loads(mf.read_text()); topic=old.get('topic',f'Commercial real estate lesson {lesson}')
    client=OpenAI(); a=generate_copy(client,lesson,topic)

    # Cover: photo first, minimal copy, curiosity hook.
    cover_scene=f'eye-catching exterior of a well-maintained commercial investment property relevant to {topic}, dramatic three-quarter angle'
    im=make_photo(client,topic,cover_scene)
    overlay(im,lesson,'Commercial Investor Academy',words(a.get('cover_hook'),8),words(a.get('cover_subtitle'),12),145)
    im.save(folder/'slide1.jpg','JPEG',quality=94,optimize=True)

    for idx,s in enumerate(a['slides'],start=2):
        im=make_photo(client,topic,clean(s.get('visual_scene')))
        # alternate overlay density/placement by slide for visible variety
        d=ImageDraw.Draw(im,'RGBA')
        if idx%2==0:
            d.rectangle((0,0,W,520),fill=(3,15,31,205)); d.rectangle((0,1050,W,H),fill=(3,15,31,205))
            d.rounded_rectangle((48,45,160,100),radius=12,fill=(*RED,245)); draw_text(d,(65,57,145,92),str(idx),WHITE,25,20,True,1)
            draw_text(d,(55,135,990,185),words(s.get('kicker'),4).upper(),GOLD,25,19,True,2)
            y=draw_text(d,(55,205,1000,365),words(s.get('title'),7).upper(),WHITE,46,28,True,4)
            draw_text(d,(55,y+15,1000,500),words(s.get('body'),26),GRAY,27,20,False,4)
        else:
            d.rounded_rectangle((45,650,1035,1160),radius=30,fill=(3,15,31,218))
            d.rounded_rectangle((75,690,185,745),radius=12,fill=(*RED,245)); draw_text(d,(92,702,170,737),str(idx),WHITE,24,19,True,1)
            draw_text(d,(75,780,980,830),words(s.get('kicker'),4).upper(),GOLD,24,18,True,2)
            y=draw_text(d,(75,850,985,995),words(s.get('title'),7).upper(),WHITE,44,27,True,4)
            draw_text(d,(75,y+12,980,1125),words(s.get('body'),26),GRAY,26,19,False,4)
        d.rectangle((0,1218,W,H),fill=(3,15,31,230)); d.text((45,1245),'RE/MAX ACE REALTY • COMMERCIAL',font=font(19,True),fill=WHITE)
        site='dmsellscre.com'; ff=font(21,True); d.text((W-45-width(d,site,ff),1265),site,font=ff,fill=WHITE)
        im.save(folder/f'slide{idx}.jpg','JPEG',quality=94,optimize=True)

    stamp=datetime.now(timezone.utc); version=stamp.strftime('%Y%m%d%H%M%S')
    caption=clean(a.get('caption'))+'\n\n'+' '.join(a.get('hashtags',[]))
    old['caption']=caption; old['created_at']=stamp.isoformat()
    for item in old.get('files',[]):
        if isinstance(item,dict) and item.get('photo'):
            item['photo']=item['photo'].split('?',1)[0]+f'?v={version}'
    mf.write_text(json.dumps(old,indent=2),encoding='utf-8')
    (folder/'caption.txt').write_text(caption,encoding='utf-8')
    (folder/'enhanced_v3.json').write_text(json.dumps({'lesson':lesson,'visual_version':3,'topic':topic,'asset_version':version,'style':'photo-led'},indent=2),encoding='utf-8')
    print(f'Refreshed Lesson {lesson} with photo-led visual system v3: {version}')

if __name__=='__main__': main()
