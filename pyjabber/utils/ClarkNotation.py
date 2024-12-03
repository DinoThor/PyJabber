# https://sabre.io/xml/clark-notation/
import re
from typing import Tuple


def deglose(tag: str):
    """
    Return the namespace and tag separated in a 2-tuple
    :return: (namespace, tag)
    """
    namespace = tag.split("}")[0].replace("{", "")
    tag = tag.split("}")[1]
    return namespace, tag


def clarkFromTuple(tuple: Tuple[str, str]):
    """
    Generate a clark notaion from a tuple in the format (namespace, tag).
    It's also possible to pass a tuple form of only a tag element (tag)
    """
    if tuple[0] is None:
        return f"{tuple[1]}"
    return f"{{{tuple[0]}}}{tuple[1]}"


def isClark(tag: str) -> bool:
    """
    Regex to check if a string is in the clark notation format
    """
    return re.match(
        "^\\{[a-zA-Z0-9:/#?=&;.]+?\\}[a-zA-Z_][a-zA-Z0-9_]*$",
        tag) is not None
