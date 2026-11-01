"""Write a narrated concept film (love, heartbreak, addiction, nihilism...) as a Day One-style shot list.

  python story/essay.py concept --title "Addiction" [--minutes auto|5] --dir build/writing
  python story/essay.py shots   --dir build/writing
  python story/essay.py merge   --dir build/writing --out build/film.json

Nothing is pre-scripted: for every title the writer invents a concrete story that dramatizes the
concept (who the hero is, where they are, what they do, what the inner voice says), and a narrator
explains the idea over the action. Every shot is composed from the engine's vocabulary
(engine/vocab.json): sets, time and weather, poses, moods, props, phone screens, notes, calendars,
speech bubbles, the inner voice, counters, big words and camera framing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'story'))
from validate import VOCAB, repair  # noqa: E402
from pipeline.writing.llm import Writer, Rejected, notice  # noqa: E402

WPS = 2.45            # narration words per second (Chatterbox, calm delivery)

FORMAT = """THE FORMAT: a narrated animated video essay in the visual language of Day One Films ("Loneliness", "Lust vs Love",
"Your Winter Arc Starts Now"), explaining one concept from psychology or philosophy.

THE PICTURE - a small human story that makes the concept physical:
- A plain cream blob character (the hero) lives through the concept in ordinary, specific places: a bedroom at 3:17am, a desk lit by
  a lamp, a kitchen with the fridge light, a bus stop in the rain, a cafe, a park bench, a rooftop at sunset, a gym, a hallway, an office.
- THE INNER VOICE: a black silhouette with glowing eyes is the concept's dark side made visible (craving for addiction, doubt for love,
  emptiness for nihilism, the past for heartbreak, fear, envy...). Its glow colour fits it. It stands beside the hero at weak moments
  and says SHORT lowercase lines (2-6 words): "just one more.", "nobody would notice.", "what's the point?". It wins early, loses at the end.
- Other people appear (friends, a partner, strangers) with distinct looks, and short lowercase dialogue in speech bubbles: "you okay?", "...yeah."
- SPECIFIC PHYSICAL DETAILS carry the meaning: a message typed then deleted, a call declined, a feed scrolling at 2am, a phone switched off,
  a note written in a notebook, a calendar with days crossed off, an alarm, two coffees on a table, rain, a door opening onto light.
- The hero MOVES and ACTS: walks, sits, lies awake, slumps, hugs knees, types, calls, cries, laughs, runs, falls, gets up, hugs someone.
- Colour carries emotion: cold or grey while stuck, the inner voice's colour in temptation, warm amber in connection, sunset for hope.
- An optional story device the viewer can track: a counter (e.g. "DAYS CLEAN 0", or two that contrast like "SEEN / KNOWN"),
  day chapters ("DAY 1", "DAY 30"), or none.

THE NARRATION - a calm, intelligent voice-over that EXPLAINS the concept while the story plays:
- It defines the concept clearly, explains how it works (the psychology or philosophy, with real thinkers or well-established ideas named
  accurately in your own words), why it feels the way it does, the strongest turn or objection, and what can change.
- It is concrete and connected to what is on screen ("He tells himself it's one more video. The brain calls that a reward."), never a lecture
  detached from the picture. Short spoken sentences of 6-18 words. Second person or third person, warm, honest, never preachy.
- It covers roughly half of the running time. Between narrated passages the story plays without narration: acting, dialogue, the inner voice.
- A few lines can twist: "The phone gave him a new face every second." / "She only had one."
- NO invented quotations, NO statistics or percentages, NO "studies show", NO diagnosing the viewer.

STRUCTURE (adapt it; do not follow it mechanically): (1) a cold open line on black that hooks; (2) the hero's ordinary moment that shows the
concept; (3) the narrator names and defines it; (4) the inner voice wins small moments while the narrator explains the mechanism; (5) a
trigger: a person, a message, an invitation; (6) a first attempt; (7) a relapse or low point; (8) the turn: the narrator's key insight, a decision
(an extreme close-up, a phone switched off, a note written); (9) change over time; (10) a quiet payoff with another person or with
themselves; (11) a two-line quote card that twists; (12) a title card with a short tagline; (13) like and subscribe.
"""

BANNED = [
    (r'\b\d+(?:\.\d+)?\s*(?:%|percent|per cent)', 'contains a percentage or statistic'),
    (r'\b(?:studies|research|scientists|psychologists|experts)\s+(?:show|shows|prove|proves|proved|found|suggest|demonstrate)', 'claims research findings'),
    (r'["“][^"”]{25,}["”]', 'contains a direct quotation'),
    (r'\byou\s+(?:have|suffer from)\s+(?:depression|anxiety|adhd|a disorder|an addiction)', 'diagnoses the viewer'),
]


def sets_text():
    return '; '.join(f'{k} ({s["about"]})' for k, s in VOCAB['sets'].items())


def target_seconds(minutes):
    return (minutes * 60, minutes * 60) if minutes else (210, 330)


def split_sentences(text):
    parts = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', str(text or '').strip()) if p.strip()]
    out = []
    for p in parts:                       # keep each caption within two lines
        while len(p) > 150:
            cut = p.rfind(',', 0, 140)
            cut = cut if cut > 50 else p.rfind(' ', 0, 140)
            out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
        out.append(p)
    return out


def beat_narration(beat):
    n = beat.get('narration') or []
    if isinstance(n, str):
        n = split_sentences(n)
    return [s for x in n for s in split_sentences(x)]


# ---------------------------------------------------------------- stage 1: concept and beats
def concept_prompt(title, minutes):
    lo, hi = target_seconds(minutes)
    v = VOCAB
    length = (f'about {minutes:g} minutes ({lo:.0f} seconds) in total' if minutes else
              f'the length this concept deserves: {lo // 60:.0f}-{hi // 60:.1f} minutes ({lo}-{hi} seconds) in total')
    words = round((lo + hi) / 2 * .5 * WPS)
    return FORMAT + f"""
You are the writer-director. For the topic below, invent an ORIGINAL story that dramatizes it (a new hero, new places, new situation;
never a generic or reused plot) and write the concept and beat sheet as JSON:
{{"title": short video title,
 "youtube_titles": [3 honest, curiosity-driven titles, max 70 characters],
 "description": 2 short paragraphs then a line of 3-5 hashtags, "tags": [10-15 search tags], "pinned_comment": one question for viewers,
 "thumbnail_words": 2-4 bold words,
 "idea": {{"definition": one sentence, "mechanism": how it works, "thinkers": real thinkers or ideas you will mention, "turn": the key insight}},
 "logline": one sentence of the story,
 "inner_voice": what the black silhouette represents in this film, "demon_color": hex colour,
 "device": {{"type": "counter" | "days" | "none", "items": [{{"label": "...", "color": "#hex"}}]}},
 "cast": [{{"id": "hero", "kind": "hero", "hood": true}}, {{"id": "demon", "kind": "demon"}}, then 1-3 people:
          {{"id": short lowercase name, "kind": "friend" | "extra", "hair": ..., "hair_color": ..., "top": colour, "top_style": ..., "pants": colour,
           "scarf": colour, "hat": ..., "glasses": true|false}}],
 "music_prompt": instrumental style for an AI composer: instruments, mood arc, bpm,
 "opening_line": the cold-open line on black,
 "beats": [{{"name": ..., "seconds": 8-24, "where": set, "time": night|dawn|day|dusk, "weather": none|rain|snow, "grade": colour grade,
            "emotion": hero mood, "what_happens": concrete visible action and acting (who does what, what objects, what is on screens),
            "narration": [the narrator's sentences over this beat, in order; [] for an unnarrated beat],
            "demon_line": optional, "dialogue": [{{"who": id, "text": ...}}], "phone": optional what is on the phone,
            "insert": optional note/calendar/photo/letter and what it shows, "big_text": optional e.g. "DAY 1.",
            "counter_values": numbers for the device, "chapter": optional, "relapse": true|false}}],
 "quote": [two lines, the second twists the first], "logo": ["X vs Y." or the concept in two or three words, "short tagline"]}}

LENGTH: {length}. Write 14-20 beats. Narration in total about {words} words (roughly half the running time), spread over the film
with some beats unnarrated. A narrated beat lasts at least as long as its narration takes to speak ({WPS} words per second) plus a pause.

VOCABULARY - use only these:
sets: {sets_text()}
grades: {list(v['grades'])}; moods: {v['moods']}; times: {v['times']}; weather: {v['weather']}
wardrobe: hair {v['wardrobe']['hair']}; hair_color {v['wardrobe']['hair_color']}; top/pants/scarf colours ({v['wardrobe']['top']});
top_style {v['wardrobe']['top_style']}; hat {v['hats']}.
"""


def check_concept(sheet, minutes):
    problems = []
    beats = sheet.get('beats') or []
    if len(beats) < 10:
        problems.append(f'only {len(beats)} beats; write 14-24')
    lo, hi = target_seconds(minutes)
    total = 0.
    words = 0
    for i, b in enumerate(beats):
        lines = beat_narration(b)
        w = sum(len(x.split()) for x in lines)
        words += w
        secs = max(float(b.get('seconds') or 10), w / WPS + 1.5 * max(1, len(lines)) + 2)
        total += secs
        for line in lines:
            for pattern, why in BANNED:
                if re.search(pattern, line, re.I):
                    problems.append(f'beat {i + 1} narration {why}: "{line[:80]}"')
        if b.get('where') not in VOCAB['sets']:
            b['where'] = 'void'
    total += 18                           # cold open and closing cards
    if minutes:
        if abs(total - lo) / lo > .25:
            problems.append(f'the film would run about {total / 60:.1f} minutes but {minutes:g} were asked; '
                            f'{"add" if total < lo else "remove"} beats or narration ({words} narration words now)')
    elif not lo * .85 <= total <= hi * 1.15:
        problems.append(f'the film would run about {total / 60:.1f} minutes with {words} narration words; aim for {lo // 60:.0f}-{hi / 60:.1f} minutes')
    narrated = sum(1 for b in beats if beat_narration(b))
    if beats and not .35 <= narrated / len(beats) <= .85:
        problems.append(f'{narrated} of {len(beats)} beats are narrated; narrate roughly half to two thirds of them')
    if not any(b.get('demon_line') for b in beats):
        problems.append('the inner voice never speaks; give it short lines in several beats')
    return problems, total


def stage_concept(title, minutes, out_dir, research=''):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    writer = Writer()
    system = concept_prompt(title, minutes) + 'Return only JSON.'
    user = f'TOPIC: {title}\n\nBACKGROUND READING (for accuracy, do not copy):\n{research[:2200] or "(none)"}\n\nWrite the JSON now.'
    report = {}

    def validate(data):
        problems, total = check_concept(data, minutes)
        report['estimated_seconds'] = total
        if problems:
            length_only = all('minutes' in p for p in problems)
            target = target_seconds(minutes)[0] if minutes else sum(target_seconds(None)) / 2
            raise Rejected('; '.join(problems[:8]), data if length_only else None, abs(total - target))
        return data

    t0 = time.time()
    sheet = writer.json(system, user, validate, temperature=.85, max_tokens=6500)
    sheet['_title'] = title
    sheet['_writer'] = writer.used
    idmap = {}
    for p in sheet.get('cast') or []:
        raw = str(p.get('id', '')); clean = re.sub(r'[^a-z0-9_]', '', raw.lower())[:12] or 'friend'
        idmap[raw] = clean; p['id'] = clean
    for b in sheet.get('beats') or []:
        b['narration'] = beat_narration(b)
        for d in b.get('dialogue') or []:
            d['who'] = idmap.get(str(d.get('who')), re.sub(r'[^a-z0-9_]', '', str(d.get('who', '')).lower())[:12])
    (out / 'beats.json').write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    beats = sheet['beats']
    notice('Concept', f"{sheet.get('title')}: {sheet.get('logline', '')} | inner voice: {sheet.get('inner_voice', '')} | "
                      f"{len(beats)} beats, about {report.get('estimated_seconds', 0) / 60:.1f} min, by {writer.used} in {(time.time() - t0):.0f}s")
    for k in range(0, len(beats), 6):
        notice(f'Beats {k + 1}-{min(len(beats), k + 6)}', ' || '.join(
            f"{i + 1}. {b.get('where')}: {str(b.get('what_happens', ''))[:110]}" for i, b in enumerate(beats[k:k + 6], k)))
    return sheet


# ---------------------------------------------------------------- stage 2: shots
def shot_rules():
    v = VOCAB
    return f"""SHOT JSON (one object per shot):
{{"dur": seconds 2-7,
 "set": one of {list(v['sets'])}, "time": one of {v['times']}, "weather": one of {v['weather']}, "grade": one of {list(v['grades'])},
 "clock": "03:17" (bedroom clock), "camera": {{"frame": one of {list(v['frames'])}, "on": actor id, "push": 0.03-0.12}},
 "actors": [{{"id": cast id, "x": 0-100, "to": 0-100 (walk/run target), "pose": one of {list(v['poses'])},
             "mood": one of {v['moods']}, "hold": one of {v['holds']}, "facing": -1|0|1, "seated": true,
             "target": id (lean/grab/hug/reachout), "at": seconds delay, "depth": "back", "scale": 0.4-1.2}}],
 "lines": [{{"who": actor id | "narrator", "text": str, "twist": str (narrator only, optional), "at": seconds, "style": "bubble"|"float"|"thought"|"whisper"}}],
 "hud": {{"values": [numbers or [from, to]], "chapter": "DAY 4", "alert": true}}, "big": {{"text": "DAY 1.", "at": 0.3}},
 "phone": {{"app": one of {list(v['phone_apps'])}, "contact": name, "time": "18:02", "messages": [{{"from": "them"|"me", "text": str, "at": s}}],
           "typing": {{"text": str, "at": s, "action": "delete"|"send"}}, "notifications": [{{"app": str, "text": str, "at": s}}],
           "call": {{"decline_at": s}}, "off_at": s}},
 "insert": {json.dumps(v['inserts'])},
 "items": [{{"type": one of {v['items']}, "x": 0-100, "on": "nightstand"|"desk"|"table"|"bed"}}],
 "door": [0, 1], "door_at": s, "music": one of {v['music_levels']}, "transition": one of {v['transitions']}}}
SPOTS per set: {json.dumps({k: s['spots'] for k, s in v['sets'].items()})}
SEATS: {json.dumps({k: s.get('seat') for k, s in v['sets'].items() if s.get('seat')})}
RULES:
- NARRATION: each of the beat's narration sentences goes, in order, on its own shot as {{"who": "narrator", "text": the sentence, "at": 0.2}}.
  While the narrator speaks, the picture keeps acting: give that shot an action that matches the sentence. Never put two narration sentences on one shot.
- Unnarrated shots are short (2-4 s) and full of acting: dialogue bubbles, the inner voice's lines, phones, inserts, reactions.
- Vary framing like an editor: never more than two "wide" in a row; "close" for reactions (detailed faces), "extreme" for a decision,
  "two" for two characters together, "medium" for actions, "phone"/"insert" for objects (no actors on those).
- Characters move: use walk/run with "x" and "to"; use the set's seats for sit/type/lie; change poses from shot to shot.
- The inner voice (id "demon") stands within 10-14 of the hero when it speaks, pose lean or grab with target "hero".
- Two people at a table or bench face each other: facing 1 on the left, -1 on the right.
- Every actor gets a mood. Every shot of a beat uses the beat's set, time, weather and grade unless the beat moves.
"""


def shots_for(beats, first, sheet, writer, example):
    cast = ', '.join(f"{p.get('id')} ({p.get('kind')})" for p in sheet.get('cast', []) if p.get('id'))
    system = FORMAT + '\n' + shot_rules() + f"""
You are the storyboard artist. Turn EACH beat below into 2-6 shots (more shots for longer beats; one narration sentence per shot).
Reply with JSON only: {{"beats": [{{"beat": beat number, "shots": [...]}}]}}.
Cast: {cast}. Inner voice: {sheet.get('inner_voice', '')}. Story device: {json.dumps(sheet.get('device') or {})} - put counter values in hud.values.
Example shots from a different film in this visual language (copy the JSON shape and craft, not the story):
{example}"""
    payload = [{'beat': first + i + 1, **{k: v for k, v in b.items() if k != 'seconds'}, 'seconds': b.get('seconds')} for i, b in enumerate(beats)]
    user = f"Film: {sheet.get('title')} - {sheet.get('logline', '')}\nBeats:\n{json.dumps(payload, ensure_ascii=False)}"

    def validate(data):
        groups = data.get('beats') if isinstance(data, dict) else None
        if not isinstance(groups, list) or not groups:
            raise ValueError('return {"beats": [{"beat": n, "shots": [...]}]}')
        got = {}
        for g in groups:
            if isinstance(g, dict) and isinstance(g.get('shots'), list) and g['shots']:
                try:
                    got[int(g.get('beat')) - first - 1] = g['shots']
                except (TypeError, ValueError):
                    pass
        missing = [first + i + 1 for i in range(len(beats)) if i not in got]
        if missing:
            raise ValueError(f'no shots for beats {missing}')
        return got

    return writer.json(system, user, validate, temperature=.55, max_tokens=5200, attempts=3)


def place_narration(beat, shots):
    """Guarantee every narration sentence is spoken, in order, one per shot, without losing any."""
    sentences = beat_narration(beat)
    for s in shots:
        s['lines'] = [l for l in (s.get('lines') or []) if isinstance(l, dict) and l.get('who') != 'narrator']
    if not sentences:
        return shots
    visual = [s for s in shots if not s.get('card')] or shots
    while len(visual) < len(sentences):               # extend with a fresh angle of the last shot
        base = json.loads(json.dumps(visual[-1]))
        frame = (base.get('camera') or {}).get('frame', 'wide')
        nxt = {'wide': 'medium', 'medium': 'close', 'close': 'wide', 'two': 'close', 'extreme': 'medium', 'phone': 'medium', 'insert': 'medium'}[frame] \
            if frame in ('wide', 'medium', 'close', 'two', 'extreme', 'phone', 'insert') else 'medium'
        if frame in ('phone', 'insert'):
            base.pop('phone', None); base.pop('insert', None)
            if not base.get('actors'):
                base['actors'] = [{'id': 'hero', 'x': 50, 'pose': 'stand', 'mood': beat.get('emotion', 'neutral')}]
        base['camera'] = {'frame': nxt, 'on': 'hero', 'push': .05}
        base['lines'] = []
        shots.insert(shots.index(visual[-1]) + 1, base)
        visual.append(base)
    # spread sentences evenly over the visual shots
    step = len(visual) / len(sentences)
    for k, sentence in enumerate(sentences):
        shot = visual[min(len(visual) - 1, int(k * step))]
        shot['lines'].insert(0, {'who': 'narrator', 'text': sentence, 'at': .25})
        shot['dur'] = max(float(shot.get('dur') or 3), .25 + len(sentence.split()) / WPS + .8)
    return shots


def ensure_demon(beat, shots):
    """If the beat's inner-voice line was not staged, add a shot of it beside the hero."""
    line = str(beat.get('demon_line') or '').strip()
    if not line or any(l.get('who') == 'demon' for s in shots for l in (s.get('lines') or [])):
        return shots
    anchor = next((s for s in reversed(shots) if s.get('actors')), None)
    hero = next((a for a in (anchor or {}).get('actors', []) if a.get('id') == 'hero'), None)
    pose = hero.get('pose') if hero and hero.get('pose') in ('sit', 'slump', 'lie', 'phone', 'type', 'stand', 'hugknees', 'headhands') else 'stand'
    x = float(hero.get('x', 50)) if hero else 50
    base = {k: anchor[k] for k in ('set', 'time', 'weather', 'grade', 'clock') if anchor and k in anchor}
    shots.append({**base, 'dur': 3.2, 'camera': {'frame': 'two', 'on': 'hero', 'push': .06},
                  'actors': [{'id': 'demon', 'x': x - 12 if x > 30 else x + 12, 'pose': 'lean', 'target': 'hero'},
                             {'id': 'hero', 'x': x, 'pose': pose, 'mood': beat.get('emotion', 'sad'),
                              **({'seated': True} if pose == 'phone' and hero and hero.get('seated') else {})}],
                  'lines': [{'who': 'demon', 'text': line, 'at': .7}], 'music': 'low'})
    return shots


def example_shots():
    ref = json.loads((ROOT / 'examples' / 'dayone-style-reference.json').read_text())
    return json.dumps([ref['shots'][k] for k in (1, 3, 5, 9, 13, 16, 18)], ensure_ascii=False)


def stage_shots(out_dir, group=4):
    out = Path(out_dir)
    sheet = json.loads((out / 'beats.json').read_text())
    beats = sheet['beats']
    writer = Writer()
    example = example_shots()
    result = {}
    t0 = time.time()
    for first in range(0, len(beats), group):
        chunk = beats[first:first + group]
        try:
            got = shots_for(chunk, first, sheet, writer, example)
        except Exception as exc:  # noqa: BLE001 -- smaller chunks, then a simple fallback
            notice('Storyboard retry', f'beats {first + 1}-{first + len(chunk)}: {str(exc)[:300]}', 'warning')
            got = {}
            for i, b in enumerate(chunk):
                try:
                    got.update({i: shots_for([b], first + i, sheet, writer, example)[0]})
                except Exception as exc2:  # noqa: BLE001
                    notice('Storyboard fallback', f'beat {first + i + 1}: {str(exc2)[:200]}', 'warning')
                    got[i] = fallback_shots(b)
        for i, shots in got.items():
            result[first + i] = ensure_demon(beats[first + i], place_narration(beats[first + i], [s for s in shots if isinstance(s, dict)]))
        print(f'beats {first + 1}-{first + len(chunk)}: {sum(len(result.get(first + i, [])) for i in range(len(chunk)))} shots', flush=True)
    (out / 'shots.json').write_text(json.dumps(result, ensure_ascii=False))
    notice('Storyboard', f'{sum(len(v) for v in result.values())} shots for {len(beats)} beats in {(time.time() - t0) / 60:.1f} min by {writer.used}')


def fallback_shots(beat):
    """A plain but correct staging when the model cannot storyboard a beat."""
    mood = beat.get('emotion') if beat.get('emotion') in VOCAB['moods'] else 'neutral'
    base = {k: beat[k] for k in ('time', 'weather', 'grade') if beat.get(k)}
    seat = VOCAB['sets'].get(beat.get('where'), {}).get('seat')
    pose = 'sit' if seat else 'stand'
    shots = [{**base, 'dur': 3.5, 'set': beat.get('where', 'void'), 'camera': {'frame': 'wide', 'push': .04},
              'actors': [{'id': 'hero', 'x': 48, 'pose': pose, 'mood': mood}]},
             {**base, 'dur': 3.0, 'set': beat.get('where', 'void'), 'camera': {'frame': 'close', 'on': 'hero', 'push': .06},
              'actors': [{'id': 'hero', 'x': 50, 'pose': pose, 'mood': mood}]}]
    if beat.get('demon_line'):
        shots.append({**base, 'dur': 3.0, 'set': beat.get('where', 'void'), 'camera': {'frame': 'two', 'on': 'hero'},
                      'actors': [{'id': 'demon', 'x': 38, 'pose': 'lean', 'target': 'hero'}, {'id': 'hero', 'x': 50, 'pose': pose, 'mood': mood}],
                      'lines': [{'who': 'demon', 'text': beat['demon_line'], 'at': .6}]})
    return shots


# ---------------------------------------------------------------- stage 3: merge
def stage_merge(out_dir, out_path):
    out = Path(out_dir)
    sheet = json.loads((out / 'beats.json').read_text())
    per = {int(k): v for k, v in json.loads((out / 'shots.json').read_text()).items()}
    shots = []
    for i, beat in enumerate(sheet['beats']):
        for s in per.get(i) or place_narration(beat, fallback_shots(beat)):
            if not s.get('card') and (s.get('camera') or {}).get('frame') != 'insert':
                s.setdefault('set', beat.get('where'))
            for key in ('time', 'grade'):
                if beat.get(key):
                    s.setdefault(key, beat[key])
            if beat.get('weather') and beat['weather'] != 'none':
                s.setdefault('weather', beat['weather'])
            if beat.get('relapse') and isinstance(s.get('hud'), dict):
                s['hud'].setdefault('alert', True)
            s['beat'] = i + 1
            shots.append(s)
    cast = {'hero': {'kind': 'hero', 'hood': True}, 'demon': {'kind': 'demon'}}
    for p in sheet.get('cast') or []:
        pid = p.get('id')
        if not pid:
            continue
        entry = {k: v for k, v in p.items() if k != 'id' and v not in (None, '', 'none', False)}
        if pid == 'demon':
            entry = {'kind': 'demon'}
        cast[pid] = {**cast.get(pid, {}), **entry}
    dev = sheet.get('device') or {}
    hud = {'items': dev.get('items')[:2]} if dev.get('type') == 'counter' and dev.get('items') else None
    head = []
    opening = str(sheet.get('opening_line') or '').strip()
    if opening:
        head.append({'dur': 3.4 + len(opening.split()) / WPS, 'music': 'low', 'card': {'style': 'line', 'lines': [opening]},
                     'lines': [{'who': 'narrator', 'text': opening, 'at': .3, 'hidden': True}]})
    tail = []
    q = [str(x) for x in (sheet.get('quote') or [])]
    if len(q) >= 2:
        tail.append({'dur': 6.0, 'music': 'high', 'card': {'style': 'quote', 'lines': q[:2]},
                     'lines': [{'who': 'narrator', 'text': q[0], 'twist': q[1], 'at': .4, 'hidden': True}]})
    logo = [str(x) for x in (sheet.get('logo') or [])]
    if logo:
        tail.append({'dur': 4.6, 'music': 'high', 'card': {'style': 'logo', 'lines': logo[:3]}})
    tail.append({'dur': 4.4, 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this made you think, like and subscribe.']},
                 'actors': [{'id': 'hero', 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}]})
    film = {'title': sheet.get('title') or sheet.get('_title'), 'logline': sheet.get('logline', ''),
            'demon_color': sheet.get('demon_color'), 'narrator': 'male', 'hud': hud,
            'music': {'prompt': sheet.get('music_prompt') or ''}, 'cast': cast, 'shots': head + shots + tail,
            'publish': {k: sheet.get(k) for k in ('youtube_titles', 'description', 'tags', 'pinned_comment', 'thumbnail_words', 'idea', 'inner_voice')},
            'writer': sheet.get('_writer')}
    film, notes = repair(film)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(film, indent=1, ensure_ascii=False))
    script_md(film, Path(out_path).with_name('story.md'))
    spoken = sum(len(l['text'].split()) for s in film['shots'] for l in s['lines'] if l['who'] == 'narrator')
    notice('Shot list', f"{film['title']}: {len(film['shots'])} shots, {film['duration'] / 60:.1f} min before voice, {spoken} narration words")
    for n in notes[:12]:
        print(' -', n)
    return film


def script_md(film, path):
    lines = [f'# {film["title"]}', '', f'_{film.get("logline", "")}_', '']
    t = 0.
    for i, s in enumerate(film['shots']):
        cam = (s.get('camera') or {}).get('frame', 'wide')
        who = ', '.join(f'{a["id"]} {a["pose"]}' + (f' ({a["mood"]})' if a.get('mood') else '') for a in s.get('actors', []))
        stamp = f'**{i + 1:02d}** `{int(t // 60)}:{t % 60:04.1f}`'
        if s.get('card'):
            desc = f'{stamp} CARD ({s["card"]["style"]}): ' + ' / '.join(s['card']['lines'])
        elif cam == 'insert':
            desc = f'{stamp} INSERT {s["insert"]["type"]}: {s["insert"].get("text", "")}'
        elif cam == 'phone':
            desc = f'{stamp} PHONE {s["phone"].get("app")}'
        else:
            desc = f'{stamp} {s.get("set")} · {cam}' + (f' · {s["grade"]}' if s.get('grade') else '') + f' · {who}'
        lines.append(desc)
        for ln in s.get('lines', []):
            lines.append(f'  - {ln["who"]}: "{ln["text"]}"' + (f' / "{ln["twist"]}"' if ln.get('twist') else ''))
        t += s['dur']
    path.write_text('\n'.join(lines) + '\n')


def minutes_value(text):
    text = str(text or 'auto').strip().lower()
    return None if text in ('', 'auto', '0') else float(text)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['concept', 'shots', 'merge'])
    ap.add_argument('--title', default='')
    ap.add_argument('--minutes', default='auto')
    ap.add_argument('--dir', default='build/writing')
    ap.add_argument('--out', default='build/film.json')
    ap.add_argument('--research', default='')
    a = ap.parse_args()
    if a.stage == 'concept':
        research = Path(a.research).read_text() if a.research and Path(a.research).exists() else ''
        stage_concept(a.title, minutes_value(a.minutes), a.dir, research)
    elif a.stage == 'shots':
        stage_shots(a.dir)
    else:
        stage_merge(a.dir, a.out)
