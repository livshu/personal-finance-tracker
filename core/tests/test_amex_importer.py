from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.importers.amex import AmexCSVFormatError, parse_amex_csv
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from core.models import Account, Transaction

class AmexImporterTests(SimpleTestCase):
    def test_parse_amex_csv_with_valid_file(self):
        csv_content = """Date,Description,Amount,Extended Details,Appears On Your Statement As,Address,Town/City,Postcode,Country,Reference,Category
13/03/2026,TESCO STORE 5122 5122TE LONDON,1.50,,TESCO STORE 5122,123 HIGH STREET,LONDON,SW1A 1AA,UNITED KINGDOM,ABC123,General Purchases-Groceries
12/03/2026,REFUND AMAZON,-5.99,,AMAZON,1 AMAZON WAY,LONDON,EC1A 1AA,UNITED KINGDOM,REF999,Refunds
"""
        uploaded_file = SimpleUploadedFile(
            "amex.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        parsed_rows = parse_amex_csv(uploaded_file)

        self.assertEqual(len(parsed_rows), 2)

        self.assertEqual(str(parsed_rows[0]["date"]), "2026-03-13")
        self.assertEqual(
            parsed_rows[0]["description_raw"],
            "TESCO STORE 5122 5122TE LONDON",
        )
        self.assertEqual(parsed_rows[0]["transaction_type"], "debit")
        self.assertEqual(str(parsed_rows[0]["amount"]), "1.50")
        self.assertEqual(
            parsed_rows[0]["appears_on_statement_as"],
            "TESCO STORE 5122",
        )
        self.assertEqual(parsed_rows[0]["reference"], "ABC123")
        self.assertEqual(
            parsed_rows[0]["category_label"],
            "General Purchases-Groceries",
        )

        self.assertEqual(str(parsed_rows[1]["date"]), "2026-03-12")
        self.assertEqual(parsed_rows[1]["transaction_type"], "credit")
        self.assertEqual(str(parsed_rows[1]["amount"]), "5.99")

    def test_parse_amex_csv_rejects_unexpected_headers(self):
        csv_content = """Date,Description,Amount,Category
13/03/2026,TESCO,1.50,Groceries
"""
        uploaded_file = SimpleUploadedFile(
            "bad_headers.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        with self.assertRaises(AmexCSVFormatError):
            parse_amex_csv(uploaded_file)

    def test_parse_amex_csv_rejects_zero_amount(self):
        csv_content = """Date,Description,Amount,Extended Details,Appears On Your Statement As,Address,Town/City,Postcode,Country,Reference,Category
13/03/2026,TESCO STORE 5122 5122TE LONDON,0.00,,TESCO STORE 5122,123 HIGH STREET,LONDON,SW1A 1AA,UNITED KINGDOM,ABC123,General Purchases-Groceries
"""
        uploaded_file = SimpleUploadedFile(
            "zero_amount.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        with self.assertRaises(AmexCSVFormatError):
            parse_amex_csv(uploaded_file)

class AmexImportFlowTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Amex",
            account_type=Account.AccountType.CREDIT_CARD,
            owner_type=Account.OwnerType.PERSONAL,
            institution="American Express",
            currency="GBP",
        )

        self.csv_content = """Date,Description,Amount,Extended Details,Appears On Your Statement As,Address,Town/City,Postcode,Country,Reference,Category
13/03/2026,TESCO STORE 5122 5122TE LONDON,1.50,,TESCO STORE 5122,123 HIGH STREET,LONDON,SW1A 1AA,UNITED KINGDOM,ABC123,General Purchases-Groceries
12/03/2026,REFUND AMAZON,-5.99,,AMAZON,1 AMAZON WAY,LONDON,EC1A 1AA,UNITED KINGDOM,REF999,Refunds
"""

    def make_uploaded_file(self):
        return SimpleUploadedFile(
            "amex.csv",
            self.csv_content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_import_amex_csv_preview_shows_new_rows(self):
        response = self.client.post(
            reverse("import_amex_csv"),
            {
                "account": self.account.id,
                "csv_file": self.make_uploaded_file(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/amex_preview.html")
        self.assertEqual(response.context["new_row_count"], 2)
        self.assertEqual(response.context["duplicate_count"], 0)
        self.assertEqual(len(response.context["parsed_rows"]), 2)

        preview_data = self.client.session["amex_import_preview"]
        self.assertEqual(preview_data["account_id"], self.account.id)
        self.assertEqual(preview_data["uploaded_file_name"], "amex.csv")
        self.assertEqual(len(preview_data["parsed_rows"]), 2)

    def test_confirm_amex_import_creates_transactions_and_skips_duplicates(self):
        preview_response = self.client.post(
            reverse("import_amex_csv"),
            {
                "account": self.account.id,
                "csv_file": self.make_uploaded_file(),
            },
        )
        self.assertEqual(preview_response.status_code, 200)

        confirm_response = self.client.post(reverse("confirm_amex_import"))

        self.assertEqual(confirm_response.status_code, 200)
        self.assertTemplateUsed(confirm_response, "core/amex_import_success.html")
        self.assertEqual(confirm_response.context["imported_count"], 2)
        self.assertEqual(confirm_response.context["skipped_count"], 0)
        self.assertEqual(Transaction.objects.count(), 2)

        first_transaction = Transaction.objects.order_by("date", "id").first()
        self.assertEqual(first_transaction.account, self.account)
        self.assertIn(first_transaction.transaction_type, ["debit", "credit"])
        self.assertEqual(first_transaction.source_file, "amex.csv")
        self.assertEqual(first_transaction.notes, "Amex import")

        second_preview_response = self.client.post(
            reverse("import_amex_csv"),
            {
                "account": self.account.id,
                "csv_file": self.make_uploaded_file(),
            },
        )
        self.assertEqual(second_preview_response.status_code, 200)
        self.assertEqual(second_preview_response.context["new_row_count"], 0)
        self.assertEqual(second_preview_response.context["duplicate_count"], 2)

        second_confirm_response = self.client.post(reverse("confirm_amex_import"))

        self.assertEqual(second_confirm_response.status_code, 200)
        self.assertEqual(second_confirm_response.context["imported_count"], 0)
        self.assertEqual(second_confirm_response.context["skipped_count"], 2)
        self.assertEqual(Transaction.objects.count(), 2)