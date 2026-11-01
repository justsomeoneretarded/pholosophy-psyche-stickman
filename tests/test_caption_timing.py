from pipeline.speech.caption_timing import align_caption_words
def test_script_words_are_preserved_and_recognized_timing_is_used():
    words=align_caption_words('What if I get this wrong?',[
        {'word':'What','start':.2,'end':.4},{'word':'if','start':.4,'end':.5},
        {'word':'I','start':.5,'end':.6},{'word':'get','start':.6,'end':.8},
        {'word':'this','start':.8,'end':1.},{'word':'wrong','start':1.,'end':1.4}],1.7)
    assert ' '.join(w['word'] for w in words)=='What if I get this wrong?'
    assert words[0]['start']==.2
    assert words[-1]['end']==1.4
def test_missing_word_is_interpolated_and_disclosed_not_dropped():
    words=align_caption_words('A real conversation begins.',[
        {'word':'A','start':0,'end':.1},{'word':'conversation','start':.5,'end':1.},{'word':'begins','start':1.,'end':1.4}],1.5)
    assert words[1]['word']=='real'
    assert words[1]['timing_source']=='estimated_between_anchors'
    assert .1<=words[1]['start']<=words[1]['end']<=.5
