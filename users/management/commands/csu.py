from django.conf import settings
from django.core.management import BaseCommand

from users.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            email="admin@example.com", defaults={"is_active": True, "is_staff": True, "is_superuser": True}
        )
        if created:
            user.set_password(settings.ADMIN_PASSWORD)
            user.save()
            self.stdout.write(self.style.SUCCESS("Superuser created"))
        else:
            self.stdout.write("Admin user already exists")
