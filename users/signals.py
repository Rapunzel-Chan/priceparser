# users/signals.py
import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


@receiver(post_save, sender=User)
def set_default_avatar(sender, instance, created, **kwargs):
    if created and not instance.avatar:

        default_avatar_path = os.path.join(settings.BASE_DIR, "static", "img", "default-avatar.png")

        if os.path.exists(default_avatar_path):
            with open(default_avatar_path, "rb") as f:

                instance.avatar.save(f"user_{instance.id}_default.png", ContentFile(f.read()), save=True)
