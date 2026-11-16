import logging
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from sesame.utils import get_parameters

logger = logging.getLogger(__name__)


class MagicLinkRequestForm(forms.Form):
    email = forms.EmailField()


def _format_time(moment):
    # e.g. "Sun 8 Nov 2026, 14:32:05 UTC" (in TIME_ZONE, named explicitly)
    local = timezone.localtime(moment)
    return f"{local:%a} {local.day} {local:%b %Y, %H:%M:%S} {local.tzname()}"


def magic_link_email(link, now=None):
    """Subject and body for a sign-in email, stamped with when it was
    requested and when the link stops working."""
    now = now or timezone.now()
    max_age = settings.SESAME_MAX_AGE
    max_age = max_age if isinstance(max_age, timedelta) else timedelta(seconds=max_age)
    minutes = round(max_age.total_seconds() / 60)
    local_now = timezone.localtime(now)
    return {
        # The time in the subject stops mail clients threading every sign-in
        # email together, so the newest link is easy to find.
        "subject": f"Your sign-in link ({local_now:%H:%M} {local_now.tzname()})",
        "message": (
            f"Sign in here (one-time use, expires in {minutes} minutes):\n\n"
            f"{link}\n\n"
            f"Requested: {_format_time(now)}\n"
            f"Expires:   {_format_time(now + max_age)}\n\n"
            "If you didn't request this, you can ignore this email."
        ),
    }


def client_ip(request):
    """The visitor's IP. Behind nginx on the same machine, REMOTE_ADDR is
    loopback, so take the rightmost X-Forwarded-For entry: the one nginx
    itself appended, which the client can't forge. X-Forwarded-For is only
    trusted from loopback, never from a direct connection."""
    remote = request.META.get("REMOTE_ADDR", "")
    if remote in ("127.0.0.1", "::1"):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded.strip():
            return forwarded.split(",")[-1].strip()
        if real := request.META.get("HTTP_X_REAL_IP", "").strip():
            return real
    return remote


def allow_login_link(email, ip):
    """Record this request and say whether it's within the rate limits.

    Every request counts, whether or not the email matches an account, so
    the limit itself reveals nothing about which accounts exist.
    """
    from .models import LoginLinkRequest

    def digest(value):
        return salted_hmac("login-link-rate-limit", value.lower()).hexdigest()

    since = timezone.now() - timedelta(seconds=settings.LOGIN_LINK_WINDOW)
    LoginLinkRequest.objects.filter(created_at__lt=since).delete()
    email_hash, ip_hash = digest(email), digest(ip)
    recent = LoginLinkRequest.objects.filter(created_at__gte=since)
    allowed = (
        recent.filter(email_hash=email_hash).count() < settings.LOGIN_LINK_MAX_PER_EMAIL
        and recent.filter(ip_hash=ip_hash).count() < settings.LOGIN_LINK_MAX_PER_IP
    )
    LoginLinkRequest.objects.create(email_hash=email_hash, ip_hash=ip_hash)
    if not allowed:
        logger.warning("Sign-in link request rate-limited (ip=%s)", ip)
    return allowed


@require_POST
def request_magic_link(request):
    form = MagicLinkRequestForm(request.POST)
    if form.is_valid() and allow_login_link(form.cleaned_data["email"], client_ip(request)):
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
                **magic_link_email(request.build_absolute_uri(link_path)),
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
