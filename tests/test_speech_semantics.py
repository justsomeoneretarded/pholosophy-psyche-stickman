from pipeline.speech.verification import speech_tokens,negation_change
def test_asr_punctuation_is_not_a_pronunciation_error():
    assert speech_tokens("its lessons")==speech_tokens("it's lessons")
    assert speech_tokens("don't do that")==speech_tokens("do not do that")
def test_missing_negation_is_caught_even_in_a_long_accurate_sentence():
    assert negation_change('This pattern does not prove a diagnosis even if the behavior feels familiar.',
                           'This pattern does prove a diagnosis even if the behavior feels familiar.')
    assert not negation_change("It doesn't prove anything.","It does not prove anything.")
