import subprocess,json,math,time,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
from pipeline.animation.scene import frame,font
def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
def render(episode,timeline,captions,out,size=(1920,1080),fps=30,quality='high'):
    out=Path(out);segments=out/'segments';segments.mkdir(exist_ok=True);started=time.monotonic();counts=[]
    for scene,row in zip(episode.scenes,timeline):
        signature=hashlib.sha256((scene.model_dump_json()+json.dumps([size,fps,quality,captions,'renderer-v2'])).encode()).hexdigest()
        dest=segments/(scene.id+'.mp4');marker=segments/(scene.id+'.sha256')
        # Filenames derive from validated positional indices, not model-generated paths.
        if not scene.id.replace('_','').isalnum():raise ValueError('Scene id must be alphanumeric')
        count=round(row['end']*fps)-round(row['start']*fps);counts.append(count)
        if dest.exists() and marker.exists() and marker.read_text()==signature:
            if abs(float(probe(dest)['format']['duration'])-count/fps)<.08:continue
        temp=dest.with_suffix('.partial.mp4')
        cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{size[0]}x{size[1]}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','20' if quality=='high' else '24','-pix_fmt','yuv420p','-threads','2',str(temp)]
        print(f'Rendering {scene.id}: {count} frames',flush=True)
        with open(segments/(scene.id+'.log'),'w') as log:
            process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=log)
            try:
                for k in range(count):
                    t=k/fps;gt=row['start']+t
                    cap=next((c['text'] for c in captions if c['start']<=gt<c['end']),'')
                    process.stdin.write(frame(scene,t,size,cap).tobytes())
                process.stdin.close()
                if process.wait()!=0:raise RuntimeError(f'Render failed: {scene.id}; see segment log')
            except BaseException:
                process.kill();process.wait();raise
        temp.replace(dest);marker.write_text(signature)
    listing=segments/'concat.txt';listing.write_text('\n'.join("file '"+s.id+".mp4'" for s in episode.scenes))
    subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','1','-i',str(listing),'-c','copy',str(out/'silent.mp4')],check=True)
    sheet=Image.new('RGB',(960,math.ceil(len(episode.scenes)/3)*200),'white')
    for i,s in enumerate(episode.scenes):
        thumb=frame(s,s.duration*.5,size).resize((320,180));sheet.paste(thumb,(i%3*320,i//3*200))
        ImageDraw.Draw(sheet).text((i%3*320+5,i//3*200+181),s.id,fill='black')
    sheet.save(out/'contact_sheet.jpg')
    return {'render_seconds':time.monotonic()-started,'frames':sum(counts),'native_resolution':list(size),'fps':fps}
def thumbnail(episode,out):
    import textwrap
    s=next((s for s in episode.scenes if s.symbol!='none'),episode.scenes[0]).model_copy(deep=True)
    s.text='';s.transition='cut';image=frame(s,s.duration*.55,(1280,720));d=ImageDraw.Draw(image)
    lines=textwrap.wrap(episode.title.rstrip('?!').upper(),width=24)[:3];ft=font(48)
    for i,line in enumerate(lines):
        y=38+i*60;width=d.textbbox((0,0),line,font=ft)[2]
        d.rounded_rectangle((30,y-5,50+width,y+55),radius=8,fill='#263343');d.text((40,y),line,font=ft,fill='white')
    image.save(Path(out)/'thumbnail.png')
