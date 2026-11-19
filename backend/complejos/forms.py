from django import forms

from .models import Complejo, Cancha, Tarifa


class TarifaAdminForm(forms.ModelForm):
    complejo = forms.ModelChoiceField(
        queryset=Complejo.objects.all(),
        label="Complejo deportivo",
        empty_label="Seleccione un complejo",
    )

    class Meta:
        model = Tarifa
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # El usuario debe elegir primero un complejo.
        self.fields["cancha"].queryset = Cancha.objects.none()

        if self.is_bound:
            complejo_id = self.data.get("complejo")
        elif self.instance.pk:
            complejo_id = self.instance.cancha.complejo_id
            self.fields["complejo"].initial = complejo_id
        else:
            complejo_id = None

        if complejo_id and str(complejo_id).isdigit():
            self.fields["cancha"].queryset = Cancha.objects.filter(
                complejo_id=complejo_id
            ).order_by("nombre")

    def clean(self):
        datos = super().clean()
        complejo = datos.get("complejo")
        cancha = datos.get("cancha")

        if complejo and cancha and cancha.complejo_id != complejo.pk:
            raise forms.ValidationError(
                "La cancha no pertenece al complejo seleccionado."
            )

        return datos
