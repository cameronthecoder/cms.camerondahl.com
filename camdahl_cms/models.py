from django.db import models


class LoginLinkRequest(models.Model):
    """One row per sign-in link request, for rate limiting /login-link/.

    Stored in the database (not Django's per-process memory cache) so the
    limit holds across every gunicorn worker. The email and IP are stored as
    keyed hashes, never in plain text. Rows older than the rate-limit window
    are deleted as new requests come in.
    """

    id = models.BigAutoField(primary_key=True)
    email_hash = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "login link request"
