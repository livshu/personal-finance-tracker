from django.core.management.base import BaseCommand

from core.categorization import suggest_category_for_merchant
from core.exclusion_rules import is_excluded_description
from core.models import Transaction
from core.normalization import normalize_merchant
from core.transfer_rules import is_transfer_description


class Command(BaseCommand):
    help = (
        "Backfill merchant_normalized, category, transfer flag, and exclusion flag "
        "for existing transactions."
    )

    def handle(self, *args, **options):
        updated_count = 0
        merchant_updated_count = 0
        category_updated_count = 0
        transfer_updated_count = 0
        excluded_updated_count = 0

        transactions = Transaction.objects.select_related("category").all()

        for transaction in transactions:
            changed = False

            new_merchant_normalized = normalize_merchant(transaction.description_raw)

            if new_merchant_normalized != transaction.merchant_normalized:
                transaction.merchant_normalized = new_merchant_normalized
                merchant_updated_count += 1
                changed = True

            merchant_normalized = transaction.merchant_normalized

            suggested_category = suggest_category_for_merchant(merchant_normalized)
            if suggested_category != transaction.category and suggested_category is not None:
                transaction.category = suggested_category
                category_updated_count += 1
                changed = True

            new_is_transfer = is_transfer_description(transaction.description_raw)
            if new_is_transfer != transaction.is_transfer:
                transaction.is_transfer = new_is_transfer
                transfer_updated_count += 1
                changed = True

            new_is_excluded = is_excluded_description(transaction.description_raw)
            if new_is_excluded != transaction.is_excluded:
                transaction.is_excluded = new_is_excluded
                excluded_updated_count += 1
                changed = True

            if changed:
                transaction.save(
                    update_fields=[
                        "merchant_normalized",
                        "category",
                        "is_transfer",
                        "is_excluded",
                    ]
                )
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill complete. Updated {updated_count} transactions. "
                f"merchant_normalized updated on {merchant_updated_count}, "
                f"category updated on {category_updated_count}, "
                f"is_transfer updated on {transfer_updated_count}, "
                f"is_excluded updated on {excluded_updated_count}."
            )
        )