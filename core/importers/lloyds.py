import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation


EXPECTED_HEADERS = [
    "Transaction Date",
    "Transaction Type",
    "Sort Code",
    "Account Number",
    "Transaction Description",
    "Debit Amount",
    "Credit Amount",
    "Balance",
]


class LloydsCSVFormatError(Exception):
    pass


def parse_lloyds_csv(uploaded_file):
    """
    Parse a Lloyds current account CSV file and return a list of cleaned rows.

    This function does not write anything to the database.
    It only validates and normalises the CSV content.
    """
    decoded_lines = uploaded_file.read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded_lines)

    actual_headers = reader.fieldnames
    if actual_headers != EXPECTED_HEADERS:
        raise LloydsCSVFormatError(
            f"Unexpected headers. Expected {EXPECTED_HEADERS}, got {actual_headers}."
        )

    parsed_rows = []

    for row_number, row in enumerate(reader, start=2):
        debit_raw = (row.get("Debit Amount") or "").strip()
        credit_raw = (row.get("Credit Amount") or "").strip()

        if bool(debit_raw) == bool(credit_raw):
            raise LloydsCSVFormatError(
                f"Row {row_number}: expected exactly one of Debit Amount or Credit Amount."
            )

        if debit_raw:
            transaction_type = "debit"
            amount_raw = debit_raw
        else:
            transaction_type = "credit"
            amount_raw = credit_raw

        try:
            amount = Decimal(amount_raw)
        except InvalidOperation as exc:
            raise LloydsCSVFormatError(
                f"Row {row_number}: invalid amount '{amount_raw}'."
            ) from exc

        try:
            date = datetime.strptime(
                row["Transaction Date"].strip(), "%d/%m/%Y"
            ).date()
        except ValueError as exc:
            raise LloydsCSVFormatError(
                f"Row {row_number}: invalid date '{row['Transaction Date']}'."
            ) from exc

        parsed_rows.append(
            {
                "date": date,
                "description_raw": row["Transaction Description"].strip(),
                "transaction_type": transaction_type,
                "amount": amount,
                "bank_transaction_type": row["Transaction Type"].strip(),
                "source_sort_code": row["Sort Code"].strip(),
                "source_account_number": str(row["Account Number"]).strip(),
                "balance": row["Balance"],
            }
        )

    return parsed_rows