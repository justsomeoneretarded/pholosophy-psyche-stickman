import pytest
from story.package import publishing_text
def test_thumbnail_words_accepts_model_word_array():
    assert publishing_text(['TOO','MUCH','THINKING'])=='TOO MUCH THINKING'
    assert publishing_text(' THINK AGAIN ')=='THINK AGAIN'
    assert publishing_text(None,'Default')=='Default'
def test_metadata_is_not_spoken_or_printed_as_python_repr():
    with pytest.raises(ValueError):publishing_text({'text':'unexpected'})
