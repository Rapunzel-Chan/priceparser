from rest_framework import serializers

from users.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Полный сериализатор для создания пользователя через API.
    Пароль — write_only; при создании корректно вызываем set_password.
    """

    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("id", "email", "password", "phone", "avatar", "country", "is_active")
        read_only_fields = ("is_active",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "avatar", "country"]


class UserPrivateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]
