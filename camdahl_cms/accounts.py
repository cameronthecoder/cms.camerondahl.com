from django import forms
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import render, reverse
from django.views.decorators.http import require_http_methods

from sesame.utils import get_query_string


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField(label="Email")


@require_http_methods(["GET", "POST"])
def request_magic_link(request):
    sent = False
    if request.method == "POST":
        form = MagicLinkRequestForm(request.POST)
        if form.is_valid():
            User = get_user_model()
            user = User.objects.filter(
                email__iexact=form.cleaned_data["email"],
                is_staff=True,
                is_active=True,
            ).first()
            if user is not None:
                link_path = reverse("wagtailadmin_home") + get_query_string(user)
                send_mail(
                    subject="Your sign-in link",
                    message=(
                        "Sign in here (expires in 15 minutes, one-time use):\n\n"
                        + request.build_absolute_uri(link_path)
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                )
            # Same response whether or not the email matched an account, so
            # this can't be used to enumerate staff accounts.
            sent = True
            form = MagicLinkRequestForm()
    else:
        form = MagicLinkRequestForm()

    return render(request, "account/login_link.html", {"form": form, "sent": sent})
