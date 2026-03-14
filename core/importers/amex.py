import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation


EXPECTED_HEADERS = [
    "Date",
    "Description",
    "Amount",
    "Extended Details",
    "Appears On Your Statement As",
    "Address",
    "Town/City",
    "Postcode",
    "Country",
    "Reference",
    "Category",
]


class AmexCSVFormatError(Exception):
    pass


def parse_amex_csv(uploaded_file):
    """
    Parse an Amex CSV export and return a list of cleaned rows.

    This does not write anything to the database.
    """
    decoded_lines = uploaded_file.read().decode("utf-8-sig").splitlines()
    reader = csv.DictReader(decoded_lines)

    actual_headers = reader.fieldnames
    if actual_headers != EXPECTED_HEADERS:
        raise AmexCSVFormatError(
            f"Unexpected headers. Expected {EXPECTED_HEADERS}, got {actual_headers}."
        )

    parsed_rows = []

    for row_number, row in enumerate(reader, start=2):
        date_raw = (row.get("Date") or "").strip()
        description_raw = (row.get("Description") or "").strip()
        amount_raw = (row.get("Amount") or "").strip()

        if not date_raw and not description_raw and not amount_raw:
            continue

        if not description_raw:
            raise AmexCSVFormatError(
                f"Row {row_number}: missing Description."
            )

        try:
            date = datetime.strptime(date_raw, "%d/%m/%Y").date()
        except ValueError as exc:
            raise AmexCSVFormatError(
                f"Row {row_number}: invalid date '{date_raw}'."
            ) from exc

        try:
            signed_amount = Decimal(amount_raw.replace(",", ""))
        except InvalidOperation as exc:
            raise AmexCSVFormatError(
                f"Row {row_number}: invalid amount '{amount_raw}'."
            ) from exc

        if signed_amount == 0:
            raise AmexCSVFormatError(
                f"Row {row_number}: amount cannot be zero."
            )

        if signed_amount < 0:
            transaction_type = "credit"
            amount = abs(signed_amount)
        else:
            transaction_type = "debit"
            amount = signed_amount

        parsed_rows.append(
            {
                "date": date,
                "description_raw": description_raw,
                "transaction_type": transaction_type,
                "amount": amount,
                "appears_on_statement_as": (
                    row.get("Appears On Your Statement As") or ""
                ).strip(),
                "reference": (row.get("Reference") or "").strip(),
                "category_label": (row.get("Category") or "").strip(),
            }
        )

    return parsed_rows