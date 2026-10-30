import numpy as np
import pytest
from pipeline.models import Scene, Action, Prop
from pipeline.animation.scene import frame, character_scale

ENVIRONMENTS = ['bedroom', 'classroom', 'office', 'street', 'park', 'living_room', 'cafe', 'library', 'hallway', 'city',
                'void', 'stage', 'mindscape', 'staircase', 'crossroads', 'gathering', 'empty_room', 'hill', 'nature']


def scene(**kw):
    base = dict(id='r', purpose='Render test', narration='A character shows a clear feeling on screen.', duration=4,
                actions=[Action(action='idle', end=4)])
    base.update(kw)
    return Scene(**base)


@pytest.mark.parametrize('env', ENVIRONMENTS)
def test_every_environment_renders_distinct_content(env):
    im = np.asarray(frame(scene(environment=env), 2, (480, 270), ss=1)).astype(float)
    assert im.shape == (270, 480, 3)
    assert im.std() > 8


def test_faces_change_with_emotion():
    a = np.asarray(frame(scene(actions=[Action(action='idle', end=4, emotion='happy')], camera='static'), 2, (640, 360), ss=1)).astype(float)
    b = np.asarray(frame(scene(actions=[Action(action='idle', end=4, emotion='angry')], camera='static'), 2, (640, 360), ss=1)).astype(float)
    assert np.mean(np.abs(a - b)) > .05


def test_vertical_has_its_own_framing():
    assert character_scale((1080, 1920)) / 1920 > .30
    assert frame(scene(symbol='thought'), 1, (360, 640), ss=1).size == (360, 640)


def test_switching_lights_off_darkens_the_room():
    s = scene(props=[Prop(id='switch', kind='light_switch', x=.6)],
              actions=[Action(action='flip_switch', start=0, end=2, target='switch')])
    lit = np.asarray(frame(s, .1, (320, 180), ss=1)).mean()
    dark = np.asarray(frame(s, 3.5, (320, 180), ss=1)).mean()
    assert dark < lit * .7
