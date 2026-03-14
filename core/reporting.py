from decimal import Decimal

from core.models import Account, Transaction


JOINT_ACCOUNT_SHARE = Decimal("0.50")


def get_reporting_amount(transaction: Transaction) -> Decimal:
    """
    Return the amount that should count in personal reporting.

    Raw transaction.amount stays unchanged in the database.
    Joint-account transactions count as 50%.
    Personal-account transactions count in full.
    """
    if transaction.account.owner_type == Account.OwnerType.JOINT:
        return transaction.amount * JOINT_ACCOUNT_SHARE

    return transaction.amount