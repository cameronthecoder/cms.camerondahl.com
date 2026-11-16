import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from wagtail.models import Page, Site

from about.models import AboutPage
from blog.models import Author, BlogIndexPage, BlogPage, Category
from home.models import HomePage


class SiteTreeMixin:
    """Builds Root > Home > {About, Writings > two posts} on a default Site."""

    def setUp(self):
        root = Page.get_first_root_node()
        Site.objects.all().delete()
        self.home = root.add_child(instance=HomePage(title="Home", slug="home-test"))
        Site.objects.create(hostname="testserver", root_page=self.home, is_default_site=True)

        self.about = self.home.add_child(
            instance=AboutPage(title="About", slug="about", biography="Hi, I'm Cam.")
        )
        index = self.home.add_child(instance=BlogIndexPage(title="Writings", slug="writings"))
        self.author = Author.objects.create(name="Cam", email="cam@example.com")
        self.category = Category.objects.create(name="Opinion", slug="opinion")
        self.older = index.add_child(instance=BlogPage(
            title="Older", slug="older", date=datetime.date(2025, 1, 1), intro="old",
            author=self.author, category=self.category,
            body=[("heading", "Hello world")],
        ))
        self.newer = index.add_child(instance=BlogPage(
            title="Newer", slug="newer", date=datetime.date(2026, 1, 1), intro="new",
        ))
        self.draft = index.add_child(instance=BlogPage(
            title="Draft", slug="draft", date=datetime.date(2026, 6, 1), intro="draft", live=False,
        ))


class V3APITests(SiteTreeMixin, TestCase):
    def test_about_returns_the_about_page(self):
        response = self.client.get("/api/v3/about/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.about.id)
        self.assertEqual(data["meta"]["type"], "about.AboutPage")
        self.assertEqual(data["biography"], "Hi, I'm Cam.")

    def test_about_404s_when_unpublished(self):
        self.about.unpublish()
        self.assertEqual(self.client.get("/api/v3/about/").status_code, 404)

    def test_writings_list_is_live_only_newest_first(self):
        data = self.client.get("/api/v3/writings/").json()
        self.assertEqual(data["count"], 2)
        self.assertEqual([item["meta"]["slug"] for item in data["items"]], ["newer", "older"])

    def test_writing_detail_by_slug(self):
        data = self.client.get("/api/v3/writings/older/").json()
        self.assertEqual(data["id"], self.older.id)
        self.assertEqual(data["author"]["name"], "Cam")
        self.assertIsNone(data["author"]["avatar"])
        self.assertEqual(data["category"]["slug"], "opinion")
        self.assertIsNone(data["image"])
        self.assertEqual(data["reading_time"], 1)
        self.assertEqual(data["body"][0]["type"], "heading")

    def test_writing_detail_hides_drafts(self):
        self.assertEqual(self.client.get("/api/v3/writings/draft/").status_code, 404)
        self.assertEqual(self.client.get("/api/v3/writings/nope/").status_code, 404)

    def test_v2_is_gone(self):
        # Unknown paths fall through to the admin's catch-all, which 404s for
        # a signed-in user (and redirects to login otherwise).
        user = get_user_model().objects.create_superuser("cam", "cam@example.com", "pw")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/v2/pages/").status_code, 404)


class HeadlessPreviewTests(SiteTreeMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_superuser("cam", "cam@example.com", "pw")
        self.client.force_login(self.user)

    def test_admin_preview_redirects_to_frontend_and_api_serves_draft(self):
        # Post an edited (unsaved) title to the admin preview endpoint, as the
        # editor's preview panel does, then follow the token to the API.
        preview_url = reverse("wagtailadmin_pages:preview_on_edit", args=[self.older.id])
        self.client.post(preview_url, {**_edit_form_data(self.older), "title": "Unsaved title"})
        response = self.client.get(preview_url)

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        client_url = settings.WAGTAIL_HEADLESS_PREVIEW["CLIENT_URLS"]["default"].rstrip("/") + "/"
        self.assertTrue(location.startswith(client_url + "?"), location)

        query = location.split("?", 1)[1]
        self.client.logout()  # the frontend calls the API anonymously
        data = self.client.get(f"/api/v3/preview/?{query}").json()
        self.assertEqual(data["id"], self.older.id)
        self.assertEqual(data["title"], "Unsaved title")

    def test_preview_rejects_bad_tokens(self):
        bad = self.client.get("/api/v3/preview/?content_type=blog.blogpage&token=forged")
        self.assertEqual(bad.status_code, 404)
        unknown = self.client.get("/api/v3/preview/?content_type=auth.user&token=x")
        self.assertEqual(unknown.status_code, 404)


class AdminAtRootTests(SiteTreeMixin, TestCase):
    def test_root_is_admin(self):
        self.assertRedirects(self.client.get("/"), "/login/?next=/", fetch_redirect_response=False)
        user = get_user_model().objects.create_superuser("cam", "cam@example.com", "pw")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get(reverse("api_routes")).status_code, 200)

    def test_magic_link_route_moved(self):
        self.assertEqual(reverse("request_magic_link"), "/login-link/")
        self.assertEqual(self.client.post("/login-link/", {"email": "x@example.com"}).status_code, 302)


def _edit_form_data(page):
    """Minimal valid edit-form POST for a BlogPage."""
    return {
        "title": page.title,
        "slug": page.slug,
        "date": page.date.isoformat(),
        "intro": page.intro,
        "tags": "",
        "body-count": "0",
        "references-TOTAL_FORMS": "0",
        "references-INITIAL_FORMS": "0",
        "references-MIN_NUM_FORMS": "0",
        "references-MAX_NUM_FORMS": "1000",
    }


class MagicLinkEmailTests(TestCase):
    def test_email_has_request_and_expiry_timestamps(self):
        from datetime import datetime, timezone as dt_timezone
        from unittest import mock

        from django.core import mail

        get_user_model().objects.create_user(
            "cam", "cam@example.com", "pw", is_staff=True
        )
        fixed = datetime(2026, 11, 8, 14, 32, 5, tzinfo=dt_timezone.utc)
        with mock.patch("camdahl_cms.accounts.timezone.now", return_value=fixed):
            self.client.post("/login-link/", {"email": "CAM@example.com"})

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Your sign-in link (14:32 UTC)")
        self.assertIn("Requested: Sun 8 Nov 2026, 14:32:05 UTC", email.body)
        self.assertIn("Expires:   Sun 8 Nov 2026, 14:47:05 UTC", email.body)
        self.assertIn("expires in 15 minutes", email.body)
        self.assertIn("http://testserver/?sesame=", email.body)

    def test_no_email_for_unknown_address(self):
        from django.core import mail

        self.client.post("/login-link/", {"email": "nobody@example.com"})
        self.assertEqual(len(mail.outbox), 0)


class LoginLinkRateLimitTests(TestCase):
    def setUp(self):
        get_user_model().objects.create_user("cam", "cam@example.com", "pw", is_staff=True)

    def request_link(self, email="cam@example.com", **extra):
        response = self.client.post("/login-link/", {"email": email}, **extra)
        self.assertEqual(response.status_code, 302)  # same response either way
        return response

    def test_per_email_limit(self):
        from django.core import mail

        for _ in range(5):
            self.request_link(email="CAM@example.com")
        self.assertEqual(len(mail.outbox), settings.LOGIN_LINK_MAX_PER_EMAIL)

    def test_unknown_emails_count_towards_ip_limit(self):
        from django.core import mail

        for i in range(settings.LOGIN_LINK_MAX_PER_IP):
            self.request_link(email=f"nobody{i}@example.com")
        self.request_link()
        self.assertEqual(len(mail.outbox), 0)

    def test_ip_comes_from_nginx_behind_loopback(self):
        from django.core import mail

        for i in range(settings.LOGIN_LINK_MAX_PER_IP):
            self.request_link(email=f"x{i}@example.com", HTTP_X_FORWARDED_FOR="203.0.113.9")
        # A different visitor (nginx's appended entry is rightmost) still gets through,
        # even if they put the blocked address first.
        self.request_link(HTTP_X_FORWARDED_FOR="203.0.113.9, 198.51.100.7")
        self.assertEqual(len(mail.outbox), 1)

    def test_limit_resets_after_window(self):
        from datetime import timedelta
        from unittest import mock

        from django.core import mail
        from django.utils import timezone

        for _ in range(settings.LOGIN_LINK_MAX_PER_EMAIL):
            self.request_link()
        later = timezone.now() + timedelta(seconds=settings.LOGIN_LINK_WINDOW + 1)
        with mock.patch("django.utils.timezone.now", return_value=later):
            self.request_link()
        self.assertEqual(len(mail.outbox), settings.LOGIN_LINK_MAX_PER_EMAIL + 1)
