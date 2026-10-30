"""Articulated stickman rig.

World units: one unit is roughly one character height. The floor is y=0 and
"up" is negative y (screen convention). A character is described by a small
set of *controls* (hip position, torso lean, facing, hand and foot targets,
face state). Controls are easy to blend; joints are derived from them with
two-bone inverse kinematics, so limb lengths never change.
"""
from dataclasses import dataclass, field, replace
import math

THIGH = SHIN = .245
UPPER_ARM = FOREARM = .165
TORSO = .31
NECK = .05
HEAD_R = .12
STAND_HIP = -.465          # hip height when standing (slightly bent knees)
SEAT_HIP = -.29            # hip height when seated on a chair
ARM_REACH = UPPER_ARM + FOREARM
LEG_REACH = THIGH + SHIN

# ---------------------------------------------------------------- vocabulary
# Every action the writer may request. Grouped for the prompt and the planner.
ACTION_GROUPS = {
    'movement': ['walk', 'run', 'sprint', 'sneak', 'pace', 'enter', 'leave', 'stop', 'turn', 'jump', 'climb_stairs'],
    'posture': ['sit', 'stand', 'lie_down', 'sleep', 'get_up', 'kneel', 'crouch', 'fall', 'recover', 'stumble'],
    'gesture': ['idle', 'talk', 'point', 'wave', 'shrug', 'think', 'scratch_head', 'facepalm', 'head_in_hands', 'cry',
                'celebrate', 'laugh', 'argue', 'nod', 'shake_head', 'cross_arms', 'hands_on_hips', 'clap', 'flinch',
                'shiver', 'sigh', 'stretch', 'look_around', 'check_watch', 'dance', 'bow', 'cower', 'panic', 'yawn'],
    'interaction': ['handshake', 'hug', 'high_five', 'comfort', 'push', 'pull', 'give', 'chase'],
    'object': ['pick_up', 'put_down', 'drop', 'carry', 'use_phone', 'type', 'read', 'drink', 'open_door',
               'look_out_window', 'lean_on_wall', 'flip_switch', 'look_at'],
}
ACTIONS = [a for group in ACTION_GROUPS.values() for a in group]

EMOTIONS = ['neutral', 'happy', 'sad', 'angry', 'scared', 'surprised', 'confused', 'thoughtful', 'anxious',
            'tired', 'proud', 'embarrassed', 'loving', 'determined']

# Default emotion an action expresses (None keeps whatever the actor felt).
ACTION_EMOTION = {
    'cry': 'sad', 'head_in_hands': 'sad', 'sigh': 'sad', 'celebrate': 'happy', 'laugh': 'happy', 'dance': 'happy',
    'wave': 'happy', 'high_five': 'happy', 'argue': 'angry', 'push': 'angry', 'think': 'thoughtful',
    'scratch_head': 'confused', 'shrug': 'confused', 'facepalm': 'embarrassed', 'flinch': 'surprised',
    'cower': 'scared', 'panic': 'scared', 'shiver': 'scared', 'yawn': 'tired', 'sleep': 'tired',
    'hug': 'loving', 'comfort': 'loving', 'cross_arms': 'determined', 'hands_on_hips': 'proud',
    'look_around': 'anxious', 'check_watch': 'anxious', 'chase': 'determined', 'look_out_window': 'thoughtful',
    'fall': 'surprised', 'stumble': 'surprised', 'stretch': 'happy', 'clap': 'happy', 'bow': 'proud',
}

# What a partner automatically does when someone performs an interaction on them.
REACTIONS = {
    'handshake': 'handshake', 'hug': 'hug', 'high_five': 'high_five', 'comfort': 'comforted', 'push': 'pushed',
    'pull': 'pulled', 'give': 'receive', 'talk': 'listen', 'argue': 'argue', 'point': 'look_at', 'wave': 'wave',
    'chase': 'flee', 'laugh': 'laugh', 'clap': 'bow',
}

# Prop kinds an action needs (first is preferred when one must be added).
ACTION_PROPS = {
    'sit': ('chair', 'bench', 'sofa', 'bed', 'rock'), 'lie_down': ('bed', 'sofa', 'bench'), 'sleep': ('bed', 'sofa', 'bench'),
    'type': ('computer', 'desk', 'table'), 'use_phone': ('phone',), 'read': ('book',), 'drink': ('cup',),
    'open_door': ('door',), 'look_out_window': ('window',), 'lean_on_wall': ('wall',),
    'flip_switch': ('light_switch',), 'climb_stairs': ('stairs',),
}
HANDHELD = ('phone', 'box', 'book', 'cup', 'bag')
SEATS = ('chair', 'bench', 'sofa', 'bed')

LOCOMOTION = {'walk', 'run', 'sprint', 'sneak', 'pace', 'enter', 'leave', 'stop', 'chase', 'flee', 'climb_stairs'}


def ease(t):
    t = max(0., min(1., t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0., min(1., t))
    return 1 - (1 - t) ** 3


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def lerp(a, b, t):
    return a + (b - a) * t


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def ik(root, target, l1, l2, bend=1):
    """Two-bone IK. Returns (middle joint, end joint); end is clamped to reach."""
    dx, dy = target[0] - root[0], target[1] - root[1]
    d = max(abs(l1 - l2) + 1e-6, min(l1 + l2 - 1e-6, math.hypot(dx, dy)))
    angle = math.atan2(dy, dx)
    offset = math.acos(max(-1., min(1., (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
    mid = (root[0] + l1 * math.cos(angle + bend * offset), root[1] + l1 * math.sin(angle + bend * offset))
    end = (root[0] + d * math.cos(angle), root[1] + d * math.sin(angle))
    return mid, end


@dataclass
class Controls:
    """Blendable description of a character at one instant."""
    x: float = 0.
    y: float = STAND_HIP          # hip height (negative = above floor)
    lean: float = 0.              # torso angle from vertical, positive toward facing
    facing: float = 1.            # -1..1; sign gives side, magnitude <1 turns toward camera
    head: float = 0.              # head pitch: positive looks down, negative looks up
    head_turn: float = 0.         # extra sideways turn of the face (shake head, look around)
    shrug: float = 0.             # shoulder raise
    hands: tuple = ((0., -.15), (0., -.15))   # (back hand, front hand) world targets
    feet: tuple = ((0., 0.), (0., 0.))        # (back foot, front foot) world targets
    look: tuple = (0., 0.)        # pupil direction, -1..1
    emotion: str = 'neutral'
    mouth: float = 0.             # 0 closed .. 1 wide open (speech, laughing)
    blink: float = 0.             # 0 open .. 1 closed
    eyes_closed: bool = False
    effects: tuple = ()
    visible: float = 1.           # 0 hidden (off stage / through a door) .. 1

    def copy(self, **changes):
        return replace(self, **changes)


def _blend_points(a, b, q):
    return tuple(mix(p, r, q) for p, r in zip(a, b))


def polar(root, point, f):
    """Hand position as (radius, angle) around the shoulder; angle 0 = in front, +pi/2 = down."""
    vx, vy = point[0] - root[0], point[1] - root[1]
    return math.hypot(vx, vy), math.atan2(vy, vx * f)


def unpolar(root, r, a, f):
    return (root[0] + r * math.cos(a) * f, root[1] + r * math.sin(a))


def arc_mix(root_a, a, f_a, root_b, b, f_b, q):
    """Interpolate a hand along an arc around the shoulder (never through it)."""
    ra, aa = polar(root_a, a, f_a)
    rb, ab = polar(root_b, b, f_b)
    root = mix(root_a, root_b, q)
    f = f_a + (f_b - f_a) * q
    return unpolar(root, lerp(ra, rb, q), lerp(aa, ab, q), f)


def blend(a, b, q):
    """Blend two Controls. Discrete fields switch half way."""
    if q <= 0:
        return a
    if q >= 1:
        return b
    late = q >= .5
    sa, sb = shoulder_of(a), shoulder_of(b)
    fa, fb = max(-1., min(1., a.facing)), max(-1., min(1., b.facing))
    fa = fa if abs(fa) > .05 else (.05 if fa >= 0 else -.05)
    fb = fb if abs(fb) > .05 else (.05 if fb >= 0 else -.05)
    hands = tuple(arc_mix(sa, ha, 1 if fa >= 0 else -1, sb, hb, 1 if fb >= 0 else -1, q) for ha, hb in zip(a.hands, b.hands))
    return Controls(
        x=lerp(a.x, b.x, q), y=lerp(a.y, b.y, q), lean=lerp(a.lean, b.lean, q), facing=lerp(a.facing, b.facing, q),
        head=lerp(a.head, b.head, q), head_turn=lerp(a.head_turn, b.head_turn, q), shrug=lerp(a.shrug, b.shrug, q),
        hands=hands, feet=_blend_points(a.feet, b.feet, q), look=mix(a.look, b.look, q),
        emotion=b.emotion if late else a.emotion, mouth=lerp(a.mouth, b.mouth, q), blink=max(a.blink, b.blink),
        eyes_closed=b.eyes_closed if late else a.eyes_closed, effects=b.effects if late else a.effects,
        visible=lerp(a.visible, b.visible, q))


def side(c):
    return 1 if c.facing >= 0 else -1


def torso_dir(lean, facing):
    # Continuous in facing so turning never snaps the torso or head.
    return (math.sin(lean) * max(-1., min(1., facing)), -math.cos(lean))


def shoulder_of(c):
    u = torso_dir(c.lean, c.facing)
    return (c.x + u[0] * TORSO, c.y + u[1] * TORSO - c.shrug)


def head_of(c):
    u = torso_dir(c.lean, c.facing)
    s = shoulder_of(c)
    neck = (s[0] + u[0] * NECK, s[1] + u[1] * NECK + c.shrug * .6)
    a = math.atan2(u[1], u[0]) + c.head * max(-1., min(1., c.facing))
    return neck, (neck[0] + math.cos(a) * HEAD_R * 1.05, neck[1] + math.sin(a) * HEAD_R * 1.05)


@dataclass
class Pose:
    joints: dict
    emotion: str = 'neutral'
    facing: float = 1.
    controls: Controls = field(default_factory=Controls)


def _clear_of_shoulder(root, target, f, clearance=.16):
    """Keep hand targets out of the shoulder singularity, continuously.

    A hand target passing straight through the shoulder would whip the elbow
    around in a frame or two; nudging close targets forward and down makes the
    arm sweep smoothly instead."""
    vx, vy = target[0] - root[0], target[1] - root[1]
    d = math.hypot(vx, vy)
    if d >= clearance:
        return target
    push = (clearance - d) * 1.6
    return (target[0] + .8 * f * push, target[1] + .6 * push)


def ik_turning(root, target, l1, l2, bend):
    """IK whose bend may be fractional: |bend|<1 foreshortens the limb as if it rotates in depth."""
    mid, end = ik(root, target, l1, l2, 1)
    if bend >= 1:
        return mid, end
    ax, ay = end[0] - root[0], end[1] - root[1]
    n = ax * ax + ay * ay or 1e-9
    k = ((mid[0] - root[0]) * ax + (mid[1] - root[1]) * ay) / n
    foot = (root[0] + ax * k, root[1] + ay * k)
    return (foot[0] + (mid[0] - foot[0]) * bend, foot[1] + (mid[1] - foot[1]) * bend), end


TURN_WIDTH = .3


def solve(c):
    """Controls -> joint positions. 'right' limbs are the front (camera-near) limbs."""
    f = side(c)
    fc = max(-1., min(1., c.facing))
    hip = (c.x, c.y)
    shoulder = shoulder_of(c)
    neck, head = head_of(c)
    j = {'hip': hip, 'shoulder': shoulder, 'neck': neck, 'head': head}
    for i, name in enumerate(('left', 'right')):      # left = back limb, right = front limb
        depth = (-1 if i == 0 else 1) * .016 * fc
        hh = (hip[0] + depth, hip[1])
        ss = (shoulder[0] + depth * 1.2, shoulder[1])
        bend = max(-1., min(1., fc / TURN_WIDTH))
        knee, foot = ik_turning(hh, c.feet[i], THIGH, SHIN, -bend)
        elbow, hand = ik_turning(ss, _clear_of_shoulder(ss, c.hands[i], f), UPPER_ARM, FOREARM, bend)
        j.update({name + '_hip': hh, name + '_knee': knee, name + '_foot': foot,
                  name + '_shoulder': ss, name + '_elbow': elbow, name + '_hand': hand})
    return Pose(j, c.emotion, c.facing, c)


BONES = [('hip', 'shoulder'), ('shoulder', 'neck'), ('neck', 'head')] + \
    [(center, s + '_' + center) for center in ('hip', 'shoulder') for s in ('left', 'right')] + \
    [(s + '_' + a, s + '_' + b) for s in ('left', 'right') for a, b in
     [('hip', 'knee'), ('knee', 'foot'), ('shoulder', 'elbow'), ('elbow', 'hand')]]

LIMBS = [('hip', 'knee', THIGH), ('knee', 'foot', SHIN), ('shoulder', 'elbow', UPPER_ARM), ('elbow', 'hand', FOREARM)]
