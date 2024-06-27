# https://sabre.io/xml/clark-notation/
import re

def deglose(tag: str):
    namespace   = tag.split("}")[0].replace("{", "")
    tag         = tag.split("}")[1]
    return namespace, tag

def clarkFromTuple(tuple):
    if tuple[0] is None:
        return f"{tuple[1]}"
    return f"{{{tuple[0]}}}{tuple[1]}"

def isClark(tag: str) -> bool:
    return re.match("^\{[a-zA-Z0-9:/#?=&;.]+?\}[a-zA-Z_][a-zA-Z0-9_]*$", tag) is not None
