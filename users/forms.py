from django import forms
from django.contrib.auth.forms import UserCreationForm

from price_parser.forms import StyleFormMixin
from users.models import User

# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from users.models import User


class UserRegisterForm(UserCreationForm):
    """
    Наследуем стандартный UserCreationForm, но привязываем его к нашей модели User.
    Password поля (password1/password2) уже добавлены в родительский класс.
    """
    class Meta:
        model = User
        # указываем email — password1 и password2 добавит UserCreationForm автоматически
        fields = ("email",)

    def save(self, commit=True):
        # сохраняем пользователя вручную, хэшируем пароль корректно
        user = super().save(commit=False)
        user.is_active = False  # по умолчанию неактивный — ожидаем подтверждение по почте
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """
    Форма редактирования профиля — только безопасные поля.
    """
    class Meta:
        model = User
        fields = ["email", "phone", "avatar", "country"]


# class UserProfileForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = ["email", "phone", "avatar", "country"]
#
#
# class UserRegisterForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ("email", "password1", "password2")
