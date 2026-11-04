from story.staging import staging_contract, validate_staging
import pytest

def test_editor_contract_matches_runtime_vocabulary():
    contract=staging_contract()
    assert 'write' in contract['poses']
    assert 'paint' not in contract['poses']
    assert 'pencil' in contract['holds']
    assert 'actors' in contract['phase_fields']

def test_unsupported_prop_error_offers_real_alternatives():
    with pytest.raises(ValueError,match='choose one of.*pencil'):
        validate_staging({'staging':[{'actors':[{'id':'a','pose':'write','hold':'paintbrush'}]}]},[{'id':'a'}])
