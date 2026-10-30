import math
import numpy as np
import pytest
from pipeline.models import Scene, Action, Prop, Episode
from pipeline.animation.acting import plan_for
from pipeline.animation.rig import ACTIONS, LIMBS, STAND_HIP
from pipeline.animation.scene import character_scale
from pipeline.production.director import prepare
from pipeline.production.quality import motion_checks

WW = 1920 / character_scale((1920, 1080))


def scene(actions, props=(), characters=('main',), duration=8, **kw):
    return Scene(id='s1', purpose='Acting test', narration='A character performs a clear and readable action.',
                 duration=duration, characters=list(characters), props=list(props), actions=actions, **kw)


def poses(s, t):
    return plan_for(s, WW).poses(t)


def needs(action):
    kinds = {'sit': 'chair', 'lie_down': 'bed', 'sleep': 'bed', 'type': 'computer', 'use_phone': 'phone', 'read': 'book',
             'drink': 'cup', 'open_door': 'door', 'look_out_window': 'window', 'lean_on_wall': 'wall',
             'flip_switch': 'light_switch', 'climb_stairs': 'stairs', 'pick_up': 'box', 'carry': 'box'}
    return kinds.get(action)


@pytest.mark.parametrize('action', ACTIONS)
def test_every_action_keeps_rigid_bones_and_stays_above_floor(action):
    partner = action in ('handshake', 'hug', 'high_five', 'comfort', 'push', 'pull', 'give', 'chase')
    props = [Prop(id='thing', kind=needs(action), x=.6)] if needs(action) else []
    target = 'friend' if partner else ('thing' if props else None)
    s = scene([Action(action=action, start=.5, end=4, target=target)], props,
              ('main', 'friend') if partner else ('main',), duration=5)
    plan = plan_for(s, WW)
    previous = {}
    for t in np.arange(0, 5, 1 / 30):
        for actor, p in plan.poses(float(t)).items():
            j = p.joints
            assert all(math.isfinite(v) for q in j.values() for v in q)
            if abs(p.controls.facing) >= .3:    # turning foreshortens limbs in depth
                for side in ('left', 'right'):
                    for a, b, length in LIMBS:
                        assert math.dist(j[side + '_' + a], j[side + '_' + b]) == pytest.approx(length, abs=1e-5)
            for foot in ('left_foot', 'right_foot'):
                assert j[foot][1] - plan.world.floor_at(j[foot][0]) < .026
            if actor in previous and p.controls.visible > .5 and previous[actor][1]:
                jump = max(math.dist(j[k], previous[actor][0][k]) for k in j)
                assert jump < .25, (action, actor, round(float(t), 2), jump)
            previous[actor] = (j, p.controls.visible > .5)


def test_walk_moves_across_stage_with_planted_feet():
    s = scene([Action(action='walk', start=0, end=4, x=.8)])
    a, b = poses(s, .2)['main'], poses(s, 3.9)['main']
    assert b.joints['hip'][0] - a.joints['hip'][0] > 1.2
    samples = [poses(s, t)['main'].joints['left_foot'] for t in np.arange(1.0, 1.25, .02)]
    grounded = [q for q in samples if abs(q[1]) < 1e-6]
    assert grounded and max(q[0] for q in grounded) - min(q[0] for q in grounded) < 1e-6


def test_character_walks_to_chair_before_sitting_and_sits_at_seat_height():
    s = scene([Action(action='sit', start=1, end=6, target='chair')], [Prop(id='chair', kind='chair', x=.8)], x_ok=None) \
        if False else scene([Action(action='sit', start=1, end=6, target='chair')], [Prop(id='chair', kind='chair', x=.8)])
    plan = plan_for(s, WW)
    start = plan.poses(0)['main'].joints['hip'][0]
    seated = plan.poses(5.5)['main'].joints['hip']
    assert abs(seated[0] - .8 * WW) < .02
    assert abs(start - .8 * WW) > .5
    assert seated[1] > STAND_HIP + .12


def test_hug_is_reciprocated_and_arms_reach_partner():
    s = scene([Action(action='hug', start=1, end=5, target='friend')], characters=('main', 'friend'))
    plan = plan_for(s, WW)
    friend_seg = plan.tracks['friend'][plan.segment('friend', 3)]
    assert friend_seg.kind == 'hug' and friend_seg.implicit
    p = plan.poses(4)
    gap = abs(p['main'].joints['hip'][0] - p['friend'].joints['hip'][0])
    assert gap < .45
    assert abs(p['main'].joints['right_hand'][0] - p['friend'].joints['shoulder'][0]) < .12


def test_handshake_hands_meet():
    s = scene([Action(action='handshake', start=0, end=5, target='friend')], characters=('main', 'friend'))
    p = poses(s, 4)
    assert math.dist(p['main'].joints['right_hand'], p['friend'].joints['right_hand']) < .06


def test_push_knocks_partner_back_with_surprise():
    s = scene([Action(action='push', start=1, end=4, target='friend')], characters=('main', 'friend'))
    before = poses(s, .5)['friend'].joints['hip'][0]
    after = poses(s, 3.8)['friend']
    assert abs(after.joints['hip'][0] - before) > .25
    assert poses(s, 2.0)['friend'].emotion == 'surprised'


def test_object_is_picked_up_carried_and_given():
    s = scene([Action(action='pick_up', start=0, end=3, target='phone'),
               Action(action='give', start=4, end=7, target='friend')],
              [Prop(id='phone', kind='phone', x=.45)], ('main', 'friend'))
    plan = plan_for(s, WW)
    p = plan.poses(3.5)
    pos, holder = plan.object_position('phone', 3.5, p)
    assert holder == 'main' and math.dist(pos, p['main'].joints['right_hand']) < 1e-9
    p = plan.poses(7.5)
    pos, holder = plan.object_position('phone', 7.5, p)
    assert holder == 'friend'


def test_enter_and_leave_control_visibility():
    s = scene([Action(action='enter', start=1, end=4, x=.4), Action(action='leave', start=5, end=9)], duration=10)
    assert poses(s, .5)['main'].controls.visible == 0
    assert poses(s, 4.5)['main'].controls.visible == 1
    assert poses(s, 9.8)['main'].controls.visible == 0


def test_emotion_persists_and_shapes_posture():
    s = scene([Action(action='cry', start=0, end=2), Action(action='walk', start=2.5, end=5, x=.8)])
    walking = poses(s, 4)['main']
    assert walking.emotion == 'sad'
    neutral = poses(scene([Action(action='walk', start=2.5, end=5, x=.8)]), 4)['main']
    assert walking.controls.lean > neutral.controls.lean


def test_idle_partner_turns_to_watch_and_talking_moves_mouth():
    s = scene([Action(action='talk', start=1, end=5, target='friend')], characters=('main', 'friend'))
    p = poses(s, 3)
    assert p['friend'].controls.facing < 0 < p['main'].controls.facing
    mouths = [poses(s, t)['main'].controls.mouth for t in np.arange(2, 3, .05)]
    assert max(mouths) > .4 and min(mouths) < .3


def test_director_adds_missing_props_and_targets_them():
    s = scene([Action(action='type', start=0, end=5), Action(action='use_phone', start=5, end=8)])
    e = Episode(title='Staging repairs', thesis='Every action that needs a prop must have a reachable prop.',
                metaphor='A desk becomes a stage.', framing='philosophical_exploration', scenes=[s, s.model_copy(deep=True, update={'id': 's2'})])
    changes = prepare(e, (1920, 1080))
    kinds = {p.kind for p in e.scenes[0].props}
    assert {'computer', 'chair', 'phone'} <= kinds
    assert all(a.target for a in e.scenes[0].actions)
    assert changes


def test_motion_qa_passes_rich_scene():
    s = scene([Action(action='enter', start=0, end=2.5, x=.3), Action(action='sit', start=3, end=6, target='chair', emotion='sad'),
               Action(action='talk', start=6.5, end=9, target='friend'), Action(action='hug', start=9.5, end=12, target='friend')],
              [Prop(id='chair', kind='chair', x=.25)], ('main', 'friend'), duration=13)
    e = Episode(title='Motion QA', thesis='A full performance keeps rigid limbs and continuous motion.',
                metaphor='A room where people meet.', framing='philosophical_exploration', scenes=[s, s.model_copy(update={'id': 's2'})])
    report = motion_checks(e, (1920, 1080))
    assert report['passed'], report['issues']
