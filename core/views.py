from django.db.models import Sum
from .models import Account, Category, Transaction
from core.importers.lloyds import LloydsCSVFormatError, parse_lloyds_csv
from django.shortcuts import redirect, render
from django.utils import timezone
from decimal import Decimal
from django.db.models.functions import Coalesce
from core.forms import LloydsCSVUploadForm, SantanderCSVUploadForm
from core.importers.santander import SantanderCSVFormatError, parse_santander_csv

def home(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    recent_transactions = Transaction.objects.select_related(
        "account", "category"
    ).order_by("-date", "-id")[:5]

    monthly_debit_total = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.DEBIT,
            is_excluded=False,
            date__gte=month_start,
            date__lte=today,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    monthly_credit_total = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.CREDIT,
            is_excluded=False,
            date__gte=month_start,
            date__lte=today,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    monthly_transfer_count = Transaction.objects.filter(
        is_transfer=True,
        date__gte=month_start,
        date__lte=today,
    ).count()

    monthly_excluded_count = Transaction.objects.filter(
        is_excluded=True,
        date__gte=month_start,
        date__lte=today,
    ).count()

    monthly_spending_by_category = (
        Transaction.objects.filter(
            transaction_type=Transaction.TransactionType.DEBIT,
            is_excluded=False,
            is_transfer=False,
            date__gte=month_start,
            date__lte=today,
            category__isnull=False,
        )
        .values("category__name")
        .annotate(total=Coalesce(Sum("amount"), Decimal("0.00")))
        .order_by("-total")
    )

    context = {
        "account_count": Account.objects.count(),
        "category_count": Category.objects.count(),
        "transaction_count": Transaction.objects.count(),
        "recent_transactions": recent_transactions,
        "monthly_debit_total": monthly_debit_total,
        "monthly_credit_total": monthly_credit_total,
        "monthly_transfer_count": monthly_transfer_count,
        "monthly_excluded_count": monthly_excluded_count,
        "monthly_spending_by_category": monthly_spending_by_category,
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

    transactions_to_create = []
    imported_at = timezone.now()
    skipped_count = 0

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

        transactions_to_create.append(
            Transaction(
                account=account,
                category=None,
                date=row_date,
                amount=row_amount,
                description_raw=row_description,
                merchant_normalized="",
                transaction_type=row_type,
                source_file=uploaded_file_name,
                imported_at=imported_at,
                notes=f"Santander import ({row['bank_transaction_type']})",
                is_transfer=False,
                is_excluded=False,
            )
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

    transactions_to_create = []
    imported_at = timezone.now()
    skipped_count = 0

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

        transactions_to_create.append(
            Transaction(
                account=account,
                category=None,
                date=row_date,
                amount=row_amount,
                description_raw=row_description,
                merchant_normalized="",
                transaction_type=row_type,
                source_file=uploaded_file_name,
                imported_at=imported_at,
                notes=f"Lloyds import ({row['bank_transaction_type']})",
                is_transfer=False,
                is_excluded=False,
            )
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