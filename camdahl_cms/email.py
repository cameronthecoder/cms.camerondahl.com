import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.utils.functional import cached_property


class TrustedCAEmailBackend(SMTPEmailBackend):
    """
    SMTP backend that trusts one specific CA/certificate file (settings.
    EMAIL_CA_CERT_FILE) instead of the system's default trust store.

    For a self-signed server (e.g. Proton Mail Bridge, which only ever
    listens on localhost and can't obtain a CA-signed certificate), this
    verifies against that exact certificate rather than disabling
    verification altogether.
    """

    @cached_property
    def ssl_context(self):
        return ssl.create_default_context(cafile=settings.EMAIL_CA_CERT_FILE)
