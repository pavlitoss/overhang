from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OrganizationForm, RegistrationForm
from .models import Membership, Organization


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            org = Organization.objects.create(
                name=form.cleaned_data["organization_name"],
                owner=user,
            )
            Membership.objects.create(user=user, organization=org, role=Membership.ROLE_OWNER)
            login(request, user)
            messages.success(request, f"Welcome to Overhang! Your workspace '{org.name}' is ready.")
            return redirect("home")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def org_settings(request):
    org = request.org
    memberships = org.memberships.select_related("user").order_by("joined_at")

    if request.method == "POST" and "update_name" in request.POST:
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization name updated.")
            return redirect("accounts:settings")
    else:
        form = OrganizationForm(instance=org)

    return render(request, "accounts/settings.html", {
        "form": form,
        "memberships": memberships,
        "is_owner": org.owner == request.user,
    })


@login_required
def remove_member(request, membership_id):
    org = request.org
    if org.owner != request.user:
        messages.error(request, "Only the owner can remove members.")
        return redirect("accounts:settings")

    membership = get_object_or_404(Membership, id=membership_id, organization=org)
    if membership.user == request.user:
        messages.error(request, "You cannot remove yourself.")
        return redirect("accounts:settings")

    membership.delete()
    messages.success(request, f"{membership.user.username} has been removed.")
    return redirect("accounts:settings")


@login_required
def add_member(request):
    org = request.org
    if org.owner != request.user:
        messages.error(request, "Only the owner can add members.")
        return redirect("accounts:settings")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f"No user found with username '{username}'.")
            return redirect("accounts:settings")

        _, created = Membership.objects.get_or_create(
            user=user,
            organization=org,
            defaults={"role": Membership.ROLE_MEMBER},
        )
        if created:
            messages.success(request, f"{username} added to your organization.")
        else:
            messages.info(request, f"{username} is already a member.")

    return redirect("accounts:settings")
