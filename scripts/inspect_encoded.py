"""Sample the encoded master around physical performances, not just planned vector stills."""
import json,subprocess,base64,sys
from pathlib import Path
p=Path(sys.argv[1]); film=json.loads((p/'film.json').read_text());selected=[];t=0
for i,s in enumerate(film['shots']):
    poses={a.get('pose') for a in s.get('actors',[])}
    if len(film['shots'])<=15 or i%5==0 or poses & {'write','show','walk','standup','sitdown','talk'}:
        selected.append((i,round(t+min(float(s['dur'])/2,2),2)))
    t+=float(s['dur'])
folder=p/'encoded-frames';folder.mkdir(exist_ok=True)
for i,at in selected:
    dest=folder/f'shot-{i:03d}-t{at:07.2f}.jpg'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(at),'-i',str(p/'video.mp4'),'-frames:v','1','-vf','scale=960:-2',str(dest)],check=True)
    dest.with_suffix('.jpg.b64').write_text(base64.b64encode(dest.read_bytes()).decode())
(p/'inspection.json').write_text(json.dumps({'source':'decoded final MP4','selected':selected,'pose_usage':json.loads((p/'quality_report.json').read_text())['pose_usage']},indent=2))
