from django.db import models
from django.http import Http404
from wagtail.api import APIField
from wagtail.models import Page
from wagtail.admin.panels import FieldPanel

class HomePage(Page):
    location = models.CharField(max_length=255, blank=True)
    education = models.TextField(blank=True)
    pronouns = models.CharField(max_length=100, blank=True)
    open_to_work = models.BooleanField(default=False)
    tagline = models.CharField(max_length=255, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('location'),
        FieldPanel('education'),
        FieldPanel('pronouns'),
        FieldPanel('open_to_work'),
        FieldPanel('tagline'),
    ]

    subpage_types = ['blog.BlogIndexPage', 'about.AboutPage']

    preview_modes = []

    def serve(self, request, *args, **kwargs):
        # Headless CMS — this page's data is served via the API, not rendered
        # as HTML by Django.
        raise Http404

    api_fields = [
        APIField('location'),
        APIField('education'),
        APIField('pronouns'),
        APIField('open_to_work'),
        APIField('tagline'),
    ]
