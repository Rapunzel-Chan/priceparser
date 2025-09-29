# users/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
import os
from django.conf import settings

User = get_user_model()


@receiver(post_save, sender=User)
def set_default_avatar(sender, instance, created, **kwargs):
    if created and not instance.avatar:
        # Путь к дефолтному аватару в статике
        default_avatar_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'default-avatar.png')

        # Проверяем, существует ли файл
        if os.path.exists(default_avatar_path):
            with open(default_avatar_path, 'rb') as f:
                # Сохраняем копию дефолтного аватара для пользователя
                instance.avatar.save(
                    f'user_{instance.id}_default.png',
                    ContentFile(f.read()),
                    save=True
                )