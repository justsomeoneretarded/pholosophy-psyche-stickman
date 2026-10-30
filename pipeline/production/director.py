"""Deterministic staging repairs: every prop an action needs exists and is targeted.

The acting planner walks characters to their targets, so the director only has
to make sure a target exists (a chair to sit on, a phone to pick up, a door to
open). Every addition is recorded as an explicit storyboard repair.
"""
from pipeline.animation.scene import character_scale
from pipeline.animation.acting import plan_for, HOME
from pipeline.animation.rig import ACTION_PROPS, HANDHELD
from pipeline.models import Prop

OFFSET = {'chair': 0., 'bench': 0., 'sofa': 0., 'bed': 0., 'computer': .14, 'desk': .14, 'table': .14,
          'window': .10, 'door': .12, 'wall': -.08, 'light_switch': .09, 'stairs': .16, 'mirror': .10}


def _free_id(scene, base):
    ids = {p.id for p in scene.props}
    ident = base
    n = 2
    while ident in ids:
        ident = f'{base}_{n}'
        n += 1
    return ident


def _add(scene, kind, x, reason, changes):
    if len(scene.props) >= 12:
        raise ValueError(scene.id + ': no room for required ' + kind + ' prop')
    prop = Prop(id=_free_id(scene, kind), kind=kind, x=max(.07, min(.93, x)))
    scene.props.append(prop)
    changes.append({'scene': scene.id, 'prop': prop.id, 'kind': kind, 'x': prop.x, 'reason': reason})
    return prop


def prepare(episode, size):
    changes = []
    scale = character_scale(size)
    ww = size[0] / scale
    for scene in episode.scenes:
        for a in sorted(scene.actions, key=lambda a: a.start):
            kinds = ACTION_PROPS.get(str(a.action))
            if not kinds:
                continue
            props = {p.id: p for p in scene.props}
            if a.target in props and props[a.target].kind in kinds:
                continue
            plan = plan_for(scene, ww)
            actor_x = (a.x if a.x is not None else plan.x_at(a.actor, a.start) / ww)
            existing = [p for p in scene.props if p.kind in kinds]
            if existing:
                prop = min(existing, key=lambda p: abs(p.x - actor_x))
                reason = f'Targeted existing {prop.kind} for {a.action}'
                changes.append({'scene': scene.id, 'prop': prop.id, 'reason': reason})
            else:
                kind = kinds[0]
                direction = 1 if actor_x < .5 else -1
                prop = _add(scene, kind, actor_x + direction * OFFSET.get(kind, .1),
                            f'Added {kind} required by {a.action}', changes)
            a.target = prop.id
            if str(a.action) == 'type' and not any(p.kind in ('chair', 'bench', 'sofa') and abs(p.x - prop.x) < .25 for p in scene.props):
                side = -1 if prop.x > .5 else 1
                _add(scene, 'chair', prop.x + side * .12, 'Added a chair so typing happens seated at the desk', changes)
    return changes
