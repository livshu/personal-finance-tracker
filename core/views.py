from django.db.models import Sum
from core.forms import LloydsCSVUploadForm
from .models import Account, Category, Transaction
from core.importers.lloyds import LloydsCSVFormatError, parse_lloyds_csv
from django.shortcuts import redirect, render
from django.utils import timezone
from decimal import Decimal

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

                return render(
                    request,
                    "core/lloyds_preview.html",
                    {
                        "account": account,
                        "uploaded_file_name": csv_file.name,
                        "parsed_rows": parsed_rows,
                    },
                )

    return render(request, "core/import_lloyds.html", {"form": form})

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

    for row in parsed_rows:
        transactions_to_create.append(
            Transaction(
                account=account,
                category=None,
                date=row["date"],
                amount=Decimal(row["amount"]),
                description_raw=row["description_raw"],
                merchant_normalized="",
                transaction_type=row["transaction_type"],
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
            "uploaded_file_name": uploaded_file_name,
        },
    )