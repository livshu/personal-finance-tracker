from decimal import Decimal
from datetime import date
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.utils import timezone
from core.reporting import get_reporting_amount
from .models import Account, Category, Transaction
from core.forms import (
    AmexCSVUploadForm,
    LloydsCSVUploadForm,
    SantanderCSVUploadForm,
)
from core.importers.amex import AmexCSVFormatError, parse_amex_csv
from core.importers.lloyds import LloydsCSVFormatError, parse_lloyds_csv
from core.importers.santander import SantanderCSVFormatError, parse_santander_csv
from core.import_services import build_transactions_for_import

def home(request):
    today = timezone.localdate()
    selected_month = request.GET.get("month")

    if selected_month:
        try:
            year_str, month_str = selected_month.split("-")
            selected_year = int(year_str)
            selected_month_number = int(month_str)
            month_start = date(selected_year, selected_month_number, 1)
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

    month_end = next_month_start - timezone.timedelta(days=1)

    recent_transactions = (
        Transaction.objects.select_related("account", "category")
        .filter(date__gte=month_start, date__lte=month_end)
        .order_by("-date", "-id")[:10]
    )

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

    monthly_transfer_count = Transaction.objects.filter(
        is_transfer=True,
        date__gte=month_start,
        date__lte=month_end,
    ).count()

    monthly_excluded_count = Transaction.objects.filter(
        is_excluded=True,
        date__gte=month_start,
        date__lte=month_end,
    ).count()

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


    context = {
        "account_count": Account.objects.count(),
        "category_count": Category.objects.count(),
        "transaction_count": Transaction.objects.count(),
        "recent_transactions": recent_transactions,
        "monthly_debit_total": monthly_debit_total,
        "monthly_credit_total": monthly_credit_total,
        "monthly_net_amount": monthly_net_amount,
        "monthly_transfer_count": monthly_transfer_count,
        "monthly_excluded_count": monthly_excluded_count,
        "monthly_spending_by_category": monthly_spending_by_category,
        "category_chart_labels": category_chart_labels,
        "category_chart_values": category_chart_values,
        "selected_month": selected_month,
    }
    return render(request, "core/home.html", context)

def import_lloyds_csv(request):
    form = LloydsCSVUploadForm()

    if request.method == "POST":
        form = LloydsCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            account = form.cleaned_data["account"]
            csv_file = form.cleaned_data["csv_file"]

            try:
                parsed_rows = parse_lloyds_csv(csv_file)
            except LloydsCSVFormatError as exc:
                form.add_error("csv_file", str(exc))
            else:
                serializable_rows = [
                    {
                        "date": row["date"].isoformat(),
                        "description_raw": row["description_raw"],
                        "transaction_type": row["transaction_type"],
                        "amount": str(row["amount"]),
                        "bank_transaction_type": row["bank_transaction_type"],
                    }
                    for row in parsed_rows
                ]

                request.session["lloyds_import_preview"] = {
                    "account_id": account.id,
                    "uploaded_file_name": csv_file.name,
                    "parsed_rows": serializable_rows,
                }

                preview_debit_rows = [
                row for row in parsed_rows if row["transaction_type"] == "debit"
                ]
                preview_credit_rows = [
                    row for row in parsed_rows if row["transaction_type"] == "credit"
                ]

                preview_debit_total = sum((row["amount"] for row in preview_debit_rows), start=Decimal("0.00"))
                preview_credit_total = sum((row["amount"] for row in preview_credit_rows), start=Decimal("0.00"))
                duplicate_count = 0

                for row in parsed_rows:
                    already_exists = Transaction.objects.filter(
                        account=account,
                        date=row["date"],
                        amount=row["amount"],
                        description_raw=row["description_raw"],
                        transaction_type=row["transaction_type"],
                    ).exists()

                    if already_exists:
                        duplicate_count += 1

                new_row_count = len(parsed_rows) - duplicate_count
                return render(
                    request,
                    "core/lloyds_preview.html",
                    {
                        "account": account,
                        "uploaded_file_name": csv_file.name,
                        "parsed_rows": parsed_rows,
                        "preview_debit_count": len(preview_debit_rows),
                        "preview_credit_count": len(preview_credit_rows),
                        "preview_debit_total": preview_debit_total,
                        "preview_credit_total": preview_credit_total,
                        "duplicate_count": duplicate_count,
                        "new_row_count": new_row_count,
                    },
                )

    return render(request, "core/import_lloyds.html", {"form": form})


def import_santander_csv(request):
    form = SantanderCSVUploadForm()

    if request.method == "POST":
        form = SantanderCSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            account = form.cleaned_data["account"]
            csv_file = form.cleaned_data["csv_file"]

            try:
                parsed_rows = parse_santander_csv(csv_file)
            except SantanderCSVFormatError as exc:
                form.add_error("csv_file", str(exc))
            else:
                preview_debit_rows = [
                    row for row in parsed_rows if row["transaction_type"] == "debit"
                ]
                preview_credit_rows = [
                    row for row in parsed_rows if row["transaction_type"] == "credit"
                ]

                preview_debit_total = sum(
                    (row["amount"] for row in preview_debit_rows),
                    start=Decimal("0.00"),
                )
                preview_credit_total = sum(
                    (row["amount"] for row in preview_credit_rows),
                    start=Decimal("0.00"),
                )

                serializable_rows = [
                    {
                        "date": row["date"].isoformat(),
                        "description_raw": row["description_raw"],
                        "transaction_type": row["transaction_type"],
                        "amount": str(row["amount"]),
                        "bank_transaction_type": row["bank_transaction_type"],
                    }
                    for row in parsed_rows
                ]

                request.session["santander_import_preview"] = {
                    "account_id": account.id,
                    "uploaded_file_name": csv_file.name,
                    "parsed_rows": serializable_rows,
                }

                return render(
                    request,
                    "core/santander_preview.html",
                    {
                        "account": account,
                        "uploaded_file_name": csv_file.name,
                        "parsed_rows": parsed_rows,
                        "preview_debit_count": len(preview_debit_rows),
                        "preview_credit_count": len(preview_credit_rows),
                        "preview_debit_total": preview_debit_total,
                        "preview_credit_total": preview_credit_total,
                    },
                )

    return render(request, "core/import_santander.html", {"form": form})



def confirm_santander_import(request):
    if request.method != "POST":
        return redirect("import_santander_csv")

    preview_data = request.session.get("santander_import_preview")
    if not preview_data:
        return redirect("import_santander_csv")

    account = Account.objects.get(id=preview_data["account_id"])
    uploaded_file_name = preview_data["uploaded_file_name"]
    parsed_rows = preview_data["parsed_rows"]

    transactions_to_create, skipped_count = build_transactions_for_import(
    account=account,
    uploaded_file_name=uploaded_file_name,
    parsed_rows=parsed_rows,
    notes_builder=lambda row: f"Santander import ({row['bank_transaction_type']})",
)

    Transaction.objects.bulk_create(transactions_to_create)

    del request.session["santander_import_preview"]

    return render(
        request,
        "core/santander_import_success.html",
        {
            "account": account,
            "imported_count": len(transactions_to_create),
            "skipped_count": skipped_count,
            "uploaded_file_name": uploaded_file_name,
        },
    )

def confirm_lloyds_import(request):
    if request.method != "POST":
        return redirect("import_lloyds_csv")

    preview_data = request.session.get("lloyds_import_preview")
    if not preview_data:
        return redirect("import_lloyds_csv")

    account = Account.objects.get(id=preview_data["account_id"])
    uploaded_file_name = preview_data["uploaded_file_name"]
    parsed_rows = preview_data["parsed_rows"]

    transactions_to_create, skipped_count = build_transactions_for_import(
        account=account,
        uploaded_file_name=uploaded_file_name,
        parsed_rows=parsed_rows,
        notes_builder=lambda row: f"Lloyds import ({row['bank_transaction_type']})",
    )
    Transaction.objects.bulk_create(transactions_to_create)

    del request.session["lloyds_import_preview"]

    return render(
        request,
        "core/lloyds_import_success.html",
        {
            "account": account,
            "imported_count": len(transactions_to_create),
            "skipped_count": skipped_count,
            "uploaded_file_name": uploaded_file_name,
        },
    )

def import_amex_csv(request):
    form = AmexCSVUploadForm()

    if request.method == "POST":
        form = AmexCSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            account = form.cleaned_data["account"]
            csv_file = form.cleaned_data["csv_file"]

            try:
                parsed_rows = parse_amex_csv(csv_file)
            except AmexCSVFormatError as exc:
                form.add_error("csv_file", str(exc))
            else:
                preview_rows = []

                for row in parsed_rows:
                    already_exists = Transaction.objects.filter(
                        account=account,
                        date=row["date"],
                        amount=row["amount"],
                        description_raw=row["description_raw"],
                        transaction_type=row["transaction_type"],
                    ).exists()

                    preview_rows.append(
                        {
                            **row,
                            "is_duplicate": already_exists,
                        }
                    )

                preview_debit_rows = [
                    row for row in preview_rows if row["transaction_type"] == "debit"
                ]
                preview_credit_rows = [
                    row for row in preview_rows if row["transaction_type"] == "credit"
                ]

                preview_debit_total = sum(
                    (row["amount"] for row in preview_debit_rows),
                    start=Decimal("0.00"),
                )
                preview_credit_total = sum(
                    (row["amount"] for row in preview_credit_rows),
                    start=Decimal("0.00"),
                )

                duplicate_count = sum(
                    1 for row in preview_rows if row["is_duplicate"]
                )
                new_row_count = len(preview_rows) - duplicate_count

                serializable_rows = [
                    {
                        "date": row["date"].isoformat(),
                        "description_raw": row["description_raw"],
                        "transaction_type": row["transaction_type"],
                        "amount": str(row["amount"]),
                        "appears_on_statement_as": row["appears_on_statement_as"],
                        "reference": row["reference"],
                        "category_label": row["category_label"],
                        "is_duplicate": row["is_duplicate"],
                    }
                    for row in preview_rows
                ]

                request.session["amex_import_preview"] = {
                    "account_id": account.id,
                    "uploaded_file_name": csv_file.name,
                    "parsed_rows": serializable_rows,
                }

                return render(
                    request,
                    "core/amex_preview.html",
                    {
                        "account": account,
                        "uploaded_file_name": csv_file.name,
                        "parsed_rows": preview_rows,
                        "preview_debit_count": len(preview_debit_rows),
                        "preview_credit_count": len(preview_credit_rows),
                        "preview_debit_total": preview_debit_total,
                        "preview_credit_total": preview_credit_total,
                        "duplicate_count": duplicate_count,
                        "new_row_count": new_row_count,
                    },
                )

    return render(request, "core/import_amex.html", {"form": form})

def confirm_amex_import(request):
    if request.method != "POST":
        return redirect("import_amex_csv")

    preview_data = request.session.get("amex_import_preview")
    if not preview_data:
        return redirect("import_amex_csv")

    account = Account.objects.get(id=preview_data["account_id"])
    uploaded_file_name = preview_data["uploaded_file_name"]
    parsed_rows = preview_data["parsed_rows"]

    transactions_to_create, skipped_count = build_transactions_for_import(
        account=account,
        uploaded_file_name=uploaded_file_name,
        parsed_rows=parsed_rows,
        notes_builder=lambda row: "Amex import",
    )
    Transaction.objects.bulk_create(transactions_to_create)

    del request.session["amex_import_preview"]

    return render(
        request,
        "core/amex_import_success.html",
        {
            "account": account,
            "imported_count": len(transactions_to_create),
            "skipped_count": skipped_count,
            "uploaded_file_name": uploaded_file_name,
        },
    )