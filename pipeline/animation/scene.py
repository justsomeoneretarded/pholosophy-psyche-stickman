"""Native-resolution procedural composition; all character limbs are connected."""
import math,textwrap
from functools import lru_cache
from PIL import Image,ImageDraw,ImageFont
from pipeline.animation.rig import pose,mix,ease,Pose,BONES
COLORS={'main':'#263343','friend':'#367e91','shadow':'#805868','future':'#ad802e'}
PALETTES={'reflective':('#f0eee7','#c5d8dc','#64899a'),'hopeful':('#f6f0de','#dedbbd','#b89740'),'tense':('#e7e6e9','#c5bdca','#a46465'),'sad':('#e2e8ee','#bdc9d7','#6b839e'),'playful':('#fff0df','#e0d2b9','#d09257')}
@lru_cache(maxsize=64)
def font(size):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',max(10,int(size)))

def actor_pose(scene,actor,t,world_width=2.5,world_height=None):
    world_height=world_height or world_width*9/16
    actions=sorted([a for a in scene.actions if a.actor==actor],key=lambda a:a.start)
    previous=None;last=None
    for a in actions:
        if t<a.start:break
        prop=next((p for p in scene.props if p.id==a.target),None)
        target=((prop.x-a.x)*world_width,(prop.y-.78)*world_height) if prop else None
        local=min(t-a.start,a.end-a.start)
        origin=a.x*world_width
        if a.action=='handshake' and len(scene.characters)>1:
            partner=next(c for c in scene.characters if c!=actor)
            other=next((b.x for b in scene.actions if b.actor==partner),.65 if partner!='main' else .35)*world_width
            center=(origin+other)/2;direction=1 if other>origin else -1
            final_origin=center-direction*.25
            travel=abs(final_origin-origin)
            if local<travel/.24:
                # Approach through the same planted-foot walk cycle, not sliding poses.
                current=pose('walk',local,a.end-a.start,0,0,None,direction)
            else:
                origin=final_origin
                # Matched pair controls share a world-space contact target.
                current=pose('handshake',local,a.end-a.start,0,0,(center-origin,-.73),direction)
        else:current=pose(a.action,local,a.end-a.start,0,0,target)
        current.joints={k:(v[0]+origin,v[1]) for k,v in current.joints.items()}
        if previous and t<a.start+.35:
            q=ease((t-a.start)/.35)
            # Blend joints then re-solve limbs to preserve segment lengths.
            from pipeline.animation.rig import ik
            current.joints={k:mix(previous.joints[k],v,q) for k,v in current.joints.items()}
            for side in ('left','right'):
                j=current.joints
                j[side+'_knee'],j[side+'_foot']=ik(j[side+'_hip'],j[side+'_foot'],.255,.255,-1)
                j[side+'_elbow'],j[side+'_hand']=ik(j[side+'_shoulder'],j[side+'_hand'],.17,.17,1 if side=='left' else -1)
        previous=current;last=a
        if t<=a.end:return current,a
    if previous:
        # A held pose breathes; grounded feet and attached hands remain anchored.
        bob=.003*math.sin((t-last.end)*3)
        for k in ('head','neck','shoulder'):previous.joints[k]=(previous.joints[k][0],previous.joints[k][1]+bob)
        return previous,last
    q=pose('idle',t);base=.30 if actor=='main' else .67
    q.joints={k:(v[0]+base*world_width,v[1]) for k,v in q.joints.items()}
    return q,None

def character_scale(size):
    w,h=size
    return min(w*.58,h*.37) if h>w else min(w*.36,h*.49)

def frame(scene,t,size=(1920,1080),caption='',diagnostic=False):
    w,h=size;vertical=h>w;ground=.78*h;scale=character_scale(size);world_width=w/scale
    bg,back,accent=PALETTES[scene.mood]
    im=Image.new('RGB',size,bg);d=ImageDraw.Draw(im);u=max(0,min(1,t/scene.duration))
    zoom=1+.07*ease(u) if scene.camera=='push_in' else 1.07-.07*ease(u) if scene.camera=='pull_out' else 1
    pan=math.sin(u*math.pi)*w*.025 if scene.camera=='pan' else 0
    if scene.camera=='track':
        p,_=actor_pose(scene,scene.characters[0],t,world_width,h/scale);pan=(p.joints['hip'][0]*scale-w*.42)*.55
    shake=math.sin(t*67)*math.exp(-t*6)*w*.003 if scene.camera=='shake' else 0
    def xy(p):
        x=p[0]*scale;y=ground+p[1]*scale
        return ((x-w/2)*zoom+w/2-pan+shake,(y-h*.55)*zoom+h*.55)
    def line(points,fill=COLORS['main'],width=6):
        d.line([xy(p) for p in points],fill=fill,width=max(2,int(width*w/1280)),joint='curve')
    def rect(x0,y0,x1,y1,fill,outline=None):
        aa=xy((x0*world_width,(y0*h-ground)/scale));bb=xy((x1*world_width,(y1*h-ground)/scale))
        d.rectangle((*aa,*bb),fill,outline)
    env=scene.environment
    if env in ('office','bedroom','classroom','library','living_room','cafe','hallway','empty_room'):
        for i in range(3):
            x=.10+i*.30;rect(x,.21,x+.18,.50,back);rect(x+.012,.225,x+.168,.48,bg)
        if env=='library':
            for i in range(16):rect(.07+i*.055,.35,.095+i*.055,.55,accent if i%3 else back)
    elif env in ('park','nature','hill','city','street','crossroads','gathering'):
        for i in range(7):
            x=i*w/6-t*.3;y=h*.55-math.sin(i*2)*h*.05
            if env in ('city','street'):d.rectangle((x,y-h*.22,x+w*.11,h*.78),fill=back)
            else:d.ellipse((x-w*.1,y-h*.22,x+w*.15,y+h*.12),fill=back)
        for i in range(3):
            x=(i*.36*w+t*4)%(w+w*.2)-w*.1;d.ellipse((x,h*.13,x+w*.14,h*.17),fill='white')
    elif env=='mindscape':
        for i in range(7):
            x=w*(.1+i*.14);y=h*(.25+.10*math.sin(t*.3+i));d.ellipse((x-12,y-12,x+12,y+12),fill=back)
    d.rectangle((0,ground,w,h),fill=back);d.line((0,ground,w,ground),fill=accent,width=max(1,w//650))
    actors={actor:actor_pose(scene,actor,t,world_width,h/scale) for actor in scene.characters}
    for p in scene.props:
        x,y=p.x,p.y
        if p.kind in ('chair','bench'):
            # Seat is aligned to the rig's seated pelvis, in world units.
            seat=(ground-.31*scale)/h
            rect(x-.055,seat-.15,x-.045,seat,accent);rect(x-.05,seat,x+.07,seat+.015,accent)
            for dx in (-.04,.055):rect(x+dx,seat,x+dx+.01,.78,accent)
        elif p.kind in ('desk','table','computer'):
            rect(x-.12,y-.16,x+.12,y-.14,accent)
            for dx in (-.10,.09):rect(x+dx,y-.14,x+dx+.013,.78,accent)
            if p.kind=='computer':rect(x-.07,y-.30,x+.07,y-.19,COLORS['main']);rect(x-.06,y-.29,x+.06,y-.20,back)
        elif p.kind in ('door','mirror','window'):
            rect(x-.065,y-.38,x+.065,y,accent);rect(x-.052,y-.367,x+.05,y-.01,bg)
            if p.kind=='door':
                opening=next((ease((t-a.start)/max(.1,a.end-a.start)) for ap,a in actors.values() if a and a.action=='open_door' and a.target==p.id),0)
                rect(x-.05,y-.36,x+.05-.08*opening,y-.01,back)
        elif p.kind=='clock':
            cx,cy=x*w,y*h-h*.3;r=min(w,h)*.055
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=bg,outline=accent,width=3)
            d.line((cx,cy,cx+math.sin(t)*r*.7,cy-math.cos(t)*r*.7),fill=accent,width=3)
        elif p.kind in ('phone','box','book','cup','bag'):
            owner=None;drop=None
            for ap,a in actors.values():
                if a and a.target==p.id and a.action in ('pick_up','carry','use_phone','drop'):
                    if a.action=='drop':drop=(ap,a)
                    elif a.action!='pick_up' or t-a.start>(a.end-a.start)*.45:owner=ap.joints['right_hand']
            if owner:cx,cy=xy(owner)
            elif drop:
                ap,a=drop;cx,cy=xy(ap.joints['right_hand']);age=max(0,t-a.start-.3);cy=min(ground-8,cy+scale*age*age*1.8)
            else:cx,cy=xy((x*world_width,(y*h-ground)/scale))
            rr=scale*.035;d.rounded_rectangle((cx-rr,cy-rr,cx+rr,cy+rr*1.5),radius=3,fill=accent)
        elif p.kind=='stairs':
            for i in range(4):rect(x+i*.04,y-i*.04,x+(i+1)*.04,.78,accent)
        else:
            rect(x-.04,y-.08,x+.04,y,accent)
    if scene.symbol!='none':
        cx=w*(.5 if vertical else .65);cy=h*.30;r=min(w*.20,h*.17)
        if scene.symbol=='thought':
            r*=1+.035*math.sin(t*2)
            d.rounded_rectangle((cx-r,cy-r*.65,cx+r,cy+r*.65),radius=int(r*.3),outline=accent,width=3)
            for i in range(3):
                q=8-i*2;d.ellipse((cx-r*.5-i*15-q,cy+r*.7+i*15-q,cx-r*.5-i*15+q,cy+r*.7+i*15+q),fill=accent)
            for i in range(5):
                aa=i*1.3+t*.3;d.text((cx+math.cos(aa)*r*.6,cy+math.sin(aa)*r*.4),'?',font=font(int(h*.028)),fill=accent)
        elif scene.symbol in ('loop','waves','circles','chains'):
            for i in range(5):
                rr=r*(.2+i*.17);d.arc((cx-rr,cy-rr*.5,cx+rr,cy+rr*.5),int(t*25+i*20),int(t*25+i*20+290),fill=accent,width=3)
        elif scene.symbol in ('maze','decision_tree','memory'):
            for i in range(6):
                xx=cx-r+i*r*.35;d.line((xx,cy-r*.55,xx,cy+r*.55,xx+r*.15,cy+r*.55),fill=accent,width=3)
        elif scene.symbol=='doors':
            for i in range(3):
                xx=cx-r+i*r*.7;d.rectangle((xx,cy-r*.6,xx+r*.4,cy+r*.6),outline=accent,width=4)
        else:d.line((cx-r,cy,cx+r,cy,cx,cy-r*.5,cx,cy+r*.5),fill=accent,width=4)
    for actor,(p,a) in actors.items():
        color=COLORS[actor];j=p.joints;hip=xy(j['hip'])
        d.ellipse((hip[0]-scale*.13,ground,hip[0]+scale*.13,ground+8),fill=accent)
        for aa,bb in BONES:line([j[aa],j[bb]],color,7)
        for side in ('left','right'):
            for joint in ('knee','elbow','hand'):
                cx,cy=xy(j[side+'_'+joint]);rr=scale*.012;d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=color)
            f=j[side+'_foot'];line([f,(f[0]+.045,f[1])],color,7)
        cx,cy=xy(j['head']);r=scale*.078
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=bg,outline=color,width=max(3,int(w/280)))
        for dx in (-.025,.025):
            ex=cx+(dx+.012*p.facing)*scale;ey=cy-scale*.008
            d.ellipse((ex-2,ey-3,ex+2,ey+3),fill=color)
        if p.emotion=='happy':d.arc((cx-r*.4,cy,cx+r*.5,cy+r*.6),0,180,fill=color,width=2)
        elif p.emotion=='sad':d.arc((cx-r*.4,cy+r*.3,cx+r*.5,cy+r*.7),180,360,fill=color,width=2)
        else:d.line((cx-r*.15,cy+r*.35,cx+r*.25,cy+r*.35),fill=color,width=2)
        if p.emotion=='angry':
            d.line((cx-r*.55,cy-r*.38,cx-r*.12,cy-r*.17),fill=color,width=3)
        if diagnostic:
            for v in j.values():
                xx,yy=xy(v);d.ellipse((xx-3,yy-3,xx+3,yy+3),fill='red')
    if scene.text:
        ft=font(int(h*(.035 if vertical else .038)));box=d.textbbox((0,0),scene.text,font=ft)
        if box[2]>w*.9:ft=font(int(ft.size*w*.9/box[2]))
        d.text((w*.5,h*.085),scene.text,font=ft,fill=COLORS['main'],anchor='mm')
    if caption:
        ft=font(int(h*(.025 if vertical else .032)));yy=h*.86
        for txt in textwrap.wrap(caption,width=30 if vertical else 64)[:3]:
            tw=d.textbbox((0,0),txt,font=ft)[2]
            d.rounded_rectangle((w/2-tw/2-14,yy-5,w/2+tw/2+14,yy+ft.size+10),radius=7,fill=COLORS['main'])
            d.text((w/2,yy),txt,font=ft,fill='white',anchor='mt');yy+=ft.size*1.4
    if scene.transition=='fade' and t<.25:im=Image.blend(Image.new('RGB',size,bg),im,ease(t/.25))
    return im
