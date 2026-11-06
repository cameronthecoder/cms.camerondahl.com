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
