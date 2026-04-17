import bleach


def sanitize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return bleach.clean(value, tags=[], attributes={}, protocols=[], strip=True)


def sanitize_payload(data: dict) -> dict:
    cleaned: dict = {}
    for key, value in data.items():
        if isinstance(value, str):
            cleaned[key] = sanitize_text(value)
        elif isinstance(value, list):
            cleaned[key] = [sanitize_payload(item) if isinstance(item, dict) else sanitize_text(item) if isinstance(item, str) else item for item in value]
        elif isinstance(value, dict):
            cleaned[key] = sanitize_payload(value)
        else:
            cleaned[key] = value
    return cleaned

