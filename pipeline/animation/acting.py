"""Acting planner: turns a scene's action list into continuous character performance.

For each actor the planner builds a gap-free list of segments covering the
whole scene. It inserts what a human animator would add automatically:

* walking (or running) to a prop or partner before acting on it,
* standing up before walking away from a chair or bed,
* partner reactions (a hug is hugged back, a push knocks the other person back,
  talking makes the other person listen and nod),
* object ownership (a phone is picked up, held, handed over or dropped),
* emotion that persists between actions and shapes posture, gait and face,
* idle life: breathing, weight shifts, blinking and looking at the other person.

Controls for an instant are produced by evaluating the active segment and
blending from the previous one, then solved into joints by the rig.
"""
from dataclasses import dataclass, field
import math
from functools import lru_cache
from pipeline.animation.rig import (
    arc_mix, Controls, Pose, solve, blend, ease, ease_out, mix, lerp, shoulder_of, head_of, side,
    STAND_HIP, SEAT_HIP, ACTION_EMOTION, REACTIONS, LOCOMOTION, HANDHELD, SEATS, ARM_REACH,
)

HOME = {'main': .30, 'friend': .68, 'shadow': .50, 'future': .84}
SPEED = {'walk': .55, 'stop': .55, 'run': 1.35, 'sprint': 2.0, 'sneak': .32, 'pace': .5, 'enter': .6,
         'leave': .6, 'chase': 1.45, 'flee': 1.5, 'climb_stairs': .42}
GAP = {'handshake': .52, 'high_five': .50, 'hug': .33, 'comfort': .36, 'push': .40, 'pull': .44, 'give': .55,
       'talk': .85, 'argue': .75, 'laugh': .9, 'point': 1.1, 'wave': 1.2, 'clap': 1.0, 'chase': .45}
BLEND = .32
STAIR_W, STAIR_H, STAIR_N = .17, .12, 4
TABLE_TOP, BED_TOP, SEAT_TOP = -.42, -.31, -.27


def noise(t, seed=0.):
    """Smooth deterministic noise in roughly -1..1."""
    return .5 * math.sin(t * 1.3 + seed * 2.1) + .3 * math.sin(t * 2.9 + seed * 5.7) + .2 * math.sin(t * 5.3 + seed * 1.3)


def hashed(*values):
    h = 2166136261
    for ch in repr(values):
        h = (h ^ ord(ch)) * 16777619 & 0xffffffff
    return h / 0xffffffff


# ---------------------------------------------------------------- the world
class World:
    """Geometry of the set: prop positions, floor height, surfaces and use spots."""

    def __init__(self, scene, ww):
        self.scene = scene
        self.ww = ww
        self.props = {p.id: p for p in scene.props}
        from pipeline.animation import setpieces
        piece = setpieces.get(getattr(scene, 'setpiece', None))
        self.terrain = getattr(piece, 'floor', None) if piece else None
        self.piece = piece

    def px(self, prop):
        return prop.x * self.ww

    def by_kind(self, kinds):
        return [p for p in self.scene.props if p.kind in kinds]

    def stairs_x0(self, p):
        return self.px(p) - STAIR_W * STAIR_N / 2

    def floor_at(self, x):
        y = self.terrain(x, self.ww) if self.terrain else 0.
        for p in self.by_kind(('stairs',)):
            x0 = self.stairs_x0(p)
            if x0 <= x < x0 + STAIR_W * STAIR_N:
                y = min(y, -(math.floor((x - x0) / STAIR_W) + 1) * STAIR_H)
            elif x0 + STAIR_W * STAIR_N <= x < x0 + STAIR_W * STAIR_N + .55:
                y = min(y, -STAIR_N * STAIR_H)
        return y

    def surface_at(self, x):
        """Height where a small object rests at x (table, bed or floor)."""
        best = self.floor_at(x)
        for p in self.scene.props:
            half = {'desk': .30, 'table': .30, 'computer': .30, 'bed': .48, 'bench': .40, 'sofa': .42}.get(p.kind)
            if half and abs(self.px(p) - x) < half:
                top = {'bed': BED_TOP, 'bench': SEAT_TOP, 'sofa': SEAT_TOP}.get(p.kind, TABLE_TOP)
                best = min(best, top)
        return best

    def near_table(self, prop):
        tables = self.by_kind(('desk', 'table', 'computer'))
        tables = [q for q in tables if abs(self.px(q) - self.px(prop)) < .9]
        return min(tables, key=lambda q: abs(self.px(q) - self.px(prop))) if tables else None

    def seat_facing(self, prop):
        table = self.near_table(prop)
        if table:
            return 1 if self.px(table) > self.px(prop) else -1
        if prop.kind == 'bed':
            return 1 if self.px(prop) > self.ww / 2 else -1   # pillow toward the nearer edge
        return 1 if self.px(prop) < self.ww / 2 else -1

    def stage(self, x):
        return max(.18, min(self.ww - .18, x))

    def spot(self, kind, prop, x):
        """Where to stand (hip x) and which way to face to use a prop."""
        p = self.px(prop)
        s = 1 if x <= p else -1               # approach from the side the actor is on
        if prop.kind in SEATS + ('rock',) and kind in ('sit', 'lie_down', 'sleep'):
            return p, self.seat_facing(prop)
        if prop.kind in ('desk', 'table', 'computer'):
            if kind == 'type':
                chair = next((c for c in self.by_kind(('chair', 'bench', 'sofa')) if abs(self.px(c) - p) < .8), None)
                if chair:
                    return self.px(chair), 1 if p > self.px(chair) else -1
                return p - .40 * s, s
            return p - .42 * s, s
        if prop.kind == 'wall':
            return p - .17 * s, -s
        if prop.kind == 'stairs':
            x0 = self.stairs_x0(prop)
            return x0 + STAIR_W * STAIR_N + .25, 1
        if prop.kind in HANDHELD:
            return p - .27 * s, s
        if prop.kind == 'door':
            return p - .33 * s, s
        return p - .30 * s, s


# ---------------------------------------------------------------- segments
@dataclass
class Seg:
    t0: float
    t1: float
    kind: str
    x0: float
    x1: float
    facing: float
    posture0: str
    posture1: str
    emotion: str = 'neutral'
    prop: str = None
    partner: str = None
    action: object = None
    implicit: bool = False
    params: dict = field(default_factory=dict)
    seat_y: float = SEAT_HIP
    holding: str = None


@dataclass
class State:
    x: float
    facing: float
    posture: str = 'stand'
    emotion: str = 'neutral'
    seat_y: float = SEAT_HIP
    seat_prop: str = None
    holding: str = None


@dataclass
class ExplicitAct:
    """An action to perform, explicit from the script or implied as a reaction."""
    actor: str
    kind: str
    start: float
    end: float
    x: float = None
    target: str = None
    emotion: str = None
    implicit: bool = False
    source: object = None


def gather(scene, ww):
    """Explicit actions plus implied partner reactions, per actor."""
    acts = {a: [] for a in scene.characters}
    for a in scene.actions:
        acts[a.actor].append(ExplicitAct(a.actor, str(a.action), a.start, a.end,
                                         None if a.x is None else a.x * ww, a.target,
                                         getattr(a, 'emotion', None), False, a))
    # Old storyboards sometimes give both people 'handshake' without a target.
    mutual = ('handshake', 'hug', 'high_five')
    for actor, items in acts.items():
        for e in items:
            if e.kind in mutual and not e.target and len(scene.characters) > 1:
                e.target = next(c for c in scene.characters if c != actor)
    for actor, items in list(acts.items()):
        for e in items:
            partner = e.target if e.target in scene.characters else None
            if not partner or partner == actor or e.implicit:
                continue
            reaction = REACTIONS.get(e.kind)
            if not reaction:
                continue
            busy = [o for o in acts[partner] if o.start < e.end and e.start < o.end]
            if any(o.kind in mutual and o.target == actor for o in busy):
                for o in busy:          # the partner is the receiving side of a mutual act
                    if o.kind in mutual and o.target == actor and o.source is not None and \
                            scene.characters.index(partner) > scene.characters.index(actor):
                        o.implicit = True
                continue
            if busy:
                continue
            acts[partner].append(ExplicitAct(partner, reaction, e.start, e.end, None, actor, None, True))
    for items in acts.values():
        items.sort(key=lambda e: e.start)
    return acts


class ScenePlan:
    def __init__(self, scene, ww, wh=None):
        self.scene = scene
        self.ww = ww
        self.world = World(scene, ww)
        self.duration = scene.duration
        self.acts = gather(scene, ww)
        self.lights = []          # times the light switch flips
        self.doors = {}           # door id -> list of (t_open, t_close)
        self.objects = {}         # prop id -> list of events (t, kind, actor or (x, y))
        self.tracks = {}
        guess = {a: self._initial(a) for a in scene.characters}
        self.positions = None
        previous = None
        for _ in range(5):        # later passes use partner positions from the pass before
            self.lights, self.doors, self.objects = [], {}, {}
            self.tracks = {a: self._plan(a, guess) for a in scene.characters}
            self.positions = self.tracks
            signature = [(round(g.t0, 3), round(g.x1, 3)) for segs in self.tracks.values() for g in segs]
            if signature == previous:
                break
            previous = signature
        self.beats = sorted(
            [(s.t0, s.t1, actor, s.kind, s.partner, s.prop) for actor, segs in self.tracks.items()
             for s in segs if s.action is not None and not s.implicit], key=lambda b: b[0])

    # ---------------------------------------------------------- planning
    def _initial(self, actor):
        first = next((e for e in self.acts[actor] if e.x is not None and e.kind not in LOCOMOTION), None)
        x = first.x if first else HOME.get(actor, .5) * self.ww
        for other in self.scene.characters:
            if other == actor:
                break
            o = next((e.x for e in self.acts[other] if e.x is not None), HOME.get(other, .5) * self.ww)
            if abs(o - x) < .35:
                x = o + (.6 if o < self.ww / 2 else -.6)
        return self.world.stage(x)

    def x_at(self, actor, t):
        segs = (self.positions or {}).get(actor)
        if not segs:
            return self._initial(actor)
        for s in segs:
            if s.t0 <= t < s.t1:
                return self._seg_x(s, t)
        return segs[-1].x1

    def _seg_x(self, s, t):
        if s.kind in ('_move',) or s.kind in LOCOMOTION:
            travel = s.params.get('travel', 0.)
            if s.kind == 'pace':
                return s.x0 + s.params['amp'] * math.sin((t - s.t0) / max(.1, s.t1 - s.t0) * math.tau)
            if travel <= 0:
                return s.x1
            d = move_distance(t - s.t0, travel, abs(s.x1 - s.x0))
            return s.x0 + math.copysign(d, s.x1 - s.x0)
        if s.kind == 'pushed':
            return lerp(s.x0, s.x1, ease_out((t - s.t0) / .6))
        if s.kind == 'fall':
            return lerp(s.x0, s.x1, ease((t - s.t0) / .6))
        return s.x1

    def _partner_x(self, partner, t):
        if self.positions:
            return self.x_at(partner, t)
        return self._initial(partner)

    def _travel_time(self, distance, speed):
        return distance / speed + (.25 if distance > .05 else 0)

    def _plan(self, actor, guess):
        w = self.world
        acts = self.acts[actor]
        x0 = self._initial(actor)
        others = [c for c in self.scene.characters if c != actor]
        facing = 1 if x0 < w.ww / 2 else -1
        if others:
            facing = 1 if self._partner_x(others[0], 0) > x0 else -1
        st = State(x0, facing)
        if acts and acts[0].kind == 'enter':
            st.posture = 'hidden'
            first = acts[0].x if acts[0].x is not None else HOME.get(actor, .5) * w.ww
            st.x = -.45 if w.stage(first) < w.ww / 2 else w.ww + .45
        segs = []
        cursor = 0.

        def idle(until):
            nonlocal cursor
            if until - cursor > 1e-4:
                segs.append(Seg(cursor, until, '_idle', st.x, st.x, st.facing, st.posture, st.posture,
                                st.emotion, seat_y=st.seat_y, holding=st.holding,
                                partner=others[0] if others else None))
                cursor = until

        for e in acts:
            kind = e.kind
            start, end = max(e.start, cursor), max(e.end, cursor + .2)
            emotion = e.emotion or ACTION_EMOTION.get(kind) or {
                'pushed': 'surprised', 'flee': 'scared', 'receive': 'happy', 'comforted': 'sad'}.get(kind) or st.emotion
            prop = w.props.get(e.target) if e.target in w.props else None
            partner = e.target if e.target in self.scene.characters else None
            dest, face = self._destination(e, st, prop, partner, start)
            opening = not segs and start < .3 and not e.implicit
            if opening and dest is not None:
                st.x = dest                     # the scene opens with the actor already in place
                if face is not None:
                    st.facing = face
            # ---------- preparation: stand up and travel before the action body
            prep = 0.
            need_up = st.posture in ('sit', 'lie', 'down', 'kneel', 'crouch') and (
                (dest is not None and abs(dest - st.x) > .08) or kind in LOCOMOTION or kind in ('jump', 'dance'))
            if kind in ('stand', 'get_up', 'recover'):
                need_up = False
            up_time = .7 if need_up else 0.
            distance = abs(dest - st.x) if dest is not None and kind not in LOCOMOTION else 0.
            speed = SPEED['walk'] if emotion not in ('sad', 'tired') else .42
            travel = self._travel_time(distance, speed) if distance > .06 else 0.
            prep = up_time + travel
            begin = max(cursor, start - prep)
            body = max(start, begin + prep)
            room = end - body
            if prep and room < max(.7, .5 * (end - start)):
                # Not enough time at walking pace: hurry.
                avail = max(.25, (end - start) * .5 - up_time + (start - begin))
                speed = min(2.2, max(speed, distance / max(.2, avail - .25)))
                travel = self._travel_time(distance, speed) if distance > .06 else 0.
                prep = up_time + travel
                body = max(start, begin + prep)
            idle(begin)
            if need_up:
                segs.append(Seg(cursor, cursor + up_time, 'get_up', st.x, st.x, st.facing, st.posture, 'stand',
                                st.emotion, seat_y=st.seat_y, holding=st.holding))
                cursor += up_time
                st.posture = 'stand'
            if travel:
                direction = 1 if dest > st.x else -1
                segs.append(Seg(cursor, cursor + travel, '_move', st.x, dest, direction, 'stand', 'stand', st.emotion,
                                params={'travel': travel, 'speed': speed, 'gait': 'run' if speed > 1.1 else 'walk'},
                                holding=st.holding))
                cursor += travel
                st.x = dest
                st.facing = direction
            idle(body)
            # ---------- the action body
            seg = self._body(e, st, prop, partner, dest, face, cursor, max(cursor + .2, end), emotion)
            if opening and kind in ('sit', 'lie_down', 'sleep', 'type'):
                seg.posture0 = seg.posture1       # already seated / asleep when the scene starts
                seg.params.pop('sit_down', None)
            segs.append(seg)
            cursor = seg.t1
            st.emotion = seg.emotion
        idle(max(cursor, self.duration) + 3600)
        return segs

    def _destination(self, e, st, prop, partner, start):
        """Where the actor must be (hip x) for the action body, and the facing there."""
        w = self.world
        kind = e.kind
        if e.implicit and kind not in ('flee', 'pushed', 'pulled'):
            return None, None
        if partner and kind in GAP and kind != 'chase':
            px = self._partner_x(partner, start)
            s = 1 if px >= st.x else -1
            gap = GAP[kind]
            if kind in ('talk', 'argue', 'laugh', 'point', 'wave', 'clap') and abs(px - st.x) < 1.9:
                return None, s                      # close enough to address them from here
            if .6 * gap <= abs(px - st.x) <= 1.5 * gap:
                return None, s                      # already at a comfortable distance
            return w.stage(px - s * gap), s
        if prop is not None and kind not in ('look_at', 'point', 'drop', 'carry', 'think', 'talk'):
            if kind in ('use_phone', 'read', 'drink') and self._held_by(prop.id, start) not in (None,):
                return None, None
            x, f = w.spot(kind, prop, st.x)
            return w.stage(x) if prop.kind != 'stairs' else x, f
        if e.x is not None and kind not in LOCOMOTION and abs(e.x - st.x) > .2:
            return w.stage(e.x), None
        return None, None

    def _held_by(self, prop_id, t):
        holder = None
        for ev in self.objects.get(prop_id, []):
            if ev[0] <= t:
                holder = ev[2] if ev[1] == 'hold' else None
        return holder

    def _body(self, e, st, prop, partner, dest, face, t0, t1, emotion):
        w = self.world
        kind = e.kind
        dur = t1 - t0
        facing = face if face is not None else st.facing
        if partner and kind not in ('flee',):
            facing = 1 if self._partner_x(partner, t0) >= st.x else -1
        if prop is not None and kind in ('look_at', 'point', 'pick_up', 'put_down', 'open_door', 'flip_switch',
                                         'look_out_window', 'use_phone', 'read', 'drink', 'type'):
            facing = face if face is not None else (1 if w.px(prop) >= st.x else -1)
        seg = Seg(t0, t1, kind, st.x, st.x, facing, st.posture, st.posture, emotion, prop=prop.id if prop else None,
                  partner=partner, action=e.source if e.source is not None else e, implicit=e.implicit,
                  seat_y=st.seat_y, holding=st.holding)
        p = seg.params
        # ---- locomotion bodies
        if kind in LOCOMOTION:
            if kind == 'pace':
                p['amp'] = .4
                p['travel'] = dur
                seg.x1 = st.x
            else:
                if kind == 'enter':
                    target = e.x if e.x is not None else HOME.get(e.actor, .5) * w.ww
                    target = w.stage(target)
                    edge = -.45 if target < w.ww / 2 else w.ww + .45
                    seg.x0 = edge
                    st.posture = 'stand'
                    seg.posture0 = seg.posture1 = 'stand'
                elif kind == 'leave':
                    door = prop if prop is not None and prop.kind == 'door' else None
                    if door:
                        target = w.px(door)
                        p['door'] = door.id
                    else:
                        target = -.5 if st.x < w.ww / 2 else w.ww + .5
                elif kind == 'climb_stairs':
                    stairs = prop or next(iter(w.by_kind(('stairs',))), None)
                    target = w.spot('climb', stairs, st.x)[0] if stairs else st.x + .8
                elif kind == 'chase' and partner:
                    pend = self._partner_x(partner, t1)
                    target = w.stage(pend - (1 if pend > st.x else -1) * GAP['chase'])
                elif kind == 'flee' and partner:
                    away = 1 if st.x >= self._partner_x(partner, t0) else -1
                    target = w.stage(st.x + away * 1.3)
                elif e.x is not None and abs(e.x - st.x) > .12:
                    target = w.stage(e.x)
                else:
                    direction = st.facing or 1
                    target = st.x + direction * SPEED.get(kind, .55) * dur * .8
                    if not .3 < target < w.ww - .3:
                        target = st.x - direction * SPEED.get(kind, .55) * dur * .8
                    target = w.stage(target)
                speed = SPEED.get(kind, .55) * (.8 if emotion in ('sad', 'tired') else 1.)
                distance = abs(target - seg.x0)
                walk_dur = dur - (1.0 if p.get('door') else 0.)
                travel = self._travel_time(distance, speed)
                if getattr(self.scene, 'style', 'classic') == 'noir' and kind in ('walk', 'stop') and travel < walk_dur * .85:
                    speed = max(.14, distance / max(.5, walk_dur * .9 - .25))      # cinematic: walks fill their beat
                    travel = self._travel_time(distance, speed)
                if travel > walk_dur:
                    speed = min(SPEED.get(kind, .55) * 1.8, distance / max(.2, walk_dur - .25))
                    travel = min(walk_dur, self._travel_time(distance, speed))
                p['travel'] = max(.01, travel)
                p['speed'] = speed
                seg.x1 = target
                seg.facing = 1 if target >= seg.x0 else -1
                if p.get('door'):
                    p['door_start'] = t0 + travel
                    self.doors.setdefault(p['door'], []).append((t0 + travel + .1, t1 + 1.2))
            st.x = seg.x1
            st.facing = seg.facing if kind != 'flee' else seg.facing
            if kind == 'leave':
                st.posture = 'hidden'
                seg.posture1 = 'hidden'
            return seg
        # ---- in-place movement
        if kind == 'pushed':
            back = -facing
            seg.x1 = w.stage(st.x + back * .38)
            st.x = seg.x1
            return seg
        if kind == 'fall':
            seg.x1 = w.stage(st.x + facing * .12)
            st.x = seg.x1
            st.posture = seg.posture1 = 'down'
            return seg
        if kind == 'turn':
            seg.facing = -st.facing
            st.facing = seg.facing
            return seg
        if kind in ('sit', 'lie_down', 'sleep'):
            seat = prop if prop is not None and prop.kind in SEATS + ('rock',) else None
            lying = kind != 'sit'
            if seat is not None:
                top = {'bed': BED_TOP, 'bench': SEAT_TOP, 'sofa': SEAT_TOP}.get(seat.kind, SEAT_TOP)
                seg.seat_y = top - .02 if not lying else top - .035
                seg.x1 = w.px(seat)
                if lying and seat.kind == 'bed':
                    seg.facing = w.seat_facing(seat)
                st.seat_prop = seat.id
            else:
                seg.seat_y = -.07 if lying else SEAT_HIP
            st.seat_y = seg.seat_y
            st.x = seg.x1
            st.posture = seg.posture1 = 'lie' if lying else 'sit'
            st.facing = seg.facing
            return seg
        if kind in ('stand', 'get_up', 'recover'):
            st.posture = seg.posture1 = 'stand'
            return seg
        if kind in ('kneel', 'crouch', 'cower'):
            st.posture = seg.posture1 = 'kneel' if kind == 'kneel' else 'stand'
            return seg
        if kind == 'type':
            if st.posture != 'sit':
                chair = next((c for c in w.by_kind(('chair', 'bench', 'sofa')) if abs(w.px(c) - st.x) < .3), None)
                seg.seat_y = (SEAT_TOP - .02) if chair else SEAT_HIP
                st.posture = seg.posture1 = 'sit'
                st.seat_y = seg.seat_y
                seg.params['sit_down'] = True
            table = next(iter(sorted(w.by_kind(('computer', 'desk', 'table')), key=lambda q: abs(w.px(q) - st.x))), None)
            if table:
                p['desk_x'] = w.px(table)
            return seg
        # ---- objects
        if prop is not None and prop.kind in HANDHELD:
            holder = self._held_by(prop.id, t0)
            events = self.objects.setdefault(prop.id, [])
            if kind in ('pick_up', 'use_phone', 'read', 'drink', 'carry') and holder != e.actor:
                if holder is None:
                    reach = min(1.1, dur * .5) if kind != 'pick_up' else min(1.6, dur)
                    p['reach'] = reach
                    p['rest'] = (w.px(prop), w.surface_at(w.px(prop)))
                    events.append((t0 + reach * .45, 'hold', e.actor))
                    st.holding = prop.id
                    seg.holding = None
                    p['grab_at'] = t0 + reach * .45
            elif kind == 'put_down' and holder == e.actor:
                spot = st.x + facing * .30
                events.append((t0 + min(1.2, dur) * .5, 'rest', (spot, w.surface_at(spot))))
                st.holding = None
                p['release'] = min(1.2, dur) * .5
                p['place'] = (spot, w.surface_at(spot))
            elif kind == 'drop' and holder == e.actor:
                events.append((t0 + .3, 'fall', e.actor))
                st.holding = None
        elif kind in ('put_down', 'drop') and st.holding:
            pid = st.holding
            if kind == 'drop':
                self.objects.setdefault(pid, []).append((t0 + .3, 'fall', e.actor))
            else:
                spot = st.x + facing * .30
                self.objects.setdefault(pid, []).append((t0 + min(1.2, dur) * .5, 'rest', (spot, w.surface_at(spot))))
                p['release'] = min(1.2, dur) * .5
                p['place'] = (spot, w.surface_at(spot))
            st.holding = None
        if kind == 'give' and partner and st.holding:
            self.objects.setdefault(st.holding, []).append((t0 + min(1.4, dur) * .55, 'hold', partner))
            p['transfer'] = st.holding
            st.holding = None
        if kind == 'open_door' and prop is not None:
            self.doors.setdefault(prop.id, []).append((t0 + .45, 1e9))
        if kind == 'flip_switch':
            self.lights.append(t0 + min(1., dur) * .55)
        return seg

    # ---------------------------------------------------------- evaluation
    def segment(self, actor, t):
        segs = self.tracks[actor]
        lo, hi = 0, len(segs) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if segs[mid].t1 <= t:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def holding(self, actor, t):
        held = []
        for pid, events in self.objects.items():
            if self._held_by(pid, t) == actor:
                held.append(pid)
        return held

    def lights_on(self, t):
        return sum(1 for x in self.lights if x <= t) % 2 == 0

    def door_open(self, door_id, t):
        amount = 0.
        for t_open, t_close in self.doors.get(door_id, []):
            if t >= t_open:
                amount = max(amount, ease((t - t_open) / .5) * (1 - ease((t - t_close) / .6)))
        return amount

    def controls(self, actor, t, partners=None):
        c = self._controls_at(actor, self.segment(actor, t), t, partners, 0)
        piece = self.world.piece
        if piece is not None and hasattr(piece, 'adjust'):
            c = piece.adjust(actor, c, t, self)
        return c

    def _controls_at(self, actor, i, t, partners, depth):
        """Evaluate segment i at t, blending in from the (itself blended) previous segment."""
        segs = self.tracks[actor]
        seg = segs[i]
        c = evaluate(self, actor, seg, t, partners)
        if i > 0 and t - seg.t0 < BLEND and segs[i - 1].posture1 != 'hidden' and seg.posture0 != 'hidden':
            prev = segs[i - 1]
            at = min(t, prev.t1)
            if depth < 4:
                before = self._controls_at(actor, i - 1, at, partners, depth + 1)
            else:
                before = evaluate(self, actor, prev, at, partners)
            c = blend(before, c, ease((t - seg.t0) / BLEND))
        return c

    def pose(self, actor, t, partners=None):
        return solve(self.controls(actor, t, partners))

    def poses(self, t):
        """All actors at time t, with interaction contacts refined against partners."""
        first = {a: self.pose(a, t) for a in self.scene.characters}
        result = {}
        for a in self.scene.characters:
            seg = self.tracks[a][self.segment(a, t)]
            if seg.partner and seg.kind not in ('_idle',):
                result[a] = self.pose(a, t, first)
            else:
                result[a] = first[a]
        return result

    def current_action(self, actor, t):
        seg = self.tracks[actor][self.segment(actor, t)]
        return seg.action if not seg.implicit else None

    def object_position(self, prop_id, t, poses):
        prop = self.world.props[prop_id]
        rest = (self.world.px(prop), self.world.surface_at(self.world.px(prop)))
        state = ('rest', rest)
        for ev in self.objects.get(prop_id, []):
            if ev[0] <= t:
                state = ev[1:] + (ev[0],)
        if state[0] == 'hold':
            j = poses[state[1]].joints if state[1] in poses else None
            if j is None:
                return rest, None
            return j['right_hand'], state[1]
        if state[0] == 'fall':
            actor, t_rel = state[1], state[2]
            start = self.pose(actor, t_rel).joints['right_hand']
            age = t - t_rel
            floor = self.world.floor_at(start[0])
            y = start[1] + 4.5 * age * age
            if y > floor:
                # one small bounce
                over = age - math.sqrt(max(0, (floor - start[1]) / 4.5))
                y = floor - max(0., .06 * math.sin(min(math.pi, over * 9)))
            return (start[0] + .15 * min(age, .4), y), None
        return state[1], None


def move_distance(tau, travel, distance):
    """Distance covered after tau seconds of a move lasting `travel` (trapezoid speed profile)."""
    if travel <= 0 or distance <= 0:
        return distance
    u = max(0., min(1., tau / travel))
    a = .25
    if u < a:
        s = .5 * u * u / a
    elif u > 1 - a:
        s = (1 - a) - .5 * (1 - u) ** 2 / a
    else:
        s = .5 * a + (u - a)
    return distance * max(0., min(1., s / (1 - a)))


# ---------------------------------------------------------------- posture bases
class Ctx:
    pass


def stand_base(world, x, f, t, seed, emotion):
    elev_hip = world.floor_at(x)
    sway = .010 * noise(t * .5, seed)
    breathe = math.sin(t * 2.3 + seed)
    c = Controls(x=x + sway * f, y=STAND_HIP + elev_hip + .0035 * breathe, lean=.03, facing=f, head=.04,
                 emotion=emotion)
    bx, fx = x - .055 * f, x + .065 * f
    c.feet = ((bx, world.floor_at(bx)), (fx, world.floor_at(fx)))
    s = shoulder_of(c)
    c.hands = ((s[0] - .035 * f, s[1] + .305 + .004 * breathe), (s[0] + .045 * f, s[1] + .305 + .004 * breathe))
    return c


def sit_base(world, x, f, t, seed, emotion, seat_y):
    breathe = math.sin(t * 2.3 + seed)
    c = Controls(x=x, y=seat_y + .002 * breathe, lean=-.04, facing=f, head=.06, emotion=emotion)
    c.feet = ((x + .20 * f, 0.), (x + .25 * f, 0.))
    s = shoulder_of(c)
    c.hands = ((x + .16 * f, seat_y - .03), (x + .21 * f, seat_y - .035))
    return c


def lie_base(world, x, f, t, seed, emotion, bed_y):
    breathe = math.sin(t * 1.4 + seed)
    c = Controls(x=x, y=bed_y, lean=math.pi / 2 - .02, facing=f, head=-.05, emotion=emotion)
    c.feet = ((x - .47 * f, bed_y - .015), (x - .46 * f, bed_y - .05))
    c.hands = ((x + .11 * f, bed_y - .07 - .006 * breathe), (x + .19 * f, bed_y - .08 - .006 * breathe))
    return c


def down_base(world, x, f, t, seed, emotion):
    c = Controls(x=x, y=-.075, lean=math.pi / 2 - .05, facing=f, head=-.2, emotion=emotion)
    c.feet = ((x - .46 * f, -.02), (x - .40 * f, -.09))
    c.hands = ((x + .12 * f, -.01), (x + .38 * f, -.02))
    return c


def kneel_base(world, x, f, t, seed, emotion):
    c = Controls(x=x, y=-.30, lean=.08, facing=f, head=.12, emotion=emotion)
    c.feet = ((x - .26 * f, 0.), (x + .19 * f, 0.))
    s = shoulder_of(c)
    c.hands = ((s[0] + .05 * f, s[1] + .28), (x + .2 * f, -.30))
    return c


def base_for(plan, posture, x, f, t, seed, emotion, seat_y):
    w = plan.world
    if posture == 'sit':
        return sit_base(w, x, f, t, seed, emotion, seat_y)
    if posture == 'lie':
        return lie_base(w, x, f, t, seed, emotion, seat_y)
    if posture == 'down':
        return down_base(w, x, f, t, seed, emotion)
    if posture == 'kneel':
        return kneel_base(w, x, f, t, seed, emotion)
    c = stand_base(w, x, f, t, seed, emotion)
    if posture == 'hidden':
        c.visible = 0.
    return c


# ---------------------------------------------------------------- emotion body language
def emote(c, emotion, t, seed, posture):
    f = side(c)
    standing = posture == 'stand'
    s = shoulder_of(c)
    if emotion == 'sad':
        c.lean += .14
        c.head += .38
        c.look = (0., .6)
        if standing:
            c.y += .012
        c.hands = tuple((h[0] - .02 * f, h[1] + .015) for h in c.hands)
    elif emotion == 'tired':
        c.lean += .10
        c.head += .25
        c.y += .01 if standing else 0
    elif emotion == 'happy':
        c.lean -= .04
        c.head -= .10
        if standing:
            c.y -= .008 * abs(math.sin(t * 5 + seed))
    elif emotion in ('proud', 'determined'):
        c.lean -= .07
        c.head -= .08
    elif emotion == 'angry':
        c.lean += .10
        c.head += .10
        c.hands = tuple(mix(h, (s[0] + .10 * f, s[1] + .22), .55) for h in c.hands)
    elif emotion == 'scared':
        c.lean -= .06
        c.y += .03 if standing else 0
        c.x += .0045 * math.sin(t * 43 + seed)
        c.shrug = .03
        c.hands = ((s[0] + .06 * f, s[1] + .13), (s[0] + .12 * f, s[1] + .11))
        c.look = (.3 * math.sin(t * 2.3 + seed), 0.)
    elif emotion == 'anxious':
        c.shrug = .015
        c.hands = ((s[0] + .07 * f + .015 * math.sin(t * 7), s[1] + .2), (s[0] + .10 * f, s[1] + .19 + .015 * math.sin(t * 6)))
        c.look = (.6 * noise(t * 1.7, seed), .1)
    elif emotion == 'embarrassed':
        c.head += .25
        c.look = (-.4, .5)
    elif emotion == 'surprised':
        c.lean -= .08
        c.head -= .05
    elif emotion == 'confused':
        c.head_turn = .12 * math.sin(t * .8 + seed)
    elif emotion == 'thoughtful':
        c.head -= .12
        c.look = (.5, -.7)
    return c


def life(c, t, seed, actor_effects=()):
    """Blinks and other small involuntary motion."""
    period = 3.3 + 1.6 * hashed(seed, 'blink')
    phase = (t + seed * 1.7) % period
    if phase < .13:
        c.blink = 1 - abs(phase - .065) / .065
    return c


EFFECTS = {'sad': (), 'angry': ('vein',), 'scared': ('sweat',), 'anxious': ('sweat',), 'confused': ('question',),
           'embarrassed': ('blush',), 'loving': ('hearts',), 'tired': (), 'surprised': ('exclaim',)}


# ---------------------------------------------------------------- evaluation
def evaluate(plan, actor, seg, t, partners=None):
    w = plan.world
    seed = hashed(actor) * 10
    u = max(0., t - seg.t0)
    dur = max(.05, seg.t1 - seg.t0)
    kind = seg.kind
    emotion = seg.emotion
    f = seg.facing
    ctx = Ctx()
    ctx.plan, ctx.actor, ctx.seg, ctx.t, ctx.u, ctx.dur, ctx.seed = plan, actor, seg, t, u, dur, seed
    ctx.partner_pose = partners.get(seg.partner) if partners and seg.partner else None
    ctx.target = target_point(plan, seg, t, ctx.partner_pose)

    if kind == '_move' or kind in LOCOMOTION:
        c = locomote(plan, seg, t, seed, emotion)
    elif kind == '_idle':
        c = base_for(plan, seg.posture0, seg.x0, f, t, seed, emotion, seg.seat_y)
        c = emote(c, emotion, t, seed, seg.posture0)
        if seg.partner and seg.posture0 != 'hidden':
            # Keep an eye on the other person.
            px = plan.x_at(seg.partner, t)
            want = 1 if px > seg.x0 else -1
            if seg.posture0 == 'stand' and want != f and abs(px - seg.x0) > .25:
                q = ease((u - .4) / .35) if u > .4 else 0.
                c.facing = lerp(f, want, q)
            c.look = (c.look[0] + (.4 if (px > seg.x0) == (c.facing > 0) else -.2), c.look[1])
    else:
        posture = 'stand' if kind in ('get_up', 'recover', 'stand') else seg.posture0
        c = base_for(plan, posture, plan._seg_x(seg, t), f, t, seed, emotion, seg.seat_y)
        c = emote(c, emotion, t, seed, posture)
        c = act(c, kind, ctx)
    # holding an object while doing something that does not use hands explicitly
    if seg.holding and kind in ('_idle', '_move') or (seg.holding and kind in LOCOMOTION):
        c = hold_pose(plan, seg.holding, c)
    effects = set(c.effects) | set(EFFECTS.get(c.emotion, ()))
    if 'exclaim' in effects and u > 1.2:
        effects.discard('exclaim')
    if 'question' in effects and u > 2.5 and kind not in ('scratch_head', 'shrug'):
        effects.discard('question')
    c.effects = tuple(sorted(effects))
    if seg.posture0 == 'hidden' and kind == '_idle':
        c.visible = 0.
    return life(c, t, seed)


def target_point(plan, seg, t, partner_pose):
    w = plan.world
    if seg.partner:
        if partner_pose is not None:
            return partner_pose.joints['head']
        return (plan.x_at(seg.partner, t), -.95)
    if seg.prop and seg.prop in w.props:
        p = w.props[seg.prop]
        x = w.px(p)
        y = {'clock': -1.45, 'window': -.95, 'mirror': -.85, 'calendar': -1.1, 'light_switch': -.62,
             'door': -.48, 'lamp': -1.1, 'sign': -1.1}.get(p.kind, w.surface_at(x) - .03)
        return (x, y)
    return None


def hold_pose(plan, prop_id, c):
    kind = plan.world.props[prop_id].kind if prop_id in plan.world.props else 'phone'
    f = side(c)
    s = shoulder_of(c)
    if kind == 'box':
        c.hands = ((s[0] + .16 * f, s[1] + .24), (s[0] + .22 * f, s[1] + .24))
    elif kind == 'bag':
        c.hands = (c.hands[0], (s[0] + .03 * f, s[1] + .32))
    else:
        c.hands = (c.hands[0], (s[0] + .14 * f, s[1] + .23))
    return c


def locomote(plan, seg, t, seed, emotion):
    """Walk/run cycle with planted feet, arm swing, lean and terrain following."""
    w = plan.world
    kind = seg.kind
    p = seg.params
    u = max(0., t - seg.t0)
    gait = p.get('gait') or {'run': 'run', 'sprint': 'run', 'chase': 'run', 'flee': 'run'}.get(kind, 'walk')
    if kind == 'sneak':
        gait = 'sneak'
    speed = p.get('speed', SPEED.get(kind, .55))
    if kind == 'pace':
        x = plan._seg_x(seg, t)
        dx = math.cos(u / max(.1, seg.t1 - seg.t0) * math.tau)
        smooth = max(-1., min(1., dx * 3))
        direction = 1 if dx >= 0 else -1
        dist = p['amp'] * 4 * (u / max(.1, seg.t1 - seg.t0))
        travel_done = False
    else:
        distance = abs(seg.x1 - seg.x0)
        dist = move_distance(u, p.get('travel', 0.), distance)
        direction = 1 if seg.x1 >= seg.x0 else -1
        x = seg.x0 + direction * dist
        travel_done = u >= p.get('travel', 0.)
    stride = {'walk': .44, 'run': .78, 'sneak': .30}[gait]
    stride *= .85 if emotion in ('sad', 'tired') else 1.
    lift = {'walk': .075, 'run': .16, 'sneak': .05}[gait]
    phase = dist / stride
    feet = []
    for i in range(2):
        ph = phase + i * .5
        step = math.floor(ph)
        q = ph - step
        if kind == 'pace':
            fx = x + smooth * .3 * stride * math.sin(ph * math.tau)
            fy = -max(0., math.sin(ph * math.tau)) * lift * abs(smooth)
        else:
            anchor = seg.x0 + direction * (step - i * .5 + .3) * stride
            if q < .6:
                fx, fy = anchor, 0.
            else:
                s = (q - .6) / .4
                fx = anchor + direction * stride * ease(s)
                fy = -math.sin(math.pi * s) * lift
        fy += w.floor_at(fx)
        feet.append((fx, fy))
    elev = (w.floor_at(feet[0][0]) + w.floor_at(feet[1][0])) / 2
    bob = math.cos(phase * math.tau * 2) * {'walk': .012, 'run': .03, 'sneak': .008}[gait]
    hip_y = {'walk': STAND_HIP, 'run': STAND_HIP + .03, 'sneak': STAND_HIP + .08}[gait] + elev + bob
    lean = {'walk': .07, 'run': .22, 'sneak': .22}[gait]
    if kind == 'sprint':
        lean += .08
    c = Controls(x=x, y=hip_y, lean=lean, facing=smooth if kind == 'pace' else direction,
                 head=-.05 if gait == 'run' else .02, emotion=emotion)
    # feet indices: put the back foot first relative to facing
    c.feet = (feet[0], feet[1])
    s = shoulder_of(c)
    hands = []
    for i in range(2):
        other = feet[1 - i]
        swing = max(-.22, min(.22, (other[0] - x) * direction * 1.15))
        if gait == 'run':
            hands.append((s[0] + direction * (swing * .9 + .05), s[1] + .17 - .05 * abs(swing)))
        elif gait == 'sneak':
            hands.append((s[0] + direction * (.14 + .04 * i), s[1] + .16))
        else:
            hands.append((s[0] + direction * swing, s[1] + .30 - .03 * abs(swing)))
    c.hands = tuple(hands)
    c = emote(c, emotion, t, seed, 'stand') if emotion not in ('scared', 'anxious', 'angry') else c
    if emotion == 'scared':
        c.effects = ('sweat',)
    if travel_done and kind != 'pace':
        # settle onto planted feet after arriving
        rest = stand_base(w, seg.x1, direction, t, seed, emotion)
        rest = emote(rest, emotion, t, seed, 'stand')
        c = blend(c, rest, ease((u - p.get('travel', 0.)) / .35))
    if p.get('door') and u >= p.get('travel', 0.):
        door_t = u - p['travel']
        c.visible = 1 - ease((door_t - .55) / .45)
        c.x += direction * .25 * ease((door_t - .35) / .6)
    if kind == 'leave' and not p.get('door') and travel_done:
        c.visible = 0.
    return c


def interp_keys(keys, u):
    """Piecewise eased interpolation through (time, value) keys."""
    if u <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if u <= t1:
            q = ease((u - t0) / max(1e-6, t1 - t0))
            if isinstance(a, tuple):
                return mix(a, b, q)
            return lerp(a, b, q)
    return keys[-1][1]


def act(c, kind, ctx):
    """Apply a gesture / interaction / object action on top of the posture base."""
    seg, u, dur, t, seed = ctx.seg, ctx.u, ctx.dur, ctx.t, ctx.seed
    plan = ctx.plan
    w = plan.world
    f = side(c)
    s = shoulder_of(c)
    neck, hd = head_of(c)
    tgt = ctx.target
    gin = ease(u / .4)
    hand = lambda dx, dy: (s[0] + dx * f, s[1] + dy)     # point relative to shoulder, facing-aware
    effects = set(c.effects)

    def look_at(point, amount=1.):
        if point is None:
            return
        dx = (point[0] - hd[0]) * f
        dy = point[1] - hd[1]
        n = math.hypot(dx, dy) or 1
        c.look = (max(-1, min(1, dx / n)) * amount, max(-1, min(1, dy / n)) * amount)
        if dy < -.3:
            c.head -= .15 * amount

    def reach(point, q, which=1):
        hands = list(c.hands)
        hands[which] = arc(c, hands[which], point, q)
        c.hands = tuple(hands)

    look_at(tgt, .8)
    if kind in ('idle', 'listen', 'look_at', 'stop'):
        if kind == 'listen':
            c.head += .08 * max(0., math.sin(u * 3.1)) * (1 if int(u / 2.2) % 2 == 0 else 0)
        if kind == 'look_at' and tgt is not None:
            c.lean -= .03
    elif kind == 'talk':
        block = int(u / .75)
        q = ease((u % .75) / .3)
        poses = [(.20, .18), (.24, .07), (.15, .22), (.26, .02), (.11, .25), (.22, .12)]
        a = poses[int(hashed(seed, block - 1) * len(poses))]
        b = poses[int(hashed(seed, block) * len(poses))]
        reach(hand(*mix(a, b, q)), gin)
        both = max(0., math.sin(u * math.pi / 2.3)) ** 2
        reach(hand(.10 + .05 * math.sin(u * 3), .17), gin * both, 0)
        c.mouth = (.2 + .5 * abs(math.sin(u * 10.5 + seed))) * (1 if (u % 2.6) < 2.2 else 0)
        c.head += .04 * math.sin(u * 4)
        if not seg.partner:
            c.facing = lerp(c.facing, .45 * f, gin)        # address the viewer
            c.look = (-.2, 0.)
    elif kind == 'argue':
        reach(hand(.23, .12 + .07 * math.sin(u * 8)), gin)
        reach(hand(.08, .22), gin * .6, 0)
        c.lean += .12 * gin
        c.mouth = .35 + .45 * abs(math.sin(u * 9))
        c.emotion = 'angry'
    elif kind == 'point':
        aim = tgt if tgt is not None else hand(.34, -.02)
        if tgt is not None:
            d = math.hypot(aim[0] - s[0], aim[1] - s[1]) or 1
            aim = (s[0] + (aim[0] - s[0]) / d * ARM_REACH * .98, s[1] + (aim[1] - s[1]) / d * ARM_REACH * .98)
        reach(aim, gin)
        c.lean += .05 * gin
    elif kind == 'wave':
        reach(hand(.10 + .07 * math.sin(u * 10), -.24), gin)
        c.mouth = .15
    elif kind == 'shrug':
        q = ease(u / .35) * (1 - ease((u - dur + .4) / .4))
        c.hands = (arc(c, c.hands[0], hand(-.17, .20), q), arc(c, c.hands[1], hand(.23, .19), q))
        c.shrug = .045 * q
        c.head_turn = .15 * q
        effects.add('question')
    elif kind == 'think':
        reach(add_pt(hd, (.06 * f, .12)), gin)
        reach(hand(.10, .25), gin, 0)
        c.head -= .18 * gin
        c.look = (.6, -.8)
    elif kind == 'scratch_head':
        reach(add_pt(hd, (-.02 * f, -.09 + .012 * math.sin(u * 22))), gin)
        c.head_turn = .1
        effects.add('question')
    elif kind == 'facepalm':
        reach(add_pt(hd, (.07 * f, .0)), ease(u / .25))
        c.head += .3 * gin
        c.eyes_closed = u > .3
    elif kind == 'head_in_hands':
        reach(add_pt(hd, (.07 * f, .05)), gin, 0)
        reach(add_pt(hd, (.10 * f, .04)), gin)
        c.lean += .30 * gin
        c.head += .45 * gin
        c.y += .01 * math.sin(u * 9) if seg.posture0 == 'stand' else 0
        c.eyes_closed = True
    elif kind == 'cry':
        reach(add_pt(hd, (.05 * f, .02)), gin, 0)
        reach(add_pt(hd, (.10 * f, .01)), gin)
        c.lean += .12
        c.head += .25
        c.shrug = .015 * abs(math.sin(u * 13))
        c.eyes_closed = True
        c.mouth = .25 + .15 * abs(math.sin(u * 7))
        effects.add('tears')
    elif kind == 'celebrate':
        hop = abs(math.sin(u * 5.5)) if seg.posture0 == 'stand' else 0
        c.y -= .13 * hop
        c.feet = tuple((p[0], p[1] - .13 * hop) for p in c.feet)
        s2 = shoulder_of(c)
        c.hands = (arc(c, c.hands[0], (s2[0] - .12 * f, s2[1] - .28), gin), arc(c, c.hands[1], (s2[0] + .18 * f, s2[1] - .28), gin))
        c.mouth = .8
        c.lean -= .08
        effects.add('sparkles')
    elif kind == 'laugh':
        c.lean += (-.18 + .10 * math.sin(u * 9)) * gin
        c.head -= .2 * gin
        reach(hand(.10, .30), gin)
        reach(hand(.05, .29), gin, 0)
        c.mouth = .55 + .4 * abs(math.sin(u * 13))
        c.eyes_closed = True
        c.emotion = 'happy'
    elif kind == 'nod':
        c.head += .3 * max(0., math.sin(u * 7)) * gin
    elif kind == 'shake_head':
        c.head_turn = .45 * math.sin(u * 8) * gin
    elif kind == 'cross_arms':
        reach(hand(.14, .21), gin)
        reach(hand(.16, .19), gin, 0)
        c.lean -= .04
    elif kind == 'hands_on_hips':
        reach((c.x + .05 * f, c.y - .03), gin)
        reach((c.x - .07 * f, c.y - .04), gin, 0)
    elif kind == 'clap':
        apart = .05 + .06 * abs(math.sin(u * 9))
        reach(hand(.22 + apart * .5, .15), gin)
        reach(hand(.22 - apart * .5, .15), gin, 0)
        c.mouth = .3
        effects.add('sparkles')
    elif kind == 'flinch':
        q = ease_out(u / .2) * (1 - ease((u - .8) / 1.))
        c.lean -= .2 * q
        c.x -= .08 * f * ease_out(u / .25)
        c.hands = (arc(c, c.hands[0], hand(.10, .02), q), arc(c, c.hands[1], hand(.16, -.02), q))
        c.shrug = .04 * q
        c.emotion = 'surprised'
        effects.add('exclaim')
    elif kind == 'shiver':
        c.x += .006 * math.sin(u * 50)
        reach(hand(.10, .16), gin)
        reach(hand(.12, .14), gin, 0)
        c.shrug = .03
    elif kind == 'sigh':
        q = math.sin(min(math.pi, u / 1.6 * math.pi))
        c.shrug = .035 * q if u < 1.6 else 0
        c.head += .2 * ease((u - 1) / .6)
        c.mouth = .2 * q
    elif kind == 'stretch':
        q = ease(u / .6) * (1 - ease((u - dur + .7) / .6))
        c.hands = (arc(c, c.hands[0], hand(-.04, -.33), q), arc(c, c.hands[1], hand(.04, -.33), q))
        c.lean -= .12 * q
        c.mouth = .4 * q
        c.eyes_closed = q > .7
    elif kind == 'yawn':
        q = math.sin(min(math.pi, u / 1.8 * math.pi))
        reach(add_pt(hd, (.09 * f, .07)), q)
        c.mouth = .9 * q
        c.eyes_closed = q > .5
        c.head -= .15 * q
        effects.add('zzz')
    elif kind == 'look_around':
        sweep = math.sin(u * 1.9)
        c.facing = f * max(-1., min(1., 2.5 * math.cos(u * 1.4)))
        c.head_turn = .3 * math.sin(u * 3.8)
        c.look = (sweep, -.1)
    elif kind == 'check_watch':
        reach(hand(.18, .14), gin, 0)
        reach(hand(.17, .12), gin)
        c.head += .3 * gin
        c.look = (.3, .8)
    elif kind == 'dance':
        beat = u * 4.2
        c.x += .05 * math.sin(beat * math.pi / 2) * f
        c.y -= .03 * abs(math.sin(beat * math.pi))
        up = .5 + .5 * math.sin(beat * math.pi)
        c.hands = (arc(c, c.hands[0], hand(.06, .18 - .42 * up), gin), arc(c, c.hands[1], hand(.2, -.24 + .42 * up), gin))
        c.lean = .1 * math.sin(beat * math.pi / 2)
        c.mouth = .5
        effects.add('sparkles')
    elif kind == 'bow':
        q = math.sin(min(math.pi, u / 1.4 * math.pi))
        c.lean += .7 * q
        c.head += .2 * q
    elif kind == 'cower':
        q = gin
        c.y += .17 * q
        c.lean += .35 * q
        c.feet = ((c.x - .10 * f, c.feet[0][1]), (c.x + .14 * f, c.feet[1][1]))
        s2 = shoulder_of(c)
        _, hd2 = head_of(c)
        c.hands = (arc(c, c.hands[0], add_pt(hd2, (-.03 * f, -.08)), q), arc(c, c.hands[1], add_pt(hd2, (.05 * f, -.09)), q))
        c.x += .005 * math.sin(u * 45)
        c.eyes_closed = True
        effects.add('sweat')
    elif kind == 'panic':
        reach(add_pt(hd, (-.04 * f, -.08)), gin, 0)
        reach(add_pt(hd, (.06 * f, -.09)), gin)
        c.x += .05 * math.sin(u * 7) * f
        c.feet = tuple((p[0] + .04 * math.sin(u * 7 + i * math.pi) * f, p[1] - .04 * max(0, math.sin(u * 14 + i * math.pi))) for i, p in enumerate(c.feet))
        c.mouth = .7
        c.emotion = 'scared'
        effects.update(('sweat', 'exclaim'))
    elif kind == 'jump':
        k = u / max(.5, min(dur, 1.1))
        crouch = math.sin(min(math.pi, k * 3 * math.pi)) * .06 if k < .33 else 0
        air = math.sin(max(0., min(1., (k - .25) / .55)) * math.pi) * .3
        c.y += crouch - air
        c.feet = tuple((p[0], p[1] - air) for p in c.feet)
        s2 = shoulder_of(c)
        c.hands = (arc(c, c.hands[0], (s2[0] - .1 * f, s2[1] - .25), air / .3), arc(c, c.hands[1], (s2[0] + .15 * f, s2[1] - .25), air / .3))
    elif kind == 'stumble':
        q = math.sin(min(math.pi, u / 1.1 * math.pi))
        c.lean += .45 * q
        c.x += .12 * f * ease(u / 1.1)
        c.hands = (arc(c, c.hands[0], hand(-.2, -.15), q), arc(c, c.hands[1], hand(.28, -.1), q))
        c.feet = (c.feet[0], (c.feet[1][0] + .15 * f * q, c.feet[1][1]))
        effects.add('exclaim')
    elif kind == 'fall':
        q = ease(u / .65)
        down = down_base(w, plan._seg_x(seg, t), f, t, seed, c.emotion)
        c = blend(c, down, q)
        effects.add('exclaim')
    elif kind in ('get_up', 'recover', 'stand'):
        q = ease(u / min(dur, .9))
        if seg.posture0 in ('sit', 'lie', 'down', 'kneel'):
            start = base_for(plan, seg.posture0, seg.x0, f, t, seed, c.emotion, seg.seat_y)
            if seg.posture0 in ('down', 'lie'):
                mid = sit_base(w, seg.x0, f, t, seed, c.emotion, seg.seat_y) if seg.seat_y < -.15 else \
                    kneel_base(w, seg.x0, f, t, seed, c.emotion)
                c = blend(start, mid, q * 2) if q < .5 else blend(mid, c, q * 2 - 1)
            else:
                c = blend(start, c, q)
    elif kind in ('sit', 'lie_down', 'sleep', 'type') and (seg.posture0 == 'stand' or seg.params.get('sit_down')):
        q = ease(u / .75)
        seated = sit_base(w, seg.x1, f, t, seed, c.emotion, seg.seat_y) if kind in ('sit', 'type') else \
            lie_base(w, seg.x1, f, t, seed, c.emotion, seg.seat_y)
        if kind in ('lie_down', 'sleep'):
            mid = sit_base(w, seg.x1, f, t, seed, c.emotion, seg.seat_y - .02)
            stand = c
            c = blend(stand, mid, ease(u / .5)) if u < .5 else blend(mid, seated, ease((u - .5) / .6))
        else:
            c = blend(c, seated, q)
        if kind == 'sleep' and u > 1.2:
            c.eyes_closed = True
            effects.add('zzz')
        if kind == 'type' and u > .75:
            c = typing(c, seg, u, f)
        if kind == 'sit':
            c = emote(c, c.emotion, t, seed, 'sit')
    elif kind == 'sleep':
        c.eyes_closed = True
        effects.add('zzz')
    elif kind == 'type':
        c = typing(c, seg, u, f)
    elif kind in ('kneel', 'crouch'):
        q = ease(u / .6)
        if kind == 'kneel':
            c = blend(c, kneel_base(w, seg.x0, f, t, seed, c.emotion), q)
        else:
            c.y += .16 * q
            c.lean += .35 * q
            c.feet = ((c.x - .09 * f, c.feet[0][1]), (c.x + .14 * f, c.feet[1][1]))
    elif kind == 'turn':
        q = ease(u / .35)
        c.facing = lerp(-seg.facing, seg.facing, q)
    # ---------------- interactions
    elif kind == 'handshake':
        meet = contact_point(c, ctx, -.56, .5)
        meet = (meet[0], meet[1] + .015 * math.sin(u * 14) * ease((u - .3) / .2))
        reach(meet, gin)
        c.mouth = .15
        c.emotion = c.emotion if c.emotion != 'neutral' else 'happy'
    elif kind == 'high_five':
        q = ease(u / .45)
        meet = contact_point(c, ctx, -1.16, .5)
        reach(meet, q)
        c.lean -= .05
        if .4 < u < .8:
            effects.add('sparkles')
        c.emotion = 'happy'
    elif kind == 'hug':
        pp = ctx.partner_pose
        px = pp.joints['shoulder'][0] if pp else plan.x_at(seg.partner, t)
        back = (px + .06 * f, s[1] + .12)
        reach(back, gin)
        reach((px + .02 * f, s[1] + .17), gin, 0)
        c.lean += .12 * gin
        c.head += .15 * gin
        c.eyes_closed = u > .6
        effects.add('hearts')
    elif kind == 'comfort':
        pp = ctx.partner_pose
        sh = pp.joints['shoulder'] if pp else (plan.x_at(seg.partner, t), STAND_HIP - .3)
        reach((sh[0] - .03 * f, sh[1] - .01), gin)
        c.head += .15
        c.lean += .06
        c.emotion = 'loving'
    elif kind == 'comforted':
        c.head += .3 * (1 - ease((u - dur * .6) / 1.))
        c.emotion = 'sad' if u < dur * .6 else 'neutral'
    elif kind == 'push':
        pp = ctx.partner_pose
        chest = pp.joints['shoulder'] if pp else (plan.x_at(seg.partner, t), -.72)
        q = ease(u / .3)
        reach((chest[0] - .03 * f, chest[1] + .07), q)
        reach((chest[0] - .05 * f, chest[1] + .11), q, 0)
        c.lean += .25 * q * (1 - ease((u - .6) / .5))
        c.mouth = .5
    elif kind == 'pushed':
        q = ease_out(u / .5)
        c.x = plan._seg_x(seg, t)
        c.lean -= .35 * math.sin(min(math.pi, u / .9 * math.pi))
        c.hands = (arc(c, c.hands[0], hand(-.1, -.12), q * (1 - ease((u - .7) / .4))), arc(c, c.hands[1], hand(.18, -.15), q * (1 - ease((u - .7) / .4))))
        c.feet = ((c.feet[0][0] - .1 * f * math.sin(min(math.pi, u * 3)), c.feet[0][1]), c.feet[1])
        c.emotion = 'surprised'
        effects.add('exclaim')
    elif kind == 'pull':
        meet = contact_point(c, ctx, -.52, .55)
        reach(meet, gin)
        c.lean -= .18 * ease((u - .4) / .4)
        c.x -= .12 * f * ease((u - .4) / .8)
    elif kind == 'pulled':
        c.lean += .2 * ease((u - .4) / .4)
        reach(hand(.30, .08), gin)
        c.x += .1 * f * ease((u - .4) / .8)
    elif kind in ('give', 'receive'):
        meet = contact_point(c, ctx, -.62, .5)
        q = math.sin(min(math.pi, u / min(dur, 1.4) * math.pi)) if u < min(dur, 1.4) else 0
        reach(meet, ease(min(1, q * 1.4)))
        if kind == 'receive':
            c.emotion = 'happy' if u > .5 else c.emotion
    # ---------------- objects
    elif kind in ('pick_up', 'carry', 'use_phone', 'read', 'drink', 'put_down', 'drop'):
        c = object_action(c, kind, ctx, effects)
    elif kind == 'open_door':
        knob = (tgt[0] - .07 * f, -.50) if tgt else hand(.3, .1)
        q = ease(u / .45) * (1 - ease((u - 1.2) / .4))
        reach(knob, q)
        c.lean += .05 * q
    elif kind == 'flip_switch':
        sw = tgt if tgt else hand(.3, 0)
        q = math.sin(min(math.pi, u / min(dur, 1.1) * math.pi))
        reach(sw, q)
    elif kind == 'look_out_window':
        c.hands = (arc(c, c.hands[0], (c.x - .10 * f, c.y - .04), gin), arc(c, c.hands[1], (c.x - .08 * f, c.y - .06), gin))
        c.head -= .12
        c.lean -= .02
    elif kind == 'lean_on_wall':
        c.lean -= .18 * gin
        c.x += 0
        c.feet = ((c.x + .10 * f, c.feet[0][1]), (c.x + .20 * f, c.feet[1][1]))
        reach(hand(.14, .21), gin)
        reach(hand(.16, .19), gin, 0)
    elif kind == 'flee':
        pass
    c.effects = tuple(sorted(effects | set(c.effects)))
    return c


def arc(c, a, b, q):
    """Move a hand from a to b along an arc around the current shoulder."""
    s = shoulder_of(c)
    f = side(c)
    return arc_mix(s, a, f, s, b, f, max(0., min(1., q)))


def add_pt(a, b):
    return (a[0] + b[0], a[1] + b[1])


def contact_point(c, ctx, height, share):
    """Meeting point between this actor and the partner at `height` (world y above the floor)."""
    plan, seg, t = ctx.plan, ctx.seg, ctx.t
    pp = ctx.partner_pose
    px = pp.joints['shoulder'][0] if pp else plan.x_at(seg.partner, t)
    sx = shoulder_of(c)[0]
    mid_x = sx + (px - sx) * share
    return (mid_x, height + plan.world.floor_at(mid_x))


def typing(c, seg, u, f):
    s = shoulder_of(c)
    desk = seg.params.get('desk_x')
    reach_x = desk - .16 * f if desk is not None else s[0] + .26 * f
    reach_x = s[0] + f * min(abs(reach_x - s[0]), .30)
    y = -.445
    c.hands = ((reach_x - .03 * f, y + .012 * max(0, math.sin(u * 17))), (reach_x + .02 * f, y + .012 * max(0, math.sin(u * 15 + 1.7))))
    c.head += .05
    c.look = (.6, .1)
    return c


def object_action(c, kind, ctx, effects):
    plan, seg, u, dur, t = ctx.plan, ctx.seg, ctx.u, ctx.dur, ctx.t
    f = side(c)
    p = seg.params
    reach_time = p.get('reach', 0.)
    rest = p.get('rest')
    if reach_time and u < reach_time and rest:
        # crouch / reach toward the object, grasp at 45%
        k = u / reach_time
        low = rest[1] > -.30
        down = math.sin(min(math.pi, k / .9 * math.pi))
        if low:
            c.y += .17 * down
            c.lean += .5 * down
            c.feet = (c.feet[0], (c.feet[1][0] + .06 * f * down, c.feet[1][1]))
        else:
            c.lean += .12 * down
        hands = list(c.hands)
        hands[1] = arc(c, hands[1], rest, ease(k / .45) * (1 - ease((k - .45) / .55)))
        c.hands = tuple(hands)
        held_target = hold_target(plan, seg, c, kind, u)
        if k > .45:
            hands[1] = arc(c, rest, held_target, ease((k - .45) / .55))
            c.hands = tuple(hands)
        return c
    if kind in ('put_down', 'drop') and 'place' in p:
        k = u / max(.3, p['release'] * 2)
        place = p['place']
        low = place[1] > -.30
        down = math.sin(min(math.pi, k * math.pi))
        if low:
            c.y += .17 * down
            c.lean += .5 * down
        c.hands = (c.hands[0], arc(c, c.hands[1], place, down))
        return c
    if kind == 'drop':
        c.hands = (c.hands[0], arc(c, c.hands[1], (shoulder_of(c)[0] + .16 * f, shoulder_of(c)[1] + .2), 1 - ease(u / .3)))
        c.emotion = 'surprised' if c.emotion == 'neutral' else c.emotion
        return c
    target = hold_target(plan, seg, c, kind, u)
    c.hands = (c.hands[0], target if reach_time else arc(c, c.hands[1], target, ease(u / .35)))
    settle = ease((u - reach_time) / .35) if reach_time else ease(u / .35)
    if kind == 'use_phone':
        c.head += .22
        c.look = (.5, .7)
        c.hands = (arc(c, c.hands[0], (target[0] - .02 * f, target[1] + .03), .7 * settle), (c.hands[1][0] + .004 * math.sin(u * 13), c.hands[1][1]))
        effects.add('glow')
    elif kind == 'read':
        c.head += .25
        c.look = (.4, .8)
        c.hands = (arc(c, c.hands[0], (target[0] - .05 * f, target[1] + .01), .8 * settle), c.hands[1])
    elif kind == 'drink':
        sip = max(0., math.sin((u - reach_time) * 1.9 - 1.2))
        _, hd = head_of(c)
        mouth = (hd[0] + .11 * f, hd[1] + .07)
        c.hands = (c.hands[0], arc(c, c.hands[1], mouth, sip))
        c.head -= .2 * sip
        c.eyes_closed = sip > .7
    elif kind == 'carry':
        prop = plan.world.props.get(seg.prop)
        if prop and prop.kind == 'box':
            s = shoulder_of(c)
            c.hands = (arc(c, c.hands[0], (s[0] + .16 * f, s[1] + .24), settle), arc(c, c.hands[1], (s[0] + .22 * f, s[1] + .24), settle))
    return c


def hold_target(plan, seg, c, kind, u):
    s = shoulder_of(c)
    _, hd = head_of(c)
    f = side(c)
    if kind == 'use_phone':
        return (hd[0] + .17 * f, hd[1] + .14)
    if kind == 'read':
        return (s[0] + .22 * f, s[1] + .14)
    if kind == 'drink':
        return (s[0] + .17 * f, s[1] + .20)
    return (s[0] + .15 * f, s[1] + .23)


# ---------------------------------------------------------------- cache
_CACHE = {}


def plan_for(scene, ww, wh=None):
    key = (id(scene), round(ww, 4), scene.model_dump_json())
    plan = _CACHE.get(key)
    if plan is None:
        if len(_CACHE) > 48:
            _CACHE.clear()
        plan = _CACHE[key] = ScenePlan(scene, ww, wh)
    return plan
