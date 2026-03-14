from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from core.importers.lloyds import LloydsCSVFormatError, parse_lloyds_csv


class LloydsImporterTests(SimpleTestCase):
    def test_parse_lloyds_csv_with_valid_file(self):
        csv_content = """Transaction Date,Transaction Type,Sort Code,Account Number,Transaction Description,Debit Amount,Credit Amount,Balance
01/03/2026,FPO,12-34-56,12345678,TEST PAYMENT,25.50,,1000.00
02/03/2026,BGC,12-34-56,12345678,SALARY,,2500.00,3500.00
"""
        uploaded_file = SimpleUploadedFile(
            "lloyds.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        parsed_rows = parse_lloyds_csv(uploaded_file)

        self.assertEqual(len(parsed_rows), 2)

        self.assertEqual(str(parsed_rows[0]["date"]), "2026-03-01")
        self.assertEqual(parsed_rows[0]["transaction_type"], "debit")
        self.assertEqual(str(parsed_rows[0]["amount"]), "25.50")
        self.assertEqual(parsed_rows[0]["description_raw"], "TEST PAYMENT")

        self.assertEqual(str(parsed_rows[1]["date"]), "2026-03-02")
        self.assertEqual(parsed_rows[1]["transaction_type"], "credit")
        self.assertEqual(str(parsed_rows[1]["amount"]), "2500.00")
        self.assertEqual(parsed_rows[1]["description_raw"], "SALARY")

    def test_parse_lloyds_csv_rejects_unexpected_headers(self):
        csv_content = """Date,Type,Description,Amount
01/03/2026,FPO,TEST PAYMENT,25.50
"""
        uploaded_file = SimpleUploadedFile(
            "bad_headers.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        with self.assertRaises(LloydsCSVFormatError):
            parse_lloyds_csv(uploaded_file)

    def test_parse_lloyds_csv_rejects_invalid_debit_credit_row(self):
        csv_content = """Transaction Date,Transaction Type,Sort Code,Account Number,Transaction Description,Debit Amount,Credit Amount,Balance
01/03/2026,FPO,12-34-56,12345678,INVALID ROW,25.50,10.00,1000.00
"""
        uploaded_file = SimpleUploadedFile(
            "invalid_row.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        with self.assertRaises(LloydsCSVFormatError):
            parse_lloyds_csv(uploaded_file)