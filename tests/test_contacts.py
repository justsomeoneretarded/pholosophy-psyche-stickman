import math
import pytest
from pipeline.models import Scene,Action,Prop
from pipeline.animation.scene import actor_pose
from pipeline.animation.rig import pose

def test_handshake_has_shared_contact():
    s=Scene(id='handshake',purpose='Meet another person',narration='Two people meet and acknowledge each other.',duration=3,characters=['main','friend'],actions=[Action(actor='main',action='handshake',end=3,x=.35),Action(actor='friend',action='handshake',end=3,x=.65)])
    a,_=actor_pose(s,'main',1.5);b,_=actor_pose(s,'friend',1.5)
    assert math.dist(a.joints['right_hand'],b.joints['right_hand'])<1e-5

def test_pickup_reaches_real_prop_coordinate():
    ww=1920/(1080*.49);wh=1080/(1080*.49)
    s=Scene(id='pickup',purpose='Pick up the phone',narration='She reaches for the phone before deciding to leave.',duration=3,props=[Prop(id='phone',kind='phone',x=.48,y=.70)],actions=[Action(action='pick_up',end=3,x=.40,target='phone')])
    p,_=actor_pose(s,'main',3*.44,ww,wh)
    grip=(.48*ww,(.70-.78)*wh)
    assert math.dist(p.joints['right_hand'],grip)<.015

def test_crouch_preserves_torso_length():
    p=pose('pick_up',1.2,3,target=(.29,-.16))
    assert math.dist(p.joints['hip'],p.joints['shoulder'])==pytest.approx(.30)
