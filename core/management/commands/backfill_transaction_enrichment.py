from django.core.management.base import BaseCommand

from core.categorization import suggest_category_for_merchant
from core.models import Transaction
from core.normalization import normalize_merchant


class Command(BaseCommand):
    help = (
        "Backfill merchant_normalized and category for existing transactions "
        "where those fields are blank."
    )

    def handle(self, *args, **options):
        updated_count = 0
        merchant_updated_count = 0
        category_updated_count = 0

        transactions = Transaction.objects.select_related("category").all()

        for transaction in transactions:
            changed = False

            new_merchant_normalized = normalize_merchant(transaction.description_raw)

            if new_merchant_normalized != transaction.merchant_normalized:
                transaction.merchant_normalized = new_merchant_normalized
                merchant_updated_count += 1
                changed = True

            merchant_normalized = transaction.merchant_normalized

            if transaction.category is None:
                suggested_category = suggest_category_for_merchant(merchant_normalized)
                if suggested_category is not None:
                    transaction.category = suggested_category
                    category_updated_count += 1
                    changed = True

            if changed:
                transaction.save(update_fields=["merchant_normalized", "category"])
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Updated {updated_count} transactions. "
                f"merchant_normalized set on {merchant_updated_count}, "
                f"category set on {category_updated_count}."
            )
        )