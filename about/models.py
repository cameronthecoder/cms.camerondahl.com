from django.db import models
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel
class AboutPage(Page):
    biography = models.TextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('biography')
    ]

    max_count = 1

    subpage_types = []
