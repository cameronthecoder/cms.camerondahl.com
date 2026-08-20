from django.db import models
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


    api_fields = [
        APIField('location'),
        APIField('education'),
        APIField('pronouns'),
        APIField('open_to_work'),
        APIField('tagline'),
    ]
