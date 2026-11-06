from django.db import models
from wagtail.api import APIField
from wagtail.models import Page
from wagtail_headless_preview.models import HeadlessPreviewMixin
from wagtail.admin.panels import FieldPanel
class AboutPage(HeadlessPreviewMixin, Page):
    biography = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('biography')
    ]

    max_count = 1

    subpage_types = []


    api_fields = [
        APIField('biography'),
    ]
