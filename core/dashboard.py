from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from core.models import Transaction
from core.reporting import get_reporting_amount


TRANSACTION_DRILLDOWN_METRICS = {
    "debit": {
        "label": "Total debit transactions",
        "filters": {
            "transaction_type": Transaction.TransactionType.DEBIT,
            "is_excluded": False,
        },
    },
    "credit": {
        "label": "Total credit transactions",
        "filters": {
            "transaction_type": Transaction.TransactionType.CREDIT,
            "is_excluded": False,
        },
    },
    "transfer": {
        "label": "Transfer transactions",
        "filters": {
            "is_transfer": True,
        },
    },
    "excluded": {
        "label": "Excluded transactions",
        "filters": {
            "is_excluded": True,
        },
    },
    "uncategorized": {
        "label": "Uncategorized spend transactions",
        "filters": {
            "transaction_type": Transaction.TransactionType.DEBIT,
            "is_excluded": False,
            "is_transfer": False,
            "category__isnull": True,
        },
    },
}


def get_selected_month_window(selected_month: str | None):
    """
    Return the selected month string plus the start/end dates for that month.

    If selected_month is missing or invalid, fall back to the current month.

    Returns:
        (selected_month, month_start, month_end)
    """
    today = timezone.localdate()

    if selected_month:
        try:
            if len(selected_month) == 7:
                year_str, month_str = selected_month.split("-")
                selected_year = int(year_str)
                selected_month_number = int(month_str)
                month_start = date(selected_year, selected_month_number, 1)
            else:
                parsed_date = datetime.strptime(selected_month, "%Y-%m-%d").date()
                month_start = parsed_date.replace(day=1)
        except (ValueError, TypeError):
            month_start = today.replace(day=1)
            selected_month = month_start.strftime("%Y-%m")
    else:
        month_start = today.replace(day=1)
        selected_month = month_start.strftime("%Y-%m")

    if month_start.month == 12:
        next_month_start = date(month_start.year + 1, 1, 1)
    else:
        next_month_start = date(month_start.year, month_start.month + 1, 1)

    month_end = next_month_start - timedelta(days=1)

    return selected_month, month_start, month_end



def get_monthly_summary(month_start, month_end):
    """
    Return the reporting-aware monthly debit, credit, and net totals
    for the selected month window.
    """
    monthly_debit_transactions = Transaction.objects.select_related("account").filter(
        transaction_type=Transaction.TransactionType.DEBIT,
        is_excluded=False,
        date__gte=month_start,
        date__lte=month_end,
    )

    monthly_credit_transactions = Transaction.objects.select_related("account").filter(
        transaction_type=Transaction.TransactionType.CREDIT,
        is_excluded=False,
        date__gte=month_start,
        date__lte=month_end,
    )

    monthly_debit_total = sum(
        (get_reporting_amount(transaction) for transaction in monthly_debit_transactions),
        start=Decimal("0.00"),
    )

    monthly_credit_total = sum(
        (get_reporting_amount(transaction) for transaction in monthly_credit_transactions),
        start=Decimal("0.00"),
    )

    monthly_net_amount = monthly_credit_total - monthly_debit_total

    return {
        "monthly_debit_total": monthly_debit_total,
        "monthly_credit_total": monthly_credit_total,
        "monthly_net_amount": monthly_net_amount,
    }



def get_monthly_category_breakdown(month_start, month_end):
    """
    Return reporting-aware category totals and chart-ready values
    for debit transactions in the selected month window.
    """
    monthly_category_transactions = Transaction.objects.select_related(
        "account", "category"
    ).filter(
        transaction_type=Transaction.TransactionType.DEBIT,
        is_excluded=False,
        is_transfer=False,
        date__gte=month_start,
        date__lte=month_end,
        category__isnull=False,
    )

    category_totals = {}

    for transaction in monthly_category_transactions:
        category_name = transaction.category.name
        reporting_amount = get_reporting_amount(transaction)

        if category_name not in category_totals:
            category_totals[category_name] = Decimal("0.00")

        category_totals[category_name] += reporting_amount

    monthly_spending_by_category = [
        {"category__name": name, "total": total}
        for name, total in sorted(
            category_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    category_chart_labels = [
        item["category__name"] for item in monthly_spending_by_category
    ]

    category_chart_values = [
        float(item["total"]) for item in monthly_spending_by_category
    ]

    return {
        "monthly_spending_by_category": monthly_spending_by_category,
        "category_chart_labels": category_chart_labels,
        "category_chart_values": category_chart_values,
    }



def get_uncategorized_metrics(month_start, month_end):
    """
    Return reporting-aware metrics for uncategorized debit transactions
    in the selected month window.
    """
    uncategorized_transactions = Transaction.objects.select_related("account").filter(
        transaction_type=Transaction.TransactionType.DEBIT,
        is_excluded=False,
        is_transfer=False,
        date__gte=month_start,
        date__lte=month_end,
        category__isnull=True,
    )

    uncategorized_total = sum(
        (get_reporting_amount(transaction) for transaction in uncategorized_transactions),
        start=Decimal("0.00"),
    )

    return {
        "uncategorized_transaction_count": uncategorized_transactions.count(),
        "uncategorized_total": uncategorized_total,
    }


def get_transaction_drilldown_queryset(metric, month_start, month_end):
    """
    Return the label and queryset for a supported drilldown metric.
    """
    metric_config = TRANSACTION_DRILLDOWN_METRICS.get(metric)

    if metric_config is None:
        return None, None

    transactions = (
        Transaction.objects.select_related("account", "category")
        .filter(
            date__gte=month_start,
            date__lte=month_end,
            **metric_config["filters"],
        )
        .order_by("-date", "-id")
    )

    return metric_config["label"], transactions
