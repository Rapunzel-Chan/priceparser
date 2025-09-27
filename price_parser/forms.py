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
        fields = ['name', 'platform', 'interval', 'manual', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-select'}),
            'interval': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например, 6h'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# from django import forms
# from .models import Product
#
# class ProductSelectForm(forms.Form):
#     products = forms.ModelMultipleChoiceField(
#         queryset=Product.objects.all(),
#         widget=forms.CheckboxSelectMultiple,
#         required=True
#     )


class StyleFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field, forms.BooleanField):
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"