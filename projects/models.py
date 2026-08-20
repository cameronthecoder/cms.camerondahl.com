from django.db import models
from wagtail.snippets.models import register_snippet
from django.forms import CheckboxSelectMultiple
from wagtail.admin.panels import FieldPanel, InlinePanel


@register_snippet
class Technology(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="e.g., devicon class or emoji")
    
    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('icon'),
    ]

    api_fields = [
        'name',
        'slug',
        'icon',
    ]
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Technologies"
        ordering = ['name']


@register_snippet
class Project(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    featured_image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    gallery = models.ManyToManyField(
        'wagtailimages.Image',
        blank=True,
        related_name='project_gallery'
    )
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    technologies = models.ManyToManyField(
        'projects.Technology',
        blank=True,
        related_name='projects'
    )
    date = models.DateField()
    featured = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    panels = [
        FieldPanel('title'),
        FieldPanel('slug'),
        FieldPanel('description'),
        FieldPanel('featured_image'),
        FieldPanel('gallery'),
        FieldPanel('project_url'),
        FieldPanel('github_url'),
        FieldPanel('technologies', widget=CheckboxSelectMultiple),
        FieldPanel('date'),
        FieldPanel('featured'),
        FieldPanel('order'),
    ]
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['order', '-date']
