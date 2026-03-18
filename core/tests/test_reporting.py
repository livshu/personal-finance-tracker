from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
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
        self.non_santander_joint_account = Account.objects.create(
            name="Monzo Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="Monzo",
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

    def test_get_reporting_amount_keeps_non_santander_joint_accounts_at_full_value(self):
        transaction = Transaction.objects.create(
            account=self.non_santander_joint_account,
            date="2026-03-14",
            amount=Decimal("80.00"),
            description_raw="MONZO JOINT",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        reporting_amount = get_reporting_amount(transaction)

        self.assertEqual(reporting_amount, Decimal("80.00"))

    def test_get_reporting_amount_accepts_santander_institution_variants(self):
        santander_uk_joint_account = Account.objects.create(
            name="Santander UK Joint",
            account_type=Account.AccountType.CURRENT,
            owner_type=Account.OwnerType.JOINT,
            institution="  Santander UK  ",
            currency="GBP",
        )
        transaction = Transaction.objects.create(
            account=santander_uk_joint_account,
            date="2026-03-14",
            amount=Decimal("2100.00"),
            description_raw="RENT",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

        reporting_amount = get_reporting_amount(transaction)

        self.assertEqual(reporting_amount, Decimal("1050.00"))



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

    def test_home_kpi_tiles_link_to_transactions_drilldown(self):
        response = self.client.get("/")

        self.assertContains(
            response,
            f'{reverse("transactions_drilldown")}?month={date.today().strftime("%Y-%m")}&metric=debit',
        )
        self.assertContains(
            response,
            f'{reverse("transactions_drilldown")}?month={date.today().strftime("%Y-%m")}&metric=credit',
        )
        self.assertContains(
            response,
            f'{reverse("transactions_drilldown")}?month={date.today().strftime("%Y-%m")}&metric=transfer',
        )
        self.assertContains(
            response,
            f'{reverse("transactions_drilldown")}?month={date.today().strftime("%Y-%m")}&metric=excluded',
        )
        self.assertContains(
            response,
            f'{reverse("transactions_drilldown")}?month={date.today().strftime("%Y-%m")}&metric=uncategorized',
        )

    def test_home_recent_transactions_use_reporting_display_amounts(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        recent_transactions = response.context["recent_transactions"]
        joint_transaction = next(
            transaction
            for transaction in recent_transactions
            if transaction.description_raw == "SALARY JOINT"
        )

        self.assertEqual(joint_transaction.amount, Decimal("1000.00"))
        self.assertEqual(joint_transaction.display_amount, Decimal("500.00"))
        self.assertTrue(joint_transaction.has_reporting_adjustment)
        self.assertContains(response, "£500.00")
        self.assertContains(response, "Raw: £1000.00")


class TransactionsDrilldownTests(TestCase):
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
        self.groceries = Category.objects.create(name="Groceries", is_income=False)
        self.salary = Category.objects.create(name="Salary", is_income=True)
        self.selected_month = date.today().replace(day=1)
        self.outside_month = (
            date(self.selected_month.year - 1, 12, 15)
            if self.selected_month.month == 1
            else date(self.selected_month.year, self.selected_month.month - 1, 15)
        )

        self.debit_transaction = Transaction.objects.create(
            account=self.personal_account,
            date=self.selected_month.replace(day=20),
            amount=Decimal("25.00"),
            description_raw="MONTHLY DEBIT",
            merchant_normalized="",
            category=self.groceries,
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )
        self.credit_transaction = Transaction.objects.create(
            account=self.joint_account,
            date=self.selected_month.replace(day=18),
            amount=Decimal("1000.00"),
            description_raw="MONTHLY CREDIT",
            merchant_normalized="",
            category=self.salary,
            transaction_type=Transaction.TransactionType.CREDIT,
            is_transfer=False,
            is_excluded=False,
        )
        self.transfer_transaction = Transaction.objects.create(
            account=self.personal_account,
            date=self.selected_month.replace(day=16),
            amount=Decimal("15.00"),
            description_raw="MONTHLY TRANSFER",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=True,
            is_excluded=False,
        )
        self.excluded_transaction = Transaction.objects.create(
            account=self.personal_account,
            date=self.selected_month.replace(day=14),
            amount=Decimal("9.00"),
            description_raw="MONTHLY EXCLUDED",
            merchant_normalized="",
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=True,
        )
        self.uncategorized_transaction = Transaction.objects.create(
            account=self.personal_account,
            date=self.selected_month.replace(day=12),
            amount=Decimal("30.00"),
            description_raw="MONTHLY UNCATEGORIZED",
            merchant_normalized="",
            category=None,
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )
        Transaction.objects.create(
            account=self.personal_account,
            date=self.outside_month,
            amount=Decimal("99.00"),
            description_raw="OLD MONTH DEBIT",
            merchant_normalized="",
            category=self.groceries,
            transaction_type=Transaction.TransactionType.DEBIT,
            is_transfer=False,
            is_excluded=False,
        )

    def test_transactions_drilldown_filters_each_metric(self):
        metric_expectations = {
            "debit": [
                self.debit_transaction,
                self.transfer_transaction,
                self.uncategorized_transaction,
            ],
            "credit": [self.credit_transaction],
            "transfer": [self.transfer_transaction],
            "excluded": [self.excluded_transaction],
            "uncategorized": [self.uncategorized_transaction],
        }

        for metric, expected_transactions in metric_expectations.items():
            with self.subTest(metric=metric):
                response = self.client.get(
                    reverse("transactions_drilldown"),
                    {"month": self.selected_month.strftime("%Y-%m"), "metric": metric},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["transactions"]), expected_transactions)
                self.assertEqual(
                    response.context["transaction_count"],
                    len(expected_transactions),
                )

    def test_transactions_drilldown_uses_reporting_display_amounts(self):
        response = self.client.get(
            reverse("transactions_drilldown"),
            {"month": self.selected_month.strftime("%Y-%m"), "metric": "credit"},
        )

        self.assertEqual(response.status_code, 200)
        transaction = response.context["transactions"][0]

        self.assertEqual(transaction.amount, Decimal("1000.00"))
        self.assertEqual(transaction.display_amount, Decimal("500.00"))
        self.assertTrue(transaction.has_reporting_adjustment)
        self.assertContains(response, "£500.00")
        self.assertContains(response, "Raw: £1000.00")
