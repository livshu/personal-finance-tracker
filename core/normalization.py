import re


MERCHANT_RULES = [
    ("TESCO", "Tesco"),
    ("SAINSBURY", "Sainsbury's"),
    ("AMAZON", "Amazon"),
    ("AMZN", "Amazon"),
    ("UBER", "Uber"),
    ("TRAINLINE", "Trainline"),
    ("PRET", "Pret"),
    ("COSTA", "Costa"),
    ("STARBUCKS", "Starbucks"),
]


def normalize_merchant(description_raw: str) -> str:
    """
    Convert a raw bank description into a cleaner merchant label.

    This is a lightweight first version:
    - trims whitespace
    - uppercases for matching
    - removes obvious punctuation noise
    - applies simple keyword rules
    - falls back to a cleaned title-cased version
    """
    cleaned = (description_raw or "").strip()

    if not cleaned:
        return ""

    normalized_for_matching = re.sub(r"[^A-Z0-9 ]+", " ", cleaned.upper())
    normalized_for_matching = re.sub(r"\s+", " ", normalized_for_matching).strip()

    for keyword, merchant_name in MERCHANT_RULES:
        if keyword in normalized_for_matching:
            return merchant_name

    fallback = re.sub(r"\s+", " ", cleaned).strip()
    return fallback.title()