from decimal import Decimal

from django.utils import timezone

from core.categorization import suggest_category_for_merchant
from core.models import Transaction
from core.normalization import normalize_merchant


def build_transactions_for_import(account, uploaded_file_name, parsed_rows, notes_builder):
    """
    Turn parsed import rows into Transaction objects, skipping duplicates.

    Returns:
        (transactions_to_create, skipped_count)
    """
    transactions_to_create = []
    skipped_count = 0
    imported_at = timezone.now()

    for row in parsed_rows:
        row_date = row["date"]
        row_amount = Decimal(row["amount"])
        row_description = row["description_raw"]
        row_type = row["transaction_type"]

        already_exists = Transaction.objects.filter(
            account=account,
            date=row_date,
            amount=row_amount,
            description_raw=row_description,
            transaction_type=row_type,
        ).exists()

        if already_exists:
            skipped_count += 1
            continue

        merchant_normalized = normalize_merchant(row_description)
        category = suggest_category_for_merchant(merchant_normalized)

        transactions_to_create.append(
            Transaction(
                account=account,
                category=category,
                date=row_date,
                amount=row_amount,
                description_raw=row_description,
                merchant_normalized=merchant_normalized,
                transaction_type=row_type,
                source_file=uploaded_file_name,
                imported_at=imported_at,
                notes=notes_builder(row),
                is_transfer=False,
                is_excluded=False,
            )
        )

    return transactions_to_create, skipped_count