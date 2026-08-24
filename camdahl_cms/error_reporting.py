from pathlib import Path

from django.views.debug import ExceptionReporter

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates" / "emails"


class ConciseExceptionReporter(ExceptionReporter):
    """
    Custom error report used for ADMINS emails on unhandled exceptions —
    a trimmed-down, styled report instead of Django's default (which dumps
    the full settings, sys.path, installed apps, and middleware into every
    email).

    Only applies when is_email=True. The in-browser DEBUG=True debug page
    still uses Django's normal rich, interactive templates.

    See https://docs.djangoproject.com/en/5.2/howto/error-reporting/
    """

    @property
    def text_template_path(self):
        if self.is_email:
            return TEMPLATES_DIR / "error_report.txt"
        return super().text_template_path

    @property
    def html_template_path(self):
        if self.is_email:
            return TEMPLATES_DIR / "error_report.html"
        return super().html_template_path
