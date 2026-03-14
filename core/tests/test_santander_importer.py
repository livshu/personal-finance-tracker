from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from core.importers.santander import (
    SantanderCSVFormatError,
    parse_santander_csv,
)


class SantanderImporterTests(SimpleTestCase):
    def test_parse_santander_csv_with_valid_file(self):
        csv_content = """Date;Type;Merchant/Description;Debit/Credit;Balance;
14/03/2026;DEB;TESCO;-54.23;£1200.00;
13/03/2026;CRD;SALARY;2500.00;£1254.23;
"""
        uploaded_file = SimpleUploadedFile(
            "santander.csv",
            csv_content.encode("cp1252"),
            content_type="text/csv",
        )

        parsed_rows = parse_santander_csv(uploaded_file)

        self.assertEqual(len(parsed_rows), 2)

        self.assertEqual(str(parsed_rows[0]["date"]), "2026-03-14")
        self.assertEqual(parsed_rows[0]["description_raw"], "TESCO")
        self.assertEqual(parsed_rows[0]["transaction_type"], "debit")
        self.assertEqual(str(parsed_rows[0]["amount"]), "54.23")

        self.assertEqual(str(parsed_rows[1]["date"]), "2026-03-13")
        self.assertEqual(parsed_rows[1]["description_raw"], "SALARY")
        self.assertEqual(parsed_rows[1]["transaction_type"], "credit")
        self.assertEqual(str(parsed_rows[1]["amount"]), "2500.00")

    def test_parse_santander_csv_rejects_unexpected_headers(self):
        csv_content = """Date;Description;Amount;
14/03/2026;TESCO;-54.23;
"""
        uploaded_file = SimpleUploadedFile(
            "bad_headers.csv",
            csv_content.encode("cp1252"),
            content_type="text/csv",
        )

        with self.assertRaises(SantanderCSVFormatError):
            parse_santander_csv(uploaded_file)

    def test_parse_santander_csv_rejects_zero_amount(self):
        csv_content = """Date;Type;Merchant/Description;Debit/Credit;Balance;
14/03/2026;DEB;TESCO;0.00;£1200.00;
"""
        uploaded_file = SimpleUploadedFile(
            "zero_amount.csv",
            csv_content.encode("cp1252"),
            content_type="text/csv",
        )

        with self.assertRaises(SantanderCSVFormatError):
            parse_santander_csv(uploaded_file)