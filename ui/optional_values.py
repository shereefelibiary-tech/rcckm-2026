from typing import Optional


MISSING_STRINGS = {"", "missing", "not done", "not performed", "none", "null"}


def parse_optional_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.lower() in MISSING_STRINGS:
            return None
        value = cleaned
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_optional_int(value) -> Optional[int]:
    parsed = parse_optional_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def format_optional_value(value, unit=None, missing_label="missing") -> str:
    parsed = parse_optional_float(value)
    if parsed is None:
        return missing_label
    if parsed.is_integer():
        text = str(int(parsed))
    else:
        text = f"{parsed:g}"
    unit_text = str(unit or "").strip()
    return f"{text} {unit_text}".strip()
