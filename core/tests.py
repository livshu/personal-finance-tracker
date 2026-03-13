from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Account, Category, Transaction


class AccountModelTests(TestCase):
    def test_account_str_returns_name(self):
        account = Account.objects.create(
            name="NatWest Current",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.PERSONAL,
            institution="NatWest",
            currency="GBP",
        )

        self.assertEqual(str(account), "NatWest Current")


class CategoryModelTests(TestCase):
    def test_category_str_returns_name(self):
        category = Category.objects.create(
            name="Groceries",
            is_income=False,
        )

        self.assertEqual(str(category), "Groceries")


class TransactionModelTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create(
            name="Santander Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="Santander",
            currency="GBP",
        )
        self.category = Category.objects.create(
            name="Rent",
            is_income=False,
        )

    def test_transaction_can_be_created_with_account_and_category(self):
        transaction = Transaction.objects.create(
            account=self.account,
            category=self.category,
            date="2026-03-13",
            amount=Decimal("1050.00"),
            description_raw="RENT PAYMENT",
            merchant_normalized="Landlord",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        self.assertEqual(transaction.account, self.account)
        self.assertEqual(transaction.category, self.category)
        self.assertEqual(transaction.amount, Decimal("1050.00"))
        self.assertEqual(transaction.transaction_type, Transaction.TransactionType.DEBIT)

    def test_transaction_str_contains_date_description_and_amount(self):
        transaction = Transaction.objects.create(
            account=self.account,
            category=self.category,
            date="2026-03-13",
            amount=Decimal("54.23"),
            description_raw="TESCO STORES",
            merchant_normalized="Tesco",
            transaction_type=Transaction.TransactionType.DEBIT,
        )

        self.assertIn("2026-03-13", str(transaction))
        self.assertIn("TESCO STORES", str(transaction))
        self.assertIn("54.23", str(transaction))

    def test_transaction_amount_must_be_positive(self):
        transaction = Transaction(
            account=self.account,
            category=self.category,
            date="2026-03-13",
            amount=Decimal("0.00"),
            description_raw="INVALID TEST",
            merchant_normalized="Invalid",
            transaction_type=Transaction.TransactionType.DEBIT,
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_credit_transaction_cannot_use_non_income_category(self):
        transaction = Transaction(
            account=self.account,
            category=self.category,  # Rent is not an income category
            date="2026-03-13",
            amount=Decimal("100.00"),
            description_raw="INVALID CREDIT TEST",
            merchant_normalized="Invalid",
            transaction_type=Transaction.TransactionType.CREDIT,
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()

    def test_debit_transaction_cannot_use_income_category(self):
        income_category = Category.objects.create(
            name="Salary",
            is_income=True,
        )

        transaction = Transaction(
            account=self.account,
            category=income_category,
            date="2026-03-13",
            amount=Decimal("100.00"),
            description_raw="INVALID DEBIT TEST",
            merchant_normalized="Invalid",
            transaction_type=Transaction.TransactionType.DEBIT,
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()
