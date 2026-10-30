"""Write a noir essay script (beats) for a title with the free Groq writer."""
import re
from pipeline.animation import setpieces
from pipeline.writing.beats import Script, estimate
from pipeline.writing.llm import Writer, Rejected

SYSTEM = """You are the writer-director of a respected YouTube channel of philosophy and psychology video essays.
The videos are minimalist stickman animation: black, white and grey, faceless figures, a spotlight, empty space,
and one warm amber colour reserved for moments of meaning or hope. Pictures carry the ideas through visual metaphor.
Narration is calm, intelligent and human. Some beats have no narration at all, only music and image.
You return only JSON."""

RULES = """Write the complete script as JSON with this shape:
{"title": str, "thesis": str,
 "beats": [{"mode": "narrated"|"silent", "narration": str, "on_screen": str, "setpiece": str, "labels": [str],
            "tone": "dark"|"light", "amber": bool, "delivery": "calm"|"normal"|"dramatic", "seconds": number}],
 "youtube_titles": [3 strings], "description": str, "tags": [10-15 strings], "pinned_comment": str, "thumbnail_words": str}

STRUCTURE
- Beat 1 is a SILENT cold open that poses the idea visually (6-14 seconds). Beat 2 is usually a silent title_card whose label is the topic word and whose on_screen line is a short subtitle.
- Then alternate: mostly narrated beats, with a silent beat every 2-4 beats to let an image breathe. About 55-70% of the running time is narration.
- Build an argument: hook, what the idea is, where it comes from (real thinkers and ideas, explained accurately), what it feels like in a life, the strongest objection or turn, and a resolution that leaves the viewer thinking. End on a silent beat.
- Narrated beats: 40-110 words each, spoken English, short sentences, concrete images, no lists, no "in this video", no "smash that like button".
- Silent beats: "narration" is empty, "seconds" 6-14, "on_screen" is empty or one short line (max 6 words) such as a question.

VISUALS
- Every beat picks one setpiece from the catalogue whose metaphor matches what is being said. Use at least 8 different setpieces; never the same setpiece more than 3 times, and never twice in a row except a silent beat continuing a narrated one.
- labels are the short words the setpiece displays (see each setpiece). Use UPPERCASE single words where the setpiece shows words.
- tone: "dark" for doubt, loss, fear and introspection; "light" for everyday life, clarity and calm. Vary it.
- amber: true only where meaning, hope, choice or warmth appears (usually the last third). Most beats are false.
- delivery: "calm" by default; "dramatic" for a turning point; "normal" for explanation.

HONESTY
- Explain real philosophers and psychologists accurately, in your own words. NO invented quotations, NO direct quotes in quotation marks, NO statistics or percentages, NO "studies show" or "research proves", NO diagnosing the viewer.

PUBLISHING
- youtube_titles: 3 curiosity-driven but honest titles (max 70 characters). description: 2 short paragraphs plus a line of 3-5 hashtags. pinned_comment: one question that invites replies. thumbnail_words: 2-4 bold words.
"""


def length_brief(minutes):
    if minutes:
        total = minutes * 60
        words = round(total * .62 * 2.35)
        return (f'TARGET LENGTH: about {minutes:g} minutes ({total:.0f} seconds) in total. That means roughly {words} narration words '
                f'in total plus silent beats. Silent beats count toward the length.')
    return ('TARGET LENGTH: Auto. Choose the length this topic deserves, between 5 and 8 minutes in total (roughly 450-700 narration '
            'words plus silent beats, typically 12-18 beats). Do not pad, but do not be brief: develop each idea.')


BANNED = [
    (r'\b\d+(?:\.\d+)?\s*(?:%|percent|per cent)', 'contains a percentage or statistic'),
    (r'\b(?:studies|research|scientists|psychologists|experts)\s+(?:show|shows|prove|proves|proved|found|suggest|demonstrate)', 'claims research findings'),
    (r'["“][^"”]{12,}["”]', 'contains a direct quotation in quotation marks'),
    (r'\byou\s+(?:have|suffer from|are suffering from)\s+(?:depression|anxiety|adhd|a disorder)', 'diagnoses the viewer'),
    (r'\b(?:in this video|like and subscribe|smash)', 'contains YouTube filler'),
]


def repair(script, title):
    """Fix structural slips automatically instead of sending the script back."""
    beats = list(script.beats)
    topic = re.sub(r'[^A-Za-z ]', ' ', title.split('-')[0].split(':')[0]).strip().split()
    word = (max(topic, key=len) if topic else 'MEANING').upper()[:24]
    if beats[0].mode != 'silent':
        beats.insert(0, beats[0].model_copy(update={'mode': 'silent', 'narration': '', 'setpiece': 'title_card', 'labels': [word],
                                                    'seconds': 7, 'on_screen': '', 'amber': False}))
    if beats[-1].mode != 'silent':
        first = beats[0]
        beats.append(first.model_copy(update={'seconds': 7, 'on_screen': first.on_screen or '', 'amber': any(b.amber for b in beats[-4:])}))
    return script.model_copy(update={'beats': beats})


def check(script, minutes):
    """Hard problems only (the writer is asked to fix these); returns (problems, notes, seconds)."""
    problems, notes = [], []
    beats = script.beats
    total = sum(estimate(b) for b in beats)
    narrated = sum(estimate(b) for b in beats if b.mode == 'narrated')
    if minutes:
        if abs(total - minutes * 60) / (minutes * 60) > .25:
            words = sum(len(b.narration.split()) for b in beats if b.mode == 'narrated')
            need = round((minutes * 60 - (total - narrated)) * 2.35)
            problems.append(f'the script would run about {total / 60:.1f} minutes but {minutes:g} minutes were requested; '
                            f'it has {words} narration words, aim for about {need}')
    elif not 3.5 * 60 <= total <= 10 * 60:
        words = sum(len(b.narration.split()) for b in beats if b.mode == 'narrated')
        problems.append(f'the script would run about {total / 60:.1f} minutes with {words} narration words; '
                        f'Auto length needs 5-8 minutes, about 500-700 narration words')
    for i, b in enumerate(beats):
        if b.mode == 'narrated':
            n = len(b.narration.split())
            if n > 170:
                problems.append(f'beat {i + 1} narration has {n} words; split it into two beats (max 170)')
            for pattern, why in BANNED:
                if re.search(pattern, b.narration, re.I):
                    problems.append(f'beat {i + 1} {why}')
    counts = {}
    for b in beats:
        counts[b.setpiece] = counts.get(b.setpiece, 0) + 1
    if total and not .45 <= narrated / total <= .85:
        notes.append(f'narration is {narrated / total:.0%} of the running time')
    if len(counts) < 6:
        notes.append(f'only {len(counts)} different setpieces')
    over = [k for k, v in counts.items() if v > 4]
    if over:
        notes.append('setpieces used often: ' + ', '.join(over))
    sentences = [s.strip().lower() for b in beats for s in re.split(r'[.!?]', b.narration) if len(s.split()) > 6]
    if len(sentences) != len(set(sentences)):
        problems.append('repeats a narration sentence word for word')
    return problems, notes, total


def write(title, minutes=None, research=None, writer=None):
    writer = writer or Writer()
    context = (research or {}).get('context', '')[:6000]
    user = (f'TOPIC / TITLE: {title}\n\n{length_brief(minutes)}\n\n{RULES}\n'
            f'SETPIECE CATALOGUE (setpiece: what it shows. Labels: what to put in labels)\n{setpieces.catalog()}\n\n'
            f'BACKGROUND READING (for accuracy; do not copy sentences):\n{context or "(none available; rely on well-established knowledge)"}\n\n'
            'Return the JSON now.')
    report = {}

    def validate(data):
        script = repair(Script.model_validate(data), title)
        problems, notes, total = check(script, minutes)
        if problems:
            soft = all('minutes' in p for p in problems)      # only the length is off
            target = minutes * 60 if minutes else 6.5 * 60
            raise Rejected('; '.join(problems[:10]), script if soft else None, abs(total - target))
        for n in notes:
            print(f'::notice title=Script note::{n}', flush=True)
        report['estimated_seconds'] = total
        report['notes'] = notes
        return script

    script = writer.json(SYSTEM, user, validate)
    report['model'] = writer.used
    return script, report
