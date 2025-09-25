from django.contrib import admin
from users.models import User

# Register your models here.



# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ("id", "email", "phone", "country")
#     search_fields = ("email", "phone", "country")

# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from users.models import User
from users.forms import UserRegisterForm


class UserAdminChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class UserAdmin(BaseUserAdmin):
    """
    Админ для кастомного User.
    Исправлено list_display — заменяем 'town' на 'country'.
    """
    add_form = UserRegisterForm
    form = UserAdminChangeForm
    model = User

    list_display = ("id", "email", "phone", "country", "is_active", "is_staff")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Личная информация", {"fields": ("phone", "avatar", "country")}),
        ("Права", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )


admin.site.register(User, UserAdmin)
