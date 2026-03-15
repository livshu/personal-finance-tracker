def is_transfer_description(description_raw: str) -> bool:
    """
    Return True if the raw transaction description looks like a transfer.

    First version:
    - if the description contains 'olivia shuter' or 'o shuter',
      treat it as a transfer
    """
    if not description_raw:
        return False

    normalized_description = " ".join(description_raw.strip().lower().split())

    transfer_markers = [
        "olivia shuter",
        "o shuter",
    ]

    return any(marker in normalized_description for marker in transfer_markers)