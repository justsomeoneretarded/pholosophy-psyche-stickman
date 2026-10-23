import subprocess
from pipeline.production.quality import visual_samples
def test_blank_video_is_detected(tmp_path):
    path=tmp_path/'blank.mp4'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=white:s=320x180:d=3','-c:v','libx264','-pix_fmt','yuv420p',str(path)],check=True)
    report=visual_samples(path)
    assert report['sample_count']>=1
    assert report['all_blank']
