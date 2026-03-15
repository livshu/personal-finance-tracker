from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.importers.santander import (
    SantanderStatementFormatError,
    parse_santander_statement,
)
from core.models import Account, Transaction


VALID_STATEMENT_HTML = b"""<!DOCTYPE html>
<html>
<body>
<table>
    <tr><td></td><td>Transactions</td></tr>
    <tr>
        <td></td>
        <td>Date</td>
        <td></td>
        <td>Description</td>
        <td></td>
        <td>Money in</td>
        <td>Money Out</td>
        <td>Balance</td>
    </tr>
    <tr>
        <td></td>
        <td>14/03/2026</td>
        <td></td>
        <td>TESCO STORES 5122 (VIA APPLE PAY), ON 13-03-2026</td>
        <td></td>
        <td></td>
        <td>&pound;8.35</td>
        <td>&pound;107.00</td>
    </tr>
    <tr>
        <td></td>
        <td>11/03/2026</td>
        <td></td>
        <td>FASTER PAYMENTS RECEIPT REF.Joint Account FROM D Clark</td>
        <td></td>
        <td>&pound;100.00</td>
        <td></td>
        <td>&pound;145.72</td>
    </tr>
</table>
</body>
</html>
"""


class SantanderImporterTests(SimpleTestCase):
    def make_uploaded_file(self, name="santander_statement.xls", content=None):
        return SimpleUploadedFile(
            name,
            content or VALID_STATEMENT_HTML,
            content_type="application/vnd.ms-excel",
        )

    def test_parse_santander_statement_with_valid_file(self):
        parsed_rows = parse_santander_statement(self.make_uploaded_file())

        self.assertEqual(len(parsed_rows), 2)

        self.assertEqual(str(parsed_rows[0]["date"]), "2026-03-14")
        self.assertEqual(
            parsed_rows[0]["description_raw"],
            "TESCO STORES 5122 (VIA APPLE PAY), ON 13-03-2026",
        )
        self.assertEqual(parsed_rows[0]["transaction_type"], "debit")
        self.assertEqual(str(parsed_rows[0]["amount"]), "8.35")
        self.assertEqual(parsed_rows[0]["bank_transaction_type"], "Money out")

        self.assertEqual(str(parsed_rows[1]["date"]), "2026-03-11")
        self.assertEqual(parsed_rows[1]["transaction_type"], "credit")
        self.assertEqual(str(parsed_rows[1]["amount"]), "100.00")
        self.assertEqual(parsed_rows[1]["bank_transaction_type"], "Money in")

    def test_parse_santander_statement_rejects_unexpected_structure(self):
        uploaded_file = self.make_uploaded_file(
            name="bad_statement.xls",
            content=b"<html><body><table><tr><td>Date</td><td>Amount</td></tr></table></body></html>",
        )

        with self.assertRaises(SantanderStatementFormatError):
            parse_santander_statement(uploaded_file)

    def test_parse_santander_statement_rejects_zero_amount(self):
        uploaded_file = self.make_uploaded_file(
            name="zero_amount.xls",
            content=b"""<html><body><table>
            <tr><td>Date</td><td>Description</td><td>Money in</td><td>Money Out</td><td>Balance</td></tr>
            <tr><td>14/03/2026</td><td>TESCO</td><td></td><td>&pound;0.00</td><td>&pound;100.00</td></tr>
            </table></body></html>""",
        )

        with self.assertRaises(SantanderStatementFormatError):
            parse_santander_statement(uploaded_file)


class SantanderImportFlowTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Santander Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="Santander",
            currency="GBP",
        )

    def make_uploaded_file(self, name="santander_statement.xls"):
        return SimpleUploadedFile(
            name,
            VALID_STATEMENT_HTML,
            content_type="application/vnd.ms-excel",
        )

    def test_import_santander_preview_shows_parsed_rows(self):
        response = self.client.post(
            reverse("import_santander_csv"),
            {
                "account": self.account.id,
                "statement_file": self.make_uploaded_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/santander_preview.html")
        self.assertEqual(len(response.context["parsed_rows"]), 2)
        self.assertEqual(response.context["preview_debit_count"], 1)
        self.assertEqual(response.context["preview_credit_count"], 1)
        self.assertEqual(response.context["preview_debit_total"], Decimal("8.35"))
        self.assertEqual(response.context["preview_credit_total"], Decimal("100.00"))

        preview_data = self.client.session["santander_import_preview"]
        self.assertEqual(preview_data["account_id"], self.account.id)
        self.assertEqual(preview_data["uploaded_file_name"], "santander_statement.xls")
        self.assertEqual(len(preview_data["parsed_rows"]), 2)

    def test_confirm_santander_import_creates_transactions_and_skips_duplicates(self):
        preview_response = self.client.post(
            reverse("import_santander_csv"),
            {
                "account": self.account.id,
                "statement_file": self.make_uploaded_file(),
            },
        )
        self.assertEqual(preview_response.status_code, 200)

        confirm_response = self.client.post(reverse("confirm_santander_import"))

        self.assertEqual(confirm_response.status_code, 200)
        self.assertTemplateUsed(confirm_response, "core/santander_import_success.html")
        self.assertEqual(confirm_response.context["imported_count"], 2)
        self.assertEqual(confirm_response.context["skipped_count"], 0)
        self.assertEqual(Transaction.objects.count(), 2)

        debit_transaction = Transaction.objects.get(
            description_raw="TESCO STORES 5122 (VIA APPLE PAY), ON 13-03-2026"
        )
        credit_transaction = Transaction.objects.get(
            description_raw="FASTER PAYMENTS RECEIPT REF.Joint Account FROM D Clark"
        )

        self.assertEqual(debit_transaction.account, self.account)
        self.assertEqual(debit_transaction.amount, Decimal("8.35"))
        self.assertEqual(debit_transaction.transaction_type, "debit")
        self.assertEqual(debit_transaction.source_file, "santander_statement.xls")
        self.assertEqual(debit_transaction.notes, "Santander import (Money out)")

        self.assertEqual(credit_transaction.amount, Decimal("100.00"))
        self.assertEqual(credit_transaction.transaction_type, "credit")

        second_preview_response = self.client.post(
            reverse("import_santander_csv"),
            {
                "account": self.account.id,
                "statement_file": self.make_uploaded_file(),
            },
        )
        self.assertEqual(second_preview_response.status_code, 200)

        second_confirm_response = self.client.post(reverse("confirm_santander_import"))

        self.assertEqual(second_confirm_response.status_code, 200)
        self.assertEqual(second_confirm_response.context["imported_count"], 0)
        self.assertEqual(second_confirm_response.context["skipped_count"], 2)
        self.assertEqual(Transaction.objects.count(), 2)
