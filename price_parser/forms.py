from django import forms

class ProductSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Поиск товара"}),
        label="Поиск"
    )
    shortlist = forms.BooleanField(required=False, label="Только шортлист")
