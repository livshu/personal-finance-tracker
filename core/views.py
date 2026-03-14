from django.db.models import Sum
from django.shortcuts import render

from .models import Account, Category, Transaction


def home(request):
    recent_transactions = Transaction.objects.select_related(
        "account", "category"
    ).order_by("-date", "-id")[:5]

    debit_total = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.DEBIT,
            is_excluded=False,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    credit_total = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.CREDIT,
            is_excluded=False,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    transfer_count = Transaction.objects.filter(is_transfer=True).count()
    excluded_count = Transaction.objects.filter(is_excluded=True).count()

    context = {
        "account_count": Account.objects.count(),
        "category_count": Category.objects.count(),
        "transaction_count": Transaction.objects.count(),
        "recent_transactions": recent_transactions,
        "debit_total": debit_total,
        "credit_total": credit_total,
        "transfer_count": transfer_count,
        "excluded_count": excluded_count,
    }
    return render(request, "core/home.html", context)