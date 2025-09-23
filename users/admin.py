from django.contrib import admin
from users.models import User

# Register your models here.



@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "phone", "country")
    search_fields = ("email", "phone", "country")
