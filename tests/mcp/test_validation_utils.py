import pytest
from pythonium.mcp.utils.validation import Validator, ValidationError, SchemaValidator


def test_validator_basic_and_schema():
    v = Validator()
    v.validate_field('a', 'name', ['required', 'string'])
    with pytest.raises(ValidationError):
        v.validate_field('', 'name', ['required', 'non_empty_string'])

    schema = {'n': ['required', 'string'], 'c': ['positive_integer']}
    v.validate_schema({'n': 'x', 'c': 2}, schema)
    with pytest.raises(ValidationError):
        v.validate_schema({'n': 'x', 'c': 0}, schema)


def test_schema_validator_configs():
    sv = SchemaValidator()
    sv.validate_detector_config({'enabled': True, 'severity': 'info', 'config': {}})
    with pytest.raises(ValidationError):
        sv.validate_detector_config({'enabled': 'yes', 'severity': 'info', 'config': {}})

    sv.validate_analysis_config({'analysis': {'track_issues': True}, 'performance': {'max_workers': 1}})
    with pytest.raises(ValidationError):
        sv.validate_analysis_config({'performance': {'max_workers': 0}})

    sv.validate_issue_data({
        'id': '1',
        'detector': 'd',
        'severity': 'info',
        'message': 'msg',
        'file_path': 'f.py',
        'line': 1
    })

