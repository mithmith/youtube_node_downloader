import re


def clean_string(s: str) -> str:
    allowed_chars = r"A-Za-zА-Яа-я0-9_\-"
    return re.sub(rf"[^{allowed_chars}]", "", s)
