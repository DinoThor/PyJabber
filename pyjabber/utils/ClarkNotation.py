# https://sabre.io/xml/clark-notation/
import re

def deglose(tag: str):
    namespace   = tag.split("}")[0].replace("{", "")
    tag         = tag.split("}")[1] 
    return namespace, tag

def clarkFromStr(namespace, tag):
    return f"{{{namespace}}}{tag}"

def isClark(tag: str) -> bool:
    return re.match("^\{[a-zA-Z0-9:/#?=&;.]+?\}[a-zA-Z_][a-zA-Z0-9_]*$", str) is not None
