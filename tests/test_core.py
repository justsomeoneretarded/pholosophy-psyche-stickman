import math, json, subprocess
from pathlib import Path
import numpy as np
import pytest
from pydantic import ValidationError
from pipeline.animation.rig import ik, ACTIONS
from pipeline.animation.scene import frame
from pipeline.models import Scene, Action, Episode, Prop
from pipeline.config import Config
from pipeline.speech.alignment import subtitles, stamp, align
from pipeline.production.render import render, probe
from pipeline.production.quality import motion_checks

def scene(action='walk'):
    return Scene(id='s1',purpose='A meaningful motion test',narration='The character takes one small step before considering the next decision.',duration=2,actions=[Action(action=action,end=2,x=.3)])

def test_unknown_action_and_prop_fail():
    with pytest.raises(ValidationError):Action(action='execute_python',end=1)
    with pytest.raises(ValidationError):Scene(**{**scene().model_dump(),'actions':[{'action':'pick_up','end':1,'target':'missing'}]})

def test_overlap_and_nonfinite_fail():
    data=scene().model_dump();data['actions']=[{'action':'walk','end':2},{'action':'run','start':1,'end':2}]
    with pytest.raises(ValidationError):Scene(**data)
    with pytest.raises(ValidationError):Action(action='walk',end=float('nan'))

def test_title_is_data():
    c=Config(title='Why $(touch /tmp/injected) is just text')
    assert '$(touch' in c.title
    with pytest.raises(ValidationError):Config(title='bad\ninput')

def test_subtitles_and_timing(tmp_path):
    captions=[{'start':0,'end':1.234,'text':'A single step.'}]
    subtitles(captions,tmp_path)
    assert '00:00:01,234' in (tmp_path/'subtitles.srt').read_text()
    assert (tmp_path/'subtitles.vtt').read_text().startswith('WEBVTT')
    assert stamp(3601.125)=='01:00:01,125'

def test_native_frames_and_dynamic_limbs():
    s=scene('run')
    a=np.array(frame(s,.4,(640,360)));b=np.array(frame(s,.6,(640,360)))
    assert a.shape==(360,640,3)
    assert np.mean(np.abs(a.astype(float)-b.astype(float)))>.1
    assert frame(s,.5,(360,640)).size==(360,640)

def test_real_ffmpeg_encode_and_decode(tmp_path):
    s=scene('wave');s.duration=.5;s.actions[0].end=.5;s.transition='cut'
    e=Episode(title='Test articulated video',thesis='A real articulated character should move in a streamed video.',metaphor='A stage demonstrates a motion.',framing='philosophical_exploration',scenes=[s,s.model_copy(update={'id':'s2'})])
    result=render(e,[{'start':0,'end':.5},{'start':.5,'end':1}],[],tmp_path,(320,180),30)
    assert result['frames']==30
    data=probe(tmp_path/'silent.mp4')
    assert float(data['format']['duration'])==pytest.approx(1,abs=.05)
    subprocess.run(['ffmpeg','-v','error','-i',str(tmp_path/'silent.mp4'),'-f','null','-'],check=True)
