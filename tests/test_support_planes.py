import math
import pytest
from pipeline.models import Episode,Scene,Action,Prop
from pipeline.production.director import prepare
from pipeline.animation.scene import actor_pose,character_scale
def test_phone_on_floor_is_reached_before_it_is_lifted():
    s=Scene(id='s1',purpose='Reach a grounded object',narration='He reaches down, picks up the phone, and checks the message.',duration=3,props=[Prop(id='phone',kind='phone',x=.43,y=.65)],actions=[Action(action='use_phone',end=3,x=.35,target='phone')])
    e=Episode(title='A real phone contact',thesis='The physical phone must rest on a surface before it is reached.',metaphor='A phone becomes a distraction.',framing='philosophical_exploration',scenes=[s,s.model_copy(deep=True,update={'id':'s2'})])
    assert prepare(e,(1920,1080))
    scale=character_scale((1920,1080));ww=1920/scale;wh=1080/scale
    p,_=actor_pose(e.scenes[0],'main',1.2*.44,ww,wh)
    target=(.43*ww,(e.scenes[0].props[0].y-.78)*wh)
    assert math.dist(p.joints['right_hand'],target)<.015
    assert e.scenes[0].props[0].y==pytest.approx(.78-.0525*scale/1080)
