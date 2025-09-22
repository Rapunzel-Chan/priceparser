from django import forms
from django.contrib.auth.forms import UserCreationForm

from price_parser.forms import StyleFormMixin
from users.models import User


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "phone", "avatar", "country"]


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "password1", "password2")
