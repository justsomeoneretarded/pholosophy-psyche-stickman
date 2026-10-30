"""Native-resolution renderer: environments, props, expressive characters and an editing camera.

Everything is drawn in world units through a camera (centre + zoom), at 2x
supersampling for smooth lines, then reduced to the output size.
"""
import math
import textwrap
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFont
from pipeline.animation.rig import ease, ease_out, mix, HEAD_R, HANDHELD, Pose
from pipeline.animation.acting import plan_for, STAIR_W, STAIR_H, STAIR_N, TABLE_TOP, BED_TOP, SEAT_TOP, hashed, noise

COLORS = {'main': '#25313f', 'friend': '#2f7f8f', 'shadow': '#5b3b5f', 'future': '#b07a1f'}
FACE = {'main': '#fffaf2', 'friend': '#fffaf2', 'shadow': '#3a2840', 'future': '#fffaf2'}


def _hex(c):
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def tint(a, b, q):
    a, b = _hex(a) if isinstance(a, str) else a, _hex(b) if isinstance(b, str) else b
    return tuple(int(round(x + (y - x) * q)) for x, y in zip(a, b))


class Palette:
    def __init__(self, wall, wall2, floor, floor2, accent, accent2, sky, sky2, ground, ground2):
        self.wall, self.wall2, self.floor, self.floor2 = wall, wall2, floor, floor2
        self.accent, self.accent2, self.sky, self.sky2 = accent, accent2, sky, sky2
        self.ground, self.ground2 = ground, ground2
        self.wood = tint(floor2, '#7a5236', .55)
        self.dark = tint(accent, '#101820', .6)


PALETTES = {
    'reflective': Palette('#ece7dc', '#d8d0c0', '#c9b79c', '#b39f82', '#4f7d8c', '#d98e4a', '#cfe3ec', '#f3efe4', '#a9c48f', '#93b07a'),
    'hopeful': Palette('#f6efdc', '#e6dabc', '#d6bf94', '#c2a679', '#c9962e', '#4f9a7a', '#bfe2f2', '#fff4d6', '#9fcf7f', '#86b86b'),
    'tense': Palette('#e2dee3', '#c9c2cc', '#a99fa8', '#958a95', '#a3484b', '#4b5a7a', '#c5c4d4', '#e8e3e6', '#8f9c86', '#7c8a74'),
    'sad': Palette('#dfe5ea', '#c6d0d9', '#a9b4bf', '#95a1ad', '#5d7896', '#8e7aa8', '#b9c8d6', '#e1e7ec', '#93a89a', '#80968a'),
    'playful': Palette('#fdf0df', '#f3dcc0', '#e2bf94', '#cfa77a', '#e0763e', '#3f8fc4', '#bfe6f5', '#fff3dc', '#a6d97c', '#8dc463'),
}
INTERIOR = ('bedroom', 'classroom', 'office', 'living_room', 'cafe', 'library', 'hallway', 'empty_room', 'staircase')
OUTDOOR = ('street', 'park', 'city', 'crossroads', 'gathering', 'hill', 'nature')

FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


ASSETS = __import__('pathlib').Path(__file__).resolve().parents[2] / 'assets' / 'fonts'
FACES = {'display': ASSETS / 'BebasNeue-Regular.ttf', 'serif': ASSETS / 'CormorantGaramond-Medium.ttf',
         'serif_italic': ASSETS / 'CormorantGaramond-MediumItalic.ttf', 'headline': ASSETS / 'Anton-Regular.ttf'}


@lru_cache(maxsize=160)
def face_font(face, size):
    path = FACES.get(face)
    try:
        return ImageFont.truetype(str(path), max(8, int(size)))
    except (OSError, TypeError):
        return font(size, True)


@lru_cache(maxsize=96)
def font(size, bold=False):
    try:
        return ImageFont.truetype(BOLD_PATH if bold else FONT_PATH, max(8, int(size)))
    except OSError:
        return ImageFont.truetype(FONT_PATH, max(8, int(size)))


def character_scale(size):
    w, h = size
    return min(w * .58, h * .37) if h > w else min(w * .36, h * .49)


def world_size(size):
    s = character_scale(size)
    return size[0] / s, size[1] / s


def actor_pose(scene, actor, t, world_width=None, world_height=None):
    """(Pose, current explicit action or None) — used by QA and tests."""
    ww = world_width or 1920 / character_scale((1920, 1080))
    plan = plan_for(scene, ww, world_height)
    poses = plan.poses(t)
    return poses[actor], plan.current_action(actor, t)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, size, ss, cam, scale, background):
        self.W, self.H = size[0] * ss, size[1] * ss
        self.ss = ss
        self.im = Image.new('RGB', (self.W, self.H), background)
        self.d = ImageDraw.Draw(self.im)
        self.cx, self.cy, self.zoom = cam
        self.k = scale * ss * self.zoom
        self.x0 = self.cx - self.W / 2 / self.k
        self.x1 = self.cx + self.W / 2 / self.k
        self.y0 = self.cy - self.H / 2 / self.k
        self.y1 = self.cy + self.H / 2 / self.k

    def p(self, x, y):
        return ((x - self.cx) * self.k + self.W / 2, (y - self.cy) * self.k + self.H / 2)

    def px(self, v):
        return max(1, int(round(v * self.k)))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0):
        a, b = self.p(min(x0, x1), min(y0, y1)), self.p(max(x0, x1), max(y0, y1))
        self.d.rectangle((a[0], a[1], b[0], b[1]), fill=fill, outline=outline, width=self.px(width) if width else 0)

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, width=0):
        a, b = self.p(min(x0, x1), min(y0, y1)), self.p(max(x0, x1), max(y0, y1))
        if b[0] - a[0] < 2 or b[1] - a[1] < 2:
            return
        self.d.rounded_rectangle((a[0], a[1], b[0], b[1]), radius=max(1, min(self.px(r), int((b[0] - a[0]) / 2), int((b[1] - a[1]) / 2))),
                                 fill=fill, outline=outline, width=self.px(width) if width else 0)

    def poly(self, pts, fill=None, outline=None, width=0):
        self.d.polygon([self.p(*q) for q in pts], fill=fill, outline=outline, width=self.px(width) if width else 1)

    def line(self, pts, fill, width, round_caps=True):
        sp = [self.p(*q) for q in pts]
        wpx = self.px(width)
        self.d.line(sp, fill=fill, width=wpx, joint='curve')
        if round_caps and wpx > 2:
            r = wpx / 2
            for q in (sp[0], sp[-1]):
                self.d.ellipse((q[0] - r, q[1] - r, q[0] + r, q[1] + r), fill=fill)

    def circle(self, x, y, r, fill=None, outline=None, width=0):
        c = self.p(x, y)
        rr = r * self.k
        if rr < .5:
            return
        self.d.ellipse((c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr), fill=fill, outline=outline,
                       width=self.px(width) if width else 0)

    def ellipse(self, x, y, rx, ry, fill=None, outline=None, width=0):
        c = self.p(x, y)
        if rx * self.k < .5 or ry * self.k < .5:
            return
        self.d.ellipse((c[0] - rx * self.k, c[1] - ry * self.k, c[0] + rx * self.k, c[1] + ry * self.k), fill=fill,
                       outline=outline, width=self.px(width) if width else 0)

    def arc(self, x, y, rx, ry, a0, a1, fill, width):
        c = self.p(x, y)
        box = (c[0] - rx * self.k, c[1] - ry * self.k, c[0] + rx * self.k, c[1] + ry * self.k)
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            return
        self.d.arc(box, a0, a1, fill=fill, width=self.px(width))

    def chord(self, x, y, rx, ry, a0, a1, fill):
        c = self.p(x, y)
        box = (c[0] - rx * self.k, c[1] - ry * self.k, c[0] + rx * self.k, c[1] + ry * self.k)
        if box[2] - box[0] < 1 or box[3] - box[1] < 1:
            return
        self.d.chord(box, a0, a1, fill=fill)

    def text(self, x, y, s, size, fill, bold=True, anchor='mm', face=None):
        f = face_font(face, size * self.k) if face else font(size * self.k, bold)
        self.d.text(self.p(x, y), s, font=f, fill=fill, anchor=anchor)


# ---------------------------------------------------------------- camera
FACE_KINDS = {'cry', 'facepalm', 'head_in_hands', 'think', 'laugh', 'sigh', 'shrug', 'scratch_head', 'yawn', 'nod',
              'shake_head', 'use_phone', 'read', 'talk', 'drink', 'look_around', 'check_watch', 'panic', 'flinch'}
BODY_KINDS = {'walk', 'run', 'sprint', 'sneak', 'pace', 'enter', 'leave', 'chase', 'jump', 'fall', 'celebrate',
              'dance', 'climb_stairs', 'stumble', 'stretch', '_move', 'open_door', 'lie_down', 'sleep'}
PAIR_KINDS = {'handshake', 'hug', 'high_five', 'comfort', 'push', 'pull', 'give'}


def _shots(plan, scene):
    if hasattr(plan, '_shots'):
        return plan._shots
    beats = plan.beats
    marks = sorted({0.} | {round(b[0], 3) for b in beats if b[0] < scene.duration - .5})
    shots = []
    for i, m in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else scene.duration + 1e6
        mid = m + min(.6, (end - m) / 2)
        active = [b for b in beats if b[0] <= mid < b[1]]
        if not active:
            framing = ('wide',)
        else:
            pair = next((b for b in active if b[4] and b[4] != b[2]), None)
            body = next((b for b in active if b[3] in BODY_KINDS), None)
            face = next((b for b in active if b[3] in FACE_KINDS), None)
            if pair:
                framing = ('two', pair[2], pair[4])
            elif body:
                framing = ('wide',)
            elif face and len({b[2] for b in active}) == 1:
                framing = ('close', face[2]) if len(shots) % 2 == 0 or len(scene.characters) == 1 else ('medium', face[2])
            else:
                actors = sorted({b[2] for b in active})
                framing = ('medium', actors[0]) if len(actors) == 1 else ('wide',)
        if shots and (shots[-1][2] == framing or m - shots[-1][0] < 1.3):
            shots[-1] = (shots[-1][0], end, shots[-1][2])
            continue
        shots.append((m, end, framing))
    # open on an establishing wide shot
    if shots and shots[0][2] != ('wide',) and len(shots) > 0:
        first = shots[0]
        if first[1] - first[0] > 3.2:
            shots[0] = (first[0], first[0] + 1.6, ('wide',))
            shots.insert(1, (first[0] + 1.6, first[1], first[2]))
    plan._shots = shots
    return shots


def _frame_cam(plan, framing, t, poses, size, scale):
    w, h = size
    ww, wh = w / scale, h / scale
    cy0 = (h / 2 - .78 * h) / scale
    kind = framing[0]
    if kind == 'wide':
        return (ww / 2, cy0, 1.0)
    if kind == 'medium':
        a = framing[1]
        j = poses[a].joints if a in poses else None
        x = j['hip'][0] if j else plan.x_at(a, t)
        y = (j['shoulder'][1] + .12) if j else -.65
        return (x, min(y, cy0 * .6, -.6), 1.35)
    if kind == 'close':
        a = framing[1]
        j = poses[a].joints if a in poses else None
        x, y = (j['head'] if j else (plan.x_at(a, t), -.95))
        return (x, y + .16, 2.15)
    if kind == 'two':
        a, b = framing[1], framing[2]
        xa = poses[a].joints['hip'][0] if a in poses else plan.x_at(a, t)
        xb = poses[b].joints['hip'][0] if b in poses else plan.x_at(b, t)
        zoom = max(1.0, min(1.42, ww * .9 / (abs(xa - xb) + 1.4)))
        return ((xa + xb) / 2, -.68, zoom)
    return (ww / 2, cy0, 1.0)


def _clamp_cam(cam, size, scale):
    cx, cy, zoom = cam
    ww = size[0] / scale
    half = ww / (2 * zoom)
    cx = max(half, min(ww - half, cx)) if half < ww / 2 else ww / 2
    bottom = cy + size[1] / 2 / (scale * zoom)
    min_bottom = .5 if zoom > 1.2 else .3          # never show the floor ending
    return (cx, cy, zoom)


def camera(plan, scene, t, poses, size, scale):
    shots = _shots(plan, scene)
    i = next((k for k, s in enumerate(shots) if s[0] <= t < s[1]), len(shots) - 1)
    t0, t1, framing = shots[i]
    cam = _frame_cam(plan, framing, t, poses, size, scale)
    # slow push-in over every shot keeps the frame alive
    drift = {'push_in': .10, 'pull_out': -.08}.get(scene.camera, .035)
    progress = min(1., (t - t0) / max(2., min(8., t1 - t0)))
    cam = (cam[0], cam[1], cam[2] * (1 + drift * ease(progress)) if drift > 0 else cam[2] * (1.08 + drift * ease(progress)))
    if i > 0:
        prev = shots[i - 1][2]
        same_subject = set(prev[1:]) & set(framing[1:]) or prev == ('wide',) or framing == ('wide',) and len(prev) > 1
        if same_subject and t - t0 < .55:
            before = _frame_cam(plan, prev, t, poses, size, scale)
            q = ease((t - t0) / .55)
            cam = tuple(a + (b - a) * q for a, b in zip(before, cam))
    if scene.camera == 'shake':
        cam = (cam[0] + .01 * math.sin(t * 31) * math.exp(-((t - t0) % 3) * 2), cam[1] + .008 * math.sin(t * 27), cam[2])
    return _clamp_cam(cam, size, scale)


# ---------------------------------------------------------------- environments
def draw_environment(cv, scene, plan, t, pal):
    env = scene.environment
    ww = plan.ww
    X0, X1 = min(-1, cv.x0 - .5), max(ww + 1, cv.x1 + .5)
    top = min(-5., cv.y0 - .5)
    if env in OUTDOOR:
        _sky(cv, pal, X0, X1, top, t)
        _outdoor(cv, env, pal, ww, X0, X1, t, plan)
    elif env in ('void', 'mindscape', 'stage'):
        _abstract(cv, env, pal, ww, X0, X1, top, t)
    else:
        _interior(cv, env, pal, ww, X0, X1, top, t, plan)


def _sky(cv, pal, X0, X1, top, t):
    bands = 10
    for i in range(bands):
        y0 = top + (0 - top) * i / bands
        y1 = top + (0 - top) * (i + 1) / bands
        cv.rect(X0, y0, X1, y1 + .01, tint(pal.sky, pal.sky2, i / (bands - 1)))
    cv.circle(X1 - 1.0 if X1 < 30 else 3, -1.85, .22, fill=tint(pal.sky2, '#fff2c4', .7))
    for i in range(4):
        x = (i * 1.3 + t * .05 + hashed(i) * 2) % (X1 - X0 + 2) + X0 - 1
        y = -1.95 + .25 * hashed(i, 'y')
        for dx, r in ((0, .13), (.13, .17), (.29, .12)):
            cv.circle(x + dx, y + (.17 - r) * .6, r, fill='#ffffff')


def _tree(cv, x, base, s, pal, t, i):
    sway = .015 * math.sin(t * .9 + i)
    cv.rect(x - .035 * s, base - .55 * s, x + .035 * s, base, fill=tint(pal.wood, '#3b2a1e', .3))
    for dx, dy, r in ((0, -.75, .30), (-.20, -.58, .22), (.22, -.60, .23), (.05, -.95, .2)):
        cv.circle(x + (dx + sway) * s, base + dy * s, r * s, fill=tint(pal.ground2, '#2f5a33', .35 + .1 * (i % 3)))


def _outdoor(cv, env, pal, ww, X0, X1, t, plan=None):
    horizon = -.22
    if env in ('hill', 'nature', 'park'):
        for k, (amp, col) in enumerate(((.55, tint(pal.ground, pal.sky, .45)), (.35, tint(pal.ground, pal.sky, .2)))):
            pts = [(X0, 0)] + [(x / 10, horizon - amp - .18 * math.sin(x / 10 * 1.3 + k * 2)) for x in
                               range(int(X0 * 10), int(X1 * 10) + 2)] + [(X1, 0)]
            cv.poly(pts, fill=col)
    if env in ('city', 'street'):
        for layer, (depth, col) in enumerate(((1.6, tint(pal.sky, pal.accent2, .25)), (1.0, tint(pal.wall2, pal.accent, .25)))):
            x = X0
            i = 0
            while x < X1:
                bw = .45 + .5 * hashed(layer, i)
                bh = depth * (.7 + .6 * hashed(layer, i, 'h'))
                cv.rect(x, horizon - bh, x + bw - .04, 0, fill=col)
                if layer == 1:
                    for wy in range(int(bh / .22)):
                        for wx in range(int(bw / .16)):
                            lit = hashed(i, wx, wy) > .45
                            cv.rect(x + .06 + wx * .15, horizon - bh + .1 + wy * .22, x + .12 + wx * .15,
                                    horizon - bh + .19 + wy * .22, fill='#fff1b8' if lit else tint(col, '#000', .15))
                x += bw
                i += 1
    cv.rect(X0, horizon, X1, 0, fill=tint(pal.ground, pal.sky, .15))
    if env in ('street', 'city'):
        cv.rect(X0, horizon, X1, 0, fill=tint(pal.floor, '#888', .4))
        cv.rect(X0, 0, X1, 4, fill=tint(pal.floor2, '#777', .45))
        cv.rect(X0, 0, X1, .03, fill=tint(pal.floor2, '#555', .5))
        for i in range(int(X0), int(X1) + 1):
            if i % 2 == 0:
                lx = i * 1.0 + .3
                cv.rect(lx - .015, -1.45, lx + .015, 0, fill='#4a4f57')
                cv.line([(lx, -1.45), (lx + .16, -1.5)], '#4a4f57', .025)
                cv.ellipse(lx + .2, -1.48, .07, .035, fill='#fff1b8')
    else:
        cv.rect(X0, 0, X1, 4, fill=pal.ground)
        for i in range(int(X0 * 6), int(X1 * 6)):
            if hashed(i, 'g') > .55:
                gx = i / 6
                cv.line([(gx, .06 + .1 * hashed(i)), (gx + .02, .02 + .1 * hashed(i))], pal.ground2, .012)
    if env in ('park', 'nature', 'hill'):
        for i in range(int(X0 / .9) - 1, int(X1 / .9) + 2):
            if hashed(i, 'tree') > .45:
                _tree(cv, i * .9 + .4 * hashed(i), horizon + .02, .8 + .4 * hashed(i, 's'), pal, t, i)
        if env == 'park':
            cv.poly([(X0, .9), (X1, .9), (X1, 1.4), (X0, 1.4)], fill=tint(pal.floor, pal.ground, .5))
        for i in range(3):
            bx = (t * .3 + i * 1.7) % (X1 - X0 + 2) + X0
            by = -1.6 - .15 * i + .03 * math.sin(t * 5 + i)
            wing = .04 * math.sin(t * 9 + i)
            cv.line([(bx - .07, by - wing), (bx, by), (bx + .07, by - wing)], '#3a4250', .012)
        if env == 'nature':
            for i in range(int(X0 * 4), int(X1 * 4)):
                if hashed(i, 'fl') > .8:
                    fx = i / 4
                    cv.circle(fx, .12 + .3 * hashed(i), .025, fill=pal.accent2)
    if env == 'crossroads':
        cv.poly([(ww * .5 - .35, horizon), (ww * .5 + .35, horizon), (ww * .5 + 2.2, 4), (ww * .5 - 2.2, 4)], fill=tint(pal.floor, '#999', .3))
        cv.poly([(ww * .5 - .2, horizon), (ww * .5 - .05, horizon), (ww * .05, horizon - .0), (ww * .02, horizon)], fill=tint(pal.floor, '#999', .3))
        cv.poly([(ww * .5 + .05, horizon), (ww * .5 + .2, horizon), (ww * .98, horizon), (ww * .95, horizon)], fill=tint(pal.floor, '#999', .3))
        for i in range(6):
            y = .1 + i * .3
            cv.rect(ww * .5 - .02 - i * .01, y, ww * .5 + .02 + i * .01, y + .12, fill='#f4f1e8')
        if not any(p.kind == 'sign' for p in plan.scene.props):
            _signpost(cv, ww * .5, pal, t)
    if env == 'gathering':
        for i in range(int(X0 / .32), int(X1 / .32) + 1):
            if hashed(i, 'crowd') > .25:
                gx = i * .32 + .1 * hashed(i, 'o')
                _ghost(cv, gx, -.12, .55 + .1 * hashed(i, 'sz'), tint(pal.sky, '#5a6170', .45), t, i)


def _ghost(cv, x, base, s, col, t, i):
    bob = .01 * math.sin(t * 2 + i)
    hip = (x, base - .47 * s + bob)
    sh = (x, hip[1] - .31 * s)
    w = .028 * s
    cv.line([hip, sh], col, w)
    for k in (-1, 1):
        cv.line([hip, (x + .07 * k * s, base)], col, w)
        cv.line([sh, (x + .1 * k * s, sh[1] + .27 * s + .02 * math.sin(t * 1.3 + i + k))], col, w)
    cv.circle(x, sh[1] - .17 * s, .12 * s, fill=col)


def _signpost(cv, x, pal, t):
    cv.rect(x - .025, -1.35, x + .025, 0, fill=pal.wood)
    cv.poly([(x - .02, -1.28), (x - .5, -1.28), (x - .58, -1.2), (x - .5, -1.12), (x - .02, -1.12)], fill=pal.accent)
    cv.poly([(x + .02, -1.05), (x + .5, -1.05), (x + .58, -.97), (x + .5, -.89), (x + .02, -.89)], fill=pal.accent2)


def _abstract(cv, env, pal, ww, X0, X1, top, t):
    if env == 'stage':
        cv.rect(X0, top, X1, 0, fill=tint(pal.wall, '#2b2230', .75))
        cv.poly([(ww / 2 - .25, top), (ww / 2 + .25, top), (ww / 2 + 1.3, 0), (ww / 2 - 1.3, 0)], fill=tint(pal.wall, '#2b2230', .45))
        cv.ellipse(ww / 2, .06, 1.35, .14, fill=tint(pal.floor, '#fff3c0', .35))
        for k in (-1, 1):
            edge = 0 if k < 0 else ww
            for i in range(5):
                x = edge - k * (.05 + i * .11)
                cv.rect(x - .06, top, x + .06, 0, fill=tint('#8b2635', '#4a1018', (i % 2) * .35))
        cv.rect(X0, top, X1, top + (cv.y0 - top) + .25, fill='#7a1f2c')
        cv.rect(X0, 0, X1, 4, fill=pal.wood)
        for i in range(8):
            cv.rect(X0, .05 + i * .14, X1, .055 + i * .14, fill=tint(pal.wood, '#000', .12))
        return
    if env == 'mindscape':
        for i in range(12):
            cv.rect(X0, top + (0 - top) * i / 12, X1, top + (0 - top) * (i + 1) / 12 + .01,
                    tint('#1c2146', '#5b4b8a', i / 11))
        cv.rect(X0, 0, X1, 4, fill='#3d3470')
        cv.ellipse((X0 + X1) / 2, .05, 2.2, .12, fill='#4b4084')
        dots = []
        for i in range(14):
            x = (hashed(i, 'mx') * (X1 - X0 + 2) + X0 + .15 * math.sin(t * .4 + i))
            y = -.4 - 1.6 * hashed(i, 'my') + .1 * math.sin(t * .6 + i * 2)
            dots.append((x, y))
        for a, b in zip(dots, dots[1:]):
            if math.dist(a, b) < 1.4:
                cv.line([a, b], (120, 120, 180), .005)
        for i, (x, y) in enumerate(dots):
            r = .03 + .03 * hashed(i, 'r')
            shape = i % 3
            col = ('#9fb4ff', '#f3c6ff', '#ffe29a')[i % 3]
            if shape == 0:
                cv.circle(x, y, r, fill=col)
            elif shape == 1:
                a0 = t * .5 + i
                cv.poly([(x + r * 1.4 * math.cos(a0 + k * 2.094), y + r * 1.4 * math.sin(a0 + k * 2.094)) for k in range(3)], fill=col)
            else:
                cv.circle(x, y, r * 1.3, outline=col, width=.008)
        return
    # void: soft spotlight on a plain ground
    cv.rect(X0, top, X1, 0, fill=tint(pal.wall, '#ffffff', .3))
    for i in range(6, 0, -1):
        cv.ellipse(ww / 2, -.8, .6 * i, .5 * i, fill=tint(pal.wall, '#ffffff', .5 - i * .07))
    cv.rect(X0, 0, X1, 4, fill=tint(pal.wall, pal.floor, .35))
    cv.ellipse(ww / 2, .04, 1.4, .1, fill=tint(pal.wall, pal.floor, .5))


def _window(cv, x, y0, y1, half, pal, t, curtains=True):
    cv.rect(x - half - .03, y0 - .03, x + half + .03, y1 + .05, fill=tint(pal.wall2, '#ffffff', .4))
    cv.rect(x - half, y0, x + half, y1, fill=tint(pal.sky, pal.sky2, .3))
    cv.circle(x + half * .45 + .02 * math.sin(t * .2), y0 + (y1 - y0) * .35, .07, fill='#ffffff')
    cv.circle(x + half * .45 + .08 + .02 * math.sin(t * .2), y0 + (y1 - y0) * .38, .05, fill='#ffffff')
    cv.rect(x - .012, y0, x + .012, y1, fill=tint(pal.wall2, '#ffffff', .4))
    cv.rect(x - half, (y0 + y1) / 2 - .012, x + half, (y0 + y1) / 2 + .012, fill=tint(pal.wall2, '#ffffff', .4))
    cv.rect(x - half - .06, y1, x + half + .06, y1 + .04, fill=pal.wall2)
    if curtains:
        sway = .008 * math.sin(t * .8)
        rail = y0 - .1
        cv.rect(x - half - .2, rail - .015, x + half + .2, rail + .01, fill=pal.wood)
        for k in (-1, 1):
            inner = x + k * (half + .02)
            outer = x + k * (half + .17)
            cv.poly([(inner, rail), (outer, rail), (outer + k * .02 + sway, y1 + .2), (inner + k * .05 + sway, y1 + .2)], fill=pal.accent2)
            for fold in (.35, .7):
                fx = inner + (outer - inner) * fold
                cv.line([(fx, rail + .02), (fx + k * .02 + sway, y1 + .18)], tint(pal.accent2, '#000', .15), .008)


def _interior(cv, env, pal, ww, X0, X1, top, t, plan=None):
    cv.rect(X0, top, X1, 0, fill=pal.wall)
    cv.rect(X0, -1.62, X1, -1.6, fill=pal.wall2)
    cv.rect(X0, -.08, X1, 0, fill=pal.wall2)
    cv.rect(X0, 0, X1, 4, fill=pal.floor)
    for i, y in enumerate((.035, .09, .17, .29, .46, .7)):
        cv.rect(X0, y, X1, y + .006 + i * .002, fill=pal.floor2)
    has_window = any(p.kind == 'window' for p in plan.scene.props) if plan else False
    if env == 'bedroom':
        if not has_window:
            _window(cv, ww * .18, -1.35, -.78, .28, pal, t)
        cv.rect(ww * .55 - .22, -1.4, ww * .55 + .22, -1.0, fill=pal.accent)
        cv.poly([(ww * .55 - .18, -1.04), (ww * .55 - .04, -1.26), (ww * .55 + .06, -1.12), (ww * .55 + .12, -1.2), (ww * .55 + .18, -1.04)], fill=tint(pal.accent, '#ffffff', .5))
        cv.rect(ww * .92 - .14, -.38, ww * .92 + .14, 0, fill=pal.wood)
        cv.rect(ww * .92 - .015, -.62, ww * .92 + .015, -.38, fill='#555')
        cv.poly([(ww * .92 - .09, -.62), (ww * .92 + .09, -.62), (ww * .92 + .06, -.76), (ww * .92 - .06, -.76)], fill=pal.accent2)
    elif env == 'office':
        bx = ww * .8
        cv.rect(bx - .32, -1.38, bx + .32, -.76, fill=tint(pal.sky, pal.sky2, .3))
        for i in range(9):
            cv.rect(bx - .32, -1.38 + i * .07, bx + .32, -1.36 + i * .07, fill=tint(pal.wall2, '#fff', .3))
        cv.rect(ww * .42 - .3, -1.35, ww * .42 + .3, -.95, fill=tint(pal.wood, '#d9b98c', .5))
        for i in range(5):
            nx = ww * .42 - .24 + i * .11
            cv.rect(nx, -1.3 + .06 * (i % 2), nx + .08, -1.22 + .06 * (i % 2), fill=('#f7d65a', '#8fd0e8', '#f29bb1')[i % 3])
        _plant(cv, ww * .05 + .1, pal, t)
        cv.rect(ww * .95 - .16, -.62, ww * .95 + .16, 0, fill=tint(pal.wall2, '#777', .35))
        for i in range(3):
            cv.rect(ww * .95 - .13, -.58 + i * .2, ww * .95 + .13, -.43 + i * .2, outline=tint(pal.wall2, '#555', .5), width=.008)
    elif env == 'classroom':
        cx = ww * .5
        cv.rect(cx - .95, -1.55, cx + .95, -.9, fill='#2f4a3c')
        cv.rect(cx - .97, -.9, cx + .97, -.86, fill=pal.wood)
        for i in range(6):
            y = -1.45 + i * .09
            x = cx - .8 + .2 * hashed(i)
            cv.line([(x, y), (x + .5 + .4 * hashed(i, 'l'), y + .01 * math.sin(i))], '#e8efe9', .01)
        cv.circle(cx + .55, -1.25, .12, outline='#e8efe9', width=.01)
        cv.line([(cx + .45, -1.15), (cx + .65, -1.35)], '#e8efe9', .01)
    elif env == 'library':
        for row in range(6):
            y = -1.7 + row * .27
            cv.rect(X0, y + .24, X1, y + .27, fill=pal.wood)
            x = X0
            i = 0
            while x < X1:
                bw = .035 + .03 * hashed(row, i)
                bh = .17 + .06 * hashed(row, i, 'h')
                col = (pal.accent, pal.accent2, tint(pal.accent, '#000', .3), tint(pal.accent2, '#fff', .3), pal.wood)[int(hashed(row, i, 'c') * 5)]
                cv.rect(x, y + .24 - bh, x + bw, y + .24, fill=col)
                x += bw + .006
                i += 1
    elif env == 'living_room':
        for i, (fx, fw) in enumerate(((.25, .18), (.42, .12), (.62, .2))):
            cv.rect(ww * fx - fw, -1.42, ww * fx + fw, -1.42 + fw * 1.3, fill=tint(pal.wall2, '#000', .1))
            cv.rect(ww * fx - fw + .03, -1.39, ww * fx + fw - .03, -1.45 + fw * 1.3, fill=(pal.accent, pal.accent2, pal.sky)[i])
        cv.ellipse(ww * .5, .25, 1.2, .14, fill=tint(pal.accent2, pal.floor, .5))
        if not has_window:
            _window(cv, ww * .88, -1.35, -.75, .22, pal, t)
    elif env == 'cafe':
        cv.rect(X0, -.62, X1, 0, fill=tint(pal.wood, '#000', .1))
        cv.rect(X0, -.66, X1, -.6, fill=tint(pal.wood, '#fff', .15))
        for i in range(int(X0 / .9), int(X1 / .9) + 1):
            lx = i * .9 + .45
            cv.line([(lx, top), (lx, -1.45)], '#333', .008)
            cv.chord(lx, -1.45, .11, .09, 180, 360, pal.accent)
            cv.ellipse(lx, -1.44, .05, .02, fill='#fff1b8')
            cv.rect(lx - .03, -.74, lx + .03, -.66, fill='#f4efe6')
        cv.rect(ww * .5 - .35, -1.35, ww * .5 + .35, -.9, fill='#2c2c2c')
        for i in range(4):
            cv.line([(ww * .5 - .28, -1.25 + i * .09), (ww * .5 + .1 * hashed(i), -1.25 + i * .09)], '#e9e4da', .012)
    elif env == 'hallway':
        for i in range(int(X0 / 1.1), int(X1 / 1.1) + 1):
            dx = i * 1.1 + .55
            cv.rect(dx - .22, -1.25, dx + .22, 0, fill=tint(pal.wood, pal.wall, .3))
            cv.rect(dx - .18, -1.21, dx + .18, -.02, fill=tint(pal.wood, pal.wall, .15))
            cv.circle(dx + .13, -.55, .02, fill='#c9a54b')
            cv.ellipse(dx + .55, -1.3, .05, .08, fill='#fff1b8')
    elif env == 'empty_room':
        swing = .25 * math.sin(t * 1.3)
        bx = ww * .5 + swing * .4
        cv.line([(ww * .5, top), (bx, -1.6)], '#333', .008)
        cv.circle(bx, -1.56, .05, fill='#fff1b8')
        cv.ellipse(bx, .03, .5, .05, fill=tint(pal.floor, '#fff1b8', .25))
        cv.line([(ww * .2, -1.4), (ww * .22, -1.25), (ww * .2, -1.12), (ww * .23, -1.0)], pal.wall2, .008)
    elif env == 'staircase':
        for i in range(10):
            x = ww * .55 + i * .2
            cv.rect(x, -1.0 - i * .12, X1, -.95 - i * .12, fill=pal.wall2)


def _plant(cv, x, pal, t):
    cv.poly([(x - .1, -.25), (x + .1, -.25), (x + .07, 0), (x - .07, 0)], fill=pal.accent2)
    for i in range(7):
        a = -math.pi / 2 + (i - 3) * .35 + .05 * math.sin(t * 1.1 + i)
        L = .28 + .06 * (i % 2)
        tip = (x + math.cos(a) * L, -.25 + math.sin(a) * L)
        cv.line([(x, -.25), tip], tint(pal.ground2, '#2f5a33', .4), .03)


# ---------------------------------------------------------------- props
def draw_furniture(cv, scene, plan, t, pal, poses):
    w = plan.world
    for p in scene.props:
        x = w.px(p)
        kind = p.kind
        if kind == 'door':
            opening = plan.door_open(p.id, t)
            cv.rect(x - .27, -1.34, x + .27, 0, fill=tint(pal.wall2, '#000', .15))
            cv.rect(x - .23, -1.3, x + .23, 0, fill='#2a2a33')
            leaf = .46 * (1 - .82 * opening)
            cv.rect(x - .23, -1.3, x - .23 + leaf, 0, fill=pal.wood)
            if leaf > .12:
                cv.rect(x - .23 + leaf * .15, -1.2, x - .23 + leaf * .85, -.75, outline=tint(pal.wood, '#000', .2), width=.01)
                cv.circle(x - .23 + leaf * .88, -.5, .025, fill='#d6b04d')
        elif kind == 'window':
            _window(cv, x, -1.4, -.8, .3, pal, t)
        elif kind == 'mirror':
            cv.ellipse(x, -.9, .19, .37, fill=pal.wood)
            cv.ellipse(x, -.9, .16, .33, fill=tint(pal.sky, '#ffffff', .5))
            cv.line([(x - .06, -1.05), (x + .04, -1.15)], '#ffffff', .015)
        elif kind == 'clock':
            cv.circle(x, -1.45, .14, fill='#ffffff', outline=pal.dark, width=.018)
            for k in range(12):
                a = k / 12 * math.tau
                cv.line([(x + .11 * math.sin(a), -1.45 - .11 * math.cos(a)), (x + .125 * math.sin(a), -1.45 - .125 * math.cos(a))], pal.dark, .008)
            a = t / 60 * math.tau * 6
            cv.line([(x, -1.45), (x + .1 * math.sin(a), -1.45 - .1 * math.cos(a))], pal.accent, .008)
            a2 = t / 60 * math.tau * .5 + 1
            cv.line([(x, -1.45), (x + .07 * math.sin(a2), -1.45 - .07 * math.cos(a2))], pal.dark, .016)
        elif kind == 'calendar':
            cv.rect(x - .14, -1.32, x + .14, -.98, fill='#ffffff')
            cv.rect(x - .14, -1.32, x + .14, -1.24, fill=pal.accent)
            for r in range(3):
                for c in range(5):
                    cv.rect(x - .12 + c * .05, -1.2 + r * .06, x - .09 + c * .05, -1.17 + r * .06, fill=tint(pal.wall2, '#000', .1))
        elif kind == 'light_switch':
            cv.rrect(x - .035, -.68, x + .035, -.56, .01, fill='#f5f3ee', outline=tint(pal.wall2, '#000', .2), width=.005)
            on = plan.lights_on(t)
            cv.rect(x - .01, -.65 if on else -.62, x + .01, -.62 if on else -.59, fill='#888')
        elif kind == 'lamp':
            cv.rect(x - .1, -.03, x + .1, 0, fill='#444')
            cv.rect(x - .012, -1.12, x + .012, 0, fill='#555')
            cv.poly([(x - .13, -1.1), (x + .13, -1.1), (x + .09, -1.3), (x - .09, -1.3)], fill=pal.accent2)
        elif kind == 'plant':
            _plant(cv, x, pal, t)
        elif kind == 'tv':
            cv.rect(x - .35, -.35, x + .35, 0, fill=pal.wood)
            cv.rect(x - .38, -.92, x + .38, -.42, fill='#1d1f24')
            flick = int(t * 2) % 3
            cv.rect(x - .34, -.88, x + .34, -.46, fill=(tint(pal.sky, '#6aa9d8', .4), tint(pal.accent, '#fff', .4), tint(pal.accent2, '#fff', .3))[flick])
        elif kind == 'sign':
            _signpost(cv, x, pal, t)
        elif kind == 'wall':
            cv.rect(x - .05, -1.75, x + .05, 0, fill=tint(pal.wall2, '#000', .12))
        elif kind == 'ladder':
            for k in (-1, 1):
                cv.line([(x + k * .12 - .15, 0), (x + k * .12 + .1, -1.3)], pal.wood, .025)
            for i in range(6):
                f = (i + .5) / 6.5
                cv.line([(x - .27 + .25 * f, -1.3 * f), (x - .03 + .25 * f, -1.3 * f)], pal.wood, .018)
        elif kind == 'rope':
            sway = .05 * math.sin(t * 1.2)
            cv.line([(x, cv.y0 - .1), (x + sway, -.45)], tint(pal.wood, '#c9a46c', .5), .02)
        elif kind == 'stairs':
            x0 = w.stairs_x0(p)
            for i in range(STAIR_N):
                cv.rect(x0 + i * STAIR_W, -(i + 1) * STAIR_H, x0 + STAIR_N * STAIR_W + .55, -i * STAIR_H, fill=tint(pal.wood, pal.wall, .2 + .05 * i))
                cv.rect(x0 + i * STAIR_W, -(i + 1) * STAIR_H, x0 + (i + 1) * STAIR_W, -(i + 1) * STAIR_H + .02, fill=tint(pal.wood, '#fff', .2))
            cv.line([(x0, -.75), (x0 + STAIR_N * STAIR_W, -.75 - STAIR_N * STAIR_H), (x0 + STAIR_N * STAIR_W + .55, -.75 - STAIR_N * STAIR_H)], pal.dark, .02)
        elif kind == 'bed':
            f = w.seat_facing(p)
            cv.rect(x - .52, BED_TOP + .06, x + .52, -.06, fill=pal.wood)
            for k in (-1, 1):
                cv.rect(x + k * .48 - .03, -.08, x + k * .48 + .03, 0, fill=tint(pal.wood, '#000', .2))
            cv.rrect(x + f * .52 - .05, BED_TOP - .32, x + f * .52 + .05, 0, .03, fill=tint(pal.wood, '#000', .1))
            cv.rrect(x - .5, BED_TOP, x + .5, BED_TOP + .08, .03, fill='#f4f1ea')
            cv.rrect(x + f * .40 - .1, BED_TOP - .07, x + f * .40 + .1, BED_TOP + .01, .04, fill='#ffffff')
        elif kind == 'sofa':
            f = w.seat_facing(p)
            cv.rrect(x - .5, SEAT_TOP - .02, x + .5, -.06, .04, fill=pal.accent)
            cv.rrect(x - f * .5 - .06, SEAT_TOP - .38, x - f * .5 + .06, -.06, .04, fill=tint(pal.accent, '#000', .15))
            cv.rrect(x - .55, SEAT_TOP - .14, x - .43, -.06, .04, fill=tint(pal.accent, '#000', .1))
            cv.rrect(x + .43, SEAT_TOP - .14, x + .55, -.06, .04, fill=tint(pal.accent, '#000', .1))
            for k in (-1, 1):
                cv.rect(x + k * .45 - .02, -.06, x + k * .45 + .02, 0, fill='#3b3b3b')
        elif kind in ('chair', 'bench'):
            f = w.seat_facing(p)
            half = .17 if kind == 'chair' else .42
            col = pal.wood if kind == 'chair' else tint(pal.wood, pal.accent, .25)
            cv.rect(x - half, SEAT_TOP - .025, x + half, SEAT_TOP + .015, fill=col)
            back = x - f * (half - .02) if kind == 'chair' else x
            if kind == 'chair':
                cv.rect(back - .022, SEAT_TOP - .42, back + .022, SEAT_TOP, fill=col)
                cv.rect(back - .03, SEAT_TOP - .44, back + .03, SEAT_TOP - .36, fill=col)
            else:
                for k in range(3):
                    cv.rect(x - half, SEAT_TOP - .34 + k * .1, x + half, SEAT_TOP - .3 + k * .1, fill=col)
                cv.rect(x - half + .02, SEAT_TOP - .36, x - half + .05, SEAT_TOP, fill='#3b3b3b')
                cv.rect(x + half - .05, SEAT_TOP - .36, x + half - .02, SEAT_TOP, fill='#3b3b3b')
            for k in (-1, 1):
                cv.rect(x + k * (half - .03) - .015, SEAT_TOP, x + k * (half - .03) + .015, 0, fill=tint(col, '#000', .2))
        elif kind in ('desk', 'table', 'computer'):
            cv.rect(x - .32, TABLE_TOP - .03, x + .32, TABLE_TOP + .01, fill=pal.wood)
            for k in (-1, 1):
                cv.rect(x + k * .28 - .018, TABLE_TOP, x + k * .28 + .018, 0, fill=tint(pal.wood, '#000', .2))
            if kind in ('desk', 'computer'):
                cv.rect(x + .05, TABLE_TOP + .01, x + .26, TABLE_TOP + .19, fill=tint(pal.wood, '#000', .08))
                cv.rect(x + .13, TABLE_TOP + .08, x + .18, TABLE_TOP + .1, fill='#c9a54b')
            if kind == 'computer':
                cv.rect(x - .015, TABLE_TOP - .1, x + .015, TABLE_TOP - .03, fill='#333')
                cv.rect(x - .07, TABLE_TOP - .045, x + .07, TABLE_TOP - .03, fill='#333')
                cv.rrect(x - .17, TABLE_TOP - .33, x + .17, TABLE_TOP - .09, .015, fill='#22262d')
                glow = .5 + .08 * math.sin(t * 3)
                cv.rect(x - .15, TABLE_TOP - .31, x + .15, TABLE_TOP - .11, fill=tint(pal.sky, '#ffffff', glow))
                for i in range(4):
                    cv.rect(x - .12, TABLE_TOP - .28 + i * .04, x - .12 + .06 + .14 * hashed(i, int(t)), TABLE_TOP - .265 + i * .04, fill=tint(pal.accent, '#fff', .3))
                cv.rect(x - .14, TABLE_TOP - .045, x - .02, TABLE_TOP - .03, fill='#555')


def draw_handheld(cv, scene, plan, t, pal, poses, active):
    w = plan.world
    for p in scene.props:
        if p.kind not in HANDHELD:
            continue
        pos, holder = plan.object_position(p.id, t, poses)
        x, y = pos
        f = 1
        if holder:
            pose = poses[holder]
            f = 1 if pose.facing >= 0 else -1
            if pose.controls.visible < .2:
                continue
        using = active.get(holder) if holder else None
        if p.kind == 'phone':
            if holder:
                cv.rrect(x - .025, y - .075, x + .025, y + .01, .01, fill='#1f2329')
                cv.rect(x - .019, y - .067, x + .019, y + .0, fill='#bfe9ff' if using == 'use_phone' else '#4b5563')
            else:
                cv.rrect(x - .05, y - .014, x + .05, y, .006, fill='#1f2329')
        elif p.kind == 'book':
            if using == 'read':
                cv.poly([(x - .13 * f, y - .1), (x, y - .06), (x, y + .04), (x - .13 * f, y)], fill='#fbfaf5', outline=pal.dark, width=.006)
                cv.poly([(x + .13 * f, y - .1), (x, y - .06), (x, y + .04), (x + .13 * f, y)], fill='#f2efe6', outline=pal.dark, width=.006)
                for i in range(3):
                    cv.line([(x + .02 * f, y - .04 + i * .025), (x + .1 * f, y - .07 + i * .025)], tint(pal.dark, '#fff', .5), .004)
            else:
                cv.rect(x - .08, y - (.03 if not holder else .16), x + .08, y, fill=pal.accent)
                cv.rect(x - .07, y - (.022 if not holder else .15), x + .07, y - .006, fill='#fbfaf5') if not holder else None
        elif p.kind == 'cup':
            cv.rrect(x - .035, y - .085, x + .035, y, .012, fill='#ffffff', outline=pal.dark, width=.006)
            cv.arc(x + .04, y - .045, .022, .025, 270, 90, pal.dark, .008)
            for i in range(2):
                sx = x - .01 + i * .02
                k = (t * .8 + i * .5) % 1
                cv.line([(sx + .01 * math.sin(k * 6), y - .1 - k * .12), (sx + .01 * math.sin(k * 6 + 1), y - .14 - k * .12)],
                        tint('#ffffff', pal.wall, .3), .008)
        elif p.kind == 'box':
            s = .13
            cv.rect(x - s, y - s * 1.6 if not holder else y - s * .8, x + s, y if not holder else y + s * .8, fill='#c49a63')
            yb = y - s * 1.6 if not holder else y - s * .8
            ye = y if not holder else y + s * .8
            cv.rect(x - .02, yb, x + .02, ye, fill='#d9bf86')
        elif p.kind == 'bag':
            base = y + (.18 if holder else 0)
            cv.poly([(x - .09, base - .2), (x + .09, base - .2), (x + .1, base), (x - .1, base)], fill=pal.accent2)
            cv.arc(x, base - .2, .05, .06, 180, 360, tint(pal.accent2, '#000', .3), .01)


# ---------------------------------------------------------------- characters
def draw_character(cv, actor, pose, pal, t, diagnostic=False):
    c = pose.controls
    if c.visible < .05:
        return
    j = pose.joints
    base = COLORS[actor]
    dark_doorway = '#2a2a33'
    col = tint(base, dark_doorway, 1 - c.visible) if c.visible < 1 else _hex(base)
    back = tint(col, pal.wall, .38)
    f = 1 if c.facing >= 0 else -1
    W = .034
    # floor shadow
    floor = min(0., j['hip'][1] + .5)
    height = max(0., -(min(j['left_foot'][1], j['right_foot'][1])))
    cv.ellipse(j['hip'][0], 0.01 + min(0, floor) * 0, .19 * (1 - .4 * min(1, height * 3)), .022, fill=tint(pal.floor, '#000', .18))

    def limb(names, colour):
        cv.line([j[n] for n in names], colour, W)

    def foot(name, colour):
        fx, fy = j[name]
        cv.line([(fx - .01 * f, fy), (fx + .05 * f, fy)], colour, W * 1.05)

    limb(['left_hip', 'left_knee', 'left_foot'], back)
    foot('left_foot', back)
    limb(['left_shoulder', 'left_elbow', 'left_hand'], back)
    cv.circle(*j['left_hand'], .021, fill=back)
    limb(['hip', 'shoulder', 'neck'], col)
    limb(['right_hip', 'right_knee', 'right_foot'], col)
    foot('right_foot', col)
    draw_head(cv, actor, pose, col, pal, t)
    limb(['right_shoulder', 'right_elbow', 'right_hand'], col)
    cv.circle(*j['right_hand'], .022, fill=col)
    if diagnostic:
        for v in j.values():
            cv.circle(*v, .012, fill='red')


def _rot(v, a):
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def draw_head(cv, actor, pose, col, pal, t):
    c = pose.controls
    j = pose.joints
    hx, hy = j['head']
    nx, ny = j['neck']
    rot = math.atan2(hy - ny, hx - nx) + math.pi / 2       # 0 when the head is upright
    R = HEAD_R
    face = FACE[actor] if c.visible >= 1 else tint(FACE[actor], '#2a2a33', 1 - c.visible)
    emotion = c.emotion
    if actor == 'friend':        # ponytail
        f = 1 if c.facing >= 0 else -1
        tip = (hx - f * R * 1.45, hy - R * .1 + .02 * math.sin(t * 3))
        cv.line([(hx - f * R * .8, hy - R * .55), tip], col, .03)
        cv.circle(*tip, .03, fill=col)
    if emotion == 'angry' and actor != 'shadow':
        face = tint(face, '#ff8a80', .35)
    cv.circle(hx, hy, R, fill=face, outline=col, width=.022)
    if actor == 'main':          # small hair tuft
        for k in (-1, 0, 1):
            a = rot - math.pi / 2 + k * .25
            base = (hx + R * math.cos(a), hy + R * math.sin(a))
            tip = (hx + (R + .045) * math.cos(a + .2), hy + (R + .045) * math.sin(a + .2))
            cv.line([base, tip], col, .018)
    if actor == 'shadow':
        for k in range(-2, 3):
            a = rot - math.pi / 2 + k * .3
            base1 = (hx + R * math.cos(a - .12), hy + R * math.sin(a - .12))
            base2 = (hx + R * math.cos(a + .12), hy + R * math.sin(a + .12))
            tip = (hx + (R + .06) * math.cos(a), hy + (R + .06) * math.sin(a))
            cv.poly([base1, tip, base2], fill=col)
    draw_face(cv, actor, c, (hx, hy), R, rot, col, pal, t)


def draw_face(cv, actor, c, center, R, rot, col, pal, t):
    hx, hy = center
    ff = max(-1., min(1., c.facing + c.head_turn * (1 if c.facing >= 0 else -1)))
    fx = max(-.42, min(.42, ff * .34)) * R
    spacing = R * .34 * (1 - .32 * abs(ff))
    emotion = c.emotion
    ink = col if actor != 'shadow' else (255, 255, 255)
    eye_y = -.06 * R
    closed = c.eyes_closed or c.blink > .5
    lx, ly = c.look

    def P(dx, dy):
        v = _rot((dx, dy), rot)
        return (hx + v[0], hy + v[1])

    # brows
    brow = {'angry': (.35, -.02), 'sad': (-.3, .0), 'anxious': (-.25, -.02), 'scared': (-.3, -.06), 'surprised': (0, -.1),
            'happy': (0, -.05), 'determined': (.2, -.01), 'thoughtful': (.0, -.04), 'confused': (None, -.04),
            'embarrassed': (-.2, -.01), 'tired': (-.1, .02), 'proud': (.05, -.05), 'loving': (-.1, -.04)}.get(emotion, (.05, -.03))
    for k in (-1, 1):
        ex = fx + k * spacing
        tilt = brow[0] if brow[0] is not None else (.3 if k < 0 else -.3)
        lift = brow[1] + (.05 if emotion == 'surprised' else 0)
        y = eye_y - .30 * R + lift * R * 2
        if k > 0:
            a = P(ex - .11 * R, y + tilt * .1 * R)
            b = P(ex + .11 * R, y - tilt * .1 * R)
        else:
            a = P(ex - .11 * R, y - tilt * .1 * R)
            b = P(ex + .11 * R, y + tilt * .1 * R)
        cv.line([a, b], ink, .014)
    # eyes
    for k in (-1, 1):
        ex, ey = P(fx + k * spacing, eye_y)
        if closed:
            if emotion in ('happy', 'loving') or c.mouth > .45:
                cv.arc(ex, ey + .01, .045, .035, 200, 340, ink, .013)
            else:
                cv.arc(ex, ey - .01, .045, .03, 20, 160, ink, .013)
            continue
        if emotion in ('surprised', 'scared'):
            cv.circle(ex, ey, .043, fill='#ffffff', outline=ink, width=.008)
            cv.circle(ex + lx * .012, ey + ly * .012, .019, fill=ink)
        elif emotion == 'happy' and c.mouth > .3:
            cv.arc(ex, ey + .012, .045, .04, 200, 340, ink, .014)
        elif emotion == 'tired':
            cv.chord(ex, ey, .032, .036, 0, 180, ink)
            cv.line([P(fx + k * spacing - .035, eye_y), P(fx + k * spacing + .035, eye_y)], ink, .01)
        else:
            cv.ellipse(ex + lx * .010, ey + ly * .010, .021, .03, fill=ink)
            cv.circle(ex + lx * .010 + .007, ey + ly * .010 - .01, .007, fill='#ffffff' if actor != 'shadow' else '#000000')
    # mouth
    mx, my = P(fx * 1.1, .42 * R)
    mw = .36 * R * (1 - .25 * abs(ff))
    open_amt = c.mouth
    if open_amt > .08:
        h = .03 + .12 * open_amt
        if emotion in ('happy', 'loving', 'proud'):
            cv.chord(mx, my - h * .3, mw, h, 0, 180, ink)
            if open_amt > .4:
                cv.chord(mx, my + h * .35, mw * .5, h * .4, 0, 180, (219, 96, 96))
        else:
            cv.ellipse(mx, my, mw * (.55 if emotion in ('surprised', 'scared') else .7), h * .6, fill=ink)
            if open_amt > .45:
                cv.ellipse(mx, my + h * .25, mw * .35, h * .2, fill=(219, 96, 96))
    elif emotion in ('happy', 'loving'):
        cv.arc(mx, my - .03, mw, .05, 20, 160, ink, .014)
    elif emotion in ('sad', 'tired'):
        cv.arc(mx, my + .03, mw * .8, .04, 200, 340, ink, .014)
    elif emotion == 'angry':
        cv.rect(mx - mw * .7, my - .012, mx + mw * .7, my + .016, fill='#ffffff', outline=ink, width=.006)
        cv.line([(mx - mw * .7, my + .002), (mx + mw * .7, my + .002)], ink, .004)
    elif emotion in ('surprised', 'scared'):
        cv.ellipse(mx, my, .022, .03, fill=ink)
    elif emotion in ('anxious', 'embarrassed', 'confused'):
        pts = [(mx - mw * .7 + i * mw * .35, my + (.008 if i % 2 else -.008) + (.012 * (i - 2) * .5 if emotion == 'confused' else 0)) for i in range(5)]
        cv.line(pts, ink, .011)
    elif emotion == 'proud':
        cv.line([(mx - mw * .6, my), (mx + mw * .3, my), (mx + mw * .65, my - .025)], ink, .013)
    elif emotion == 'thoughtful':
        cv.line([(mx - mw * .1, my + .005), (mx + mw * .5, my - .005)], ink, .012)
    elif emotion == 'determined':
        cv.line([(mx - mw * .6, my), (mx + mw * .6, my)], ink, .014)
    else:
        cv.arc(mx, my - .015, mw * .7, .025, 30, 150, ink, .012)
    if emotion in ('embarrassed', 'loving') or 'blush' in c.effects:
        for k in (-1, 1):
            bx, by = P(fx + k * spacing * 1.25, .22 * R)
            cv.ellipse(bx, by, .028, .014, fill=(244, 160, 170))
    if actor == 'future' and not closed:
        for k in (-1, 1):
            ex, ey = P(fx + k * spacing, eye_y)
            cv.circle(ex, ey, .047, outline=ink, width=.008)
        cv.line([P(fx - spacing + .047, eye_y), P(fx + spacing - .047, eye_y)], ink, .008)


def draw_effects(cv, actor, pose, pal, t):
    c = pose.controls
    if c.visible < .5:
        return
    j = pose.joints
    hx, hy = j['head']
    f = 1 if c.facing >= 0 else -1
    R = HEAD_R
    effects = set(c.effects)
    if 'tears' in effects:
        for k in (-1, 1):
            for i in range(2):
                q = (t * 1.6 + i * .5 + (k + 1) * .17) % 1
                ex = hx + f * .04 + k * .035
                cv.ellipse(ex + k * .02 * q, hy + .02 + q * .32, .012, .018, fill=(120, 180, 235))
    if 'sweat' in effects:
        q = (t * .7) % 1
        sx, sy = hx - f * R * .95, hy - R * .55 + q * .08
        cv.poly([(sx, sy - .045), (sx - .022, sy), (sx + .022, sy)], fill=(140, 200, 240))
        cv.circle(sx, sy, .022, fill=(140, 200, 240))
    if 'vein' in effects:
        vx, vy = hx + f * R * .75, hy - R * .85
        s = .035 * (1 + .15 * math.sin(t * 9))
        for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
            cv.arc(vx + math.cos(a + .785) * s, vy + math.sin(a + .785) * s, s * .8, s * .8,
                   math.degrees(a + .785 + 2.2), math.degrees(a + .785 + 4.0), (214, 58, 58), .012)
    if 'question' in effects:
        bob = .02 * math.sin(t * 4)
        cv.text(hx + f * .05, hy - R - .14 + bob, '?', .17, tint(pal.accent, '#000', .2))
    if 'exclaim' in effects:
        cv.text(hx + f * .02, hy - R - .14, '!', .19, (214, 70, 60))
    if 'zzz' in effects:
        for i in range(3):
            q = (t * .45 + i / 3) % 1
            cv.text(hx + f * (.1 + q * .2), hy - R - .05 - q * .3, 'z', .07 + .05 * q, tint(pal.accent, '#000', .2))
    if 'hearts' in effects:
        for i in range(2):
            q = (t * .5 + i * .5) % 1
            _heart(cv, hx + (i - .5) * .16 + .02 * math.sin(t * 3 + i), hy - R - .05 - q * .35, .035 * (1 - q * .3), (230, 90, 110))
    if 'sparkles' in effects:
        for i in range(4):
            a = i * 1.57 + t * 1.2
            r = .26 + .03 * math.sin(t * 6 + i)
            s = .025 * (1 + math.sin(t * 8 + i * 2))
            if s > .005:
                _star(cv, hx + math.cos(a) * r, hy + math.sin(a) * r * .8, s, tint(pal.accent2, '#fff3a0', .4))
    if 'glow' in effects:
        hand = j['right_hand']
        cv.ellipse(hand[0], hand[1] - .03, .07, .06, outline=(190, 233, 255), width=.006)


def _heart(cv, x, y, s, col):
    cv.circle(x - s * .5, y, s * .55, fill=col)
    cv.circle(x + s * .5, y, s * .55, fill=col)
    cv.poly([(x - s * 1.02, y + s * .15), (x + s * 1.02, y + s * .15), (x, y + s * 1.3)], fill=col)


def _star(cv, x, y, s, col):
    pts = []
    for i in range(8):
        r = s if i % 2 == 0 else s * .35
        a = i * math.pi / 4
        pts.append((x + math.cos(a) * r, y + math.sin(a) * r))
    cv.poly(pts, fill=col)


# ---------------------------------------------------------------- thought bubble symbols
def draw_symbol(cv, scene, plan, poses, t, pal):
    if scene.symbol == 'none':
        return
    owner = 'main' if 'main' in poses else scene.characters[0]
    pose = poses[owner]
    if pose.controls.visible < .5:
        return
    hx, hy = pose.joints['head']
    f = 1 if pose.facing >= 0 else -1
    windows = [(.3, max(2.5, min(6., scene.duration * .45)))]
    windows += [(sg.t0, sg.t1) for sg in plan.tracks[owner] if sg.kind in ('think', 'look_out_window', 'sigh')]
    pop = max(ease_out((t - a) / .4) * (1 - ease((t - b + .35) / .35)) for a, b in windows)
    if pop <= .01:
        return
    r = .27 * pop * min(1., 1.25 / cv.zoom)
    bx, by = hx + f * .48, hy - .55
    bx = max(cv.x0 + r + .05, min(cv.x1 - r - .05, bx))
    by = max(cv.y0 + r * .8 + .05, by)
    for i, s in enumerate((.022, .035, .05)):
        q = (i + 1) / 4
        cv.circle(hx + (bx - hx) * q + f * .02, hy - .12 + (by - hy + .12) * q, s * pop, fill='#ffffff', outline=pal.dark, width=.006)
    puffs = [(0, 0, 1)] + [(math.cos(a) * .78, math.sin(a) * .5, .45) for a in [i * math.tau / 7 for i in range(7)]]
    for dx, dy, s in puffs:
        cv.ellipse(bx + dx * r, by + dy * r, r * s * 1.15 if s == 1 else r * s, r * s * .78, fill='#ffffff', outline=pal.dark, width=.008)
    for dx, dy, s in puffs:
        cv.ellipse(bx + dx * r, by + dy * r, (r * s * 1.15 if s == 1 else r * s) - .01, r * s * .78 - .01, fill='#ffffff')
    ink = pal.accent
    s = r * .55
    sym = scene.symbol
    spin = t * .8
    if sym == 'thought':
        for i in range(3):
            a = spin + i * 2.1
            cv.text(bx + math.cos(a) * s * .7, by + math.sin(a) * s * .4, '?', s * .8, ink)
    elif sym == 'loop':
        cv.arc(bx, by, s, s * .8, int(math.degrees(spin)) % 360, int(math.degrees(spin)) % 360 + 300, ink, .02)
        a = spin
        tip = (bx + math.cos(a) * s, by + math.sin(a) * s * .8)
        cv.poly([(tip[0] + .04, tip[1]), (tip[0] - .03, tip[1] - .04), (tip[0] - .03, tip[1] + .04)], fill=ink)
    elif sym == 'maze':
        for i in range(3):
            q = s * (1 - i * .3)
            gap = (i * 70 + int(t * 20)) % 360
            cv.arc(bx, by, q, q * .8, gap + 30, gap + 360, ink, .014)
        cv.circle(bx, by, .02, fill=pal.accent2)
    elif sym == 'doors':
        for i in range(3):
            dx = (i - 1) * s * .7
            lit = int(t / 1.5) % 3 == i
            cv.rect(bx + dx - s * .25, by - s * .55, bx + dx + s * .25, by + s * .55, fill=pal.accent2 if lit else '#ffffff', outline=ink, width=.012)
    elif sym == 'waves':
        for k in range(3):
            pts = [(bx - s + i * s / 10, by + (k - 1) * s * .4 + .03 * math.sin(i * .9 + t * 3 + k)) for i in range(21)]
            cv.line(pts, ink, .012)
    elif sym == 'balance':
        tilt = .25 * math.sin(t * .9)
        cv.poly([(bx - s * .2, by + s * .7), (bx + s * .2, by + s * .7), (bx, by - s * .1)], fill=ink)
        l = (bx - s * math.cos(tilt), by - s * .1 - s * math.sin(tilt))
        rr = (bx + s * math.cos(tilt), by - s * .1 + s * math.sin(tilt))
        cv.line([l, rr], ink, .014)
        for q in (l, rr):
            cv.line([q, (q[0], q[1] + s * .35)], ink, .008)
            cv.chord(q[0], q[1] + s * .35, s * .28, s * .15, 0, 180, pal.accent2)
    elif sym == 'memory':
        for i in range(3):
            dx = (i - 1) * s * .55
            cv.rect(bx + dx - s * .3, by - s * .32 + i * .015, bx + dx + s * .3, by + s * .3 + i * .015, fill='#ffffff', outline=ink, width=.01)
            cv.circle(bx + dx, by - s * .05, s * .12, fill=pal.accent2)
    elif sym == 'chains':
        for i in range(4):
            cv.ellipse(bx - s * .75 + i * s * .5, by + .02 * math.sin(t * 2 + i), s * .3, s * .18, outline=ink, width=.016)
    elif sym == 'decision_tree':
        root = (bx, by + s * .7)
        mid = [(bx - s * .5, by), (bx + s * .5, by)]
        leaves = [(bx - s * .8, by - s * .6), (bx - s * .2, by - s * .6), (bx + s * .2, by - s * .6), (bx + s * .8, by - s * .6)]
        for m in mid:
            cv.line([root, m], ink, .012)
        for i, lf in enumerate(leaves):
            cv.line([mid[i // 2], lf], ink, .01)
            cv.circle(*lf, .025, fill=pal.accent2 if int(t / 1.2) % 4 == i else ink)
        cv.circle(*root, .03, fill=ink)
    elif sym == 'circles':
        for i in range(3):
            q = ((t * .4 + i / 3) % 1)
            cv.ellipse(bx, by, s * q, s * q * .8, outline=ink, width=.012)
    else:
        cv.text(bx, by, '...', s, ink)


# ---------------------------------------------------------------- frame
def frame(scene, t, size=(1920, 1080), caption='', diagnostic=False, ss=2):
    if getattr(scene, 'style', 'classic') == 'noir':
        from pipeline.animation.noir import frame as noir_frame
        return noir_frame(scene, t, size, caption, ss)
    w, h = size
    scale = character_scale(size)
    ww = w / scale
    plan = plan_for(scene, ww, h / scale)
    pal = PALETTES.get(scene.mood, PALETTES['reflective'])
    poses = plan.poses(t)
    cam = camera(plan, scene, t, poses, size, scale)
    cv = Canvas(size, ss, cam, scale, pal.wall)
    draw_environment(cv, scene, plan, t, pal)
    draw_furniture(cv, scene, plan, t, pal, poses)
    active = {a: (plan.tracks[a][plan.segment(a, t)].kind) for a in scene.characters}
    order = sorted(scene.characters, key=lambda a: (0 if active[a] in ('_idle', 'listen') else 1))
    for actor in order:
        draw_character(cv, actor, poses[actor], pal, t, diagnostic)
    draw_handheld(cv, scene, plan, t, pal, poses, active)
    for actor in order:
        draw_effects(cv, actor, poses[actor], pal, t)
    draw_symbol(cv, scene, plan, poses, t, pal)
    im = cv.im
    if not plan.lights_on(t):
        im = Image.blend(im, Image.new('RGB', im.size, (18, 22, 40)), .55)
    if ss > 1:
        im = im.reduce(ss) if hasattr(im, 'reduce') else im.resize(size, Image.LANCZOS)
        if im.size != tuple(size):
            im = im.resize(size, Image.LANCZOS)
    d = ImageDraw.Draw(im)
    vertical = h > w
    if scene.text:
        q = ease_out(min(1., t / .4))
        ft = font(int(h * (.034 if vertical else .042)), True)
        box = d.textbbox((0, 0), scene.text, font=ft)
        if box[2] > w * .86:
            ft = font(int(ft.size * w * .86 / box[2]), True)
            box = d.textbbox((0, 0), scene.text, font=ft)
        tw, th = box[2] - box[0], box[3] - box[1]
        y = h * .075 - (1 - q) * h * .04
        col = tint(pal.dark, pal.wall, 1 - q)
        d.rounded_rectangle((w / 2 - tw / 2 - h * .022, y - th / 2 - h * .016, w / 2 + tw / 2 + h * .022, y + th / 2 + h * .02),
                            radius=int(h * .012), fill=col)
        d.text((w / 2, y), scene.text, font=ft, fill=tint('#ffffff', pal.wall, 1 - q), anchor='mm')
    if caption:
        ft = font(int(h * (.026 if vertical else .034)), True)
        yy = h * (.80 if vertical else .855)
        for txt in textwrap.wrap(caption, width=28 if vertical else 52)[:3]:
            tw = d.textbbox((0, 0), txt, font=ft)[2]
            d.rounded_rectangle((w / 2 - tw / 2 - 16, yy - 6, w / 2 + tw / 2 + 16, yy + ft.size + 12), radius=9, fill=(20, 26, 34))
            d.text((w / 2, yy), txt, font=ft, fill='white', anchor='mt')
            yy += ft.size * 1.45
    if scene.transition == 'fade' and t < .25:
        im = Image.blend(Image.new('RGB', size, pal.wall), im, ease(t / .25))
    return im
