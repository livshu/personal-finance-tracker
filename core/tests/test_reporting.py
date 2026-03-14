from decimal import Decimal
from datetime import date
from django.test import TestCase
from core.models import Account, Category, Transaction
from core.reporting import get_reporting_amount


class ReportingAmountTests(TestCase):
    def setUp(self):
        self.personal_account = Account.objects.create(
            name="Lloyds Personal",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.PERSONAL,
            institution="Lloyds",
            currency="GBP",
        )
        self.joint_account = Account.objects.create(
            name="Santander Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="Santander",
            currency="GBP",
        )

    def test_get_reporting_amount_returns_full_amount_for_personal_account(self):
        transaction = Transaction.objects.create(
            account=self.personal_account,
            date="2026-03-14",
            amount=Decimal("80.00"),
            description_raw="TESCO",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        reporting_amount = get_reporting_amount(transaction)

        self.assertEqual(reporting_amount, Decimal("80.00"))

    def test_get_reporting_amount_returns_half_amount_for_joint_account(self):
        transaction = Transaction.objects.create(
            account=self.joint_account,
            date="2026-03-14",
            amount=Decimal("80.00"),
            description_raw="TESCO",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        reporting_amount = get_reporting_amount(transaction)

        self.assertEqual(reporting_amount, Decimal("40.00"))

    def test_get_reporting_amount_halves_joint_credit_transactions_too(self):
        transaction = Transaction.objects.create(
            account=self.joint_account,
            date="2026-03-14",
            amount=Decimal("1000.00"),
            description_raw="SALARY",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.CREDIT,
            is_transfer=False,
            is_excluded=False,
        )

        reporting_amount = get_reporting_amount(transaction)

        self.assertEqual(reporting_amount, Decimal("500.00"))



class HomeReportingTests(TestCase):
    def setUp(self):
        self.personal_account = Account.objects.create(
            name="Lloyds Personal",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.PERSONAL,
            institution="Lloyds",
            currency="GBP",
        )
        self.joint_account = Account.objects.create(
            name="Santander Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="Santander",
            currency="GBP",
        )

        self.groceries = Category.objects.create(
            name="Groceries",
            is_income=False,
        )

        today = date.today().replace(day=14)

        Transaction.objects.create(
            account=self.personal_account,
            date=today,
            amount=Decimal("20.00"),
            description_raw="TESCO PERSONAL",
            merchant_normalized="",
            category=self.groceries,
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        Transaction.objects.create(
            account=self.joint_account,
            date=today,
            amount=Decimal("80.00"),
            description_raw="TESCO JOINT",
            merchant_normalized="",
            category=self.groceries,
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        Transaction.objects.create(
            account=self.joint_account,
            date=today,
            amount=Decimal("1000.00"),
            description_raw="SALARY JOINT",
            merchant_normalized="",
            category=None,
            transaction_type=Transaction.TransactionType.CREDIT,
            is_transfer=False,
            is_excluded=False,
        )

    def test_home_uses_reporting_amounts_for_monthly_summary_and_category_totals(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["monthly_debit_total"], Decimal("60.00"))
        self.assertEqual(response.context["monthly_credit_total"], Decimal("500.00"))
        self.assertEqual(response.context["monthly_net_amount"], Decimal("440.00"))

        spending_by_category = response.context["monthly_spending_by_category"]
        self.assertEqual(len(spending_by_category), 1)
        self.assertEqual(spending_by_category[0]["category__name"], "Groceries")
        self.assertEqual(spending_by_category[0]["total"], Decimal("60.00"))

    def test_home_accepts_date_picker_month_values(self):
        today = date.today().replace(day=1)

        response = self.client.get("/", {"month": today.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_month"], today.strftime("%Y-%m"))
        self.assertEqual(response.context["selected_month_date"], today.isoformat())
