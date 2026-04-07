from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("settings/", views.org_settings, name="settings"),
    path("settings/members/add/", views.add_member, name="add_member"),
    path("settings/members/<int:membership_id>/remove/", views.remove_member, name="remove_member"),
]
