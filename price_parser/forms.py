# catalog/forms.py
from django import forms

class ProductSearchForm(forms.Form):
    product_names = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Один товар на строку"}),
        label="Названия товаров"
    )
