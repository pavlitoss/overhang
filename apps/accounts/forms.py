from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Organization


class RegistrationForm(UserCreationForm):
    organization_name = forms.CharField(
        max_length=100,
        label="Business name",
        help_text="The name of your 3D printing business.",
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "organization_name")


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ("name",)
