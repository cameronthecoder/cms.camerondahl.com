from pathlib import Path

from django.views.debug import ExceptionReporter


class ConciseExceptionReporter(ExceptionReporter):
    """
    Trims Django's default plain-text error report — which dumps the full
    settings, sys.path, installed apps, and middleware into every email —
    down to what's actually useful for triaging a production error: what
    broke, where, who hit it, and the traceback.

    Only get_traceback_text() is overridden (via a custom text_template_path),
    which is what ADMINS error emails use. The in-browser DEBUG=True HTML
    debug page is untouched, since get_traceback_html() isn't overridden.

    See https://docs.djangoproject.com/en/5.2/howto/error-reporting/
    """

    @property
    def text_template_path(self):
        return (
            Path(__file__).resolve().parent
            / "templates"
            / "emails"
            / "error_report.txt"
        )
