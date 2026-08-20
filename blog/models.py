from html import unescape

from django.db import models
from django.utils.html import strip_tags
from wagtail.models import Page, Orderable
from wagtail.snippets.models import register_snippet
from wagtail.fields import StreamField
from taggit.models import TaggedItemBase
from rest_framework import serializers
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


class BlogIndexPage(Page):
    intro = models.CharField(max_length=250, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('intro'),
    ]

    max_count = 1

    subpage_types = ['BlogPage']

    # Preview is disabled: this is a headless CMS with no server-rendered templates.
    preview_modes = []

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


class ImageFieldSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        if obj:
            return obj.file.url
        return None


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


class AuthorSerializer(serializers.ModelSerializer):
    avatar = ImageFieldSerializer(read_only=True)

    class Meta:
        model = Author
        fields = ['id', 'name', 'bio', 'avatar', 'email', 'website', 'github']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']

class BlogPage(Page):
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

    preview_modes = []

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
