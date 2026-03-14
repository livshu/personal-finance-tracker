from django import forms

from core.models import Account


class LloydsCSVUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        help_text="Choose the existing account this Lloyds CSV belongs to.",
    )
    csv_file = forms.FileField(
        help_text="Upload a Lloyds current account CSV export.",
    )


class SantanderCSVUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        help_text="Choose the existing account this Santander CSV belongs to.",
    )
    csv_file = forms.FileField(
        help_text="Upload a Santander CSV export.",
    )