import json,shutil,subprocess
from pathlib import Path
import pytest
def test_caption_chunks_do_not_cut_words_and_use_audio_time():
    if not shutil.which('node'):pytest.skip('Node required for canvas helper')
    script="""const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const code=fs.readFileSync('engine/captions.js','utf8');
assert.equal(vm.runInNewContext(code+';narratorCaption({text:"hello world",cps:1},3)'), '');
assert.equal(vm.runInNewContext(code+';narratorCaption({text:"hello world",cps:1},7)'), 'hello');
assert.equal(vm.runInNewContext(code+';narratorCaption({word_times:[{word:"A",start:1,end:1.2},{word:"reply.",start:1.2,end:2}]},.5)'), '');
assert.equal(vm.runInNewContext(code+';narratorCaption({word_times:[{word:"A",start:1,end:1.2},{word:"reply.",start:1.2,end:2}]},1.5)'), 'A reply.');
"""
    subprocess.run(['node','-e',script],check=True)
