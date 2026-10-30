"""Noir art direction for philosophy / psychology essays.

Monochrome, faceless figures, a single spotlight or pale void, film grain and
vignette. One warm amber accent is reserved for meaning and hope. Each beat is
staged by a symbolic set piece (pipeline/animation/setpieces.py).
"""
import math
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw
from pipeline.animation.rig import ease, HEAD_R
from pipeline.animation.acting import plan_for
from pipeline.animation.scene import Canvas, tint, character_scale, face_font, _hex
from pipeline.animation import setpieces


class NoirPalette:
    def __init__(self, dark):
        self.dark = dark
        if dark:
            self.bg, self.bg2, self.floor, self.line = '#141416', '#24242a', '#1c1c20', '#3a3a42'
            self.ink, self.mid, self.faint = '#ebe8e1', '#8d8a84', '#4a4950'
            self.spot = '#2c2b2a'
        else:
            self.bg, self.bg2, self.floor, self.line = '#e7e4dd', '#d4d0c7', '#dcd8cf', '#b9b4a9'
            self.ink, self.mid, self.faint = '#141416', '#7d7970', '#bdb8ae'
            self.spot = '#f3f1ec'
        self.amber, self.glow = '#e2a447', '#f6d48f'


DARK, LIGHT = NoirPalette(True), NoirPalette(False)
HEAD_DRAW = .088
CAST = {'main': None, 'friend': .28, 'future': .5, 'shadow': 'shadow'}


class Drawing:
    """Context handed to set-piece drawing hooks."""
    pass


def palette_for(scene, piece):
    tone = getattr(scene, 'tone', 'auto')
    if tone == 'auto':
        tone = piece.tone if piece else 'dark'
    return DARK if tone == 'dark' else LIGHT


def default_camera(d):
    main = d.poses.get('main') or next(iter(d.poses.values()))
    x = main.joints['hip'][0]
    u = ease(d.t / max(1., d.dur))
    return (d.ww / 2 + (x - d.ww / 2) * .45, -.66, 1.0 + .1 * u)


def clamp_camera(cam, size, scale):
    cx, cy, zoom = cam
    ww = size[0] / scale
    half = ww / (2 * zoom)
    if half < ww / 2:
        cx = max(half, min(ww - half, cx))
    return (cx, cy, zoom)


@lru_cache(maxsize=4)
def vignette_mask(size, strength):
    w, h = size
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    a = np.clip((r - .55) / .75, 0, 1) ** 1.6 * strength
    return Image.fromarray((a * 255).astype(np.uint8), 'L')


@lru_cache(maxsize=4)
def grain_frames(size):
    rng = np.random.default_rng(11)
    out = []
    for _ in range(6):
        n = np.clip(rng.normal(128, 38, (size[1], size[0])), 0, 255).astype(np.uint8)
        out.append(Image.fromarray(n, 'L').convert('RGB'))
    return out


def draw_ground(cv, pal, d):
    X0, X1 = cv.x0 - 1, cv.x1 + 1
    if pal.dark:
        main = d.poses.get('main')
        x = main.joints['hip'][0] if main and main.controls.visible > .2 else d.ww / 2
        cv.rect(X0, 0, X1, cv.y1 + 1, fill=pal.floor)
        for i in range(7, 0, -1):
            q = i / 7
            cv.ellipse(x, .05, 1.6 * q, .22 * q, fill=tint(pal.floor, pal.spot, (1 - q) * .9))
        for i in range(6, 0, -1):
            q = i / 6
            cv.poly([(x - .15 * q, cv.y0 - .2), (x + .15 * q, cv.y0 - .2), (x + 1.1 * q, .05), (x - 1.1 * q, .05)],
                    fill=tint(pal.bg, pal.spot, (1 - q) * .35))
    else:
        cv.rect(X0, 0, X1, cv.y1 + 1, fill=pal.floor)
        cv.line([(X0, 0), (X1, 0)], pal.line, .004)
        for i in range(5):
            cv.rect(X0, .04 + i * i * .03, X1, .043 + i * i * .03, fill=tint(pal.floor, pal.line, .25))


def draw_props(cv, scene, plan, pal, d):
    w = plan.world
    col = pal.faint if pal.dark else pal.mid
    for p in scene.props:
        x = w.px(p)
        k = p.kind
        f = w.seat_facing(p) if k in ('chair', 'bench', 'sofa', 'bed', 'rock') else 1
        if k == 'rock':
            cv.poly([(x - .32, 0), (x - .25, -.2), (x - .05, -.3), (x + .2, -.26), (x + .3, -.1), (x + .34, 0)], fill=col)
        elif k in ('chair', 'bench'):
            half = .17 if k == 'chair' else .4
            cv.rect(x - half, -.29, x + half, -.25, fill=col)
            if k == 'chair':
                cv.rect(x - f * half, -.72, x - f * (half - .04), -.25, fill=col)
            for s in (-1, 1):
                cv.rect(x + s * (half - .03) - .015, -.25, x + s * (half - .03) + .015, 0, fill=col)
        elif k == 'bed':
            cv.rect(x - .52, -.31, x + .52, -.08, fill=col)
            cv.rect(x + f * .5 - .04, -.62, x + f * .5 + .04, 0, fill=col)
            cv.rrect(x + f * .38 - .1, -.38, x + f * .38 + .1, -.3, .04, fill=tint(col, pal.bg, .4))
        elif k in ('desk', 'table', 'computer'):
            cv.rect(x - .32, -.45, x + .32, -.41, fill=col)
            for s in (-1, 1):
                cv.rect(x + s * .28 - .015, -.41, x + s * .28 + .015, 0, fill=col)
            if k == 'computer':
                cv.rect(x - .16, -.76, x + .16, -.52, fill=col)
                cv.rect(x - .14, -.74, x + .14, -.54, fill=tint(pal.bg, '#ffffff', .25 if not pal.dark else .1))
                cv.rect(x - .015, -.52, x + .015, -.45, fill=col)
        elif k == 'door':
            cv.rect(x - .26, -1.3, x + .26, 0, outline=col, width=.02)
        elif k == 'window':
            cv.rect(x - .3, -1.4, x + .3, -.8, fill=tint(pal.bg, '#ffffff', .2), outline=col, width=.015)
        elif k in ('phone', 'box', 'book', 'cup', 'bag'):
            pass
        else:
            cv.rect(x - .05, -.1, x + .05, 0, fill=col)


def draw_handheld(cv, scene, plan, pal, poses):
    for p in scene.props:
        if p.kind not in ('phone', 'box', 'book', 'cup', 'bag'):
            continue
        (x, y), holder = plan.object_position(p.id, plan._t, poses)
        s = {'phone': (.025, .045), 'box': (.12, .12), 'book': (.08, .1), 'cup': (.035, .045), 'bag': (.09, .1)}[p.kind]
        cv.rect(x - s[0], y - s[1] * 2 if not holder else y - s[1], x + s[0], y if not holder else y + s[1], fill=pal.ink)
        if p.kind == 'phone' and holder:
            cv.rect(x - s[0] * .75, y - s[1] * .8, x + s[0] * .75, y + s[1] * .7, fill=pal.glow if pal.dark else '#cfe6f0')


def figure_colours(actor, pal, amber_actor):
    if actor == amber_actor:
        return pal.amber, tint(pal.amber, pal.bg, .35), None
    spec = CAST.get(actor)
    if spec == 'shadow':
        if pal.dark:
            return '#050506', '#0c0c0e', pal.mid
        return '#1d1622', tint('#1d1622', pal.bg, .3), None
    base = pal.ink if spec is None else tint(pal.ink, pal.bg, spec)
    return base, tint(base, pal.bg, .32), None


def draw_figure(cv, actor, pose, pal, amber_actor=None, grounded=True):
    c = pose.controls
    if c.visible < .04:
        return
    j = pose.joints
    front, back, rim = figure_colours(actor, pal, amber_actor)
    if c.visible < 1:
        front = tint(front, pal.bg, 1 - c.visible)
        back = tint(back, pal.bg, 1 - c.visible)
    W = .036
    f = 1 if c.facing >= 0 else -1
    ground = min(0., max(j['left_foot'][1], j['right_foot'][1]))
    lift = max(0., ground - min(j['left_foot'][1], j['right_foot'][1]))
    shadow_col = tint(pal.floor, '#000000', .45 if pal.dark else .18)
    if grounded:
        cv.ellipse(j['hip'][0], ground + .012, .2 * (1 - min(.6, lift * 2)), .022, fill=shadow_col)

    def limb(names, colour, width=W):
        if rim:
            cv.line([j[n] for n in names], rim, width + .012)
        cv.line([j[n] for n in names], colour, width)

    def foot(name, colour):
        fx, fy = j[name]
        cv.line([(fx - .012 * f, fy), (fx + .05 * f, fy)], colour, W)

    limb(['left_hip', 'left_knee', 'left_foot'], back)
    foot('left_foot', back)
    limb(['left_shoulder', 'left_elbow', 'left_hand'], back)
    limb(['hip', 'shoulder', 'neck'], front, W * 1.08)
    limb(['right_hip', 'right_knee', 'right_foot'], front)
    foot('right_foot', front)
    nx, ny = j['neck']
    vx, vy = j['head'][0] - nx, j['head'][1] - ny
    n = math.hypot(vx, vy) or 1
    R = HEAD_DRAW
    hx, hy = nx + vx / n * (R + .012), ny + vy / n * (R + .012)
    cv.line([(nx, ny), (hx, hy)], front, W)
    if rim:
        cv.circle(hx, hy, R + .008, fill=rim)
    cv.circle(hx, hy, R, fill=front)
    if CAST.get(actor) == 'shadow':
        for k in (-1, 1):
            cv.circle(hx + (.035 * k + .03 * f) * min(1, abs(c.facing) + .3), hy - .01, .011,
                      fill=tint(pal.bg, '#ffffff', .75) if pal.dark else '#d9d2c5')
    limb(['right_shoulder', 'right_elbow', 'right_hand'], front)


def overlay_text(im, text, pal, t, dur, size):
    """A single line of on-screen text for silent beats, in an elegant serif."""
    w, h = size
    fade = min(ease((t - .5) / .7), 1 - ease((t - dur + .7) / .6))
    if fade <= 0:
        return im
    d = ImageDraw.Draw(im)
    ft = face_font('serif', h * .052)
    box = d.textbbox((0, 0), text, font=ft)
    if box[2] - box[0] > w * .8:
        ft = face_font('serif', h * .062 * w * .8 / (box[2] - box[0]))
    colour = tint(pal.bg, pal.ink, fade)
    spacing = ' '.join(text) if len(text) <= 14 and text.isupper() else text
    d.text((w / 2, h * .9), spacing, font=ft, fill=colour, anchor='mm')
    return im


def caption_text(im, caption, pal, size):
    w, h = size
    d = ImageDraw.Draw(im)
    ft = face_font('serif', h * .042)
    import textwrap
    yy = h * .86
    for line in textwrap.wrap(caption, width=56)[:2]:
        d.text((w / 2 + 2, yy + 2), line, font=ft, fill=(0, 0, 0), anchor='mt')
        d.text((w / 2, yy), line, font=ft, fill=(245, 242, 235), anchor='mt')
        yy += ft.size * 1.25
    return im


def frame(scene, t, size=(1920, 1080), caption='', ss=2):
    w, h = size
    scale = character_scale(size)
    ww = w / scale
    plan = plan_for(scene, ww, h / scale)
    plan._t = t
    piece = setpieces.get(scene.setpiece) or setpieces.get(setpieces.DEFAULT)
    pal = palette_for(scene, piece)
    poses = plan.poses(t)
    d = Drawing()
    d.t, d.dur, d.ww, d.pal, d.poses, d.plan, d.scene = t, scene.duration, ww, pal, poses, plan, scene
    d.labels, d.amber = list(getattr(scene, 'labels', []) or []), bool(getattr(scene, 'amber', False))
    cam = piece.camera(d) if hasattr(piece, 'camera') else default_camera(d)
    cam = clamp_camera(cam, size, scale) if cam[2] >= 1 else cam
    cv = Canvas(size, ss, cam, scale, pal.bg)
    d.cv = cv
    cv.rect(cv.x0 - 1, cv.y0 - 1, cv.x1 + 1, cv.y1 + 1, fill=pal.bg)
    grounded = not getattr(piece, 'no_ground', False)
    if grounded:
        draw_ground(cv, pal, d)
    if hasattr(piece, 'background'):
        piece.background(d)
    draw_props(cv, scene, plan, pal, d)
    for actor in scene.characters:
        draw_figure(cv, actor, poses[actor], pal, grounded=grounded)
    draw_handheld(cv, scene, plan, pal, poses)
    if hasattr(piece, 'foreground'):
        piece.foreground(d)
    im = cv.im
    if ss > 1:
        im = im.reduce(ss)
        if im.size != tuple(size):
            im = im.resize(size, Image.LANCZOS)
    black = Image.new('RGB', size, (0, 0, 0))
    im = Image.composite(black, im, vignette_mask(tuple(size), .62 if pal.dark else .38))
    im = Image.blend(im, grain_frames(tuple(size))[int(t * 24) % 6], .045)
    if not scene.voiced and scene.text:
        im = overlay_text(im, scene.text, pal, t, scene.duration, size)
    if caption:
        im = caption_text(im, caption, pal, size)
    if scene.transition == 'fade':
        fin = ease(t / .45)
        fout = 1 - ease((t - scene.duration + .35) / .35)
        q = min(fin, fout)
        if q < 1:
            im = Image.blend(Image.new('RGB', size, (0, 0, 0) if pal.dark else _hex(pal.bg)), im, max(0., q))
    return im
