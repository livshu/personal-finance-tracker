def is_transfer_description(description_raw: str) -> bool:
    """
    Return True if the raw transaction description looks like an internal
    transfer or reimbursement rather than real spend.
    """
    if not description_raw:
        return False

    normalized_description = " ".join(description_raw.strip().lower().split())

    # Real merchant / bill / rent payments that should NOT be treated as transfers
    non_transfer_markers = [
        "standing order to marsh",
        "standing order via faster payment to marsh",
        "marsh parsons",
        "edf uk card payments",
        "direct debit",
        "card purchase",
    ]

    if any(marker in normalized_description for marker in non_transfer_markers):
        return False

    transfer_markers = [
        # Existing personal-name markers
        "olivia shuter",
        "o shuter",

        # Actual transfer / reimbursement wording
        "faster payments receipt",
        "bank transfer",
        "transfer from",
        "transfer to",

        # Your observed reimbursement/reference patterns
        "ref.rent from",
        "ref.council tax from",
        "ref.wifi from",
        "joint account from",

        # Counterparty name variants
        "from d clark",
        "from clark d",
    ]

    return any(marker in normalized_description for marker in transfer_markers)