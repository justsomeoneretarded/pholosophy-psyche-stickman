"""Library of symbolic set pieces for philosophy / psychology essays.

Each set piece is a reusable visual metaphor (a wall of words crumbling, a fall
through the void, Sisyphus and his boulder...). The script writer only picks a
set piece and a few labels; the set piece supplies the staging (cast, actions,
camera) and draws its own symbolic elements, so the result is consistent and
never depends on the language model choreographing joints.

Hooks a set piece may implement (all optional except build):
  build(ctx)          -> dict of scene fields: characters, props, actions, environment
  background(d)       draw behind characters
  foreground(d)       draw in front of characters
  floor(x, ww)        terrain height at x (negative = above the base floor)
  adjust(actor, c, t, plan)  modify a character's Controls before solving
  camera(d)           (cx, cy, zoom) override
"""
import math
from pipeline.animation.rig import ease, ease_out, mix, lerp, shoulder_of, head_of, side

REGISTRY = {}


def setpiece(cls):
    REGISTRY[cls.name] = cls()
    return cls


def hashed(*values):
    h = 2166136261
    for ch in repr(values):
        h = (h ^ ord(ch)) * 16777619 & 0xffffffff
    return h / 0xffffffff


def A(action, start, end, actor='main', **kw):
    """An action using fractions of the beat duration (rescaled with the narration)."""
    return dict(actor=actor, action=action, start=start, end=end, **kw)


def window(u, a, b):
    """0..1 progress of u through [a, b]."""
    return max(0., min(1., (u - a) / max(1e-6, b - a)))


class Build:
    """What a set piece is given when it is built into a scene."""

    def __init__(self, labels, duration, amber, tone):
        self.labels = [l for l in (labels or []) if str(l).strip()]
        self.duration = duration
        self.amber = amber
        self.tone = tone

    def at(self, fraction):
        return round(self.duration * fraction, 3)

    def label(self, i, default=''):
        return self.labels[i] if i < len(self.labels) else default


class SetPiece:
    name = ''
    description = ''
    labels_hint = ''
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': [A('idle', 0, b.duration)]}

    def act(self, b, *items):
        out = []
        for name, s, e, *rest in items:
            kw = rest[0] if rest else {}
            out.append(A(name, b.at(s), b.at(e), **kw))
        return out


# ---------------------------------------------------------------- drawing helpers
def particles(cv, origin, age, count, seed, colour, spread=.6, size=.02, gravity=1.6, life=2.2):
    """Dust: deterministic particles bursting from origin, falling and fading."""
    if age <= 0 or age > life:
        return
    for i in range(count):
        vx = (hashed(seed, i, 'x') - .5) * spread
        vy = -hashed(seed, i, 'y') * spread * .6
        x = origin[0] + (hashed(seed, i, 'ox') - .5) * size * 18 + vx * age
        y = origin[1] + (hashed(seed, i, 'oy') - .5) * size * 8 + vy * age + .5 * gravity * age * age
        s = size * (.4 + hashed(seed, i, 's')) * (1 - age / life)
        cv.rect(x - s, y - s, x + s, y + s, fill=colour(age / life) if callable(colour) else colour)


def mini_figure(cv, x, base, scale, colour, phase=0., walking=False, facing=1, lean=0., arms=None):
    """A light-weight background stick figure (crowds, distant people)."""
    w = .03 * scale
    stride = .09 * scale if walking else 0
    hip = (x, base - .46 * scale - (.01 * scale * abs(math.sin(phase * math.pi * 2)) if walking else 0))
    sh = (hip[0] + math.sin(lean) * .31 * scale * facing, hip[1] - math.cos(lean) * .31 * scale)
    for k in (-1, 1):
        swing = math.sin(phase * math.tau) * k if walking else (.25 * k)
        foot = (x + swing * stride + (0 if walking else .06 * k * scale), base)
        knee = ((hip[0] + foot[0]) / 2 + .04 * scale * facing, (hip[1] + foot[1]) / 2)
        cv.line([hip, knee, foot], colour, w)
        if arms == 'up':
            hand = (sh[0] + .12 * k * scale, sh[1] - .25 * scale)
        elif arms == 'cover':
            hand = (sh[0] + .06 * facing * scale, sh[1] - .12 * scale)
        else:
            hand = (sh[0] - swing * .12 * scale * facing, sh[1] + .29 * scale)
        elbow = ((sh[0] + hand[0]) / 2 - .02 * scale * facing, (sh[1] + hand[1]) / 2)
        cv.line([sh, elbow, hand], colour, w)
    cv.line([hip, sh], colour, w)
    head = (sh[0] + math.sin(lean) * .11 * scale * facing, sh[1] - .12 * scale)
    cv.circle(head[0], head[1], .085 * scale, fill=colour)


def icon(cv, word, x, y, s, colour, pal):
    """Simple symbolic icons for common words; other words are written out."""
    w = word.strip().lower()
    if w in ('trophy', 'success', 'win', 'victory', 'achievement'):
        cv.chord(x, y - s * .2, s * .45, s * .5, 0, 180, colour)
        cv.rect(x - s * .08, y + s * .05, x + s * .08, y + s * .35, fill=colour)
        cv.rect(x - s * .3, y + s * .35, x + s * .3, y + s * .45, fill=colour)
        for k in (-1, 1):
            cv.arc(x + k * s * .45, y - s * .05, s * .18, s * .18, 90 if k > 0 else -90, 270 if k > 0 else 90, colour, s * .06)
    elif w in ('heart', 'love', 'romance', 'relationship'):
        cv.circle(x - s * .2, y - s * .1, s * .23, fill=colour)
        cv.circle(x + s * .2, y - s * .1, s * .23, fill=colour)
        cv.poly([(x - s * .42, y), (x + s * .42, y), (x, y + s * .45)], fill=colour)
    elif w in ('diploma', 'degree', 'education', 'knowledge', 'school'):
        cv.rrect(x - s * .45, y - s * .15, x + s * .45, y + s * .15, s * .1, fill=colour)
        cv.line([(x + s * .1, y + s * .1), (x + s * .05, y + s * .4)], pal.amber, s * .05)
        cv.line([(x + s * .15, y + s * .1), (x + s * .22, y + s * .4)], pal.amber, s * .05)
    elif w in ('clock', 'time', 'hours'):
        cv.circle(x, y, s * .42, outline=colour, width=s * .07)
        cv.line([(x, y), (x, y - s * .28)], colour, s * .06)
        cv.line([(x, y), (x + s * .2, y)], colour, s * .06)
    elif w in ('crown', 'power', 'status', 'fame'):
        cv.poly([(x - s * .45, y + s * .25), (x - s * .45, y - s * .2), (x - s * .22, y), (x, y - s * .35), (x + s * .22, y),
                 (x + s * .45, y - s * .2), (x + s * .45, y + s * .25)], fill=colour)
    elif w in ('money', 'wealth', 'coin', 'gold', 'riches'):
        cv.circle(x, y, s * .4, fill=colour)
        cv.text(x, y, '$', s * .55, pal.bg, face='display')
    elif w in ('house', 'home', 'family'):
        cv.poly([(x - s * .45, y - s * .02), (x, y - s * .45), (x + s * .45, y - s * .02)], fill=colour)
        cv.rect(x - s * .32, y - s * .02, x + s * .32, y + s * .4, fill=colour)
    elif w in ('god', 'faith', 'religion', 'church', 'cross'):
        cv.rect(x - s * .06, y - s * .45, x + s * .06, y + s * .45, fill=colour)
        cv.rect(x - s * .3, y - s * .22, x + s * .3, y - s * .1, fill=colour)
    else:
        cv.text(x, y, word.upper(), s * .32, colour, face='display')


def label_font_size(text, width, base):
    return min(base, width / max(1, len(text)) * 1.7)


# ---------------------------------------------------------------- set pieces
@setpiece
class WordWall(SetPiece):
    name = 'word_wall'
    description = 'A towering wall carved with big words (beliefs, values). The words crumble to dust one by one while the figure watches, then looks at its empty hands.'
    labels_hint = '3-5 single words that crumble, e.g. GOD, PURPOSE, DESTINY, MEANING'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(
            b, ('walk', 0, .18, {'x': .26}), ('look_at', .2, .78), ('shrug', .8, 1.0, {'emotion': 'sad'}))}

    def camera(self, d):
        return (d.ww * .58, -1.08, .9)

    def times(self, n):
        return [.22 + i * (.5 / max(1, n - 1 if n > 1 else 1)) for i in range(n)]

    def background(self, d):
        cv, pal, ww = d.cv, d.pal, d.ww
        words = (d.labels or ['GOD', 'PURPOSE', 'DESTINY', 'MEANING'])[:5]
        x0, x1, top = ww * .40, ww * .97, -2.05
        cv.rect(x0, top, x1, 0, fill=pal.bg2)
        for i in range(9):
            y = top + i * .23
            off = .2 if i % 2 else 0
            for k in range(8):
                bx = x0 + off + k * .4
                if bx < x1:
                    cv.rect(bx, y, min(x1, bx + .395), y + .225, outline=pal.line, width=.004)
        n = len(words)
        rows = n
        for i, word in enumerate(words):
            crumble = self.times(n)[i] * d.dur
            age = d.t - crumble
            y = top + .32 + i * (1.75 / max(1, rows))
            size = label_font_size(word, x1 - x0 - .2, .36)
            cx = (x0 + x1) / 2
            if age < 0:
                shake = .006 * math.sin(d.t * 60) if age > -.6 else 0
                cv.text(cx + shake, y, word, size, pal.ink, face='display')
            else:
                fade = max(0., 1 - age / .25)
                if fade > 0:
                    cv.text(cx, y + age * .4, word, size, tint_colour(pal.ink, pal.bg2, 1 - fade), face='display')
                particles(cv, (cx, y), age, 70, ('wall', i), lambda q: tint_colour(pal.ink, pal.bg, q), spread=.9, size=.018)


def tint_colour(a, b, q):
    from pipeline.animation.scene import tint
    return tint(a, b, max(0., min(1., q)))


@setpiece
class RoutineLoop(SetPiece):
    name = 'routine_loop'
    description = 'The daily loop: sleep, wake, walk to the desk, work, walk back to bed - repeating faster and faster under a spinning clock.'
    labels_hint = 'optional one word shown on the clock face, e.g. REPEAT'
    tone = 'light'

    def build(self, b):
        acts, t, k = [], 0., 0
        total = b.duration
        lengths = [3.2, 2.4, 1.8, 1.3, 1.0]
        cycle = 0
        while t < total - .5 and cycle < len(lengths):
            L = lengths[cycle] * max(.6, total / 14)
            for name, frac, extra in (('sleep', .22, {'target': 'bed'}), ('type', .38, {'target': 'desk'}), ('idle', .0, {})):
                if frac == 0:
                    continue
                d = L * frac / .6
                if t + d > total:
                    break
                acts.append(A(name, round(t, 3), round(t + d, 3), **extra))
                t += d + L * .2
            cycle += 1
        return {'characters': ['main'], 'props': [dict(id='bed', kind='bed', x=.18), dict(id='desk', kind='computer', x=.78)],
                'actions': acts or [A('idle', 0, total)]}

    def background(self, d):
        cv, pal = d.cv, d.pal
        x, y, r = d.ww * .5, -1.3, .22
        cv.circle(x, y, r, fill=pal.bg, outline=pal.ink, width=.02)
        speed = 1 + 6 * (d.t / max(1, d.dur)) ** 2
        a = d.t * speed * 2
        cv.line([(x, y), (x + math.sin(a) * r * .8, y - math.cos(a) * r * .8)], pal.ink, .014)
        cv.line([(x, y), (x + math.sin(a / 12) * r * .55, y - math.cos(a / 12) * r * .55)], pal.ink, .024)
        if d.labels:
            cv.text(x, y + r * .45, d.labels[0].upper(), .06, pal.mid, face='display')


@setpiece
class Crowd(SetPiece):
    name = 'crowd'
    description = 'Rows of identical faceless figures marching in sync. The main figure, among them, slows, stops and turns away from the march.'
    labels_hint = 'none needed'
    tone = 'light'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(
            b, ('walk', 0, .5, {'x': .55}), ('stop', .5, .62), ('turn', .64, .72), ('look_around', .74, 1.0, {'emotion': 'thoughtful'}))}

    def background(self, d):
        cv, pal = d.cv, d.pal
        for row, (base, scale, shade) in enumerate(((-.36, .6, .72), (-.2, .76, .55))):
            colour = tint_colour(pal.ink, pal.bg, shade)
            spacing = .38 * scale
            drift = (d.t * .28 * scale) % spacing
            n = int(d.ww / spacing) + 3
            for i in range(-1, n):
                x = i * spacing + drift - spacing + (row * .17)
                mini_figure(cv, x, base, scale, colour, phase=d.t * 1.1 + row * .3, walking=True)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        colour = tint_colour(pal.ink, pal.bg, .4)
        spacing = 1.1
        drift = (d.t * .36) % spacing
        for i in range(-1, int(d.ww / spacing) + 3):
            x = i * spacing + drift - spacing
            if abs(x - d.poses['main'].joints['hip'][0]) < .3 and d.t > d.dur * .5:
                continue          # the march parts around the one who stopped
            mini_figure(cv, x, .16, 1.05, colour, phase=d.t * 1.1, walking=True)


@setpiece
class Pillar(SetPiece):
    name = 'pillar'
    description = 'A giant stone pillar carved with a word towers over a crowd. It cracks and collapses; the people scatter.'
    labels_hint = 'one word on the pillar, e.g. CERTAINTY, TRADITION, GOD'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(
            b, ('look_at', 0, .42), ('flinch', .45, .58), ('cower', .6, .85), ('stand', .86, 1.0, {'emotion': 'confused'}))}

    def camera(self, d):
        return (d.ww * .55, -1.15, .82)

    def background(self, d):
        cv, pal, ww = d.cv, d.pal, d.ww
        x = ww * .62
        crack = .38 * d.dur
        age = d.t - crack
        word = (d.labels or ['CERTAINTY'])[0].upper()
        blocks = 7
        for i in range(blocks):
            y0 = -2.2 + i * .3
            if age <= 0:
                off, rot = (.003 * math.sin(d.t * 50) if age > -.8 else 0), 0
                cv.rect(x - .32 + off, y0, x + .32 + off, y0 + .295, fill=pal.bg2, outline=pal.line, width=.005)
            else:
                fall = age * age * 2.2 * (1 + i * .15)
                dx = (hashed('p', i) - .5) * age * 1.4
                y = min(-.3 + i * .02, y0 + fall)
                cv.rect(x - .32 + dx, y, x + .32 + dx, y + .29, fill=pal.bg2, outline=pal.line, width=.005)
        if age <= 0:
            for k, ch in enumerate(word[:8]):
                cv.text(x, -2.05 + k * .24, ch, .19, pal.ink, face='display')
            if age > -.8:
                cv.line([(x - .1, -1.2), (x + .02, -1.0), (x - .05, -.8), (x + .08, -.55)], pal.ink, .008)
        cv.rect(x - .45, -.12, x + .45, 0, fill=pal.bg2)
        particles(cv, (x, -.4), age, 90, 'pillar', lambda q: tint_colour(pal.mid, pal.bg, q), spread=1.6, size=.022, gravity=.6, life=3)
        for i in range(7):
            px = ww * .4 + i * .3 + .08 * hashed(i, 'jit')
            if abs(px - x) < .25:
                px += .5
            scatter = max(0., age) * (1.5 if px > x else -1.5) * (.6 + hashed(i, 'sc'))
            mini_figure(cv, px + scatter, 0, .62 + .1 * hashed(i, 'h'), tint_colour(pal.ink, pal.bg, .45), phase=d.t * 2 + i,
                        walking=age > 0, facing=1 if scatter >= 0 else -1, arms='cover' if 0 < age < 1.5 else None)


@setpiece
class Fall(SetPiece):
    name = 'fall'
    description = 'The figure falls endlessly through darkness while symbols of what it valued float up past it and dissolve into dust.'
    labels_hint = '2-4 things that lose meaning, e.g. trophy, heart, diploma, clock, money, crown'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': [A('idle', 0, b.duration, emotion='scared')]}

    no_ground = True

    def adjust(self, actor, c, t, plan):
        f = side(c)
        c.lean = 1.25 + .25 * math.sin(t * .45)
        c.head = -.35
        c.y = -.9 + .04 * math.sin(t * 1.3)
        c.x = plan.ww / 2 + .06 * math.sin(t * .7)
        s = shoulder_of(c)
        c.hands = ((s[0] - .05 * f, s[1] - .3 + .04 * math.sin(t * 2.1)), (s[0] + .12 * f, s[1] - .27 + .04 * math.cos(t * 2.4)))
        c.feet = ((c.x - .38 * f, c.y - .18 + .03 * math.sin(t * 1.7)), (c.x - .3 * f, c.y + .05))
        return c

    def camera(self, d):
        return (d.ww / 2, -.8, 1.1)

    def background(self, d):
        cv, pal = d.cv, d.pal
        cv.rect(cv.x0 - 1, cv.y0 - 1, cv.x1 + 1, cv.y1 + 1, fill=pal.bg)
        for i in range(36):
            x = cv.x0 + hashed(i, 'sx') * (cv.x1 - cv.x0)
            speed = 2 + 3 * hashed(i, 'sp')
            y = cv.y1 - ((d.t * speed + hashed(i, 'sy') * 10) % ((cv.y1 - cv.y0) + 1.0))
            cv.line([(x, y), (x, y + .25 + .3 * hashed(i))], tint_colour(pal.ink, pal.bg, .82), .006)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        items = (d.labels or ['trophy', 'heart', 'diploma'])[:4]
        span = d.dur / max(1, len(items))
        for i, word in enumerate(items):
            t0 = i * span
            age = d.t - t0
            if age < 0:
                continue
            side_x = (-1 if i % 2 else 1) * (.55 + .2 * hashed(i))
            y = cv.y1 + .3 - age * .55
            x = d.ww / 2 + side_x
            dissolve = span * .7
            if age < dissolve:
                q = window(age, dissolve - .8, dissolve)
                icon(cv, word, x, y, .32, tint_colour(pal.ink, pal.bg, q * .8), pal)
            particles(cv, (x, y + .3), age - dissolve, 60, ('fall', i), lambda q: tint_colour(pal.ink, pal.bg, q), spread=.5, size=.014, gravity=-.4)


@setpiece
class Desert(SetPiece):
    name = 'desert'
    description = 'A tiny figure in an endless empty desert under a pale sky; it walks slowly, stops, and lies down. Scale shows insignificance.'
    labels_hint = 'none needed'
    tone = 'light'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(
            b, ('walk', 0, .55, {'x': .55, 'emotion': 'tired'}), ('stop', .55, .62), ('sigh', .62, .74), ('lie_down', .76, 1.0))}

    def camera(self, d):
        x = d.poses['main'].joints['hip'][0] if 'main' in d.poses else d.ww / 2
        return (x, -1.1, .62 + .08 * ease(d.t / max(1, d.dur)))

    def background(self, d):
        cv, pal = d.cv, d.pal
        X0, X1 = cv.x0 - 1, cv.x1 + 1
        for i in range(14):
            y0 = cv.y0 - 1 + i * ((-.25 - cv.y0 + 1) / 14)
            cv.rect(X0, y0, X1, y0 + 1.5, fill=tint_colour(pal.bg, pal.bg2, i / 14))
        cv.circle(d.ww * .75, -2.2, .28, fill=tint_colour(pal.bg, '#ffffff', .6))
        for k, (h, shade) in enumerate(((.25, .25), (.12, .45))):
            pts = [(X0, 0)] + [(x / 6, -.25 + h * math.sin(x / 6 * .7 + k * 2.1)) for x in range(int(X0 * 6), int(X1 * 6) + 2)] + [(X1, 0)]
            cv.poly(pts, fill=tint_colour(pal.bg2, pal.mid, shade))
        cv.rect(X0, 0, X1, 6, fill=tint_colour(pal.bg2, pal.mid, .55))
        for i in range(40):
            x = X0 + ((hashed(i, 'w') * (X1 - X0) + d.t * (1.2 + hashed(i)))) % (X1 - X0)
            y = -.05 - .9 * hashed(i, 'wy')
            cv.line([(x, y), (x + .12, y)], tint_colour(pal.bg, pal.mid, .3), .004)


@setpiece
class ShadowCompanion(SetPiece):
    name = 'shadow_companion'
    description = 'The figure kneels alone, head down. A dark shadow-self walks in and kneels beside it, a hand on its shoulder.'
    labels_hint = 'none needed'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main', 'shadow'], 'actions': [
            A('kneel', 0, b.at(.3), emotion='sad', x=.42), A('head_in_hands', b.at(.32), b.at(.62)),
            A('enter', b.at(.12), b.at(.5), actor='shadow', x=.62), A('comfort', b.at(.55), b.at(1.0), actor='shadow', target='main')]}


@setpiece
class Sisyphus(SetPiece):
    name = 'sisyphus'
    description = 'A figure pushes a huge boulder up a hill; near the top it rolls back down. Endless, absurd effort (Camus).'
    labels_hint = 'optional one word on the boulder, e.g. TOMORROW'
    tone = 'light'
    TOP = .82
    BASE = .18

    def build(self, b):
        acts = [A('walk', 0, b.at(.72), x=self.TOP - .1), A('idle', b.at(.72), b.at(.78)), A('turn', b.at(.8), b.at(.86))]
        acts.append(A('walk', b.at(.88), b.at(1.0), x=self.TOP - .2, emotion='happy' if b.amber else 'tired'))
        return {'characters': ['main'], 'actions': acts}

    def camera(self, d):
        main = d.poses.get('main')
        x = main.joints['hip'][0] if main else d.ww * .4
        y = main.joints['hip'][1] if main else -.5
        return (x + .25, y - .25, .92)

    def floor(self, x, ww):
        u = (x / ww - self.BASE) / (self.TOP - self.BASE)
        return -1.0 * ease(max(0., min(1., u))) if u > 0 else 0.

    def _boulder(self, d):
        main = d.poses.get('main')
        hip_x = main.joints['hip'][0] if main else d.ww * .3
        top_x = d.ww * self.TOP
        roll = d.t - .76 * d.dur
        if roll < 0:
            x = hip_x + .42
        else:
            start = d.ww * (self.TOP - .1) + .42
            x = max(d.ww * .05, start - 2.2 * roll * roll)
        r = .36
        y = self.floor(x, d.ww) - r
        return x, y, r, roll

    def adjust(self, actor, c, t, plan):
        dur = plan.duration
        if t < .72 * dur and actor == 'main':
            f = side(c)
            c.lean = .55
            c.head = -.2
            s = shoulder_of(c)
            target = (c.x + .3 * f, s[1] + .02)
            c.hands = (mix(c.hands[0], (target[0] - .02, target[1] + .04), .9), mix(c.hands[1], target, .9))
        return c

    def background(self, d):
        cv, pal, ww = d.cv, d.pal, d.ww
        pts = [(cv.x0 - 1, 1)] + [(x / 20, self.floor(x / 20, ww)) for x in range(int((cv.x0 - 1) * 20), int((cv.x1 + 1) * 20))] + [(cv.x1 + 1, 1)]
        cv.poly(pts, fill=pal.bg2)
        cv.line([(p[0], p[1]) for p in pts[1:-1]], pal.line, .006)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        x, y, r, roll = self._boulder(d)
        spin = -(x / r)
        cv.circle(x, y, r, fill=tint_colour(pal.ink, pal.bg, .25))
        for k in range(3):
            a = spin + k * 2.1
            cv.line([(x + math.cos(a) * r * .3, y + math.sin(a) * r * .3), (x + math.cos(a) * r * .75, y + math.sin(a) * r * .75)],
                    tint_colour(pal.ink, pal.bg, .45), .012)
        if d.labels:
            cv.text(x, y, d.labels[0].upper(), .08, pal.bg, face='display')
        if roll > 0:
            particles(cv, (x, y + r), roll, 25, ('dust', int(roll * 3)), lambda q: tint_colour(pal.mid, pal.bg, q), spread=.4, size=.01, life=.8)


@setpiece
class ChalkDoor(SetPiece):
    name = 'chalk_door'
    description = 'In an empty void the figure draws a door in chalk; warm light pours through it, and the figure walks through. Creating your own meaning.'
    labels_hint = 'optional one word written above the door'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(
            b, ('walk', 0, .15, {'x': .38}), ('idle', .17, .55), ('look_at', .56, .7, {'emotion': 'determined'}), ('walk', .72, 1.0, {'x': .62}))}

    DOOR = .62

    def adjust(self, actor, c, t, plan):
        dur = plan.duration
        u = t / dur
        f = side(c)
        dx = plan.ww * self.DOOR
        if .17 <= u < .55:
            q = window(u, .19, .53)
            path = [(dx - .25, 0), (dx - .25, -1.25), (dx + .25, -1.25), (dx + .25, 0)]
            seg = min(2, int(q * 3))
            local = q * 3 - seg
            pt = mix(path[seg], path[seg + 1], local)
            s = shoulder_of(c)
            reach = .33
            v = (pt[0] - s[0], pt[1] - s[1])
            n = math.hypot(*v) or 1
            c.hands = (c.hands[0], (s[0] + v[0] / n * min(n, reach), s[1] + v[1] / n * min(n, reach)))
            c.lean = .08
        if u > .72:
            fade = window(u, .9, 1.0)
            c.visible = 1 - fade
        return c

    def background(self, d):
        cv, pal = d.cv, d.pal
        u = d.t / d.dur
        dx = d.ww * self.DOOR
        q = window(u, .19, .53)
        path = [(dx - .25, 0), (dx - .25, -1.25), (dx + .25, -1.25), (dx + .25, 0)]
        glow = window(u, .55, .7)
        if glow > 0:
            for i in range(5, 0, -1):
                cv.rect(dx - .25 - .05 * i * glow, -1.25 - .05 * i * glow, dx + .25 + .05 * i * glow, 0,
                        fill=tint_colour(pal.bg, pal.amber, .12 * glow * (6 - i) / 5))
            cv.rect(dx - .25, -1.25, dx + .25, 0, fill=tint_colour(pal.bg, pal.glow, glow))
            cv.poly([(dx - .25, 0), (dx + .25, 0), (dx + .9, .9), (dx - .9, .9)], fill=tint_colour(pal.bg, pal.amber, .35 * glow))
        drawn = q * 3
        pts = [path[0]]
        for k in range(3):
            if drawn > k:
                pts.append(mix(path[k], path[k + 1], min(1, drawn - k)))
        if len(pts) > 1:
            cv.line(pts, tint_colour('#f4f1ea', pal.bg, .05), .014)
        if d.labels and glow > .5:
            cv.text(dx, -1.45, d.labels[0].upper(), .11, pal.amber, face='display')


@setpiece
class Chains(SetPiece):
    name = 'chains'
    description = 'The figure strains forward, chained to a heavy block carved with a word. With amber, the chains break and it walks free.'
    labels_hint = 'one word on the weight, e.g. FEAR, PAST, GUILT, EXPECTATIONS'
    tone = 'dark'

    def build(self, b):
        acts = [A('walk', 0, b.at(.7 if b.amber else 1.0), x=.75, emotion='determined')]
        if b.amber:
            acts += [A('celebrate', b.at(.74), b.at(.86)), A('walk', b.at(.88), b.at(1.0), x=.9)]
        return {'characters': ['main'], 'actions': acts}

    def adjust(self, actor, c, t, plan):
        broken = getattr(plan.scene, 'amber', False) and t > .7 * plan.duration
        if not broken and t < (.7 if getattr(plan.scene, 'amber', False) else 1.0) * plan.duration:
            anchor = plan.ww * .5
            c.x = min(c.x, anchor + .25 * math.sin(min(1, t / 3) * math.pi / 2))
            c.lean = .45
            c.head = -.15
        return c

    def background(self, d):
        cv, pal = d.cv, d.pal
        bx = d.ww * .18
        cv.rect(bx - .3, -.55, bx + .3, 0, fill=pal.bg2, outline=pal.line, width=.006)
        cv.text(bx, -.28, (d.labels or ['FEAR'])[0].upper(), label_font_size((d.labels or ['FEAR'])[0], .55, .16), pal.ink, face='display')

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        main = d.poses.get('main')
        if not main:
            return
        bx = d.ww * .18 + .3
        hip = main.joints['hip']
        broken_at = .7 * d.dur if d.amber else None
        age = d.t - broken_at if broken_at else -1
        links = 14
        for i in range(links):
            q = i / links
            sag = .18 * math.sin(q * math.pi) * (1 - .8 * min(1, abs(hip[0] - bx) / 2.5))
            x = lerp(bx, hip[0], q)
            y = lerp(-.3, hip[1], q) + sag
            if age > 0:
                x += (q - .5) * age * .8
                y += age * age * 2 * (1 - abs(q - .5))
                if y > 0:
                    y = 0
            cv.ellipse(x, y, .035, .02, outline=pal.mid if age <= 0 else pal.amber, width=.008)


@setpiece
class GiantHand(SetPiece):
    name = 'giant_hand'
    description = 'An enormous hand descends from above, pressing the figure down until it cowers. With amber, the figure stands and pushes it back.'
    labels_hint = 'one word on the hand, e.g. SOCIETY, PRESSURE, FATE, OTHERS'
    tone = 'dark'

    def build(self, b):
        acts = [A('look_at', 0, b.at(.3)), A('cower', b.at(.35), b.at(.7 if b.amber else 1.0), emotion='scared')]
        if b.amber:
            acts += [A('stand', b.at(.72), b.at(.82), emotion='determined'), A('stretch', b.at(.84), b.at(1.0))]
        return {'characters': ['main'], 'actions': acts}

    def camera(self, d):
        return (d.ww / 2, -1.05, .85)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        main = d.poses.get('main')
        x = main.joints['hip'][0] if main else d.ww / 2
        u = d.t / d.dur
        down = ease(window(u, .05, .4))
        if d.amber:
            down *= 1 - ease(window(u, .74, .95))
        bottom = lerp(cv.y0 - .3, -1.35, down)
        col = tint_colour(pal.ink, pal.bg, .65)
        cv.rrect(x - .55, cv.y0 - 2, x + .55, bottom, .2, fill=col)
        for k in range(4):
            fx = x - .42 + k * .28
            cv.rrect(fx - .1, bottom - .2, fx + .1, bottom + .45, .09, fill=col)
        cv.rrect(x + .5, bottom - .55, x + .72, bottom + .1, .09, fill=col)
        if d.labels:
            cv.text(x, bottom - .55, d.labels[0].upper(), .12, pal.bg, face='display')


@setpiece
class EndlessStairs(SetPiece):
    name = 'stairs'
    description = 'The figure climbs an endless staircase rising into fog; the top never arrives. Striving without end.'
    labels_hint = 'optional one word at the top of the stairs, e.g. ENOUGH, HAPPINESS'
    tone = 'light'

    def build(self, b):
        return {'characters': ['main'], 'actions': [A('walk', 0, b.at(.85), x=.85), A('look_at', b.at(.87), b.at(1.0), emotion='tired')]}

    def floor(self, x, ww):
        start = ww * .12
        if x < start:
            return 0.
        return -math.floor((x - start) / .17 + 1) * .1

    def camera(self, d):
        main = d.poses.get('main')
        x = main.joints['hip'][0] if main else d.ww / 2
        y = main.joints['hip'][1] if main else -.6
        return (x + .4, y - .2, 1.15)

    def background(self, d):
        cv, pal, ww = d.cv, d.pal, d.ww
        start = ww * .12
        for i in range(60):
            x = start + i * .17
            if x > cv.x1 + 1:
                break
            h = (i + 1) * .1
            fog = min(1, max(0, (h - 1.0) / 2.2))
            cv.rect(x, -h, x + .17 + .002, 3, fill=tint_colour(pal.bg2, pal.bg, fog))
            cv.line([(x, -h), (x + .17, -h)], tint_colour(pal.line, pal.bg, fog), .005)
        if d.labels:
            cv.text(ww * .95, -2.3, d.labels[0].upper(), .14, tint_colour(pal.ink, pal.bg, .6), face='display')


@setpiece
class Doors(SetPiece):
    name = 'doors'
    description = 'Several doors stand alone in a void, each labelled with a choice. The figure walks between them, hesitates, and chooses one, which glows.'
    labels_hint = '2-4 short labels for the doors, e.g. COMFORT, TRUTH, ESCAPE'
    tone = 'dark'

    def build(self, b):
        n = max(2, min(4, len(b.labels) or 3))
        xs = [.25 + i * (.55 / (n - 1)) for i in range(n)]
        acts, t = [], 0.
        step = .7 / n
        for i, x in enumerate(xs):
            acts.append(A('walk', b.at(t), b.at(t + step * .6), x=x - .08))
            acts.append(A('look_at', b.at(t + step * .62), b.at(t + step * .98)))
            t += step
        acts.append(A('walk', b.at(.74), b.at(1.0), x=xs[-1], emotion='determined'))
        return {'characters': ['main'], 'actions': acts}

    def adjust(self, actor, c, t, plan):
        if t > plan.duration * .9:
            c.visible = 1 - window(t / plan.duration, .9, 1.0)
        return c

    def background(self, d):
        cv, pal = d.cv, d.pal
        labels = d.labels or ['COMFORT', 'TRUTH', 'ESCAPE']
        n = max(2, min(4, len(labels)))
        for i in range(n):
            x = d.ww * (.25 + i * (.55 / (n - 1)))
            chosen = i == n - 1 and d.t > .72 * d.dur
            glow = window(d.t / d.dur, .72, .8) if chosen else 0
            cv.rect(x - .25, -1.3, x + .25, 0, fill=tint_colour(pal.bg2, pal.glow, glow), outline=pal.line, width=.008)
            cv.circle(x + .17, -.6, .02, fill=pal.mid)
            label = labels[i] if i < len(labels) else ''
            cv.text(x, -1.48, label.upper(), label_font_size(label, .55, .1), pal.amber if chosen else pal.ink, face='display')
            cv.ellipse(x, .02, .4, .04, fill=tint_colour(pal.bg, '#000000', .3))


@setpiece
class Mirror(SetPiece):
    name = 'mirror'
    description = 'The figure faces a tall mirror, but its reflection is the dark shadow-self, moving on its own: identity, the self you hide.'
    labels_hint = 'none needed'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main', 'shadow'], 'actions': [
            A('look_at', 0, b.at(.4), x=.36), A('wave', b.at(.42), b.at(.6)), A('flinch', b.at(.66), b.at(.8)), A('sigh', b.at(.82), b.at(1.0), emotion='sad'),
            A('idle', 0, b.at(.6), actor='shadow', x=.64), A('cross_arms', b.at(.6), b.at(1.0), actor='shadow')]}

    def background(self, d):
        cv, pal = d.cv, d.pal
        x = d.ww * .64
        cv.rect(x - .42, -1.5, x + .42, .02, fill=tint_colour(pal.bg2, '#ffffff', .06), outline=pal.mid, width=.02)
        for k in range(3):
            cv.line([(x - .3 + k * .2, -1.4), (x - .15 + k * .2, -1.1)], tint_colour(pal.bg2, '#ffffff', .12), .01)


@setpiece
class Scale(SetPiece):
    name = 'scale'
    description = 'A giant balance scale weighs two labelled ideas against each other, tipping back and forth; the figure stands beneath, unable to decide.'
    labels_hint = 'exactly 2 words for the two pans, e.g. FREEDOM, SECURITY'
    tone = 'light'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(b, ('look_at', 0, .35, {'x': .5}), ('scratch_head', .36, .6), ('pace', .62, .85), ('shrug', .86, 1.0))}

    def camera(self, d):
        return (d.ww / 2, -1.2, .82)

    def background(self, d):
        cv, pal = d.cv, d.pal
        x, top = d.ww * .5, -2.15
        tilt = .22 * math.sin(d.t * .7)
        cv.rect(x - .03, top, x + .03, -1.15, fill=pal.ink)
        cv.poly([(x - .25, -1.15), (x + .25, -1.15), (x, -1.35)], fill=pal.ink)
        beam = 1.1
        l = (x - beam * math.cos(tilt), top + beam * math.sin(tilt))
        r = (x + beam * math.cos(tilt), top - beam * math.sin(tilt))
        cv.line([l, r], pal.ink, .03)
        labels = (d.labels + ['A', 'B'])[:2] if d.labels else ['FREEDOM', 'SECURITY']
        for p, word in zip((l, r), labels):
            cv.line([p, (p[0] - .25, p[1] + .45)], pal.mid, .006)
            cv.line([p, (p[0] + .25, p[1] + .45)], pal.mid, .006)
            cv.chord(p[0], p[1] + .45, .3, .1, 0, 180, pal.ink)
            cv.text(p[0], p[1] + .3, word.upper(), label_font_size(word, .5, .1), pal.ink, face='display')


@setpiece
class Flower(SetPiece):
    name = 'flower'
    description = 'In barren grey ground a single small amber flower grows and opens; the figure kneels to look at it. Hope, small meaning.'
    labels_hint = 'none needed'
    tone = 'light'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(b, ('walk', 0, .3, {'x': .42}), ('kneel', .34, .8, {'emotion': 'thoughtful'}), ('look_at', .8, 1.0))}

    def background(self, d):
        cv, pal = d.cv, d.pal
        cv.rect(cv.x0 - 1, 0, cv.x1 + 1, 4, fill=tint_colour(pal.bg2, pal.mid, .25))
        for i in range(30):
            x = cv.x0 + hashed(i, 'c') * (cv.x1 - cv.x0)
            cv.line([(x, .03 + .2 * hashed(i)), (x + .15, .05 + .2 * hashed(i))], tint_colour(pal.bg2, pal.mid, .45), .004)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        x = d.ww * .55
        grow = ease(window(d.t / d.dur, .2, .6))
        h = .3 * grow
        cv.line([(x, 0), (x + .02 * math.sin(d.t), -h)], tint_colour(pal.mid, '#3d5a3a', .5), .012)
        if grow > .2:
            cv.ellipse(x - .05, -h * .5, .05, .02, fill=tint_colour(pal.mid, '#3d5a3a', .5))
        bloom = ease(window(d.t / d.dur, .5, .75))
        if bloom > 0:
            top = (x + .02 * math.sin(d.t), -h)
            for k in range(6):
                a = k * math.pi / 3 + d.t * .1
                cv.circle(top[0] + math.cos(a) * .045 * bloom, top[1] + math.sin(a) * .045 * bloom, .035 * bloom, fill=pal.amber)
            cv.circle(top[0], top[1], .025 * bloom, fill=pal.glow)


@setpiece
class TitleCard(SetPiece):
    name = 'title_card'
    description = 'A huge title word appears letter by letter above a small, still figure. Use for the title reveal or a chapter heading.'
    labels_hint = 'the title word(s), e.g. NIHILISM'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': [A('idle', 0, b.duration, x=.5)]}

    def camera(self, d):
        return (d.ww / 2, -1.0, .95 + .06 * ease(d.t / max(1, d.dur)))

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        word = ' '.join(d.labels).upper() if d.labels else 'MEANING'
        shown = int(len(word) * window(d.t / d.dur, .1, .55) + .999)
        size = label_font_size(word, d.ww * .85, .7)
        cv.text(d.ww / 2, -1.55, word[:shown], size, pal.amber if d.amber else pal.ink, face='display')


@setpiece
class Thinker(SetPiece):
    name = 'thinker'
    description = 'The figure sits on a rock in fog, chin on hand, while words drift slowly around it and fade. Reflection, an open question.'
    labels_hint = '2-4 words drifting in the air, e.g. WHY, PURPOSE, NOTHING'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'props': [dict(id='rock', kind='rock', x=.45)],
                'actions': self.act(b, ('sit', 0, .2, {'target': 'rock', 'emotion': 'thoughtful'}), ('think', .2, 1.0))}

    def background(self, d):
        cv, pal = d.cv, d.pal
        for i in range(6, 0, -1):
            cv.ellipse(d.ww * .45, -.6, .45 * i, .3 * i, fill=tint_colour(pal.bg, pal.bg2, .25 * (6 - i) / 6 + .1))

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        words = d.labels or ['WHY']
        for i, w in enumerate(words[:4]):
            phase = d.t * .12 + i / max(1, len(words))
            a = phase * math.tau
            x = d.ww * .45 + math.cos(a) * 1.1
            y = -1.2 + math.sin(a * .7) * .45
            fade = .4 + .5 * abs(math.sin(a))
            cv.text(x, y, w.upper(), .12, tint_colour(pal.ink, pal.bg, fade), face='serif')


@setpiece
class Clock(SetPiece):
    name = 'clock'
    description = 'A giant clock looms behind the small figure; its hands race while the figure stands, then sits, as time slips away.'
    labels_hint = 'optional one word under the clock, e.g. LATER, TIME'
    tone = 'dark'

    def build(self, b):
        return {'characters': ['main'], 'actions': self.act(b, ('check_watch', 0, .35, {'x': .5, 'emotion': 'anxious'}), ('look_at', .36, .6), ('kneel', .62, 1.0, {'emotion': 'tired'}))}

    def camera(self, d):
        return (d.ww / 2, -1.15, .85)

    def background(self, d):
        cv, pal = d.cv, d.pal
        x, y, r = d.ww * .5, -1.45, .8
        cv.circle(x, y, r, fill=pal.bg2, outline=pal.line, width=.02)
        for k in range(12):
            a = k / 12 * math.tau
            cv.line([(x + math.sin(a) * r * .85, y - math.cos(a) * r * .85), (x + math.sin(a) * r * .95, y - math.cos(a) * r * .95)], pal.mid, .015)
        speed = 1 + 4 * d.t / max(1, d.dur)
        a = d.t * speed
        cv.line([(x, y), (x + math.sin(a) * r * .8, y - math.cos(a) * r * .8)], pal.mid, .012)
        cv.line([(x, y), (x + math.sin(a / 12) * r * .5, y - math.cos(a / 12) * r * .5)], pal.mid, .025)
        if d.labels:
            cv.text(x, y - r - .14, d.labels[0].upper(), .12, pal.mid, face='display')


@setpiece
class Cage(SetPiece):
    name = 'cage'
    description = 'The figure grips the bars of a cage, not noticing the door behind it is open. With amber, it turns, sees the door, and walks out.'
    labels_hint = 'optional one word on the cage, e.g. HABIT, COMFORT'
    tone = 'dark'

    def build(self, b):
        acts = [A('idle', 0, b.at(.6 if b.amber else 1.0), x=.5, emotion='sad')]
        if b.amber:
            acts += [A('turn', b.at(.62), b.at(.7)), A('walk', b.at(.72), b.at(1.0), x=.15, emotion='happy')]
        return {'characters': ['main'], 'actions': acts}

    def adjust(self, actor, c, t, plan):
        if t < (.6 if getattr(plan.scene, 'amber', False) else 1.0) * plan.duration:
            s = shoulder_of(c)
            f = side(c)
            c.hands = ((plan.ww * .5 + .3 * f, s[1] - .05), (plan.ww * .5 + .31 * f, s[1] - .08))
            c.head += .1
        return c

    def background(self, d):
        cv, pal = d.cv, d.pal
        x = d.ww * .5
        cv.rect(x - .55, -1.55, x - .5, 0, fill=pal.mid)
        cv.line([(x - .55, -1.55), (x - .9, -1.4), (x - .9, 0)], pal.mid, .01)

    def foreground(self, d):
        cv, pal = d.cv, d.pal
        x = d.ww * .5
        for k in range(7):
            bx = x + .1 + k * .07
            cv.line([(bx, -1.55), (bx, 0)], pal.ink, .014)
        cv.line([(x - .5, -1.55), (x + .55, -1.55)], pal.ink, .02)
        if d.labels:
            cv.text(x + .32, -1.7, d.labels[0].upper(), .1, pal.ink, face='display')


DEFAULT = 'thinker'


def get(name):
    return REGISTRY.get(name or '', None)


def catalog():
    """Text for the writer prompt."""
    return '\n'.join(f'- {p.name}: {p.description} Labels: {p.labels_hint}.' for p in REGISTRY.values())
