from decimal import Decimal

from core.models import Account, Transaction


JOINT_ACCOUNT_SHARE = Decimal("0.50")
REPORTING_SHARED_INSTITUTIONS = {"santander"}


def uses_joint_reporting_share(account: Account) -> bool:
    normalized_institution = " ".join((account.institution or "").split()).casefold()

    return (
        account.owner_type == Account.OwnerType.JOINT
        and any(
            normalized_institution == institution
            or normalized_institution.startswith(f"{institution} ")
            for institution in REPORTING_SHARED_INSTITUTIONS
        )
    )


def get_reporting_amount(transaction: Transaction) -> Decimal:
    if uses_joint_reporting_share(transaction.account):
        return transaction.amount * JOINT_ACCOUNT_SHARE

    return transaction.amount


def attach_reporting_display_amounts(transactions):
    decorated_transactions = []

    for transaction in transactions:
        reporting_amount = get_reporting_amount(transaction)
        transaction.reporting_amount = reporting_amount
        transaction.raw_amount = transaction.amount
        transaction.display_amount = reporting_amount
        transaction.has_reporting_adjustment = reporting_amount != transaction.amount
        decorated_transactions.append(transaction)

    return decorated_transactions
