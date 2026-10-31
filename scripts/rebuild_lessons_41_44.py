#!/usr/bin/env python3
"""Rebuild lessons 41-44 as original, diagram-led educational carousels.
No external image API; every slide is deterministic and checked before publishing.
"""
import json, math, os, textwrap
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"instagram"
W,H=1080,1350
NAVY="#091B34"; DEEP="#061225"; BLUE="#12365B"; GOLD="#F6BD4F"; WHITE="#FFFFFF"; PALE="#DCEAF4"; MUTED="#9CB5CB"; RED="#F05A64"; GREEN="#64D6B1"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LESSONS={
41:("How Commercial Property Management Protects NOI",[
("YOUR NOI IS LEAKING","5 management mistakes quietly eat your returns","cover"),
("COLLECT EVERY DOLLAR","Late rent and missed escalations reduce cash flow.","collection"),
("WATCH THE EXPENSES","Track utilities, vendor contracts and recoverable CAM.","expenses"),
("MAINTAIN BEFORE FAILURE","A small repair today can prevent a costly shutdown.","maintenance"),
("READ THE LEASE","Know which expenses the tenant must reimburse.","lease"),
("MEASURE THE IMPACT","Illustrative: $12K recovered minus $4K costs = $8K NOI.","math"),
("THE INVESTOR CHECKLIST","Audit collections, CAM, vendors and maintenance monthly.","checklist")]),
42:("Value-Add Strategies for Neighborhood Retail",[
("CAN THIS RETAIL CENTER EARN MORE?","Improve the property without guessing at returns.","cover"),
("START WITH THE STOREFRONT","Lighting, signs and curb appeal influence first impressions.","storefront"),
("GET THE TENANT MIX RIGHT","Complementary businesses can increase repeat visits.","mix"),
("FIX WHAT TENANTS NOTICE","Access, parking, lighting and maintenance come first.","parking"),
("DON'T OVERSPEND","Compare renovation cost with realistic rent upside.","math"),
("TEST BEFORE YOU COMMIT","Verify demand, zoning and permits before major upgrades.","test"),
("VALUE-ADD CHECKLIST","Prioritize projects that improve occupancy and NOI.","checklist")]),
43:("How to Evaluate a Small Industrial or Flex Property",[
("WAREHOUSE DEAL OR MONEY PIT?","Six checks before buying industrial or flex space.","cover"),
("CHECK CLEAR HEIGHT","Usable vertical space affects storage and tenant fit.","height"),
("TRUCKS NEED TO TURN","Loading doors, access and circulation are critical.","truck"),
("POWER IS NOT OPTIONAL","Verify electrical capacity for the intended use.","power"),
("KNOW THE ALLOWED USE","Confirm zoning, parking and permitted operations.","zoning"),
("INSPECT THE BIG-TICKET ITEMS","Roof, HVAC, slabs and drainage can change the deal.","inspection"),
("THE FLEX PROPERTY TEST","Match building specs to actual tenant demand.","checklist")]),
44:("How to Read a Commercial Rent Roll",[
("IS THE RENT ROLL HIDING RISK?","What the tenant list reveals about cash flow.","cover"),
("START WITH THE BASICS","Compare suite, tenant, area, rent and lease dates.","rentroll"),
("SPOT THE VACANCY","Empty suites create a gap between potential and actual rent.","vacancy"),
("WATCH LEASE EXPIRATIONS","Multiple leases ending together increase rollover risk.","timeline"),
("VERIFY THE NUMBERS","Compare rent roll against leases and payment history.","verify"),
("DON'T MISS RECOVERIES","Check CAM, taxes, insurance and gross versus NNN terms.","expenses"),
("THE 5-POINT RENT ROLL AUDIT","Verify tenants, rent, expirations, collections and recoveries.","checklist")])
}

def font(size,bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,size)

def text(d,xy,msg,size=32,color=WHITE,bold=False,spacing=12,width=930):
    f=font(size,bold); words=str(msg).split(); lines=[]; line=""
    for word in words:
        test=(line+" "+word).strip()
        if d.textbbox((0,0),test,font=f)[2]>width and line:
            lines.append(line);line=word
        else:line=test
    if line:lines.append(line)
    x,y=xy
    for ln in lines:
        d.text((x,y),ln,font=f,fill=color,stroke_width=0)
        y+=size+spacing
    return y

def rect(d,xy,fill,outline=None,r=25,width=3):
    d.rounded_rectangle(xy,radius=r,fill=fill,outline=outline,width=width)

def line(d,pts,fill=GOLD,width=9):
    d.line(pts,fill=fill,width=width,joint="curve")

def building(d,x,y,scale=1,shop=False):
    w=int(510*scale);h=int(345*scale)
    rect(d,(x,y,x+w,y+h),BLUE,r=9)
    d.polygon([(x-18,y),(x+w+18,y),(x+w+5,y-28),(x-5,y-28)],fill=GOLD)
    if shop:
        for i in range(3):
            a=x+25+i*(w-50)//3
            rect(d,(a,y+90,a+(w-80)//3,y+h-28),"#D2E8F2",r=6)
            d.rectangle((a,y+90,a+(w-80)//3,y+110),fill=RED if i==1 else GOLD)
    else:
        for j in range(3):
            for i in range(4):
                a=x+34+i*(w-60)//4;b=y+35+j*(h-60)//3
                rect(d,(a,b,a+int(70*scale),b+int(60*scale)),"#A8D5E8",r=4)

def tag(d,x,y,label,color=GOLD):
    rect(d,(x,y,x+290,y+55),color,r=12)
    text(d,(x+17,y+11),label,23,NAVY,True,width=260)

def graphic(d,kind,lesson):
    # Central, large illustrations: actual instructional charts, diagrams and property drawings.
    if kind in ("cover","storefront","mix","parking","vacancy","zoning","inspection"):
        building(d,260,505,1.05,shop=(lesson in (42,44)))
        if kind=="vacancy":
            rect(d,(510,630,720,770),NAVY,r=6);text(d,(530,680),"VACANT",33,RED,True)
        if kind=="parking":
            for i in range(5):
                d.rectangle((220+i*135,970,310+i*135,1040),outline=WHITE,width=4)
        if kind=="inspection":
            d.ellipse((700,800,880,980),outline=GOLD,width=15);line(d,[(855,955),(960,1070)],GOLD,20)
    elif kind in ("collection","expenses","math"):
        items=([("SCHEDULED","$100K"),("COLLECTED","$94K"),("GAP","$6K")] if kind=="collection"
               else [("REVENUE","+ $12K"),("COST","- $4K"),("NOI IMPACT","+ $8K")] if kind=="math"
               else [("RENT","INCOME"),("CAM","RECOVERY"),("REPAIRS","COST")])
        for i,(a,b) in enumerate(items):
            y=530+i*165;rect(d,(145,y,935,y+125),BLUE,r=20)
            text(d,(180,y+26),a,34,PALE,True)
            text(d,(630,y+24),b,38,GOLD,True,width=270)
    elif kind in ("maintenance","height","truck","power"):
        building(d,160,575,.86,False)
        if kind=="height":
            line(d,[(770,580),(770,865)],GOLD,13)
            d.polygon([(770,558),(748,603),(792,603)],fill=GOLD)
            d.polygon([(770,889),(748,845),(792,845)],fill=GOLD)
            tag(d,630,920,"CLEAR HEIGHT")
        elif kind=="truck":
            rect(d,(510,900,900,1000),GOLD,r=10);rect(d,(780,835,900,930),PALE,r=10)
            for x in (590,830):d.ellipse((x,973,x+58,1031),fill=NAVY,outline=WHITE,width=7)
        elif kind=="power":
            line(d,[(765,580),(695,740),(790,740),(700,945)],GOLD,21)
        else:
            d.ellipse((700,730,920,950),outline=GOLD,width=13)
            line(d,[(730,900),(890,760)],GOLD,14)
    elif kind=="lease" or kind=="verify" or kind=="rentroll":
        rect(d,(115,505,965,1030),WHITE,r=18)
        for j,label in enumerate(["SUITE","TENANT","RENT","EXPIRES"]):
            x=145+j*202;text(d,(x,542),label,22,NAVY,True,width=190)
        for i in range(4):
            y=615+i*92
            d.line((140,y+60,930,y+60),fill="#D1DEE9",width=3)
            vals=[str(101+i),["Cafe","Salon","Office","Vacant"][i],["$2,400","$1,850","$3,100","—"][i],["2028","2027","2026","—"][i]]
            for j,v in enumerate(vals):text(d,(145+j*202,y),v,23,RED if v in ("Vacant","2026") else NAVY,j==0,width=185)
    elif kind=="timeline":
        line(d,[(145,800),(930,800)],GOLD,12)
        for i,(year,num) in enumerate([("2026","2 leases"),("2027","1 lease"),("2028","3 leases")]):
            x=200+i*340
            d.ellipse((x-17,783,x+17,817),fill=RED if i==2 else GREEN)
            text(d,(x-60,680),year,32,WHITE,True)
            text(d,(x-75,850),num,25,PALE)
    elif kind in ("checklist","test"):
        checks=(["COLLECTIONS","EXPENSES","LEASES","MAINTENANCE"] if lesson==41 else
                ["TENANT DEMAND","PERMITS","PROJECT COST","RENT UPSIDE"] if lesson==42 else
                ["ZONING","ACCESS","POWER","ROOF / HVAC"] if lesson==43 else
                ["TENANTS","RENT","EXPIRATIONS","PAYMENTS"])
        for i,v in enumerate(checks):
            y=530+i*145;rect(d,(160,y,920,y+104),BLUE,r=16)
            d.ellipse((192,y+29,239,y+76),fill=GREEN)
            text(d,(204,y+37),"✓",27,NAVY,True)
            text(d,(280,y+28),v,34,WHITE,True)
    else:
        building(d,230,550,1,True)

def render(n,idx,heading,sub,kind,topic):
    im=Image.new("RGB",(W,H),NAVY);d=ImageDraw.Draw(im)
    for y in range(H):
        q=y/H;d.line((0,y,W,y),fill=(int(7+9*q),int(24+21*q),int(47+30*q)))
    d.rectangle((0,0,W,17),fill=GOLD)
    tag(d,55,55,f"LESSON {n}  •  {idx}/7")
    title_y=text(d,(60,160),heading,61 if idx==1 else 53,WHITE,True,spacing=15,width=960)
    text(d,(65,title_y+22),sub,30,PALE,False,spacing=11,width=930)
    graphic(d,kind,n)
    d.rectangle((0,1170,W,H),fill=DEEP)
    d.rectangle((55,1192,105,1242),fill=GOLD)
    text(d,(125,1190),"COMMERCIAL INVESTOR ACADEMY",25,WHITE,True,width=900)
    text(d,(125,1237),"RE/MAX ACE REALTY  •  dmsellscre.com",22,MUTED,width=900)
    out=BASE/f"lesson-{n:03d}"/f"slide{idx}.jpg"
    im.save(out,quality=94,optimize=True)
    return out

def main():
    for n,(topic,slides) in LESSONS.items():
        folder=BASE/f"lesson-{n:03d}"
        mf=folder/"manifest.json"
        if not mf.exists():raise RuntimeError(f"Missing {mf}")
        manifest=json.loads(mf.read_text())
        if int(manifest.get("lesson",0))!=n:raise RuntimeError(f"Manifest mismatch for {n}")
        paths=[render(n,i,*slide,topic) for i,slide in enumerate(slides,1)]
        for p in paths:
            with Image.open(p) as im:
                if im.size!=(W,H):raise RuntimeError(f"Bad slide dimensions: {p}")
        stamp=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        manifest["files"]=[{"photo":f"https://danmanrealestate.github.io/Blog/instagram/lesson-{n:03d}/slide{i}.jpg?v={stamp}"} for i in range(1,8)]
        manifest["created_at"]=datetime.now(timezone.utc).isoformat()
        mf.write_text(json.dumps(manifest,indent=2)+"\n")
        (folder/"enhanced_v3.json").write_text(json.dumps({"lesson":n,"visual_version":4,"style":"illustrated-infographic","asset_version":stamp,"topic":topic},indent=2)+"\n")
        print(f"Rebuilt {n}: {topic} ({len(paths)} slides)")
if __name__=="__main__":main()
