"""Motion diagnostic rendered by the production engine."""
from pathlib import Path
from pipeline.models import Episode,Scene,Action,Prop
from pipeline.production.render import render,probe
from pipeline.production.quality import motion_checks
import json,subprocess
moves=['walk','run','stop','sit','stand','pick_up','carry','think','wave','handshake','fall','recover','jump','celebrate']
scenes=[];timeline=[];cursor=0
for i,move in enumerate(moves):
    characters=['main','friend'] if move=='handshake' else ['main']
    props=[Prop(id='chair',kind='chair',x=.38,y=.70)] if move in ('sit','stand') else [Prop(id='phone',kind='phone',x=.48,y=.70)] if move in ('pick_up','carry') else []
    actions=[Action(action=move,start=0,end=2.5,x=.40,target='phone' if move in ('pick_up','carry') else None)]
    if move=='handshake':actions.append(Action(actor='friend',action='handshake',start=0,end=2.5,x=.66))
    s=Scene(id=f'demo_{i:02}',purpose='Rig motion demonstration',narration='Demonstrating articulated '+move+' with the production animation engine.',duration=2.5,actions=actions,props=props,characters=characters,text=move.replace('_',' ').upper(),transition='cut',symbol='thought' if move=='think' else 'none',camera='track' if move=='walk' else 'static')
    scenes.append(s);timeline.append({'start':cursor,'end':cursor+2.5});cursor+=2.5
out=Path('outputs/motion-demo');out.mkdir(parents=True,exist_ok=True)
episode=Episode(title='Motion engine demonstration',thesis='A deterministic articulated rig with inverse kinematics and contact.',metaphor='A rehearsal stage for the recurring cast.',framing='philosophical_exploration',scenes=scenes)
(out/'motion_report.json').write_text(json.dumps(motion_checks(episode,(1280,720)),indent=2))
benchmark=render(episode,timeline,[],out,(1280,720),30);print(benchmark)
(out/'silent.mp4').replace(out/'motion-demo.mp4')
(out/'benchmark.json').write_text(json.dumps(benchmark,indent=2))
(out/'ffprobe.json').write_text(json.dumps(probe(out/'motion-demo.mp4'),indent=2))
subprocess.run(['ffmpeg','-v','error','-i',str(out/'motion-demo.mp4'),'-f','null','-'],check=True)
