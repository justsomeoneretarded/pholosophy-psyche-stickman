"""Deterministic articulated rig, two-bone IK and world-space gait contacts."""
from dataclasses import dataclass
import math
ACTIONS='idle walk run sprint stop turn sit stand jump land stumble fall recover point wave shrug think scratch_head facepalm cry celebrate argue laugh push pull pick_up carry drop open_door climb_stairs handshake use_phone type'.split()
def ease(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)
def mix(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))
def ik(a,b,l1,l2,bend=1):
    dx,dy=b[0]-a[0],b[1]-a[1];d=max(abs(l1-l2)+1e-6,min(l1+l2-1e-6,math.hypot(dx,dy)))
    angle=math.atan2(dy,dx);offset=math.acos(max(-1,min(1,(l1*l1+d*d-l2*l2)/(2*l1*d))))
    return (a[0]+l1*math.cos(angle+bend*offset),a[1]+l1*math.sin(angle+bend*offset)),(a[0]+d*math.cos(angle),a[1]+d*math.sin(angle))
@dataclass
class Pose:
    joints:dict
    emotion:str='neutral'
    facing:int=1
def pose(action,t,duration=3.,x=0.,floor=0.,target=None,facing=1):
    if action not in ACTIONS:raise ValueError('Unsupported action: '+action)
    p=max(0,min(1,t/max(duration,.01)));envelope=math.sin(math.pi*p)**2
    hip=(x,floor-.49);shoulder=(x,floor-.79)
    feet=[(x-.075,floor),(x+.075,floor)];hands=[(x-.13,floor-.49),(x+.13,floor-.49)];emotion='neutral'
    if action in ('walk','run','sprint','climb_stairs','stop'):
        speed={'walk':.24,'run':.48,'sprint':.7,'climb_stairs':.18,'stop':.24}[action]
        cycle={'walk':.85,'run':.58,'sprint':.44,'climb_stairs':1.1,'stop':.85}[action];stride=speed*cycle
        root=x+speed*t*facing if action!='stop' else x+speed*(t-t*t/(2*max(duration,.01)))*facing
        hip=(root,floor-.49+math.cos(t/cycle*math.tau*2)*(.012 if action=='walk' else .025))
        shoulder=(root+(.035 if action!='walk' else .008)*facing,hip[1]-.30)
        for side in range(2):
            phase=t/cycle+side*.5;step=math.floor(phase);q=phase-step
            anchor=x+(step-side*.5)*stride*facing
            if q<.6:foot=(anchor,floor)
            else:
                u=(q-.6)/.4;foot=(anchor+stride*ease(u)*facing,floor-math.sin(math.pi*u)*(.07 if action=='walk' else .13))
            feet[side]=foot;hands[side]=(shoulder[0]+math.sin(phase*math.tau)*.15*facing,shoulder[1]+.24)
    elif action in ('sit','stand','type'):
        q=ease(p) if action=='sit' else 1-ease(p) if action=='stand' else 1.
        hip=(x-.06*q,floor-.49+.18*q);shoulder=(hip[0]+.025*q,hip[1]-.30)
        feet=[(x+.20*q-.065,floor),(x+.20*q+.065,floor)]
        hands=[(shoulder[0]+.20*q,shoulder[1]+.20),(shoulder[0]+.22*q,shoulder[1]+.18+.01*math.sin(t*12))]
    elif action in ('jump','land'):
        lift=math.sin(math.pi*p)*.22 if action=='jump' else -.07*envelope
        hip=(x,floor-.49-lift);shoulder=(x,hip[1]-.30)
        feet=[(x-.07,floor-lift if action=='jump' else floor),(x+.07,floor-lift if action=='jump' else floor)]
        hands=[(x-.20,floor-.72-lift),(x+.20,floor-.72-lift)]
    elif action in ('fall','recover','stumble'):
        q=ease(p) if action=='fall' else 1-ease(p) if action=='recover' else .4*envelope
        hip=(x+.16*q,floor-.49+.37*q);shoulder=(hip[0]+.27*q,hip[1]-.30*(1-q))
        hands=[(shoulder[0]+.12,shoulder[1]+.08),(shoulder[0]+.18,shoulder[1]+.08)]
    else:
        bob=.005*math.sin(t*3);hip=(x,floor-.49+bob);shoulder=(x,floor-.79+bob)
        hands=[(x-.12,floor-.49+bob),(x+.12,floor-.49+bob)]
        gesture=ease(t/.6)
        if action in ('point','push','pull','open_door','handshake','argue'):
            hands[1]=mix(hands[1],target or (x+.28,floor-.73),gesture)
            if action=='argue':hands[1]=(hands[1][0],hands[1][1]+.04*math.sin(t*8));emotion='angry'
        if action in ('pick_up','carry','drop','use_phone'):
            grip=target or (x+.22,floor-.45)
            if action=='pick_up':
                bend=ease(p/.28)*(1-ease((p-.45)/.55))
                hip=(x,floor-.49+.21*bend)
                shoulder=(x+.24*bend,hip[1]-math.sqrt(.30**2-(.24*bend)**2))
                hands[1]=mix(mix(hands[1],grip,ease(p/.35)),(x+.20,floor-.65),ease((p-.45)/.55))
            elif action=='drop':hands[1]=mix((x+.20,floor-.65),hands[1],ease(p))
            else:hands[1]=(x+.20,floor-.65)
        if action in ('think','scratch_head','facepalm'):
            hands[1]=mix(hands[1],(x+.06,floor-.91),gesture);emotion='thoughtful'
            if action=='scratch_head':hands[1]=(hands[1][0]+.015*math.sin(t*12),hands[1][1])
        if action in ('wave','celebrate'):
            hands[1]=(x+.21+.04*math.sin(t*10),floor-1.01);emotion='happy'
            if action=='celebrate':hands[0]=(x-.21,floor-1.01)
        if action=='shrug':hands=[(x-.23,floor-.74),(x+.23,floor-.74)];emotion='confused'
        if action=='cry':hands=[(x-.065,floor-.90),(x+.065,floor-.90)];emotion='sad'
        if action=='laugh':shoulder=(x+.015*math.sin(t*10),shoulder[1]+.02*math.sin(t*10));emotion='happy'
        if action=='turn':shoulder=(x+.025*math.sin(math.pi*p),shoulder[1]);facing=1 if p<.5 else -1
    j={'hip':hip,'shoulder':shoulder,'neck':(shoulder[0],shoulder[1]-.035),'head':(shoulder[0],shoulder[1]-.12)}
    for i,side in enumerate(('left','right')):
        hh=(hip[0]+(-.027 if i==0 else .027),hip[1]);ss=(shoulder[0]+(-.035 if i==0 else .035),shoulder[1])
        knee,foot=ik(hh,feet[i],.255,.255,-facing);elbow,hand=ik(ss,hands[i],.17,.17,1 if i==0 else -1)
        j.update({side+'_hip':hh,side+'_knee':knee,side+'_foot':foot,side+'_shoulder':ss,side+'_elbow':elbow,side+'_hand':hand})
    return Pose(j,emotion,facing)
BONES=[('hip','shoulder'),('shoulder','neck')]+[(s+'_'+a,s+'_'+b) for s in ('left','right') for a,b in [('hip','knee'),('knee','foot'),('shoulder','elbow'),('elbow','hand')]]
