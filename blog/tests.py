import datetime
import json

from django.db import connection
from django.test import TestCase
from wagtail.models import Page, Site

from blog.models import BlogIndexPage, BlogPage, CodeBlock
from home.models import HomePage


class CodeHighlightingTests(TestCase):
    def setUp(self):
        root = Page.get_first_root_node()
        Site.objects.all().delete()
        home = root.add_child(instance=HomePage(title="Home", slug="home-test"))
        Site.objects.create(hostname="testserver", root_page=home, is_default_site=True)
        self.index = home.add_child(instance=BlogIndexPage(title="Writings", slug="writings"))

    def make_post(self, code, language="py"):
        return self.index.add_child(instance=BlogPage(
            title="Post", slug="post", date=datetime.date(2026, 1, 1), intro="x",
            body=[("code", {"language": language, "code": code})],
        ))

    def stored_code_block(self, page):
        # Read the raw JSON column, bypassing StreamField conversion, to prove
        # the HTML is what's actually saved.
        with connection.cursor() as cursor:
            cursor.execute("SELECT body FROM blog_blogpage WHERE page_ptr_id = %s", [page.pk])
            raw = cursor.fetchone()[0]
        return (json.loads(raw) if isinstance(raw, str) else raw)[0]["value"]

    def test_highlighted_html_is_stored_on_save(self):
        page = self.make_post("def hi():\n    return '<b>'\n")
        stored = self.stored_code_block(page)
        self.assertEqual(stored["code"], "def hi():\n    return '<b>'\n")
        self.assertIn('<div class="highlight"', stored["highlighted"])
        self.assertIn('style="', stored["highlighted"])  # inline styles, no CSS needed
        self.assertIn("&lt;b&gt;", stored["highlighted"])  # code is escaped
        self.assertNotIn("<b>", stored["highlighted"])

    def test_highlighting_follows_edits(self):
        page = self.make_post("x = 1")
        page.body = [("code", {"language": "js", "code": "const y = 2;"})]
        page.save()
        self.assertIn("const", self.stored_code_block(page)["highlighted"])
        self.assertNotIn("x", self.stored_code_block(page)["highlighted"].split("const")[0][-5:])

    def test_revisions_store_highlighted_html(self):
        page = self.make_post("x = 1")
        revision = page.save_revision()
        block = revision.content["body"]
        block = (json.loads(block) if isinstance(block, str) else block)[0]["value"]
        self.assertIn('<div class="highlight"', block["highlighted"])

    def test_api_returns_highlighted_html_and_editor_form_omits_it(self):
        page = self.make_post("print('hi')")
        item = self.client.get("/api/v3/writings/post/").json()["body"][0]
        self.assertEqual(item["type"], "code")
        self.assertEqual(item["value"]["code"], "print('hi')")
        self.assertIn('<div class="highlight"', item["value"]["highlighted"])

        loaded = BlogPage.objects.get(pk=page.pk)
        block = loaded.body[0].block
        self.assertNotIn("highlighted", block.get_form_state(loaded.body[0].value))

    def test_every_language_choice_has_a_lexer(self):
        from pygments.lexers import get_lexer_by_name

        for value, _label in CodeBlock().child_blocks["language"].field.choices:
            get_lexer_by_name(value)  # raises ClassNotFound if not

    def test_php_highlights_without_open_tag(self):
        page = self.make_post("$x = 1;", language="php")
        # A highlighted PHP variable gets its own styled span.
        self.assertIn("<span", self.stored_code_block(page)["highlighted"])


class CodeThemeSettingTests(CodeHighlightingTests):
    """Theme comes from the CodeHighlightSettings admin setting."""

    def setUp(self):
        super().setUp()
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_superuser("cam", "cam@example.com", "pw")

    def test_default_theme_is_github_light(self):
        from blog.pygments_styles import BG_DEFAULT

        page = self.make_post("x = 1")
        self.assertIn(f"background: {BG_DEFAULT}", self.stored_code_block(page)["highlighted"])

    def test_changing_theme_in_admin_rehighlights_live_writings(self):
        from django.urls import reverse
        from pygments.styles import get_style_by_name

        page = self.make_post("x = 1")
        revisions_before = page.revisions.count()

        self.client.force_login(self.user)
        # The bare settings URL redirects to the singleton's edit view.
        response = self.client.get(
            reverse("wagtailsettings:edit", args=["blog", "codehighlightsettings"]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GitHub Light")
        # Preview panel: one sample per theme, only the saved theme visible.
        self.assertContains(response, "data-code-theme-preview")
        self.assertContains(response, '<div data-theme="github-light" >')
        self.assertContains(response, '<div data-theme="monokai" hidden>')
        self.assertContains(response, "Hello &lt;world&gt;")
        url = response.redirect_chain[-1][0] if response.redirect_chain else response.request["PATH_INFO"]
        response = self.client.post(url, {"theme": "monokai"})
        self.assertEqual(response.status_code, 302)

        monokai_bg = get_style_by_name("monokai").background_color
        self.assertIn(f"background: {monokai_bg}", self.stored_code_block(page)["highlighted"])
        api_html = self.client.get("/api/v3/writings/post/").json()["body"][0]["value"]["highlighted"]
        self.assertIn(f"background: {monokai_bg}", api_html)
        self.assertEqual(page.revisions.count(), revisions_before)  # no new revisions

    def test_removed_theme_falls_back_to_default(self):
        from blog.models import CodeHighlightSettings, highlight_code
        from blog.pygments_styles import BG_DEFAULT

        CodeHighlightSettings.objects.update_or_create(defaults={"theme": "no-such-theme"})
        self.assertIn(f"background: {BG_DEFAULT}", highlight_code("x", "py"))
