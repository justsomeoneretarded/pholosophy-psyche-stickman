"""Inspect the encoded production master; artistic judgments remain review notes."""
import argparse,json,subprocess,re
from pathlib import Path

def inspect(video,film):
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],text=True))
    failures=[];warnings=[]
    videos=[s for s in probe['streams'] if s.get('codec_type')=='video']
    audios=[s for s in probe['streams'] if s.get('codec_type')=='audio']
    duration=float(probe['format']['duration'])
    if not videos or not audios:failures.append('Encoded file must contain picture and audio')
    if videos:
        v=videos[0]
        if (v.get('width'),v.get('height'))!=(1920,1080):failures.append('Production master must be native 1920 x 1080')
        if v.get('codec_name')!='h264':failures.append('Expected H.264 picture')
        if v.get('avg_frame_rate')!='30/1':failures.append('Expected 30 FPS')
    if audios and audios[0].get('codec_name')!='aac':failures.append('Expected AAC sound')
    if abs(duration-float(film['duration']))>.15:failures.append('Encoded duration differs from the narration-fitted timeline')
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    r=subprocess.run(['ffmpeg','-v','info','-i',str(video),'-vn','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,check=True)
    summary=r.stderr.rsplit('Summary:',1)[-1]
    def number(pattern):
        m=re.search(pattern,summary);return float(m.group(1)) if m else None
    loudness=number(r'I:\s*(-?[\d.]+) LUFS')
    peak=number(r'Peak:\s*(-?[\d.]+) dBFS')
    if peak is None or peak>-.5:failures.append('Encoded audio lacks required peak headroom')
    if loudness is None or not -16<=loudness<=-12:warnings.append('Integrated loudness is outside the intended -14 LUFS neighborhood')
    lines=[l for s in film['shots'] for l in s.get('lines',[]) if l.get('who')=='narrator']
    if not lines:failures.append('No narration exists')
    if any(not l.get('voice_file') for l in lines):failures.append('A narration line has no audio attachment')
    if not (film.get('speech_verification') or {}).get('passed'):warnings.append('This revision has no complete speech-verification report')
    if any(not l.get('word_times') for l in lines):warnings.append('Some captions use estimated rather than word-aligned timing')
    poses={}
    for s in film['shots']:
        for a in s.get('actors',[]):poses[a.get('pose','stand')]=poses.get(a.get('pose','stand'),0)+1
    if sum(poses.get(p,0) for p in ['walk','run','reachout','drink','wave','point','getup','fall','type'])<3:
        warnings.append('Limited active character staging; review the film for excessive idle acting')
    return {'passed':not failures,'failures':failures,'warnings':warnings,'duration_seconds':duration,
            'loudness_lufs':loudness,'true_peak_dbfs':peak,'pose_usage':poses,'full_decode':'passed','probe':probe,
            'review_scope':'Technical evidence only. Script quality, believable acting and natural voice require separate review.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('film');p.add_argument('report');a=p.parse_args()
    report=inspect(Path(a.video),json.loads(Path(a.film).read_text()))
    Path(a.report).write_text(json.dumps(report,indent=2))
    text = f"# Production evidence\n\nDuration: {report['duration_seconds']:.3f} seconds.\n\nFull decode: {report['full_decode']}.\n\nIntegrated loudness: {report['loudness_lufs']} LUFS. True peak: {report['true_peak_dbfs']} dBFS.\n\n"
    text += "Warnings:\n" + "\n".join("- "+w for w in report['warnings']) + "\n\n"
    text += report['review_scope']+"\n"
    Path(a.report).with_name('production_report.md').write_text(text)
    if report['failures']:raise SystemExit('; '.join(report['failures']))
if __name__=='__main__':main()
