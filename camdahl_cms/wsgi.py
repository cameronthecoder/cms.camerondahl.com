"""
WSGI config for camdahl_cms project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Loads variables from .env into the environment if the file exists (local
# dev). In production, real environment variables set by the host take
# precedence and this becomes a no-op.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "camdahl_cms.settings.dev")

application = get_wsgi_application()
