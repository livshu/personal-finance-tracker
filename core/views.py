from django.http import Http404
from django.shortcuts import redirect, render
from .models import Account, Category, Transaction
from decimal import Decimal
from core.forms import (
    AmexCSVUploadForm,
    LloydsCSVUploadForm,
    SantanderStatementUploadForm,
)
from core.importers.amex import AmexCSVFormatError, parse_amex_csv
from core.importers.lloyds import LloydsCSVFormatError, parse_lloyds_csv
from core.importers.santander import (
    SantanderStatementFormatError,
    parse_santander_statement,
)
from core.import_services import build_transactions_for_import
from core.dashboard import (
    get_monthly_category_breakdown,
    get_monthly_summary,
    get_selected_month_window,
    get_transaction_drilldown_queryset,
    get_uncategorized_metrics,
)
from core.reporting import attach_reporting_display_amounts

def home(request):
    selected_month, month_start, month_end = get_selected_month_window(
        request.GET.get("month")
    )

    recent_transactions = attach_reporting_display_amounts(
        (
        Transaction.objects.select_related("account", "category")
        .filter(date__gte=month_start, date__lte=month_end)
        .order_by("-date", "-id")[:10]
        )
    )

    monthly_summary = get_monthly_summary(month_start, month_end)
    monthly_debit_total = monthly_summary["monthly_debit_total"]
    monthly_credit_total = monthly_summary["monthly_credit_total"]
    monthly_net_amount = monthly_summary["monthly_net_amount"]

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

    monthly_category_breakdown = get_monthly_category_breakdown(
        month_start, month_end
    )
    monthly_spending_by_category = monthly_category_breakdown[
        "monthly_spending_by_category"
    ]
    category_chart_labels = monthly_category_breakdown["category_chart_labels"]
    category_chart_values = monthly_category_breakdown["category_chart_values"]

    uncategorized_metrics = get_uncategorized_metrics(month_start, month_end)
    uncategorized_transaction_count = uncategorized_metrics["uncategorized_transaction_count"]
    uncategorized_total = uncategorized_metrics["uncategorized_total"]


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
        "selected_month": month_start.strftime("%Y-%m"),
        "selected_month_date": month_start.isoformat(),
        "uncategorized_transaction_count": uncategorized_transaction_count,
        "uncategorized_total": uncategorized_total,
    }
    return render(request, "core/home.html", context)


def transactions_drilldown(request):
    selected_month, month_start, month_end = get_selected_month_window(
        request.GET.get("month")
    )
    metric = request.GET.get("metric")
    metric_label, transactions = get_transaction_drilldown_queryset(
        metric, month_start, month_end
    )

    if transactions is None:
        raise Http404("Unknown transactions drilldown metric.")

    transactions = attach_reporting_display_amounts(transactions)

    context = {
        "metric": metric,
        "metric_label": metric_label,
        "selected_month": month_start.strftime("%Y-%m"),
        "selected_month_display": month_start.strftime("%B %Y"),
        "transaction_count": len(transactions),
        "transactions": transactions,
    }
    return render(request, "core/transactions_drilldown.html", context)

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
    form = SantanderStatementUploadForm()

    if request.method == "POST":
        form = SantanderStatementUploadForm(request.POST, request.FILES)

        if form.is_valid():
            account = form.cleaned_data["account"]
            statement_file = form.cleaned_data["statement_file"]

            try:
                parsed_rows = parse_santander_statement(statement_file)
            except SantanderStatementFormatError as exc:
                form.add_error("statement_file", str(exc))
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
                    "uploaded_file_name": statement_file.name,
                    "parsed_rows": serializable_rows,
                }

                return render(
                    request,
                    "core/santander_preview.html",
                    {
                        "account": account,
                        "uploaded_file_name": statement_file.name,
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
