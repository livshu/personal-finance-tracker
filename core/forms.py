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


class SantanderStatementUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        help_text="Choose the existing account this Santander statement export belongs to.",
    )
    statement_file = forms.FileField(
        help_text="Upload a Santander statement export file (.xls from Online Banking).",
    )

class AmexCSVUploadForm(forms.Form):
    account = forms.ModelChoiceField(
        queryset=Account.objects.all(),
        help_text="Choose the existing account this Amex CSV belongs to.",
    )
    csv_file = forms.FileField(
        help_text="Upload an Amex CSV export.",
    )
