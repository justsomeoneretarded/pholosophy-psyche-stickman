"""Acting showcase rendered by the production engine (no AI models needed).

Renders examples/acting-showcase.json: movement, interactions, props, lighting
and emotion across several sets, with procedural sound cues, then verifies it.
Usage: python -m scripts.demo [--size 1280x720] [--out outputs/motion-demo]
"""
import argparse
import json
import subprocess
from pathlib import Path
from pipeline.models import Episode
from pipeline.production.director import prepare
from pipeline.production.render import render, probe
from pipeline.production.quality import motion_checks
from pipeline.production.audio import design


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', default='1280x720')
    parser.add_argument('--out', default='outputs/motion-demo')
    parser.add_argument('--storyboard', default='examples/acting-showcase.json')
    args = parser.parse_args()
    size = tuple(int(v) for v in args.size.split('x'))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    episode = Episode.model_validate_json(Path(args.storyboard).read_text())
    repairs = prepare(episode, size)
    timeline, cursor = [], 0.
    for s in episode.scenes:
        timeline.append({'scene_id': s.id, 'start': cursor, 'end': cursor + s.duration})
        cursor += s.duration
    report = motion_checks(episode, size)
    (out / 'motion_report.json').write_text(json.dumps(report, indent=2))
    (out / 'scene_repairs.json').write_text(json.dumps(repairs, indent=2))
    benchmark = render(episode, timeline, [], out, size, 30, 'high')
    design(timeline, episode, out, 'ambient', 7)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(out / 'silent.mp4'), '-i', str(out / 'sound_design.wav'),
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', str(out / 'motion-demo.mp4')], check=True)
    (out / 'benchmark.json').write_text(json.dumps(benchmark, indent=2))
    (out / 'ffprobe.json').write_text(json.dumps(probe(out / 'motion-demo.mp4'), indent=2))
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(out / 'motion-demo.mp4'), '-f', 'null', '-'], check=True)
    print(json.dumps({'motion_passed': report['passed'], 'issues': report['issues'][:5], **benchmark}))
    if not report['passed']:
        raise SystemExit('Motion QA failed: ' + str(report['issues'][:5]))


if __name__ == '__main__':
    main()
