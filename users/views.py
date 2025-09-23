from django.shortcuts import render

# Create your views here.
import secrets

# Create your views here.
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, UpdateView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated

from config.settings import EMAIL_HOST_USER
from users.forms import UserProfileForm, UserRegisterForm
from users.models import User
from users.serializers import UserSerializer, UserPrivateSerializer, UserPublicSerializer


@csrf_protect
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("users:logout_done")
    return redirect("price_parser:products_list")


class UserCreateView(CreateView):
    model = User
    form_class = UserRegisterForm
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        token = secrets.token_hex(16)
        user.token = token
        user.save()
        host = self.request.get_host()
        url = f"http://{host}/users/email-confirm/{token}/"
        send_mail(
            subject="Подтверждение почты",
            message=f"Доброго времени суток! Перейдите по ссылке для подтверждения почты {url}",
            from_email=EMAIL_HOST_USER,
            recipient_list=[user.email],
        )

        # return super().form_valid(form)
        return render(self.request, "users/email_verification_notice.html")


def email_verification(request, token):
    user = get_object_or_404(User, token=token)
    user.is_active = True
    user.save()
    return redirect(reverse("users:login"))


class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = "users/profile.html"

    def get_object(self):
        return self.request.user


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = "users/profile_edit.html"
    success_url = reverse_lazy("users:profile_edit")

    def get_object(self):
        return self.request.user

class UserCreateAPIView(CreateAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = [
        AllowAny,
    ]

    def perform_create(self, serializer):
        user = serializer.save(is_active=True)
        user.set_password(user.password)
        user.save()


class UserProfileAPIView(RetrieveUpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user.pk == self.get_object().pk:
            return UserPrivateSerializer
        return UserPublicSerializer

    def get_queryset(self):
        return User.objects.all()