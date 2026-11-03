"""Write a narrated concept film (love, heartbreak, addiction, nihilism...) as an animated shot list.

  python story/essay.py concept --title "Addiction" [--minutes auto|5] --dir build/writing
  python story/essay.py shots   --dir build/writing
  python story/essay.py merge   --dir build/writing --out build/film.json

Nothing is pre-scripted. The film's structure comes from explaining the concept: the writer first
works out the explanation, then decides, idea by idea, how to show it (a moment in one person's
life, a different person, a metaphor acted out, a montage, a lesson, the inside of a mind...), and
builds every place from parts. Checks reject films that fall back on the same moves.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'story'))
from validate import VOCAB, repair  # noqa: E402
from pipeline.writing.llm import Writer, Rejected, notice, DEFAULT_MODELS  # noqa: E402
from pipeline.writing.quotation import has_attributed_quotation  # noqa: E402
from story.normalization import dialogue_lines, cast_aliases, character_ids
from story.planning import plan_in_parts
from story.editor import review_concept  # noqa: E402

WPS = 2.45            # narration words per second (Chatterbox, calm delivery)

STYLE = """THE STYLE (the look, not the story): minimal 2D animation. Soft cream blob characters with expressive faces and real body
acting; other people with their own hair, clothes and colours; dark, simple places lit by pools of light (lamps, windows, screens,
streetlights, sunsets); colour grades that follow the emotion; a calm narrator; speech bubbles; occasional big words on screen.
A black silhouette with glowing eyes MAY personify a force inside someone (a craving, a fear, grief...) when that genuinely helps
explain the concept - it is a tool, not a requirement, and most concepts do not need it in every section."""

MODES = {
    'story': 'a moment in the life of a recurring character (the film may follow one person, a couple, a family...)',
    'vignette': 'a different person in a different situation who shows the same idea from another angle',
    'metaphor': 'the idea acted out symbolically in a built place (a stage, a void with a word on the wall, a door of light, a crowd, stairs, chains of people...)',
    'montage': '3-6 very short shots of different people and places showing one pattern',
    'lesson': 'the explanation shown directly: a thinker at a desk, a classroom whiteboard, a historical moment, a diagram acted by people',
    'inner': 'the inside of a mind: a dark room or void, thoughts as words, the other self or the silhouette',
    'contrast': 'two situations cut against each other to show a difference',
    'hook': 'a strange or striking image that makes the viewer ask a question',
}

BANNED = [
    (r'\b\d+(?:\.\d+)?\s*(?:%|percent|per cent)', 'contains a percentage or statistic'),
    (r'\b(?:studies|research|scientists|psychologists|experts)\s+(?:show|shows|prove|proves|proved|found|suggest|demonstrate)', 'claims research findings'),
    (r'\byou\s+(?:have|suffer from)\s+(?:depression|anxiety|adhd|a disorder|an addiction)', 'diagnoses the viewer'),
]


def sets_text():
    return '; '.join(f'{k} ({s["about"]})' for k, s in VOCAB['sets'].items())


def target_seconds(minutes):
    return (minutes * 60, minutes * 60) if minutes else (210, 330)


def split_sentences(text):
    """Preserve spoken sentences; the caption renderer handles short visual phrases."""
    return [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'])', str(text or '').strip()) if p.strip()]


def beat_narration(beat):
    n = beat.get('narration') or []
    if isinstance(n,(str,dict)):
        n=[n]
    if not isinstance(n,list):
        raise ValueError('narration must be a sentence list')
    out=[]
    for item in n:
        if isinstance(item,dict):
            item=item.get('text')
        if not isinstance(item,str):
            raise ValueError('narration entries must be strings or objects with a text string')
        if re.match(r"^\s*\{\s*['\"]text['\"]\s*:",item):
            raise ValueError('Narration contains serialized metadata; replay the raw edited draft instead')
        out.extend(split_sentences(item))
    return out


# ---------------------------------------------------------------- stage 1: concept and beats
def scene_vocab():
    sc = VOCAB['scene']
    return (f"base {list(sc['base'])}; wall {sc['wall']}; ground {sc['ground']}; backdrop {sc['backdrop']}; light {sc['light']};\n"
            f"elements (each {{\"type\", \"x\" 0-100, optional \"label\", \"color\", \"w\", \"front\": true}}): {', '.join(sc['elements'])}")


def concept_prompt(title, minutes):
    lo, hi = target_seconds(minutes)
    v = VOCAB
    length = (f'about {minutes:g} minutes ({lo:.0f} seconds) in total' if minutes else
              f'the length this concept deserves: {lo // 60:.0f}-{hi / 60:.1f} minutes ({lo}-{hi} seconds) in total')
    words = round((lo + hi) / 2 * .85 * 2.7) if not minutes else round(lo * .85 * 2.7)
    modes = '\n'.join(f'  - {k}: {d}' for k, d in MODES.items())
    return f"""You write and direct narrated animated video essays that explain one concept from psychology or philosophy.
{STYLE}

HOW TO BUILD THIS FILM (think in this order):
1. THE EXPLANATION. What is this concept, really? How does it work, where does it come from, what do people get wrong about it,
   what do real thinkers or well-established ideas say (named accurately, in your own words), what is the strongest objection or
   turn, and what changes when you understand it? Choose the 5-8 ideas THIS concept needs, in the order that builds understanding.
   The order is yours; it must not follow a stock template (no default "hero is stuck, relapses, then wins" arc).
2. THE NARRATION for each idea: calm, intelligent, concrete spoken sentences of 6-18 words, tied to what is on screen. It carries
   the explanation; most of the running time is spoken, with purposeful short acting pauses. NO fabricated or unverified quotations attributed to real people
   (paraphrase their ideas), NO statistics or percentages, NO "studies show", NO diagnosing the viewer. The narrator MAY recount
   fictional dialogue, self-talk and inner thoughts; quotation marks alone are allowed.
3. THE PICTURE for each idea: pick the visual mode that makes THIS idea clearest, and vary the modes across the film:
{modes}
   ONLY what the engine can draw appears on screen: people (poses, moods, held objects {VOCAB['holds']}), the place parts below,
   props {VOCAB['items']}, phones, notes/letters/photos/calendars, speech bubbles and big words. Anything else (a shattered glass,
   a wilted flower, a script with a title) will simply not appear, so stage ideas through PEOPLE doing things.
   Invent specific, physical moments that belong to this concept only (what would a grieving person touch? what does pride look
   like at a dinner table?). Do not default to phones, 3am clocks, fridges or calendars unless the concept is about them.
4. PLACES: any named set ({', '.join(k for k in v['sets'] if k != 'scene')}) or a place you BUILD with "scene"
   ({scene_vocab()}). Use the places the argument or story needs; preserve continuity and build what the idea needs (a hospital room, a wedding, a classroom, a beach, a
   church, a train, a stage, a graveyard, a family dinner, a void with one word on the wall...).

Return JSON:
{{"title": short title, "youtube_titles": [3 honest curiosity-driven titles, max 70 chars], "description": 2 short paragraphs and a line
 of 3-5 hashtags, "tags": [10-15], "pinned_comment": a question for viewers, "thumbnail_words": 2-4 bold words,
 "idea": {{"definition": one sentence, "mechanism": how it works, "thinkers": who or what you cite, "turn": the key insight}},
 "approach": one sentence on how this film shows the idea (e.g. "five strangers on one night", "one marriage over forty years",
             "a lecture that keeps turning into real life"),
 "cast": [{{"id": short lowercase id, "kind": "hero"|"friend"|"extra"|"demon", "hair": ..., "hair_color": ..., "top": colour,
           "top_style": ..., "pants": colour, "scarf": colour, "hat": ..., "glasses": true|false, "hood": true|false}}],
 "inner_voice": null or {{"represents": what the silhouette is, "color": "#hex"}},
 "device": {{"type": "none" | "counter" | "days", "items": [{{"label": ..., "color": "#hex", "mode": "cumulative"|"value"}}]}} (usually none),
 "music_prompt": instrumental style for an AI composer that fits THIS concept (instruments, mood arc, bpm),
 "cold_open": optional line shown on black at the start, or "",
 "ending": optional final line shown on black, or "",
 "beats": [{{"idea": which idea this beat explains, "mode": one of {list(MODES)}, "seconds": 8-26,
            "where": a named set or "scene", "scene": {{the built place}} when where is "scene",
            "time": night|dawn|day|dusk, "weather": none|rain|snow, "grade": one of {list(v['grades'])},
            "who": [cast ids on screen], "emotion": main mood, "what_happens": concrete visible action and acting,
            "narration": [sentences, in order; [] for an unnarrated beat], "dialogue": [{{"who": id, "text": short lowercase line}}],
            "inner_voice_line": optional 2-6 lowercase words, "big_text": optional word(s) shown large}}]}}

LENGTH: {length}. Write 12-20 beats. Narration in total about {words} words: roughly two thirds of the beats are narrated with
about {round(words / 10)} words each (usually 3-4 full explanatory sentences); the rest play without narration. Count narration words
separately from what_happens, dialogue and metadata; if space is tight, shorten visual descriptions and metadata, never the narration.
A narrated beat lasts at least as long as its narration takes to speak ({WPS} words per second) plus pauses.
Producer notes describe creative intent; follow them.
VOCABULARY: moods {v['moods']}; times {v['times']}; weather {v['weather']}; wardrobe: hair {v['wardrobe']['hair']},
hair_color {v['wardrobe']['hair_color']}, top_style {v['wardrobe']['top_style']}, hat {v['hats']}, colours: {v['wardrobe']['top']}.
"""


END_CARD = re.compile(r'\b(subscribe|logo|tagline|title card|quote card|end card|credits)\b', re.I)


def drop_end_cards(sheet):
    """Remove beats that restage the automatic cards (logo, quote, like and subscribe)."""
    beats = sheet.get('beats') or []
    keep = [b for b in beats if not (END_CARD.search(str(b.get('what_happens', ''))) and not beat_narration(b))]
    sheet['beats'] = keep
    return len(beats) - len(keep)


PHONEY = re.compile(r'\b(phone|scroll|feed|screen|notification|text message|social media|app|online|internet|instagram|tiktok)\b', re.I)
STOCK = re.compile(r'\b(3:17|3am|3 am|2am|fridge|calendar|alarm clock)\b', re.I)


def place_key(b):
    if b.get('where') == 'scene' and isinstance(b.get('scene'), dict):
        sc = b['scene']
        return 'scene:' + str(sc.get('base')) + ':' + ','.join(sorted(str(e.get('type')) for e in sc.get('elements') or [] if isinstance(e, dict))[:4])
    return str(b.get('where'))


def check_concept(sheet, minutes):
    problems = []
    drop_end_cards(sheet)
    beats = sheet.get('beats') or []
    if len(beats) < 5:
        problems.append(f'only {len(beats)} argument beats; develop at least five substantive advances')
    lo, hi = target_seconds(minutes)
    total, words = 0., 0
    for i, b in enumerate(beats):
        dialogue, dialogue_problems = dialogue_lines(b.get('dialogue'), [p.get('id') for p in sheet.get('cast') or [] if isinstance(p,dict)], cast_aliases(sheet.get('cast') or []))
        b['dialogue'] = dialogue
        if sheet.get('cast'):
            b['who'], who_problems = character_ids(b.get('who',[]), sheet['cast'])
            dialogue_problems.extend(who_problems)
        problems.extend(f'beat {i+1}: {problem}' for problem in dialogue_problems)
        lines = beat_narration(b)
        if has_attributed_quotation(' '.join(lines)):
            problems.append(f'beat {i + 1} attributes a quotation to a real thinker without verified source evidence')
        w = sum(len(x.split()) for x in lines)
        words += w
        total += max(float(b.get('seconds') or 10), w / WPS + 1.5 * max(1, len(lines)) + 2)
        for line in lines:
            for pattern, why in BANNED:
                if re.search(pattern, line, re.I):
                    problems.append(f'beat {i + 1} narration {why}: "{line[:80]}"')
        if b.get('where') not in VOCAB['sets']:
            b['where'] = 'scene' if isinstance(b.get('scene'), dict) else 'void'
        if b.get('mode') not in MODES:
            b['mode'] = 'story'
    total += 8
    if minutes:
        if abs(total - lo) / lo > .25:
            problems.append(f'the film would run about {total / 60:.1f} minutes but {minutes:g} were asked; '
                            f'{"add" if total < lo else "remove"} beats or narration ({words} narration words now)')
    elif not lo * .85 <= total <= hi * 1.15:
        problems.append(f'the film would run about {total / 60:.1f} minutes with {words} narration words; aim for {lo // 60:.0f}-{hi / 60:.1f} minutes')
    want = ((lo + hi) / 2 if not minutes else lo) * .55 * WPS
    if words < want * .7:
        problems.append(f'only {words} narration words; the narrator should speak about {want:.0f} words, explaining the concept more fully')
    if beats:
        modes = {b['mode'] for b in beats}
        visual_notes = []
        if len(modes) < 3:
            visual_notes.append('Limited visual modes: review whether the acting and framing progress meaningfully')
        places = {place_key(b) for b in beats}
        if len(places) < 3:
            visual_notes.append('Few locations: preserve this if the story benefits, and inspect shot/acting variety')
        sheet['_visual_review_notes'] = visual_notes
        topic = ' '.join([str(sheet.get('_title', '')), str((sheet.get('idea') or {}).get('definition', ''))])
        producer_notes = str(sheet.get('_title', '')).partition('Direction from the producer:')[2]
        requested_screen_story = PHONEY.search(producer_notes) or re.search(r'\b(message|texting|reply|chat|email)\b', producer_notes, re.I)
        if not PHONEY.search(topic) and not requested_screen_story:
            phone_beats = sum(1 for b in beats if PHONEY.search(str(b.get('what_happens', ''))))
            if phone_beats > max(2, len(beats) // 5):
                visual_notes.append(f'{phone_beats} beats revolve around phones or screens, but this concept is not about them; find moments specific to the concept')
        stock = sum(1 for b in beats if STOCK.search(str(b.get('what_happens', ''))))
        if stock > 1:
            visual_notes.append('stock details (3am clocks, fridges, calendars, alarms) appear repeatedly; invent details specific to this concept')
        abstract = sum(1 for b in beats if (b.get('scene') or {}).get('base') == 'void' or b.get('where') == 'void')
        if abstract > max(2, len(beats) // 4):
            visual_notes.append(f'{abstract} beats happen in an empty void; show most ideas through people in real or built places')
        empty = sum(1 for b in beats if not [w for w in (b.get('who') or []) if w != 'demon'])
        if empty > len(beats) // 4:
            visual_notes.append(f'{empty} beats have no people on screen ("who"); the film is acted by people')
        demon_beats = sum(1 for b in beats if b.get('inner_voice_line'))
        if demon_beats > len(beats) // 2:
            visual_notes.append('the silhouette speaks in most beats; use it only where it explains something')
    return problems, total


def stage_concept(title, minutes, out_dir, research='', reuse_draft=None, review=True):
    if not review and not reuse_draft:
        raise ValueError('Skipping editorial inference requires an already edited draft checkpoint')
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    writer = Writer()
    system = concept_prompt(title, minutes) + 'Return only JSON.'
    user = f'TOPIC: {title}\n\nBACKGROUND READING (for accuracy, do not copy):\n{research[:3600] or "(none)"}\n\nWrite the JSON now.'
    report = {}

    def validate(data):
        data['_title'] = title
        problems, total = check_concept(data, minutes)
        report['estimated_seconds'] = total
        if problems:
            with (out / 'rejected-concepts.jsonl').open('a') as rejected:
                rejected.write(json.dumps({'problems': problems, 'response': data}, ensure_ascii=False) + '\n')
            length_only = all('minutes' in p for p in problems)
            target = target_seconds(minutes)[0] if minutes else sum(target_seconds(None)) / 2
            raise Rejected('; '.join(problems[:8]), data if length_only else None, abs(total - target))
        return data

    t0 = time.time()
    sheet = validate(json.loads(Path(reuse_draft).read_text())) if reuse_draft else plan_in_parts(writer, system, user, validate, minutes, out)
    for warning in sheet.get('_visual_review_notes', []):
        notice('Visual editorial review', warning, 'warning')
    notice('Editorial review', 'Checking argument, causal continuity and resolution before storyboarding')
    if review:
        reviewer = Writer(os.environ.get('REVIEW_MODELS', 'groq:qwen/qwen3.8-27b,groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,ollama:qwen3:4b'))
        patcher = Writer(os.environ.get('EDITOR_WRITER_MODELS','groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,ollama:qwen3:4b'))
        adjudicator = Writer(os.environ.get('EDITOR_CHECK_MODELS','groq:openai/gpt-oss-120b,groq:openai/gpt-oss-20b,ollama:qwen3:4b'))
        sheet = review_concept(sheet, patcher, check_concept, title, minutes, out, reviewer=reviewer, adjudicator=adjudicator)
    else:
        notice('Checkpoint replay', 'Reusing prior editorial work; running schema/content checks and exact-script compilation')
    sheet['_title'] = title
    sheet['_writer'] = writer.used or sheet.get('_writer')
    idmap = {}
    inner_id = next((p.get('id') for p in sheet.get('cast') or [] if p.get('kind') == 'demon'), None)
    for p in sheet.get('cast') or []:
        raw = str(p.get('id', '')); clean = re.sub(r'[^a-z0-9_]', '', raw.lower())[:12] or 'friend'
        if raw == inner_id:
            clean = 'demon'  # the renderer's inner-voice role, preserving all references below
        idmap[raw] = clean; p['id'] = clean
    clean = lambda v: idmap.get(str(v), re.sub(r'[^a-z0-9_]', '', str(v or '').lower())[:12])
    iv = sheet.get('inner_voice') if isinstance(sheet.get('inner_voice'), dict) else None
    if iv and not any(p.get('kind') == 'demon' for p in sheet.get('cast') or []):
        sheet.setdefault('cast', []).append({'id': 'demon', 'kind': 'demon'})
    for b in sheet.get('beats') or []:
        b['narration'] = beat_narration(b)
        b['who'] = [clean(w) for w in (b.get('who') or [])]
        if b.get('inner_voice_line'):
            b['demon_line'] = b['inner_voice_line']
        for d in b.get('dialogue') or []:
            d['who'] = clean(d.get('who'))
    (out / 'beats.json').write_text(json.dumps(sheet, indent=1, ensure_ascii=False))
    beats = sheet['beats']
    notice('Concept', f"{sheet.get('title')}: {sheet.get('approach', '')} | {(sheet.get('idea') or {}).get('definition', '')} | "
                      f"{len(beats)} beats, about {report.get('estimated_seconds', 0) / 60:.1f} min, by {writer.used} in {(time.time() - t0):.0f}s")
    for k in range(0, len(beats), 6):
        notice(f'Beats {k + 1}-{min(len(beats), k + 6)}', ' || '.join(
            f"{i + 1}. [{b.get('mode')}] {place_key(b)}: {str(b.get('what_happens', ''))[:100]}" for i, b in enumerate(beats[k:k + 6], k)))
    return sheet


# ---------------------------------------------------------------- stage 2: shots
def shot_rules():
    v = VOCAB
    return f"""SHOT JSON (one object per shot):
{{"dur": seconds 2-7,
 "set": one of {list(v['sets'])}, "scene": the built place when set is "scene" (copy the beat's scene; you may move elements or add a few),
 "time": one of {v['times']}, "weather": one of {v['weather']}, "grade": one of {list(v['grades'])}, "camera": {{"frame": one of {list(v['frames'])}, "on": actor id, "push": 0.03-0.12}},
 "actors": [{{"id": cast id, "x": 0-100, "to": 0-100 (walk/run target), "pose": one of {list(v['poses'])},
             "mood": one of {v['moods']}, "hold": one of {v['holds']}, "facing": -1|0|1, "seated": true,
             "target": id (lean/grab/hug/reachout), "at": seconds delay, "depth": "back", "scale": 0.4-1.2}}],
 "narration_index": 0-based source sentence number (omit for unnarrated shots),
 "lines": [{{"who": actor id, "text": str, "twist": str (narrator only, optional), "at": seconds, "style": "bubble"|"float"|"thought"|"whisper"}}],
 "hud": {{"values": [numbers or [from, to]], "chapter": "DAY 4", "alert": true}}, "big": {{"text": "DAY 1.", "at": 0.3}},
 "phone": {{"app": one of {list(v['phone_apps'])}, "contact": name, "time": "18:02", "messages": [{{"from": "them"|"me", "text": str, "at": s}}],
           "typing": {{"text": str, "at": s, "action": "delete"|"send"}}, "notifications": [{{"app": str, "text": str, "at": s}}],
           "call": {{"decline_at": s}}, "off_at": s}},
 "insert": {json.dumps(v['inserts'])},
 "items": [{{"type": one of {v['items']}, "x": 0-100, "on": "nightstand"|"desk"|"table"|"bed"}}],
 "door": [0, 1], "door_at": s, "music": one of {v['music_levels']}, "transition": one of {v['transitions']}}}
SCENE PARTS: {scene_vocab()}
SPOTS per named set: {json.dumps({k: s['spots'] for k, s in v['sets'].items() if s.get('spots')})}
SEATS: {json.dumps({k: s.get('seat') for k, s in v['sets'].items() if s.get('seat')})}
RULES:
- Return only fields used by this shot; omit unused optional props, phone screens, inserts and empty dictionaries.
- NARRATION: reference each source sentence by narration_index (0, 1, ...), in order, once.
  Never echo its text or return narrator lines; the compiler inserts the exact script.
  While the narrator speaks, give that shot an action matching the referenced sentence.
- SCENES: omit scene/time/weather/grade when unchanged; the compiler inherits them from the beat.
  Return a scene object only when its elements change. Do not copy the same environment into every shot.
- Unnarrated shots are short (2-4 s) and full of acting: dialogue bubbles, reactions, objects, movement.
- Stage the beat's MODE: a montage is many short shots of different people/places; a metaphor uses built places and big words;
  a lesson shows the idea directly; inner uses a void or dark room; contrast cuts between two situations.
- Vary framing like an editor: never more than two "wide" in a row; "close" for reactions (detailed faces), "extreme" for a decision,
  "two" for two characters together, "medium" for actions, "phone"/"insert" for objects (no actors on those).
- Characters move: use walk/run with "x" and "to"; use the set's seats for sit/type/lie; change poses from shot to shot.
- Put the beat's characters ("who") on screen. If the silhouette (id "demon") speaks, it stands within 10-14 of the person it targets,
  pose lean or grab with "target".
- Two people at a table or bench face each other: facing 1 on the left, -1 on the right.
- Every actor gets a mood. Every shot of a beat uses the beat's set, time, weather and grade unless the beat moves.
"""


def shots_for(beats, first, sheet, writer, example):
    cast = ', '.join(f"{p.get('id')} ({p.get('kind')})" for p in sheet.get('cast', []) if p.get('id'))
    system = STYLE + '\n' + shot_rules() + f"""
You are the storyboard artist. Turn EACH beat below into 2-6 shots (more for longer beats; one narration sentence per shot).
Reply with JSON only: {{"beats": [{{"beat": beat number, "shots": [...]}}]}}.
Film approach: {sheet.get('approach', '')}. Cast: {cast}. Silhouette: {json.dumps(sheet.get('inner_voice'))}.
Story device: {json.dumps(sheet.get('device') or {})} - only if it is a counter, put values in hud.values.
Cumulative counters track totals across the whole film; never reset at a new shot. Omit hud.values when unchanged. For a deliberate story reset use hud.reset=true. Values such as mood or a streak may fall and use mode=value.
JSON shape example (content is illustrative only): {example}"""
    payload = [{'beat': first + i + 1, **{k: v for k, v in b.items() if k not in ('seconds', 'idea')}, 'seconds': b.get('seconds')} for i, b in enumerate(beats)]
    user = f"Film: {sheet.get('title')} - {(sheet.get('idea') or {}).get('definition', '')}\nBeats:\n{json.dumps(payload, ensure_ascii=False)}"

    def validate(data):
        groups = data.get('beats') if isinstance(data, dict) else None
        if not isinstance(groups, list) or not groups:
            raise ValueError('return {"beats": [{"beat": n, "shots": [...]}]}')
        got = {}
        for g in groups:
            if isinstance(g, dict) and isinstance(g.get('shots'), list) and g['shots']:
                try:
                    index = int(g.get('beat')) - first - 1
                except (TypeError, ValueError):
                    continue
                if index not in range(len(beats)) or index in got:
                    raise ValueError('Return each requested beat exactly once, without extra beat numbers')
                indices = [s.get('narration_index') for s in g['shots'] if isinstance(s,dict) and s.get('narration_index') is not None]
                if indices:
                    count = len(beat_narration(beats[index]))
                    if any(type(n) is not int or not 0 <= n < count for n in indices) or indices != sorted(indices) or set(indices) != set(range(count)):
                        raise ValueError(f'Use narration_index 0..{count-1} in source order, with every sentence represented')
                got[index] = g['shots']
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
                base['actors'] = [{'id': lead(beat), 'x': 50, 'pose': 'stand', 'mood': beat.get('emotion', 'neutral')}]
        on = (base.get('actors') or [{}])[0].get('id', lead(beat))
        base['camera'] = {'frame': nxt, 'on': on, 'push': .05}
        # Continue from the preceding physical endpoint when extending narration.
        # Replaying x->to would teleport the actor backward at every new angle.
        for actor in base.get('actors') or []:
            if actor.get('pose') in ('walk','run') and 'to' in actor:
                actor['x']=actor.pop('to');actor['pose']='stand'
        base['lines'] = []
        shots.insert(shots.index(visual[-1]) + 1, base)
        visual.append(base)
    # spread sentences evenly over the visual shots
    step = len(visual) / len(sentences)
    for k, sentence in enumerate(sentences):
        explicit = [s for s in visual if s.get('narration_index') == k]
        shot = explicit[0] if explicit else visual[min(len(visual) - 1, int(k * step))]
        shot['lines'].insert(0, {'who': 'narrator', 'text': sentence, 'at': .25})
        shot['dur'] = max(float(shot.get('dur') or 3), .25 + len(sentence.split()) / WPS + .8)
    # Distribute the beat budget after adding narration angles. A cloned angle must
    # not inherit the entire prior shot duration and multiply a six-minute plan.
    minimum=[]
    for shot in visual:
        words=sum(len(line['text'].split()) for line in shot.get('lines',[]) if line.get('who')=='narrator')
        minimum.append(max(2.8,.25+words/WPS+.8))
    target=max(float(beat.get('seconds') or 0),sum(minimum))
    extra=max(0,target-sum(minimum))/len(visual)
    for shot,need in zip(visual,minimum):shot['dur']=round(need+extra,3)
    return shots


def ensure_demon(beat, shots):
    """If the beat's silhouette line was not staged, add a shot of it beside the person it speaks to."""
    line = str(beat.get('demon_line') or '').strip()
    if not line or any(l.get('who') == 'demon' for s in shots for l in (s.get('lines') or [])):
        return shots
    who = lead(beat)
    anchor = next((s for s in reversed(shots) if s.get('actors')), None)
    person = next((a for a in (anchor or {}).get('actors', []) if a.get('id') == who), None)
    pose = person.get('pose') if person and person.get('pose') in ('sit', 'slump', 'lie', 'phone', 'type', 'stand', 'hugknees', 'headhands') else 'stand'
    x = float(person.get('x', 50)) if person else 50
    base = {k: anchor[k] for k in ('set', 'scene', 'time', 'weather', 'grade') if anchor and k in anchor}
    shots.append({**base, 'dur': 3.2, 'camera': {'frame': 'two', 'on': who, 'push': .06},
                  'actors': [{'id': 'demon', 'x': x - 12 if x > 30 else x + 12, 'pose': 'lean', 'target': who},
                             {'id': who, 'x': x, 'pose': pose, 'mood': beat.get('emotion', 'sad'),
                              **({'seated': True} if person and person.get('seated') else {})}],
                  'lines': [{'who': 'demon', 'text': line, 'at': .7}], 'music': 'low'})
    return shots


def example_shots():
    """Syntax only: two shots in a built place, with neutral placeholder content."""
    return json.dumps([
        {'dur': 4.2, 'set': 'scene', 'time': 'dusk', 'grade': 'sunset',
         'scene': {'base': 'outside', 'backdrop': 'hills', 'ground': 'grass', 'elements': [{'type': 'bench', 'x': 40}, {'type': 'tree', 'x': 75}]},
         'camera': {'frame': 'wide', 'push': .04},
         'actors': [{'id': 'ana', 'x': 20, 'to': 38, 'pose': 'walk', 'mood': 'tired'}, {'id': 'leo', 'x': 46, 'pose': 'sit', 'mood': 'content'}],
         'narration_index': 0, 'lines': []},
        {'dur': 2.6, 'set': 'scene', 'time': 'dusk', 'grade': 'sunset',
         'scene': {'base': 'outside', 'backdrop': 'hills', 'ground': 'grass', 'elements': [{'type': 'bench', 'x': 40}, {'type': 'tree', 'x': 75}]},
         'camera': {'frame': 'two', 'on': 'ana'},
         'actors': [{'id': 'ana', 'x': 38, 'pose': 'sit', 'mood': 'shy', 'facing': 1}, {'id': 'leo', 'x': 46, 'pose': 'sit', 'mood': 'happy', 'facing': -1}],
         'lines': [{'who': 'leo', 'text': '<short line>', 'at': .5}]}], ensure_ascii=False)


def stage_shots(out_dir, group=2):
    out = Path(out_dir)
    sheet = json.loads((out / 'beats.json').read_text())
    beats = sheet['beats']
    if not os.environ.get('STORYBOARD_MODELS'):
        result={i:ensure_demon(b,place_narration(b,fallback_shots(b))) for i,b in enumerate(beats)}
        (out / 'shots.json').write_text(json.dumps(result,ensure_ascii=False))
        notice('Storyboard',f'{sum(map(len,result.values()))} shots compiled from the writer physical directions')
        return
    writer = Writer(os.environ.get('STORYBOARD_MODELS') or ','.join(dict.fromkeys(filter(None,[sheet.get('_writer'),*DEFAULT_MODELS.split(',')]))))
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


def lead(beat):
    who = [w for w in (beat.get('who') or []) if w and w != 'demon']
    return who[0] if who else 'hero'


def fallback_shots(beat):
    """Deterministically perform the writer's directions with supported rig motions."""
    from story.director import direct_beat
    return direct_beat(beat,VOCAB)


# ---------------------------------------------------------------- stage 3: merge
def stage_merge(out_dir, out_path):
    out = Path(out_dir)
    sheet = json.loads((out / 'beats.json').read_text())
    per = {int(k): v for k, v in json.loads((out / 'shots.json').read_text()).items()}
    shots = []
    for i, beat in enumerate(sheet['beats']):
        staged = ensure_demon(beat, place_narration(beat, per.get(i) or fallback_shots(beat)))
        for s in staged:
            if not s.get('card') and (s.get('camera') or {}).get('frame') != 'insert':
                s.setdefault('set', beat.get('where'))
                if s.get('set') == 'scene' and not isinstance(s.get('scene'), dict):
                    s['scene'] = beat.get('scene') or {'base': 'void'}
            for key in ('time', 'grade'):
                if beat.get(key):
                    s.setdefault(key, beat[key])
            if beat.get('weather') and beat['weather'] != 'none':
                s.setdefault('weather', beat['weather'])
            if beat.get('relapse') and isinstance(s.get('hud'), dict):
                s['hud'].setdefault('alert', True)
            s['beat'] = i + 1
            shots.append(s)
    cast = {}
    for p in sheet.get('cast') or []:
        pid = p.get('id')
        if not pid:
            continue
        entry = {k: v for k, v in p.items() if k != 'id' and v not in (None, '', 'none', False)}
        if pid == 'demon' or entry.get('kind') == 'demon':
            entry = {'kind': 'demon'}
        cast[pid] = {**cast.get(pid, {}), **entry}
    if not any(c.get('kind') == 'hero' for c in cast.values()):
        first = next((k for k, c in cast.items() if c.get('kind') != 'demon'), 'hero')
        cast.setdefault(first, {}).update(kind='hero')
    dev = sheet.get('device') or {}
    hud = {'items': dev.get('items')[:2]} if dev.get('type') == 'counter' and dev.get('items') else None
    head, tail = [], []
    opening = str(sheet.get('cold_open') or sheet.get('opening_line') or '').strip()
    if opening:
        head.append({'dur': 3.4 + len(opening.split()) / WPS, 'music': 'low', 'card': {'style': 'line', 'lines': [opening]},
                     'lines': [{'who': 'narrator', 'text': opening, 'at': .3, 'hidden': True}]})
    ending = str(sheet.get('ending') or '').strip()
    if ending:
        tail.append({'dur': 3.6 + len(ending.split()) / WPS, 'music': 'high', 'card': {'style': 'line', 'lines': [ending]},
                     'lines': [{'who': 'narrator', 'text': ending, 'at': .4, 'hidden': True}]})
    hero = next((k for k, c in cast.items() if c.get('kind') == 'hero'), 'hero')
    tail.append({'dur': 4.0, 'music': 'mid', 'card': {'style': 'cta', 'lines': ['If this made you think, like and subscribe.']},
                 'actors': [{'id': hero, 'x': 50, 'pose': 'wave', 'mood': 'happy', 'scale': .7}]})
    iv = sheet.get('inner_voice') if isinstance(sheet.get('inner_voice'), dict) else {}
    film = {'title': sheet.get('title') or sheet.get('_title'), 'logline': sheet.get('approach', ''),
            'demon_color': iv.get('color') or sheet.get('demon_color'), 'narrator': 'male', 'hud': hud,
            'music': {'prompt': sheet.get('music_prompt') or ''}, 'cast': cast, 'shots': head + shots + tail,
            'publish': {k: sheet.get(k) for k in ('youtube_titles', 'description', 'tags', 'pinned_comment', 'thumbnail_words', 'idea', 'inner_voice', 'approach')},
            'writer': sheet.get('_writer')}
    if (out / 'sources.json').exists():
        film['sources'] = json.loads((out / 'sources.json').read_text())
    from story.director import enrich_film
    film = enrich_film(film,sheet)
    film['editorial_origin']=sheet.get('_editorial_origin')
    review_file=out/'editorial-review.json'
    if review_file.exists():
        history=json.loads(review_file.read_text());last=history[-1]
        film['script_review']={'reviewer':last.get('reviewer'),'issues':last['review']['issues'],'major_findings_resolved':not any(issue.get('severity')=='major' for issue in last['review']['issues'])}
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
    ap.add_argument('--reuse-draft', default='')
    a = ap.parse_args()
    if a.stage == 'concept':
        research = Path(a.research).read_text() if a.research and Path(a.research).exists() else ''
        stage_concept(a.title, minutes_value(a.minutes), a.dir, research, a.reuse_draft or None)
    elif a.stage == 'shots':
        stage_shots(a.dir)
    else:
        stage_merge(a.dir, a.out)
