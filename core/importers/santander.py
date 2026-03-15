from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser


EXPECTED_HEADERS = ["date", "description", "money in", "money out", "balance"]


class SantanderStatementFormatError(Exception):
    pass


class SantanderStatementTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.current_row = []
        self.current_cell = []
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []
        elif tag == "br" and self.in_cell:
            self.current_cell.append(" ")

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append(_clean_cell_text("".join(self.current_cell)))
            self.current_cell = []
            self.in_cell = False
        elif tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = []


def _clean_cell_text(value):
    return " ".join(value.replace("\xa0", " ").split())


def _find_header_positions(rows):
    for row_index, row in enumerate(rows):
        normalized_row = [_clean_cell_text(cell).lower() for cell in row]
        positions = []
        search_start = 0

        for header in EXPECTED_HEADERS:
            try:
                position = normalized_row.index(header, search_start)
            except ValueError:
                positions = []
                break

            positions.append(position)
            search_start = position + 1

        if positions:
            return row_index, positions

    raise SantanderStatementFormatError(
        "Could not find a Santander transactions header row with Date, Description, Money in, Money out, and Balance columns."
    )


def _parse_amount(raw_value, row_number, column_name):
    cleaned = (
        raw_value.replace("£", "")
        .replace(",", "")
        .replace("+", "")
        .strip()
    )

    if not cleaned:
        return None

    try:
        amount = Decimal(cleaned)
    except InvalidOperation as exc:
        raise SantanderStatementFormatError(
            f"Row {row_number}: invalid {column_name} amount '{raw_value}'."
        ) from exc

    if amount <= 0:
        raise SantanderStatementFormatError(
            f"Row {row_number}: {column_name} amount must be greater than zero."
        )

    return amount


def parse_santander_statement(uploaded_file):
    """
    Parse a Santander statement export saved as an .xls HTML table.

    Returns a list of normalized parsed rows for the shared import flow.
    """
    file_bytes = uploaded_file.read()

    if not file_bytes:
        raise SantanderStatementFormatError("The uploaded file appears to be empty.")

    decoded_text = file_bytes.decode("cp1252", errors="replace")
    parser = SantanderStatementTableParser()
    parser.feed(decoded_text)

    if not parser.rows:
        raise SantanderStatementFormatError(
            "The uploaded file does not contain a readable Santander transactions table."
        )

    header_row_index, header_positions = _find_header_positions(parser.rows)
    parsed_rows = []

    for row in parser.rows[header_row_index + 1:]:
        if max(header_positions) >= len(row):
            continue

        date_raw = row[header_positions[0]]
        description_raw = row[header_positions[1]]
        money_in_raw = row[header_positions[2]]
        money_out_raw = row[header_positions[3]]

        if not any([date_raw, description_raw, money_in_raw, money_out_raw]):
            continue

        if not date_raw or not description_raw:
            raise SantanderStatementFormatError(
                "Found a Santander transaction row with missing date or description."
            )

        try:
            transaction_date = datetime.strptime(date_raw, "%d/%m/%Y").date()
        except ValueError as exc:
            raise SantanderStatementFormatError(
                f"Invalid transaction date '{date_raw}' in Santander statement export."
            ) from exc

        money_in_amount = _parse_amount(
            money_in_raw,
            transaction_date.strftime("%d/%m/%Y"),
            "Money in",
        )
        money_out_amount = _parse_amount(
            money_out_raw,
            transaction_date.strftime("%d/%m/%Y"),
            "Money out",
        )

        if money_in_amount and money_out_amount:
            raise SantanderStatementFormatError(
                f"Row {date_raw}: both Money in and Money out have values."
            )

        if not money_in_amount and not money_out_amount:
            continue

        if money_out_amount:
            transaction_type = "debit"
            amount = money_out_amount
            bank_transaction_type = "Money out"
        else:
            transaction_type = "credit"
            amount = money_in_amount
            bank_transaction_type = "Money in"

        parsed_rows.append(
            {
                "date": transaction_date,
                "description_raw": description_raw,
                "transaction_type": transaction_type,
                "amount": amount,
                "bank_transaction_type": bank_transaction_type,
            }
        )

    if not parsed_rows:
        raise SantanderStatementFormatError(
            "No transaction rows were found in the Santander statement export."
        )

    return parsed_rows
