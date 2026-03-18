from django.test import SimpleTestCase

from core.transfer_rules import is_transfer_description


class TransferRuleTests(SimpleTestCase):
    def test_returns_false_for_blank_input(self):
        self.assertFalse(is_transfer_description(""))
        self.assertFalse(is_transfer_description("   "))

    def test_marks_person_name_transfers_as_transfer(self):
        self.assertTrue(is_transfer_description("Payment from Olivia Shuter"))
        self.assertTrue(is_transfer_description("Payment from O Shuter"))

    def test_marks_faster_payment_reimbursement_patterns_as_transfer(self):
        self.assertTrue(
            is_transfer_description(
                "FASTER PAYMENTS RECEIPT REF.RENT FROM D CLARK"
            )
        )
        self.assertTrue(
            is_transfer_description(
                "FASTER PAYMENTS RECEIPT REF.COUNCIL TAX FROM CLARK D"
            )
        )
        self.assertTrue(
            is_transfer_description(
                "FASTER PAYMENTS RECEIPT REF.WIFI FROM D CLARK"
            )
        )
        self.assertTrue(
            is_transfer_description(
                "FASTER PAYMENTS RECEIPT REF.Joint Account FROM D Clark"
            )
        )

    def test_does_not_mark_normal_merchants_as_transfer(self):
        self.assertFalse(is_transfer_description("MARSH PARSONS"))
        self.assertFalse(is_transfer_description("TESCO STORE 5122"))
        self.assertFalse(is_transfer_description("EDF UK CARD PAYMENTS"))