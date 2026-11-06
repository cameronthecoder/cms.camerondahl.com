from html import unescape

from django.db import models
from django.utils.html import strip_tags
from wagtail.models import Page, Orderable
from wagtail_headless_preview.models import HeadlessPreviewMixin
from wagtail.snippets.models import register_snippet
from wagtail.fields import StreamField
from taggit.models import TaggedItemBase
from typing import TypedDict

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.styles import get_all_styles
from pygments.util import ClassNotFound
from django.db import DatabaseError
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting

from blog.pygments_styles import GitHubLightStyle

from wagtail.api.v3.fields import FieldSerializer
from modelcluster.fields import ParentalKey
from wagtail.documents.blocks import DocumentChooserBlock
from modelcluster.tags import ClusterTaggableManager
from wagtail.admin.panels import FieldPanel, InlinePanel
from wagtail import blocks
from wagtail.api import APIField
from wagtail.images.blocks import ImageChooserBlock

class VideoBlock(blocks.StructBlock):
    video_url = blocks.URLBlock(help_text="YouTube or Vimeo URL")
    caption = blocks.CharBlock(required=False)
    autoplay = blocks.BooleanBlock(required=False, default=False)
    
    class Meta:
        icon = 'media'


class BlogIndexPage(HeadlessPreviewMixin, Page):
    intro = models.CharField(max_length=250, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    max_count = 1

    subpage_types = ['BlogPage']

    # Preview is disabled: this is a headless CMS with no server-rendered templates.

class Reference(Orderable):
    page = ParentalKey('BlogPage', on_delete=models.CASCADE, related_name='references')
    title = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    author = models.CharField(max_length=255, blank=True)
    publication = models.CharField(max_length=255, blank=True)
    date = models.DateField(null=True, blank=True)

    panels = [
        FieldPanel('title'),
        FieldPanel('url'),
        FieldPanel('author'),
        FieldPanel('publication'),
        FieldPanel('date'),
    ]


# Code-block themes: every built-in Pygments style, plus GitHub Light (which
# Pygments doesn't ship — see blog/pygments_styles.py). Chosen in the admin
# under Settings → Code highlighting (CodeHighlightSettings below).
DEFAULT_CODE_THEME = 'github-light'
CUSTOM_CODE_THEMES = {'github-light': GitHubLightStyle}


def code_theme_choices():
    # A callable, so new Pygments styles show up without a migration.
    names = [*CUSTOM_CODE_THEMES, *sorted(set(get_all_styles()) - set(CUSTOM_CODE_THEMES))]
    labels = {'github-light': 'GitHub Light', 'github-dark': 'GitHub Dark'}
    return [
        (name, labels.get(name) or name.replace('_', ' ').replace('-', ' ').title())
        for name in names
    ]


def get_code_theme():
    """The theme saved in CodeHighlightSettings, or the default."""
    try:
        setting = CodeHighlightSettings.base_queryset().first()
    except DatabaseError:
        # Table not created yet (e.g. mid-migration).
        setting = None
    return setting.theme if setting else DEFAULT_CODE_THEME


def highlight_code(code, language, theme=None):
    """Return `code` as Pygments-highlighted HTML for the given lexer alias.

    Uses inline styles (noclasses), so the HTML renders highlighted as-is with
    no Pygments stylesheet needed on the frontend.
    """
    theme = theme or get_code_theme()
    style = CUSTOM_CODE_THEMES.get(theme, theme)
    try:
        formatter = HtmlFormatter(noclasses=True, style=style)
    except ClassNotFound:
        # A saved theme that a Pygments upgrade has since removed.
        formatter = HtmlFormatter(noclasses=True, style=CUSTOM_CODE_THEMES[DEFAULT_CODE_THEME])
    try:
        # startinline lets PHP snippets highlight without a leading "<?php";
        # other lexers ignore it.
        lexer = get_lexer_by_name(language or '', startinline=True)
    except ClassNotFound:
        lexer = TextLexer()
    return highlight(code or '', lexer, formatter)


@register_setting(icon='code')
class CodeHighlightSettings(BaseGenericSetting):
    theme = models.CharField(
        max_length=50,
        choices=code_theme_choices,
        default=DEFAULT_CODE_THEME,
        help_text='Syntax-highlighting colours for code blocks in writings. '
                  'Saving a new theme re-highlights every published writing.',
    )

    panels = [FieldPanel('theme')]

    class Meta:
        verbose_name = 'Code highlighting'

    def save(self, *args, **kwargs):
        previous = type(self).objects.filter(pk=self.pk).values_list('theme', flat=True).first()
        super().save(*args, **kwargs)
        if previous != self.theme:
            rehighlight_writings()


def rehighlight_writings():
    """Regenerate the stored highlighted HTML in every writing's code blocks.

    Writes the body directly (queryset.update) rather than page.save(), so it
    doesn't create revisions or touch published/updated timestamps. Unsaved
    drafts pick up the theme the next time they're saved or previewed.
    """
    for page in BlogPage.objects.all():
        if not any(block.block_type == 'code' for block in page.body):
            continue
        # Iterating above converted every block, so get_prep_value() now
        # re-runs CodeBlock.get_prep_value() instead of passing the stored
        # raw JSON (with the old HTML) straight through.
        BlogPage.objects.filter(pk=page.pk).update(body=page.body)


class CodeBlock(blocks.StructBlock):
    language = blocks.ChoiceBlock(choices=[
        ('py', 'Python'),
        ('js', 'JavaScript'),
        ('html', 'HTML'),
        ('css', 'CSS'),
        ('java', 'Java'),
        ('csharp', 'C#'),
        ('cpp', 'C++'),
        ('ruby', 'Ruby'),
        ('go', 'Go'),
        ('php', 'PHP'),
        ('swift', 'Swift'),
        ('kotlin', 'Kotlin'),
    ], default='py')
    code = blocks.TextBlock()

    class Meta:
        icon = 'code'

    # Pygments-highlighted HTML is computed in get_prep_value(), which runs
    # whenever the StreamField is written: page saves and publishes, draft
    # revisions, and previews. It's stored alongside `language`/`code` under
    # this key, but isn't a child block, so editors never see or edit it —
    # it's always regenerated from the current code. On load it's carried on
    # the StructValue as an attribute rather than a dict key, since
    # StructBlock looks every key up in child_blocks.
    HIGHLIGHTED_KEY = 'highlighted'

    def get_prep_value(self, value):
        prep = super().get_prep_value(value)
        prep[self.HIGHLIGHTED_KEY] = highlight_code(value.get('code', ''), value.get('language'))
        return prep

    def to_python(self, value):
        struct_value = super().to_python(value)
        struct_value.highlighted = value.get(self.HIGHLIGHTED_KEY)
        return struct_value

    def bulk_to_python(self, values):
        struct_values = super().bulk_to_python(values)
        for struct_value, raw in zip(struct_values, values):
            struct_value.highlighted = raw.get(self.HIGHLIGHTED_KEY)
        return struct_values

    def get_api_representation(self, value, context=None):
        representation = super().get_api_representation(value, context)
        # Fall back to highlighting on the fly for values that haven't been
        # saved since this was added (or were built in memory, not loaded).
        representation[self.HIGHLIGHTED_KEY] = getattr(value, 'highlighted', None) or highlight_code(
            value.get('code', ''), value.get('language')
        )
        return representation


class ImageData(TypedDict):
    id: int
    title: str
    url: str


class ImageFieldSerializer(FieldSerializer):
    """API v3 representation of an image: id, title and original-file URL."""

    def to_representation(self, value) -> ImageData:
        return {"id": value.id, "title": value.title, "url": value.file.url}


@register_snippet
class Author(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    github = models.CharField(max_length=255, blank=True)

    panels = [
        FieldPanel('name'),
        FieldPanel('bio'),
        FieldPanel('avatar'),
        FieldPanel('email'),
        FieldPanel('website'),
        FieldPanel('github'),
    ]
    
    api_fields = [
        APIField('name'),
        APIField('bio'),
        APIField('avatar', serializer=ImageFieldSerializer()),
        APIField('email'),
        APIField('website'),
        APIField('github')
    ]

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Author"
        verbose_name_plural = "Authors"
class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey(
        'BlogPage',
        related_name='tagged_items',
        on_delete=models.CASCADE
    )

@register_snippet
class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
        FieldPanel('description'),
    ]
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class SizedRichTextBlock(blocks.StructBlock):
    size = blocks.ChoiceBlock(
        choices=[
            ('sm', 'Small'),
            ('base', 'Base'),
            ('lg', 'Large'),
            ('xl', 'Extra Large'),
        ],
        default='base',
        help_text='Select the text size'
    )
    text = blocks.RichTextBlock()
    
    class Meta:
        icon = 'doc-full'
        template = 'blocks/sized_rich_text_block.html'
        label = 'Sized Paragraph'

class PulledQuote(blocks.StructBlock):
    author = blocks.TextBlock(required=False)
    source = blocks.TextBlock()
    
    class Meta:
        icon = 'openquote'
        label = 'Pulled Quote'


class AuthorData(TypedDict):
    id: int
    name: str
    bio: str
    avatar: ImageData | None
    email: str
    website: str
    github: str


class AuthorSerializer(FieldSerializer):
    def to_representation(self, value) -> AuthorData:
        return {
            "id": value.id,
            "name": value.name,
            "bio": value.bio,
            "avatar": ImageFieldSerializer().to_representation(value.avatar) if value.avatar else None,
            "email": value.email,
            "website": value.website,
            "github": value.github,
        }


class CategoryData(TypedDict):
    id: int
    name: str
    slug: str
    description: str


class CategorySerializer(FieldSerializer):
    def to_representation(self, value) -> CategoryData:
        return {
            "id": value.id,
            "name": value.name,
            "slug": value.slug,
            "description": value.description,
        }

class BlogPage(HeadlessPreviewMixin, Page):
    date = models.DateField("Post date")
    intro = models.CharField(max_length=250)
    category = models.ForeignKey(
        'blog.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='writings'
    )
    image = models.ForeignKey(
        'wagtailimages.Image',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    tags = ClusterTaggableManager(blank=True, through=BlogPageTag)
    author = models.ForeignKey(
        'blog.Author',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blog_posts'
    )
    body = StreamField([
        ('heading', blocks.CharBlock(form_classname="title")),
        ('paragraph', SizedRichTextBlock()),
        ('image', ImageChooserBlock()),
        ('pull_quote', PulledQuote()),
        ('code', CodeBlock(form_classname="textarea")),
        ('quote', blocks.BlockQuoteBlock()),
        ('video', VideoBlock()),
        ('file', DocumentChooserBlock()),
    ], use_json_field=True)

    
    @property
    def reading_time(self):
        """Estimated minutes to read the prose blocks, at ~200 words per minute."""
        words = 0
        for block in self.body:
            if block.block_type == 'heading':
                text = str(block.value)
            elif block.block_type == 'paragraph':
                text = strip_tags(str(block.value['text']))
            elif block.block_type == 'pull_quote':
                text = str(block.value['source'])
            elif block.block_type == 'quote':
                text = strip_tags(str(block.value))
            else:
                # image, code, video and file blocks are not read at prose speed
                continue
            words += len(unescape(text).split())
        return max(1, round(words / 200))
    
    subpage_types = []


    content_panels = Page.content_panels + [
        FieldPanel('date'),
        FieldPanel('author'),
        FieldPanel('image'),
        FieldPanel('category'),
        FieldPanel('tags'),
        FieldPanel('intro'),
        FieldPanel('body'),
        InlinePanel('references', label="References"),
    ]

    api_fields = [
        APIField('date'),
        APIField('intro'),
        APIField('tags'),
        APIField('category', serializer=CategorySerializer()),
        APIField('image', serializer=ImageFieldSerializer()),
        APIField('reading_time'),
        APIField('author', serializer=AuthorSerializer()),
        APIField('body'),
    ]
