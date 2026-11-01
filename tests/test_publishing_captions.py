from story.package import subtitles
def test_sidecar_captions_use_spoken_word_timestamps_and_export_vtt(tmp_path):
    film={'shots':[{'dur':5,'lines':[{'who':'narrator','text':'Hello there.','at':.25,
        'word_times':[{'word':'Hello','start':.2,'end':.5},{'word':'there.','start':.6,'end':1.0}]},
        {'who':'friend','text':'unspoken bubble','at':1}]}]}
    subtitles(film,tmp_path)
    srt=(tmp_path/'subtitles.srt').read_text()
    assert '00:00:00,450 --> 00:00:01,250' in srt
    assert 'Hello there.' in srt and 'unspoken bubble' not in srt
    assert (tmp_path/'subtitles.vtt').read_text().startswith('WEBVTT')
