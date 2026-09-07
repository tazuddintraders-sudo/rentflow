from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import StyledAuthenticationForm


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    form_class = StyledAuthenticationForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("login")


@login_required
def profile(request):
    return render(request, "accounts/profile.html", {"page_title": "My Profile"})
