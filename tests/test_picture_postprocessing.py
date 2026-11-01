"""Regression checks for the Picture part 0 thumbnail failure."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]

def test_poster_times_cli_does_not_need_pillow(tmp_path):
    film = tmp_path / 'film.json'
    film.write_text(json.dumps({'shots': [{'dur': 4, 'actors': [{'id': 'hero'}]}]}))
    # -S disables site-packages: the picture runner does not install Pillow.
    result = subprocess.run([sys.executable, '-S', str(ROOT/'story/package.py'),
                             '--poster-times', str(film)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == '2.4'

@pytest.mark.parametrize('times', ['', 'true', 'NaN', '1,,2', '-1'])
def test_invalid_poster_times_fail_before_browser_launch(tmp_path, times):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for renderer CLI regression checks')
    film = tmp_path / 'film.json'
    film.write_text(json.dumps({'title': 'CLI regression', 'shots': []}))
    result = subprocess.run([node, str(ROOT/'render/render.mjs'), '--film', str(film),
                             '--stills', str(tmp_path/'stills'), '--times', times],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode != 0
    assert '--times must be a non-empty' in result.stderr
    assert 'createPattern' not in result.stderr
