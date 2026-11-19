from django import forms
from django.contrib.admin.helpers import ActionForm


class CancelacionActionForm(ActionForm):
    motivo = forms.CharField(
        required=False,
        max_length=500,
        label="Motivo de cancelación",
        widget=forms.TextInput(attrs={"size": 40}),
    )
