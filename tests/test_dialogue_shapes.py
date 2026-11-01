from story.normalization import dialogue_lines
def test_dialogue_mapping_preserves_every_spoken_line():
    out,problems=dialogue_lines({'Alex':'I am still uncertain.','sam':'Then ask me.'},['alex','sam'])
    assert not problems
    assert out==[{'who':'alex','text':'I am still uncertain.'},{'who':'sam','text':'Then ask me.'}]
def test_single_dialogue_object_and_explicit_speaker_string_are_supported():
    assert dialogue_lines({'who':'sam','text':'Hello.'},['sam'])[0]==[{'who':'sam','text':'Hello.'}]
    assert dialogue_lines(['Sam: Hello.'],['sam'])[0]==[{'who':'sam','text':'Hello.'}]
def test_undeclared_speakers_receive_a_clear_validation_problem():
    assert dialogue_lines({'stranger':'Hello.'},['sam'])[1]
