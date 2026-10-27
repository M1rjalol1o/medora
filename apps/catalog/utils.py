import re

_APOSTROPHES = re.compile(r"[‘’ʻʼ`'´]")
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Qidiruv uchun matnni bir xil ko'rinishga keltiradi (o‘ / o' / o` -> o')."""
    text = _APOSTROPHES.sub("'", (text or "").lower())
    return _SPACES.sub(" ", text).strip()
