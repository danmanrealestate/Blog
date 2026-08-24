#!/usr/bin/env python3
from __future__ import annotations

import base64, io, json, os, re
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
IG=ROOT/'instagram'; PUB=IG/'publish_state.json'
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

def topic_visual_profile(topic):
    t=topic.lower()
    if any(k in t for k in ('due diligence','inspection','condition')):
        return {
            'cover':'suburban multi-tenant commercial property being evaluated before purchase, visible roofline, parking lot and mechanical details',
            'motifs':['property inspection','roof and HVAC review','environmental site review','survey and title documents','parking and access review','investor walkthrough']}
    if any(k in t for k in ('tenant','lease','rent roll','vacancy')):
        return {
            'cover':'active neighborhood retail center with a mix of occupied storefronts and one visibly vacant suite',
            'motifs':['retail storefront tenant','professional office suite','lease documents on a desk','vacant commercial suite','mixed-use building','tenant interview or business space review']}
    if any(k in t for k in ('cap rate','noi','cash flow','expense','income')):
        return {
            'cover':'income-producing mixed-use commercial building with street-level retail and upper-floor offices',
            'motifs':['mixed-use property','small office building','retail center','operating expense documents','building systems expense item','occupied commercial asset']}
    if any(k in t for k in ('debt','dscr','loan','financ','interest','mortgage')):
        return {
            'cover':'well-maintained small commercial investment property photographed like a lender valuation image',
            'motifs':['commercial property exterior','loan documents and calculator','office building entrance','industrial flex building','bank underwriting desk without logos','investor reviewing financing documents']}
    if any(k in t for k in ('zoning','permit','use','municipal','code')):
        return {
            'cover':'walkable Pennsylvania commercial streetscape with mixed retail, office and adaptive-reuse buildings',
            'motifs':['commercial streetscape','storefront conversion','municipal planning documents','mixed-use building','parking and access','adaptive reuse property']}
    if any(k in t for k in ('industrial','warehouse','flex')):
        return {
            'cover':'clean suburban industrial flex building with loading area and office entrance',
            'motifs':['warehouse loading area','industrial flex exterior','interior warehouse aisle','office-to-warehouse connection','truck access and parking','industrial mechanical systems']}
    if any(k in t for k in ('multifamily','apartment')):
        return {
            'cover':'small professionally managed multifamily investment property in suburban Pennsylvania',
            'motifs':['apartment exterior','common area','parking layout','unit condition review','building systems','property management walkthrough']}
    return {
        'cover':'visually distinctive suburban Pennsylvania commercial property with strong architecture and investment appeal',
        'motifs':['retail property','office building','mixed-use property','industrial flex building','commercial interior','investor property review']}

def photo_prompt(topic,scene,variation):
    return f'''Photorealistic editorial commercial real estate photograph for an Instagram educational carousel.
Topic: {topic}.
Scene: {scene}.
Visual variation: {variation}.
Chester County / Montgomery County Pennsylvania suburban commercial real estate character; believable East Coast architecture; natural daylight; polished professional real estate photography; strong depth; realistic materials; no people as the focal subject; no logos; no readable signs; no text; no watermarks. Vertical composition with useful negative space for headline overlays. Make this image clearly different from the other carousel images in property type, camera angle, distance, or interior/exterior viewpoint. This is an illustrative scene, not a depiction of a specific property.'''

def make_photo(client,topic,scene,variation):
    try:
        r=client.images.generate(model=os.getenv('OPENAI_IMAGE_MODEL','gpt-image-1'),prompt=photo_prompt(topic,scene,variation),size='1024x1536',quality='medium')
        raw=base64.b64decode(r.data[0].b64_json)
        im=Image.open(io.BytesIO(raw)).convert('RGB')
        ratio=max(W/im.width,H/im.height); nw,nh=int(im.width*ratio),int(im.height*ratio)
        im=im.resize((nw,nh),Image.Resampling.LANCZOS)
        x=(nw-W)//2; y=(nh-H)//2
        return im.crop((x,y,x+W,y+H))
    except Exception as e:
        print('Image generation fallback:',e)
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
    d.rectangle((0,1218,W,H),fill=(3,15,31,225))
    d.text((45,1242),'COMMERCIAL INVESTOR ACADEMY',font=font(23,True),fill=WHITE)
    d.text((45,1278),'RE/MAX ACE REALTY • COMMERCIAL',font=font(18,True),fill=GRAY)
    site='dmsellscre.com'; f=font(21,True); d.text((W-45-width(d,site,f),1268),site,font=f,fill=WHITE)

def content_prompt(lesson,topic,profile):
    motifs=', '.join(profile['motifs'])
    return f'''Create an educational Instagram carousel for Commercial Investor Academy Lesson {lesson}: {topic}.
Audience: newer commercial real estate investors, landlords and business owners in Chester and Montgomery Counties, Pennsylvania.
Return ONLY JSON with keys: cover_hook, cover_subtitle, slides, caption, hashtags.
slides must contain exactly 6 objects, each with kicker, title, body, visual_scene.

CONTENT RULES:
- Preserve real educational value. Do not reduce the lesson to slogans.
- Each body should be 24-38 words and teach one concrete point, action, red flag, or decision rule.
- Each title maximum 7 words. Kicker maximum 4 words.
- Slide 2 should explain the core concept.
- Slides 3-5 should teach practical checks, examples, or risks.
- Slide 6 should provide a strong investor takeaway or local application.
- Slide 7 should be a question/CTA that still includes useful guidance, not merely "contact me."
- Avoid repeating the same fact across slides.
- No invented statistics, addresses, approvals, rent figures, cap rates, loan terms, or property-specific claims.

VISUAL RULES:
- visual_scene must be a distinct photorealistic commercial-real-estate scene that reinforces the slide's teaching point.
- Use a varied mix inspired by: {motifs}.
- Across the six scenes, vary exterior/interior, wide/close, occupied/vacant, property/document/detail views where appropriate.
- Never use the same building type and camera angle on every slide.

Cover_hook maximum 8 words and should create curiosity, tension, risk, or a question rather than repeat the lesson title.
Cover_subtitle maximum 13 words and should tell the viewer what they will learn.
Caption 800-1200 characters, expanding on the lesson with a natural CTA to dmsellscre.com/investors. Exactly 15 hashtags.'''

def generate_copy(client,lesson,topic,profile):
    r=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-5-mini'),input=content_prompt(lesson,topic,profile))
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
    client=OpenAI(); profile=topic_visual_profile(topic); a=generate_copy(client,lesson,topic,profile)

    cover_variations=[
        'dramatic three-quarter exterior, slightly low camera angle',
        'street-level editorial view with architectural depth',
        'wide establishing shot with strong foreground and sky',
        'closer architectural composition emphasizing building details',
    ]
    cover_scene=profile['cover']
    im=make_photo(client,topic,cover_scene,cover_variations[lesson%len(cover_variations)])
    overlay(im,lesson,'Commercial Investor Academy',words(a.get('cover_hook'),8),words(a.get('cover_subtitle'),13),145)
    im.save(folder/'slide1.jpg','JPEG',quality=94,optimize=True)

    variations=[
        'wide exterior establishing shot',
        'close architectural or building-system detail',
        'interior commercial-space perspective',
        'document or due-diligence detail with property context',
        'street-level or parking/access perspective',
        'elevated or angled summary view',
    ]
    for idx,s in enumerate(a['slides'],start=2):
        im=make_photo(client,topic,clean(s.get('visual_scene')),variations[idx-2])
        d=ImageDraw.Draw(im,'RGBA')
        body=words(s.get('body'),38)
        if idx%3==2:
            d.rectangle((0,0,W,535),fill=(3,15,31,205)); d.rectangle((0,1080,W,H),fill=(3,15,31,210))
            d.rounded_rectangle((48,45,160,100),radius=12,fill=(*RED,245)); draw_text(d,(65,57,145,92),str(idx),WHITE,25,20,True,1)
            draw_text(d,(55,135,990,185),words(s.get('kicker'),4).upper(),GOLD,25,19,True,2)
            y=draw_text(d,(55,205,1000,355),words(s.get('title'),7).upper(),WHITE,46,28,True,4)
            draw_text(d,(55,y+15,1000,510),body,GRAY,26,19,False,6)
        elif idx%3==0:
            d.rounded_rectangle((45,690,1035,1175),radius=30,fill=(3,15,31,220))
            d.rounded_rectangle((75,725,185,780),radius=12,fill=(*RED,245)); draw_text(d,(92,737,170,772),str(idx),WHITE,24,19,True,1)
            draw_text(d,(75,815,980,865),words(s.get('kicker'),4).upper(),GOLD,24,18,True,2)
            y=draw_text(d,(75,885,985,1020),words(s.get('title'),7).upper(),WHITE,43,27,True,4)
            draw_text(d,(75,y+12,980,1150),body,GRAY,25,18,False,6)
        else:
            d.rounded_rectangle((55,135,760,1115),radius=32,fill=(3,15,31,208))
            d.rounded_rectangle((85,175,195,230),radius=12,fill=(*RED,245)); draw_text(d,(102,187,180,222),str(idx),WHITE,24,19,True,1)
            draw_text(d,(85,285,710,340),words(s.get('kicker'),4).upper(),GOLD,24,18,True,2)
            y=draw_text(d,(85,370,710,570),words(s.get('title'),7).upper(),WHITE,43,27,True,5)
            draw_text(d,(85,y+25,710,900),body,GRAY,25,18,False,7)
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
    (folder/'enhanced_v3.json').write_text(json.dumps({'lesson':lesson,'visual_version':3,'topic':topic,'asset_version':version,'style':'photo-led-topic-specific','profile':profile},indent=2),encoding='utf-8')
    print(f'Refreshed Lesson {lesson} with topic-specific photo-led visual system v3: {version}')

if __name__=='__main__': main()
