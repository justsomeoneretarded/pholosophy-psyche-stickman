"""Noir philosophy-essay production, one stage per GitHub Actions job.

  python -m pipeline.essay plan    --title "Nihilism - belief in nothing" [--minutes auto|6] [--script file.json]
  python -m pipeline.essay voice   [--narrator warguy|kit-laser|female]
  python -m pipeline.essay produce [--quality high|standard] [--format 16:9|9:16] [--captions]
All stages share --work (default work/); produce writes the package to --final.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path


def notice(title, message, level='notice'):
    print(f'::{level} title={title}::{str(message).replace(chr(10), " ")[:900]}', flush=True)


def save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))


def minutes_value(text):
    text = (text or 'auto').strip().lower()
    if text in ('', 'auto', '0'):
        return None
    value = float(text)
    if not 2 <= value <= 15:
        raise SystemExit('Duration must be Auto or between 2 and 15 minutes')
    return value


def load_script(work):
    from pipeline.writing.beats import Script
    return Script.model_validate_json((Path(work) / 'plan' / 'script.json').read_text())


def stage_plan(args):
    from pipeline.writing.beats import Script, compile_script, estimate
    from pipeline.writing.research import research
    plan = Path(args.work) / 'plan'
    plan.mkdir(parents=True, exist_ok=True)
    started = time.time()
    found = research(args.title)
    save(plan / 'research.json', found)
    for w in found['warnings']:
        notice('Research', w, 'warning')
    if args.script:
        script = Script.model_validate_json(Path(args.script).read_text())
        report = {'model': 'fixed script file', 'estimated_seconds': sum(estimate(b) for b in script.beats)}
    else:
        from pipeline.writing.essay import write
        script, report = write(args.title, minutes_value(args.minutes), found)
    compile_script(script)          # fails early if a beat cannot be staged
    (plan / 'script.json').write_text(script.model_dump_json(indent=1))
    report.update(beats=len(script.beats), seconds=time.time() - started,
                  narrated=sum(1 for b in script.beats if b.mode == 'narrated'))
    save(plan / 'writer.json', report)
    notice('Script', f"{script.title}: {len(script.beats)} beats, about {report['estimated_seconds'] / 60:.1f} min, written by {report['model']}")


def stage_voice(args):
    from pipeline.writing.beats import compile_script
    from pipeline.speech.narrator import voice_episode
    episode = compile_script(load_script(args.work))
    started = time.time()
    manifest = voice_episode(episode, Path(args.work) / 'speech', args.narrator)
    total = sum(v['seconds'] for v in manifest.values())
    notice('Narration', f'{len(manifest)} narrated beats, {total:.0f}s of speech in {(time.time() - started) / 60:.1f} min ({args.narrator})')


def stage_produce(args):
    from pipeline.writing.beats import compile_script
    from pipeline.production.essay_mix import build_timeline, mix
    from pipeline.production.render import render
    from pipeline.production import essay_package as pkg
    work, final = Path(args.work), Path(args.final)
    final.mkdir(parents=True, exist_ok=True)
    (final / 'SUCCESS.json').unlink(missing_ok=True)
    script = load_script(work)
    research = json.loads((work / 'plan' / 'research.json').read_text()) if (work / 'plan' / 'research.json').exists() else {}
    writer = json.loads((work / 'plan' / 'writer.json').read_text()) if (work / 'plan' / 'writer.json').exists() else {}
    speech_path = work / 'speech' / 'speech.json'
    speech = json.loads(speech_path.read_text()) if speech_path.exists() else {}
    episode = compile_script(script)
    missing = [s.id for s in episode.scenes if s.voiced and s.id not in speech]
    if missing:
        if args.allow_silent:
            notice('Narration missing', f'{len(missing)} beats have no speech; they are rendered at their estimated length without voice', 'warning')
        else:
            raise SystemExit(f'Narration missing for {missing[:5]}; run the voice stage first')
    size = (1080, 1920) if args.format == '9:16' else (1920, 1080)
    timeline, captions = build_timeline(episode, speech)
    total = timeline[-1]['end']
    notice('Timeline', f'{len(timeline)} beats, {total / 60:.2f} minutes')
    save(work / 'timeline.json', timeline)
    pkg.subtitles(captions, final)
    burn = captions if args.captions else []
    started = time.time()
    bench = render(episode, timeline, burn, work / 'render', size, 30, args.quality)
    notice('Render', f"{bench['frames']} frames in {(time.time() - started) / 60:.1f} min")
    scores = {m: work / 'music' / f'{m}.wav' for m in ('contemplative', 'hopeful')}
    credits = mix(work / 'render', timeline, episode, speech, work / 'speech', scores)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(work / 'render' / 'silent.mp4'), '-i', str(work / 'render' / 'final_mix.wav'),
                    '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', f'{total:.3f}',
                    '-movflags', '+faststart', str(final / 'video.mp4')], check=True)
    pkg.thumbnails(episode, script, final)
    pkg.contact_sheet(episode, final)
    pkg.publishing(script, research, credits, args.narrator, writer.get('model', 'unknown'), final)
    qa = pkg.check_video(final / 'video.mp4', size, total)
    qa.update(beats=len(timeline), narrated_beats=sum(1 for r in timeline if r['voiced']), writer=writer.get('model'),
              narrator=args.narrator, music=sorted({c['music'] for c in credits}))
    save(final / 'quality.json', qa)
    pkg.review_page(final, qa, timeline, script)
    if not qa['passed']:
        raise SystemExit('Video check failed: ' + '; '.join(qa['issues']))
    save(final / 'SUCCESS.json', {'status': 'complete', 'minutes': round(total / 60, 2)})
    notice('Done', f"{script.title}: {total / 60:.1f} min video, {qa['integrated_lufs']} LUFS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['plan', 'voice', 'produce'])
    p.add_argument('--title', default=os.environ.get('VIDEO_TITLE', ''))
    p.add_argument('--minutes', default=os.environ.get('VIDEO_MINUTES', 'auto'))
    p.add_argument('--script', default=os.environ.get('SCRIPT_FILE') or None)
    p.add_argument('--narrator', default=os.environ.get('NARRATOR', 'warguy'))
    p.add_argument('--quality', default=os.environ.get('VIDEO_QUALITY', 'high'), choices=['high', 'standard'])
    p.add_argument('--format', default=os.environ.get('VIDEO_FORMAT', '16:9'), choices=['16:9', '9:16'])
    p.add_argument('--captions', action='store_true', default=os.environ.get('BURN_CAPTIONS', 'false') == 'true')
    p.add_argument('--allow-silent', action='store_true', help='render even if narration is missing (testing)')
    p.add_argument('--work', default='work')
    p.add_argument('--final', default='outputs/video')
    args = p.parse_args()
    args.narrator = args.narrator.strip().lower().replace(' ', '-')
    if args.stage == 'plan' and not args.title.strip() and not args.script:
        raise SystemExit('A title is required')
    try:
        {'plan': stage_plan, 'voice': stage_voice, 'produce': stage_produce}[args.stage](args)
    except BaseException:
        Path(args.work).mkdir(parents=True, exist_ok=True)
        (Path(args.work) / f'FAILURE-{args.stage}.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
