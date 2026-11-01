import numpy as np
from audio.looping import loop_music
def test_crossfade_does_not_leave_holes_or_double_the_level():
    music=np.ones((100,2))*.2
    result=loop_music(music,350,10,crossfade_seconds=2)
    assert result.shape==(350,2)
    assert np.max(np.abs(result-.2))<1e-12
def test_music_loop_preserves_stereo_and_requested_length():
    music=np.column_stack([np.linspace(0,1,100),np.linspace(1,0,100)])
    result=loop_music(music,260,10,2)
    assert result.shape==(260,2)
    assert np.all(np.isfinite(result))
    assert not np.allclose(result[:,0],result[:,1])
