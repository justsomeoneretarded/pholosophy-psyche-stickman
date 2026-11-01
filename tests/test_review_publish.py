"""Regression for the publisher that previously removed 94 older review files."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def run(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
def test_publishing_preserves_other_runs_and_existing_inspection_files(tmp_path):
    remote=tmp_path/'remote.git';run('git','init','--bare',str(remote))
    first=tmp_path/'first';first.mkdir()
    (first/'review.mp4').write_text('first review')
    (first/'diagnostic.json').write_text('saved inspection')
    second=tmp_path/'second';second.mkdir()
    (second/'review.mp4').write_text('second review')
    def publish(source,number,work):
        run('bash',str(ROOT/'scripts/publish_review.sh'),str(source),str(remote),str(number),str(tmp_path/work))
    publish(first,1,'work1');publish(second,2,'work2')
    assert run('git','--git-dir',str(remote),'show','previews:previews/1/review.mp4')=='first review'
    assert run('git','--git-dir',str(remote),'show','previews:previews/2/review.mp4')=='second review'
    (first/'diagnostic.json').unlink();(first/'review.mp4').write_text('updated first review')
    publish(first,1,'work3')
    assert run('git','--git-dir',str(remote),'show','previews:previews/1/diagnostic.json')=='saved inspection'
    assert run('git','--git-dir',str(remote),'show','previews:previews/2/review.mp4')=='second review'
