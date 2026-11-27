"""Read the local sources configuration with optional // line comments."""

import json
import re

_STRING_OR_COMMENT = re.compile(r'"(?:[^"\\\r\n]|\\.)*"|//[^\r\n]*')


def load_source_config(path):
    with open(path, encoding="utf-8") as file:
        text = file.read()
    text = _STRING_OR_COMMENT.sub(
        lambda match: "" if match[0].startswith("//") else match[0], text
    )
    return json.loads(text)
