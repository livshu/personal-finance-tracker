import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation


EXPECTED_HEADERS = [
    "Date",
    "Type",
    "Merchant/Description",
    "Debit/Credit",
    "Balance",
]


class SantanderCSVFormatError(Exception):
    pass


def parse_santander_amount(raw_value):
    cleaned = (
        raw_value.strip()
        .replace("£", "")
        .replace(",", "")
        .replace("+", "")
        .strip()
    )

    try:
        signed_amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise SantanderCSVFormatError(
            f"Invalid amount value '{raw_value}'."
        ) from exc

    if signed_amount == 0:
        raise SantanderCSVFormatError("Amount cannot be zero.")

    if signed_amount < 0:
        transaction_type = "debit"
        amount = abs(signed_amount)
    else:
        transaction_type = "credit"
        amount = signed_amount

    return transaction_type, amount


def parse_santander_csv(uploaded_file):
    """
    Parse a Santander CSV export and return a list of cleaned rows.

    This does not write anything to the database.
    """
    decoded_text = uploaded_file.read().decode("cp1252")
    lines = decoded_text.splitlines()

    reader = csv.DictReader(lines, delimiter=";")
    actual_headers = reader.fieldnames

    if actual_headers is None:
        raise SantanderCSVFormatError("The uploaded file appears to be empty.")

    actual_headers = [header.strip() for header in actual_headers if header is not None]

    if actual_headers[:5] != EXPECTED_HEADERS:
        raise SantanderCSVFormatError(
            f"Unexpected headers. Expected {EXPECTED_HEADERS}, got {actual_headers}."
        )

    parsed_rows = []

    for row_number, row in enumerate(reader, start=2):
        date_raw = (row.get("Date") or "").strip()
        description_raw = (row.get("Merchant/Description") or "").strip()
        amount_raw = (row.get("Debit/Credit") or "").strip()
        bank_transaction_type = (row.get("Type") or "").strip()
        balance_raw = (row.get("Balance") or "").strip()

        if not date_raw and not description_raw and not amount_raw:
            continue

        if not description_raw:
            raise SantanderCSVFormatError(
                f"Row {row_number}: missing Merchant/Description."
            )

        try:
            date = datetime.strptime(date_raw, "%d/%m/%Y").date()
        except ValueError:
            continue
        transaction_type, amount = parse_santander_amount(amount_raw)

        parsed_rows.append(
            {
                "date": date,
                "description_raw": description_raw,
                "transaction_type": transaction_type,
                "amount": amount,
                "bank_transaction_type": bank_transaction_type,
                "balance": balance_raw,
            }
        )

    return parsed_rows