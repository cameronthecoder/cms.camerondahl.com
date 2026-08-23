from urllib.parse import urlencode

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from sesame.utils import get_parameters


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField()


@require_POST
def request_magic_link(request):
    form = MagicLinkRequestForm(request.POST)
    if form.is_valid():
        next_url = request.POST.get("next", "")
        if not url_has_allowed_host_and_scheme(
            next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            next_url = reverse("wagtailadmin_home")

        User = get_user_model()
        user = User.objects.filter(
            email__iexact=form.cleaned_data["email"],
            is_staff=True,
            is_active=True,
        ).first()
        if user is not None:
            separator = "&" if "?" in next_url else "?"
            link_path = next_url + separator + urlencode(get_parameters(user))
            send_mail(
                subject="Your sign-in link",
                message=(
                    "Sign in here (expires in 15 minutes, one-time use):\n\n"
                    + request.build_absolute_uri(link_path)
                ),
                from_email=None,
                recipient_list=[user.email],
            )

    # Same response whether or not the email matched an account, so this
    # can't be used to enumerate staff accounts.
    messages.info(
        request,
        "If that email belongs to an admin account, a sign-in link is on its way. Check your inbox.",
    )
    return redirect("wagtailadmin_login")
