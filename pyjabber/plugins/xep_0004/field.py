from enum import Enum
from typing import List


class FieldTypes(Enum):
    BOOLEAN = 'boolean'
    FIXED = 'fixed'
    HIDDEN = 'hidden'
    JID_MULTI = 'jid-multi'
    JID_SINGLE = 'jid-single'
    LIST_MULTI = 'list-multi'
    LIST_SINGLE = 'list-single'
    TEXT_MULTI = 'text-multi'
    TEXT_PRIVATE = 'text-private'
    TEXT_SINGLE = 'text-single'

    @classmethod
    def from_value(cls, value):
        for item in cls:
            if item.value == value:
                return item
        raise ValueError()


class Option:
    def __init__(self, label: str, value: str):
        self._label = label,
        self._value = value


class FieldResponse:
    def __init__(
            self,
            field_type: FieldTypes,
            var: str,
            values: List[str] = None):

        self._type = field_type
        self._var = var
        self._values = values

    @property
    def type(self) -> FieldTypes:
        return self._type

    @property
    def var(self) -> str:
        return self._var

    @property
    def values(self) -> List[str]:
        return self._values


class FieldRequest:
    def __init__(
            self,
            field_type: FieldTypes,
            var: str,
            label: str = None,
            values: List[str] = None,
            options: List[Option] = None,
            desc: str = None,
            required: bool = False):

        if field_type not in [FieldTypes.LIST_SINGLE.value, FieldTypes.LIST_MULTI.value] and options is not None:
            raise ValueError("Options is only available with FieldType of [LIST-SINGLE, LIST-MULTIPLE]")

        if options is not None and values is not None:
            raise ValueError("Options List cannot be passed along with values List")

        self._type = field_type
        self._var = var
        self._label = label
        self._values = values
        self._options = options
        self._desc = desc
        self._required = required

    @property
    def type(self) -> FieldTypes:
        return self._type

    @property
    def label(self) -> str:
        return self._label

    @property
    def var(self) -> str:
        return self._var

    @property
    def options(self) -> List[str]:
        return self._options

    @property
    def values(self) -> List[str]:
        return self._values

    @property
    def desc(self) -> str:
        return self._desc

    @property
    def required(self) -> bool:
        return self._required
