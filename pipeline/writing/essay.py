"""Write a noir essay script (beats) for a title with the free Groq writer."""
import re
from pipeline.animation import setpieces
from pipeline.writing.beats import Script, estimate
from pipeline.writing.llm import Writer

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
- Narrated beats: 25-90 words each, spoken English, short sentences, concrete images, no lists, no "in this video", no "smash that like button".
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
            'words plus silent beats). Do not pad.')


BANNED = [
    (r'\b\d+(?:\.\d+)?\s*(?:%|percent|per cent)', 'contains a percentage or statistic'),
    (r'\b(?:studies|research|scientists|psychologists|experts)\s+(?:show|shows|prove|proves|proved|found|suggest|demonstrate)', 'claims research findings'),
    (r'["“][^"”]{12,}["”]', 'contains a direct quotation in quotation marks'),
    (r'\byou\s+(?:have|suffer from|are suffering from)\s+(?:depression|anxiety|adhd|a disorder)', 'diagnoses the viewer'),
    (r'\b(?:in this video|like and subscribe|smash)', 'contains YouTube filler'),
]


def check(script, minutes):
    problems = []
    beats = script.beats
    total = sum(estimate(b) for b in beats)
    narrated = sum(estimate(b) for b in beats if b.mode == 'narrated')
    if minutes:
        if abs(total - minutes * 60) / (minutes * 60) > .2:
            problems.append(f'the script would run about {total / 60:.1f} minutes but the target is {minutes:g} minutes; '
                            f'{"add" if total < minutes * 60 else "remove"} narrated beats or narration words')
    elif not 4.5 * 60 <= total <= 9 * 60:
        problems.append(f'the script would run about {total / 60:.1f} minutes; Auto length must be between 5 and 8 minutes')
    if beats[0].mode != 'silent':
        problems.append('beat 1 must be a silent cold open')
    if beats[-1].mode != 'silent':
        problems.append('the final beat must be silent')
    if total and not .45 <= narrated / total <= .82:
        problems.append(f'narration is {narrated / total:.0%} of the running time; it should be 55-70%')
    if sum(1 for b in beats if b.mode == 'silent') < 3:
        problems.append('use at least 3 silent beats')
    counts = {}
    for i, b in enumerate(beats):
        counts[b.setpiece] = counts.get(b.setpiece, 0) + 1
        if b.mode == 'narrated':
            n = len(b.narration.split())
            if not 15 <= n <= 110:
                problems.append(f'beat {i + 1} narration has {n} words (15-110 allowed)')
            for pattern, why in BANNED:
                if re.search(pattern, b.narration, re.I):
                    problems.append(f'beat {i + 1} {why}')
        if i and b.setpiece == beats[i - 1].setpiece and not (b.mode == 'silent' and beats[i - 1].mode == 'narrated'):
            problems.append(f'beats {i} and {i + 1} repeat the setpiece {b.setpiece}')
    over = [k for k, v in counts.items() if v > 3]
    if over:
        problems.append('setpieces used more than 3 times: ' + ', '.join(over))
    if len(counts) < min(8, len(beats) - 2):
        problems.append(f'only {len(counts)} different setpieces; use at least {min(8, len(beats) - 2)}')
    sentences = [s.strip().lower() for b in beats for s in re.split(r'[.!?]', b.narration) if len(s.split()) > 6]
    if len(sentences) != len(set(sentences)):
        problems.append('repeats a narration sentence')
    return problems, total


def write(title, minutes=None, research=None, writer=None):
    writer = writer or Writer()
    context = (research or {}).get('context', '')[:6000]
    user = (f'TOPIC / TITLE: {title}\n\n{length_brief(minutes)}\n\n{RULES}\n'
            f'SETPIECE CATALOGUE (setpiece: what it shows. Labels: what to put in labels)\n{setpieces.catalog()}\n\n'
            f'BACKGROUND READING (for accuracy; do not copy sentences):\n{context or "(none available; rely on well-established knowledge)"}\n\n'
            'Return the JSON now.')
    report = {}

    def validate(data):
        script = Script.model_validate(data)
        problems, total = check(script, minutes)
        if problems:
            raise ValueError('; '.join(problems[:10]))
        report['estimated_seconds'] = total
        return script

    script = writer.json(SYSTEM, user, validate)
    report['model'] = writer.used
    return script, report
