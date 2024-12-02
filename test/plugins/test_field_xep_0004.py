import pytest

from pyjabber.plugins.xep_0004.field import FieldResponse, FieldRequest, FieldTypes, Option


def test_field_response():
    field = FieldResponse(
        field_type=FieldTypes.TEXT_SINGLE,
        var='test',
        values=['test1', 'test2']
    )

    assert field.type == FieldTypes.TEXT_SINGLE
    assert field.type.value == FieldTypes.TEXT_SINGLE.value
    assert field.var == 'test'
    assert 'test1' in field.values
    assert 'test2' in field.values


def test_field_response_missing_param():
    with pytest.raises(TypeError):
        FieldResponse(values=['test1', 'test2'])
    with pytest.raises(TypeError):
        FieldResponse(field_type=FieldTypes.TEXT_SINGLE, values=['test1', 'test2'])
    with pytest.raises(TypeError):
        FieldResponse(var='test', values=['test1', 'test2'])


def test_field_request():
    f = FieldRequest(
        field_type=FieldTypes.TEXT_SINGLE,
        var='test',
        label='labelTest',
        values=['value1'],
        desc='test description',
        required=True
    )

    assert f.type == FieldTypes.TEXT_SINGLE
    assert f.var == 'test'
    assert f.label == 'labelTest'
    assert 'value1' in f.values
    assert f.desc == 'test description'
    assert f.required == True

def test_field_requeset_invalid_options():
    with pytest.raises(ValueError):
        f = FieldRequest(
            field_type=FieldTypes.TEXT_SINGLE,
            var='test',
            label='labelTest',
            options=[Option(
                label='test',
                value='test'
            )],
            desc='test description',
            required=True
        )

    with pytest.raises(ValueError):
        f = FieldRequest(
            field_type=FieldTypes.LIST_MULTI,
            var='test',
            label='labelTest',
            values=['value1'],
            options=[Option(
                label='test',
                value='test'
            )],
            desc='test description',
            required=True
        )
