from django import forms


class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Поиск товара"}),
        label="Поиск"
    )
    shortlist = forms.BooleanField(required=False, label="Только шортлист")


from django import forms
from .models import ParserSchedule

class ParserScheduleForm(forms.ModelForm):
    class Meta:
        model = ParserSchedule
        fields = ['name', 'platform', 'interval', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'interval': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например, 6h'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
