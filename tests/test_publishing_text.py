import pytest
from story.package import publishing_text
def test_thumbnail_words_accepts_model_word_array():
    assert publishing_text(['TOO','MUCH','THINKING'])=='TOO MUCH THINKING'
    assert publishing_text(' THINK AGAIN ')=='THINK AGAIN'
    assert publishing_text(None,'Default')=='Default'
def test_metadata_is_not_spoken_or_printed_as_python_repr():
    with pytest.raises(ValueError):publishing_text({'text':'unexpected'})

def test_thumbnail_candidate_phrases_are_not_concatenated():
    from story.package import thumbnail_caption
    assert thumbnail_caption(['Break the loop','Honest message'],'Fallback')=='Break the loop'
    assert thumbnail_caption(['TOO','MUCH','THINKING'],'Fallback')=='TOO MUCH THINKING'
