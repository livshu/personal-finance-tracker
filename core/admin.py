from django.contrib import admin

from .models import Account, Category, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "owner_type", "institution", "currency")
    search_fields = ("name", "institution")
    list_filter = ("account_type", "owner_type", "currency")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "is_income")
    search_fields = ("name",)
    list_filter = ("is_income",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "description_raw",
        "account",
        "category",
        "amount",
        "transaction_type",
        "is_transfer",
        "is_excluded",
    )
    search_fields = ("description_raw", "merchant_normalized", "source_file")
    list_filter = (
        "transaction_type",
        "is_transfer",
        "is_excluded",
        "account",
        "category",
    )
    date_hierarchy = "date"
