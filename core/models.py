from django.db import models

# Create your models here.
from django.core.validators import MinValueValidator
from django.db import models
from django.core.exceptions import ValidationError


class Account(models.Model):
    class AccountType(models.TextChoices):
        CURRENT = "current", "Current Account"
        SAVINGS = "savings", "Savings Account"
        CREDIT_CARD = "credit_card", "Credit Card"
        CASH = "cash", "Cash"
        OTHER = "other", "Other"

    class OwnerType(models.TextChoices):
        PERSONAL = "personal", "Personal"
        JOINT = "joint", "Joint"

    name = models.CharField(max_length=100)
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
    )
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
    )
    institution = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=3, default="GBP")
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    is_income = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name



class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        DEBIT = "debit", "Debit"
        CREDIT = "credit", "Credit"

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    date = models.DateField()
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    description_raw = models.CharField(max_length=255)
    merchant_normalized = models.CharField(max_length=255, blank=True)
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
    )
    source_file = models.CharField(max_length=255, blank=True)
    imported_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_transfer = models.BooleanField(default=False)
    is_excluded = models.BooleanField(default=False)

    def clean(self):
        if self.category is None:
            return

        if (
            self.transaction_type == self.TransactionType.CREDIT
            and not self.category.is_income
        ):
            raise ValidationError(
                {"category": "Credit transactions should use an income category."}
            )

        if (
            self.transaction_type == self.TransactionType.DEBIT
            and self.category.is_income
        ):
            raise ValidationError(
                {"category": "Debit transactions should use a non-income category."}
            )

    def __str__(self):
        return f"{self.date} | {self.description_raw} | {self.amount}"
