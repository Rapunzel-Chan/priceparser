from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


# Create your models here.
class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name="Email")
    phone = PhoneNumberField(blank=True, verbose_name="Телефон", help_text="Введите номер телефона")
    avatar = models.ImageField(
        upload_to="users/avatars/", verbose_name="Аватар", blank=True, null=True, help_text="Загрузите свой аватар"
    )
    country = models.CharField(max_length=50, verbose_name="Страна", blank=True, null=True, help_text="Введите страну")

    token = models.CharField(max_length=100, verbose_name="Токен", blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.email
