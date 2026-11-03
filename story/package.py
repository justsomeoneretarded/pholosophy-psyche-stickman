"""Publishing files for a finished film: thumbnails, subtitles, titles, description, tags, credits.

python story/package.py build/film.json build/poster out/
`build/poster` holds full-resolution stills rendered at the times printed by `python story/package.py --poster-times build/film.json`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / 'assets' / 'fonts'
THUMB = (1280, 720)


def font(name, size):
    from PIL import ImageFont
    return ImageFont.truetype(str(FONTS / name), int(size))


def shot_times(film):
    t, out = 0., []
    for s in film['shots']:
        out.append((t, s))
        t += s['dur']
    return out


def poster_times(film):
    """Moments that make good thumbnails: emotional close-ups, the inner voice beside the hero, wide sets with people."""
    scored = []
    for t, s in shot_times(film):
        if s.get('card'):
            continue
        frame = (s.get('camera') or {}).get('frame', 'wide')
        ids = [a['id'] for a in s.get('actors', [])]
        moods = {a.get('mood') for a in s.get('actors', [])}
        score = {'close': 4, 'two': 4, 'medium': 3, 'extreme': 2, 'wide': 2}.get(frame, 0)
        score += 3 if 'demon' in ids and 'hero' in ids else 0
        score += 2 if moods & {'crying', 'hurt', 'shocked', 'scared', 'sad', 'determined', 'love', 'hopeful'} else 0
        score += 1 if s.get('grade') in ('pink', 'red', 'sunset', 'warm', 'green') else 0
        scored.append((score, t + s['dur'] * .6))
    scored.sort(key=lambda x: -x[0])
    picks, used = [], []
    for score, t in scored:
        if all(abs(t - u) > 12 for u in used):
            picks.append(round(t, 2)); used.append(t)
        if len(picks) == 3:
            break
    return picks or [5.0]


def headline(img, words, box, size, amber=None, align='left'):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    words = words.upper().split()
    lines = [' '.join(words[i:i + 2]) for i in range(0, len(words), 2)] if len(words) > 2 else [' '.join(words)]
    x0, y0, x1, y1 = box
    while size > 24:
        f = font('Anton-Regular.ttf', size)
        w = max(d.textbbox((0, 0), l, font=f)[2] for l in lines)
        if w <= x1 - x0 and len(lines) * size * 1.12 <= y1 - y0:
            break
        size -= 4
    f = font('Anton-Regular.ttf', size)
    y = y0 + (y1 - y0 - len(lines) * size * 1.12) / 2
    for line in lines:
        lw = d.textbbox((0, 0), line, font=f)[2]
        x = x0 if align == 'left' else x0 + (x1 - x0 - lw) / 2
        for word in line.split():
            colour = amber if amber and word.strip('.,!?') == words[-1].strip('.,!?') else (248, 245, 238)
            d.text((x, y), word, font=f, fill=colour, stroke_width=max(3, size // 18), stroke_fill=(8, 8, 10))
            x += d.textbbox((0, 0), word + ' ', font=f)[2]
        y += size * 1.12


def publishing_text(value, fallback=''):
    """Accept a text string or an explicit list of words; never stringify metadata."""
    if value is None or value == '':return fallback
    if isinstance(value,str):return value.strip()
    if isinstance(value,list) and all(isinstance(x,str) for x in value):return ' '.join(value).strip() or fallback
    raise ValueError('Publishing text must be a string or list of strings')

def thumbnails(film, poster_dir, out):
    from PIL import Image
    stills = sorted(Path(poster_dir).glob('*.jpg'))
    if not stills:
        return []
    words = publishing_text((film.get('publish') or {}).get('thumbnail_words'),film['title'])
    key = words.upper().split()[-1].strip('.,!?') if words else None
    accent = film.get('demon_color') or '#ff4fa0'
    accent = tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
    paths = []
    for n, still in enumerate(stills[:3]):
        src = Image.open(still).convert('RGB').resize(THUMB, Image.LANCZOS)
        src = Image.eval(src, lambda v: min(255, int(v * 1.12)))          # thumbnails read darker on phones
        shade = Image.new('RGB', THUMB, (0, 0, 0))
        if n in (0, 2):
            # Subject moved to one side, headline in the darkened other side.
            shift = 300 if n == 0 else -300
            im = Image.new('RGB', THUMB, (6, 6, 8)); im.paste(src, (shift, 0))
            # dark behind the headline, fading to clear over the subject
            col = [int(235 * min(1, max(0, (760 - x) / 260))) for x in range(THUMB[0])]
            if n == 2:
                col = col[::-1]
            row = Image.new('L', (THUMB[0], 1)); row.putdata(col)
            im = Image.composite(shade, im, row.resize(THUMB))
            box = (44, 60, 600, 660) if n == 0 else (680, 60, 1236, 660)
            headline(im, words if n == 0 else film['title'], box, 170, accent)
        else:
            mask = Image.linear_gradient('L').resize(THUMB).point(lambda v: int(max(0, v * 2.2 - 300) * .9))
            im = Image.composite(shade, src, mask)
            headline(im, words, (60, 500, 1220, 700), 150, accent, align='center')
        p = Path(out) / f'thumbnail-{n + 1:02d}.jpg'
        im.save(p, quality=92)
        paths.append(p)
    return paths


def stamp(t, sep=','):
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'


def subtitles(film, out):
    cues = []
    for t, s in shot_times(film):
        for ln in s.get('lines') or []:
            if ln.get('who') not in ('narrator', 'caption'):
                continue  # Unvoiced dialogue bubbles are on-screen acting, not narrated speech.
            start = t + (ln.get('at') or 0)
            timed = ln.get('word_times') or []
            if timed:
                for i in range(0, len(timed), 7):
                    phrase = timed[i:i+7]
                    a = start + phrase[0]['start']
                    b = min(start + phrase[-1]['end'], t+s['dur'])
                    if b > a:
                        cues.append((a,b,' '.join(w['word'] for w in phrase)))
            else:
                text = ln['text'] + (' ' + ln['twist'] if ln.get('twist') else '')
                end = min(start + (ln.get('voice_dur') or ln.get('dur') or max(1.5,len(text.split())/2.6)),t+s['dur'])
                if end > start:
                    cues.append((start,end,text))
    cues.sort()
    srt = [f'{i+1}\n{stamp(a)} --> {stamp(b)}\n{txt}\n' for i,(a,b,txt) in enumerate(cues)]
    vtt = [f'{stamp(a, ".")} --> {stamp(b, ".")}\n{txt}\n' for a,b,txt in cues]
    (Path(out)/'subtitles.srt').write_text('\n'.join(srt))
    (Path(out)/'subtitles.vtt').write_text('WEBVTT\n\n'+'\n'.join(vtt))


def chapters(film):
    out, last = [], None
    for t, s in shot_times(film):
        b = s.get('beat')
        if b and b != last and (not out or t - out[-1][0] >= 25):
            out.append((t, s))
        last = b or last
    return out


def publishing(film, out):
    out = Path(out)
    pub = film.get('publish') or {}
    titles = [t for t in (pub.get('youtube_titles') or []) if t] or [film['title']]
    (out / 'recommended-title.txt').write_text(titles[0] + '\n')
    (out / 'title-options.txt').write_text('\n'.join(titles) + '\n')
    (out / 'tags.txt').write_text(', '.join(pub.get('tags') or []) + '\n')
    (out / 'pinned-comment.txt').write_text(str(pub.get('pinned_comment') or '') + '\n')
    music = film.get('music_credit') or 'Original score generated with ACE-Step 1.5 (MIT)'
    desc = str(pub.get('description') or film.get('logline') or '').strip()
    sources = film.get('sources') or []
    reading = '\n'.join(str(s.get('title','Source')) + ': ' + str(s['url']) for s in sources if isinstance(s,dict) and str(s.get('url','')).startswith('https://'))
    if reading:
        desc += '\n\nBackground reading:\n' + reading
    (out / 'sources.json').write_text(json.dumps(sources,indent=2))
    (out / 'description.txt').write_text(f'{desc}\n\nMusic: {music}\n')
    idea = pub.get('idea') or {}
    (out / 'sources-and-credits.txt').write_text('\n'.join([
        f"CONCEPT: {idea.get('definition', '')}", f"THINKERS AND IDEAS MENTIONED: {idea.get('thinkers', '')}", '',
        f"SCRIPT: written with {film.get('writer') or 'Groq'} (free tier)",
        f"NARRATION: Chatterbox Turbo (MIT, Resemble AI), narrator: {film.get('narrator_voice', 'warguy')}",
        f'MUSIC: {music}', 'FONTS: Patrick Hand, Nunito, Share Tech Mono, Anton (SIL Open Font License)']) + '\n')


def main():
    if sys.argv[1] == '--poster-times':
        print(','.join(str(t) for t in poster_times(json.loads(Path(sys.argv[2]).read_text()))))
        return
    film = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    thumbnails(film, sys.argv[2], out)
    subtitles(film, out)
    publishing(film, out)
    (out/'script.txt').write_text('\n\n'.join(l['text']+(' '+l['twist'] if l.get('twist') else '') for s in film['shots'] for l in s.get('lines',[]) if l.get('who')=='narrator'))
    (out/'storyboard.json').write_text(json.dumps(film,indent=1,ensure_ascii=False))
    (out/'scene_timeline.json').write_text(json.dumps([{'start':t,'end':t+s['dur'],'shot':i,'beat':s.get('beat')} for i,(t,s) in enumerate(shot_times(film))],indent=2))
    for source,target in [('recommended-title.txt','youtube_title.txt'),('description.txt','youtube_description.txt'),('tags.txt','keywords.txt'),('pinned-comment.txt','pinned_comment.txt')]:
        (out/target).write_text((out/source).read_text())
    (out/'hashtags.txt').write_text(' '.join(re.findall(r'#[A-Za-z0-9_]+',(out/'description.txt').read_text())))
    thumbs=sorted(out.glob('thumbnail-*.jpg'))
    if thumbs:
        from PIL import Image
        Image.open(thumbs[0]).save(out/'thumbnail.png')
    print(f'package: {len(list(out.iterdir()))} files')


if __name__ == '__main__':
    main()
