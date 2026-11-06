# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A headless Wagtail/Django CMS backing camerondahl.com. Content is authored in the Wagtail admin and consumed by a separate frontend over Wagtail's v3 API at `/api/v3/`; Django itself does not render most of the site as HTML (see "Headless architecture" below).

## Commands

```bash
# Activate the venv first (or prefix commands with ./venv/bin/)
source venv/bin/activate

python manage.py runserver          # dev server, http://127.0.0.1:8000
python manage.py migrate
python manage.py makemigrations
python manage.py test               # all tests
python manage.py test home          # single app
python manage.py test home.tests.HomeTests.test_homepage_is_renderable  # single test
python manage.py createsuperuser
python manage.py collectstatic
```

There is no configured linter/formatter (no ruff/black/flake8 config) and no `pytest.ini`/`pyproject.toml` — tests run via Django's own test runner (`manage.py test`).

## Settings architecture

Settings live in `camdahl_cms/settings/` as `base.py` (shared), `dev.py`, and `production.py` (each does `from .base import *`), not a single `settings.py`. Which one loads is controlled by the `DJANGO_SETTINGS_MODULE` env var, defaulting to `camdahl_cms.settings.dev` (set via `os.environ.setdefault(...)` in both `manage.py` and `wsgi.py`).

Both `manage.py` and `wsgi.py` call `load_dotenv()` (python-dotenv) pointed at a `.env` file in the project root before anything else. Real environment variables always take precedence over `.env` values (dotenv never overrides an already-set var) — this is what lets the same `.env` mechanism work for both local dev and production without special-casing either.

`dev.py` has safe fallbacks for everything (insecure fixed `SECRET_KEY`, `ALLOWED_HOSTS=*`, SQLite, console email) so it runs with zero configuration. `production.py` fails loudly at import time (raises immediately) if `SECRET_KEY`, `ALLOWED_HOSTS`, or `DATABASE_URL` aren't set — there is no insecure fallback path in production. `.env.example` documents every variable both files read.

`DATABASES` is built with `dj_database_url` from `DATABASE_URL` (Postgres in production), falling back to a local `db.sqlite3` when unset (dev default).

Both settings files also do `from .local import *` at the very end inside a `try`/`except ImportError` — `camdahl_cms/settings/local.py` is gitignored, for machine-local overrides that shouldn't be committed.

## Headless architecture

- The Wagtail admin is mounted at the site root (`/`), after the API/documents/static routes in `camdahl_cms/urls.py`. The admin ends in its own `^.*/$` catch-all, so Wagtail page serving (`wagtail_urls`, listed after it) is never reached — no page is rendered as HTML by Django. `wagtail_urls` is still included only so the `wagtail_serve` route name reverses (`Page.url`, v3 `meta.html_url`). `HomePage.serve()` additionally raises `Http404`.
- The API is Wagtail 8.1's v3 API (Django Ninja, `wagtail.api.v3`), mounted at `/api/v3/` with live OpenAPI docs at `/api/v3/docs/`. Wagtail and its contrib apps register `pages`, `images`, `documents`, `redirects`, `sites`, `schema`, `snippets` and `whoami` themselves. Anonymous requests get live, public content; writes (and snippets/sites reads) need an `Authorization: Bearer <token>` API token. There is no v2 API any more (`wagtail.api.v2` and DRF are not in `INSTALLED_APPS`).
- `camdahl_cms/api.py` adds the site-specific routers to Wagtail's shared `api` instance (they must be added before `api.urls` is accessed): `writings/` (live `BlogPage`s, newest first, full content) and `writings/<slug>/`, `about/` (the single `AboutPage`), and `preview/` (see "Previews" below). Response schemas come from Wagtail's registry (`registry.get(Model._meta.label).read_schema`), so they're generated from each model's `api_fields`.
- Custom `APIField` serializers (`blog/models.py`: `ImageFieldSerializer`, `AuthorSerializer`, `CategorySerializer`) subclass `wagtail.api.v3.fields.FieldSerializer`, not DRF; the return type hint of `to_representation()` (a `TypedDict`) becomes the OpenAPI schema.
- The admin's Settings → "API routes" page (`camdahl_cms/views.py`) lists routes from the v3 OpenAPI schema.

## Previews

`wagtail-headless-preview` is installed; every page model mixes in `HeadlessPreviewMixin`. Clicking Preview in the admin stores a `PagePreview` and (with `REDIRECT_ON_PREVIEW`) redirects the preview panel to `WAGTAIL_HEADLESS_PREVIEW["CLIENT_URLS"]["default"]` (env `HEADLESS_PREVIEW_CLIENT_URL`, default `https://camerondahl.com`) as `/?content_type=<app.model>&token=<signed token>`. The frontend must handle that query on its root route and fetch `/api/v3/preview/?content_type=...&token=...`, which returns the draft in the same shape as page detail. The signed token is the only credential, so that endpoint is unauthenticated. The frontend must also allow being framed by the admin's origin (CSP `frame-ancestors`).

## Snippets

`projects.Technology`/`projects.Project` and `blog.Author`/`blog.Category` are Wagtail snippets. v3 exposes them under `/api/v3/snippets/<app.Model>/`, but only to token-authenticated requests.

## Page tree / app structure

- `home.HomePage` is the root page type; its `subpage_types` are `blog.BlogIndexPage` and `about.AboutPage`.
- `blog.BlogIndexPage` (`max_count = 1`) is the parent for `blog.BlogPage` posts. Posts use a `StreamField` (`body`) with custom blocks (`SizedRichTextBlock`, `PulledQuote`, `CodeBlock`, `VideoBlock`, plus stock image/document/quote blocks) and a `reading_time` property computed from the StreamField's prose blocks at ~200 wpm.
- `blog.Author` and `blog.Category` are snippets referenced by `BlogPage`; `blog.Reference` is an `Orderable` inline model (citations) attached via `InlinePanel`.
- `about.AboutPage` (`max_count = 1`, no subpages) holds a single biography field.
- `projects` has no `Page` model — `Technology` and `Project` are standalone snippets linked by a M2M.

## Auth: magic-link login (no passwords in production)

Admin login uses `django-sesame` (URL-token based passwordless login) instead of, or alongside, passwords:

- `AUTHENTICATION_BACKENDS` in `base.py` includes both `ModelBackend` (password) and `sesame.backends.ModelBackend`, for dev convenience. `production.py` overrides this to **only** `sesame.backends.ModelBackend` — password authentication is fully disabled in production at the backend level, not just hidden in the UI.
- `SESAME_MAX_AGE` (15 min) and `SESAME_ONE_TIME = True` in `base.py` make links short-lived and single-use.
- `camdahl_cms/accounts.py` (`request_magic_link` view, POST-only) looks up a matching active staff user by email and sends them a sign-in link via `django.core.mail`, always returning the same response regardless of whether the email matched (prevents account enumeration). Mounted at `/login-link/` in `camdahl_cms/urls.py`.
- `camdahl_cms/templates/wagtailadmin/login.html` overrides Wagtail's built-in login template using Django's self-extending-template pattern (`{% extends "wagtailadmin/login.html" %}`, relying on `TEMPLATES["DIRS"]` being searched before app template dirs). It swaps the `furniture` block to show an inline email field instead of the password form, gated by the `magic_link_login_only` context variable (`MAGIC_LINK_LOGIN_ONLY` setting, exposed via `camdahl_cms/context_processors.py`) — `False` in dev (normal password form), `True` in production.

## Email

`EMAIL_*` settings are env-driven in both `dev.py` (console backend by default) and `production.py` (SMTP by default, falling back to console if `EMAIL_HOST` is unset so a deploy without email configured doesn't crash). `ADMINS` (`base.py`) feeds Django's built-in `AdminEmailHandler`, which emails unhandled 500s automatically once `DEBUG=False` — no custom logging config needed.

`camdahl_cms/email.py` defines `TrustedCAEmailBackend`, used automatically in production when `EMAIL_CA_CERT_FILE` is set. It trusts exactly one certificate file instead of the system CA store — needed for Proton Mail Bridge, which only listens on localhost and always presents a self-signed cert. Real certificate verification stays on; trust is just scoped to that one cert rather than disabled.

## Deployment

Target is a DigitalOcean droplet running alongside other services (not containerized) — `.env` sits on disk in the project root and is read by both `manage.py` and `wsgi.py` as described above. A `Dockerfile`/`.dockerignore` exist in the repo from an earlier Docker-based approach but are **not** the current deployment path; don't assume container-based deployment when making changes.
