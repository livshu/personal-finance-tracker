def is_excluded_description(description_raw: str) -> bool:
    """
    Return True if the raw transaction description should be excluded
    from dashboard reporting.

    First version:
    - Amex payment receipt acknowledgements like
      'payment received - thank you'
    """
    if not description_raw:
        return False

    normalized_description = " ".join(description_raw.strip().lower().split())

    exclusion_markers = [
        "payment received - thank you",
        "payment received",
    ]

    return any(marker in normalized_description for marker in exclusion_markers)
