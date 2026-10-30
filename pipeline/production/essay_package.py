"""Thumbnails, publishing files and the review page for noir essays."""
import html
import json
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from pipeline.animation.scene import frame, face_font
from pipeline.production.render import probe

THUMB = (1280, 720)


def _still(scene, at):
    s = scene.model_copy(deep=True)
    s.text = ''
    s.voiced = True
    s.narration = s.narration or 'still frame for the thumbnail'
    s.transition = 'cut'
    return frame(s, s.duration * at, THUMB, ss=2)


def _pick(episode, prefer):
    for name in prefer:
        for s in episode.scenes:
            if s.setpiece == name:
                return s
    return episode.scenes[min(2, len(episode.scenes) - 1)]


def _words(d, text, box, size, face='headline', amber_word=None, fill=(245, 242, 235)):
    """Write a 1-3 line bold headline inside box, shrinking to fit; one word may be amber."""
    x0, y0, x1, y1 = box
    words = text.upper().split()
    lines = [' '.join(words[i:i + 2]) for i in range(0, len(words), 2)] if len(words) > 2 else [' '.join(words)]
    while size > 20:
        ft = face_font(face, size)
        widths = [d.textbbox((0, 0), line, font=ft)[2] for line in lines]
        height = len(lines) * size * 1.05
        if max(widths) <= x1 - x0 and height <= y1 - y0:
            break
        size -= 4
    ft = face_font(face, size)
    y = y0 + (y1 - y0 - len(lines) * size * 1.05) / 2
    for line in lines:
        x = x0
        for word in line.split():
            colour = (226, 164, 71) if amber_word and word == amber_word else fill
            stroke = (10, 10, 12) if sum(fill) > 380 else (235, 232, 225)
            d.text((x, y), word, font=ft, fill=colour, stroke_width=max(2, size // 30), stroke_fill=stroke)
            x += d.textbbox((0, 0), word + ' ', font=ft)[2]
        y += size * 1.05


def thumbnails(episode, script, out):
    out = Path(out)
    words = (script.thumbnail_words or script.title).strip()
    key = words.upper().split()[-1] if words else None
    paths = []
    hero = _pick(episode, ['chalk_door', 'fall', 'word_wall', 'desert', 'sisyphus', 'giant_hand', 'mirror'])
    im = _still(hero, .82 if hero.setpiece == 'chalk_door' else .55)
    shade = Image.new('RGB', THUMB, (0, 0, 0))
    mask = Image.linear_gradient('L').rotate(90).resize(THUMB).point(lambda v: int(v * .75))
    im = Image.composite(shade, im, mask)
    _words(ImageDraw.Draw(im), words, (50, 60, 640, 660), 150, amber_word=key)
    paths.append(out / 'thumbnail-01.jpg')
    im.save(paths[-1], quality=92)

    dark = _pick(episode, ['word_wall', 'pillar', 'shadow_companion', 'cage', 'clock', 'thinker'])
    im = _still(dark, .2)
    im = Image.blend(im, Image.new('RGB', THUMB, (0, 0, 0)), .25)
    _words(ImageDraw.Draw(im), words, (90, 40, 1190, 300), 140, face='display', amber_word=key)
    paths.append(out / 'thumbnail-02.jpg')
    im.save(paths[-1], quality=92)

    light = _pick(episode, ['desert', 'sisyphus', 'crowd', 'stairs', 'flower', 'scale'])
    im = _still(light, .7)
    big = (script.title.split(':')[0] if ':' in script.title else words.split()[0]).upper()[:14]
    d = ImageDraw.Draw(im)
    _words(d, big, (60, 40, 1220, 330), 230, face='display', fill=(20, 20, 22))
    paths.append(out / 'thumbnail-03.jpg')
    im.save(paths[-1], quality=92)
    return paths


def stamp(t, sep=','):
    ms = round(t * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02}{sep}{ms:03}'


def subtitles(captions, out):
    out = Path(out)
    srt = [f"{i + 1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}\n" for i, c in enumerate(captions)]
    vtt = ['WEBVTT\n'] + [f"{stamp(c['start'], '.')} --> {stamp(c['end'], '.')}\n{c['text']}\n" for c in captions]
    (out / 'subtitles.srt').write_text('\n'.join(srt))
    (out / 'subtitles.vtt').write_text('\n'.join(vtt))


def publishing(script, research, credits, narrator, writer_model, out):
    out = Path(out)
    titles = script.youtube_titles or [script.title]
    (out / 'recommended-title.txt').write_text(titles[0] + '\n')
    (out / 'title-options.txt').write_text('\n'.join(titles) + '\n')
    music_credit = '\n'.join(sorted({c['music'] for c in credits}))
    (out / 'description.txt').write_text(script.description.strip() + '\n\nMusic: ' + music_credit.replace('\n', '; ') + '\n')
    (out / 'tags.txt').write_text(', '.join(script.tags) + '\n')
    (out / 'pinned-comment.txt').write_text(script.pinned_comment.strip() + '\n')
    (out / 'script.txt').write_text('\n\n'.join(
        (f'[narrated] {b.narration}' if b.mode == 'narrated' else f'[silent {b.seconds:.0f}s] {b.on_screen}') + f'   <{b.setpiece}>'
        for b in script.beats))
    (out / 'script.json').write_text(script.model_dump_json(indent=1))
    lines = ['SOURCES (background reading)'] + [f"- {s['title']}: {s['url']}" for s in research.get('sources', [])]
    lines += ['', 'MUSIC', music_credit, '', 'NARRATION', f'Chatterbox Turbo (MIT, Resemble AI), narrator reference: {narrator}',
              '', 'SCRIPT', f'Written with {writer_model} (Groq free tier)', '', 'FONTS',
              'Bebas Neue, Anton, Cormorant Garamond (SIL Open Font License)']
    (out / 'sources-and-credits.txt').write_text('\n'.join(lines) + '\n')


def contact_sheet(episode, out):
    cols = 4
    rows = math.ceil(len(episode.scenes) / cols)
    sheet = Image.new('RGB', (cols * 320, rows * 200), 'white')
    for i, s in enumerate(episode.scenes):
        im = frame(s, s.duration * .55, (1280, 720), ss=1).resize((320, 180))
        sheet.paste(im, (i % cols * 320, i // cols * 200))
        ImageDraw.Draw(sheet).text((i % cols * 320 + 4, i // cols * 200 + 182), f'{i + 1}. {s.setpiece} ({"voice" if s.voiced else "silent"})', fill='black')
    sheet.save(Path(out) / 'contact-sheet.jpg', quality=88)


def review_page(out, qa, timeline, script):
    out = Path(out)
    rows = ''.join(f"<tr><td>{i + 1}</td><td>{r['start']:.1f}-{r['end']:.1f}s</td><td>{html.escape(r['setpiece'] or '')}</td>"
                   f"<td>{'narrated' if r['voiced'] else 'silent'}</td><td>{'amber' if r['amber'] else ''}</td></tr>" for i, r in enumerate(timeline))
    checks = ''.join(f'<li>{html.escape(str(k))}: {html.escape(str(v))}</li>' for k, v in qa.items() if k not in ('video', 'audio'))
    (out / 'review.html').write_text(f"""<!doctype html><meta charset=utf-8><title>Review: {html.escape(script.title)}</title>
<style>body{{font:15px system-ui;margin:24px;background:#141416;color:#eee}}img{{max-width:100%}}td{{padding:2px 10px}}</style>
<h1>{html.escape(script.title)}</h1><img src="contact-sheet.jpg"><h2>Checks</h2><ul>{checks}</ul>
<h2>Beats</h2><table>{rows}</table><h2>Thumbnails</h2><img src="thumbnail-01.jpg" width=420> <img src="thumbnail-02.jpg" width=420> <img src="thumbnail-03.jpg" width=420>""")


def check_video(path, size, expected):
    data = probe(path)
    v = next(s for s in data['streams'] if s['codec_type'] == 'video')
    a = next(s for s in data['streams'] if s['codec_type'] == 'audio')
    duration = float(data['format']['duration'])
    issues = []
    if (v['width'], v['height']) != tuple(size):
        issues.append('wrong resolution')
    if abs(duration - expected) > 1.5:
        issues.append(f'duration {duration:.1f}s differs from timeline {expected:.1f}s')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 'null', '-'], check=True)
    loud = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(path), '-vn', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                          capture_output=True, text=True).stderr[-2500:]
    import re
    lufs = re.findall(r'I:\s*(-?\d+(?:\.\d+)?) LUFS', loud)
    return {'passed': not issues, 'issues': issues, 'duration_seconds': round(duration, 2), 'resolution': f"{v['width']}x{v['height']}",
            'integrated_lufs': float(lufs[-1]) if lufs else None, 'full_decode': 'passed'}
