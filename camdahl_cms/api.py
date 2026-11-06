"""
Public API for the headless frontend.

Everything is served by Wagtail's v3 API (Django Ninja), mounted at /api/v3/.
Wagtail itself registers pages, images, documents, redirects, sites, schema,
snippets and whoami; this module adds the site-specific routes below. Live
OpenAPI docs are at /api/v3/docs/.
"""

from django.contrib.contenttypes.models import ContentType
from django.core.signing import BadSignature
from django.http import Http404, HttpRequest
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import paginate
from wagtail.api.rich_text import RichTextOutputFormat
from wagtail.api.v3.auth import AllowAnonymous, BearerTokenAuth
from wagtail.api.v3.pagination import WagtailLimitOffsetPagination
from wagtail.api.v3.querysets import get_pages_queryset
from wagtail.api.v3.registry import registry
from wagtail.api.v3.routers.pages import PageDetailSchema
from wagtail.api.v3.urls import api
from wagtail_headless_preview.models import HeadlessPreviewMixin

from about.models import AboutPage
from blog.models import BlogPage

# Same auth as Wagtail's own read endpoints: anonymous requests see live,
# public pages; a Bearer API token sees what that user can edit.
PUBLIC_READ_AUTH = [BearerTokenAuth(), AllowAnonymous()]

BlogPageSchema = registry.get(BlogPage._meta.label).read_schema
AboutPageSchema = registry.get(AboutPage._meta.label).read_schema


# --- /api/v3/writings/ -------------------------------------------------------

writings_router = Router(tags=["writings"])


def _writings_queryset(request: HttpRequest):
    return get_pages_queryset(request, BlogPage).specific().order_by("-date")


@writings_router.get(
    "/",
    response=list[BlogPageSchema],
    url_name="list_writings",
    summary="List writings",
    description="Blog posts, newest first, with full content.",
    operation_id="writings_list",
    auth=PUBLIC_READ_AUTH,
)
@paginate(WagtailLimitOffsetPagination)
def list_writings(
    request: HttpRequest,
    rich_text_format: RichTextOutputFormat | None = Query(None),  # read by the schema via request.GET
    **kwargs,
):
    return _writings_queryset(request)


@writings_router.get(
    "/{slug}/",
    response=BlogPageSchema,
    url_name="detail_writing",
    summary="Writing detail",
    description="A single blog post, looked up by slug.",
    operation_id="writings_detail",
    auth=PUBLIC_READ_AUTH,
)
def get_writing(
    request: HttpRequest,
    slug: str,
    rich_text_format: RichTextOutputFormat | None = Query(None),
):
    return get_object_or_404(_writings_queryset(request), slug=slug)


# --- /api/v3/about/ ----------------------------------------------------------

about_router = Router(tags=["about"])


@about_router.get(
    "/",
    response=AboutPageSchema,
    url_name="about",
    summary="About page",
    description="The site's single About page (AboutPage.max_count = 1).",
    operation_id="about_detail",
    auth=PUBLIC_READ_AUTH,
)
def get_about(
    request: HttpRequest,
    rich_text_format: RichTextOutputFormat | None = Query(None),
):
    page = get_pages_queryset(request, AboutPage).specific().first()
    if page is None:
        raise Http404("No About page has been published.")
    return page


# --- /api/v3/preview/ --------------------------------------------------------

preview_router = Router(tags=["preview"])


@preview_router.get(
    "/",
    response=PageDetailSchema,
    url_name="preview",
    summary="Page preview",
    description=(
        "Draft content for wagtail-headless-preview. The admin sends the "
        "frontend to `?content_type=<app.model>&token=<token>`; the frontend "
        "passes both here. The signed, short-lived token is the credential."
    ),
    operation_id="preview_detail",
    auth=None,
)
def get_preview(
    request: HttpRequest,
    content_type: str,
    token: str,
    rich_text_format: RichTextOutputFormat | None = Query(None),
):
    try:
        app_label, model_name = content_type.split(".")
        model = ContentType.objects.get_by_natural_key(app_label, model_name).model_class()
    except (ValueError, ContentType.DoesNotExist):
        raise Http404("Unknown content type.")
    if model is None or not issubclass(model, HeadlessPreviewMixin):
        raise Http404("Unknown content type.")

    try:
        page = model.get_page_from_preview_token(token)
    except BadSignature:
        raise Http404("Invalid preview token.")
    if page is None:
        raise Http404("Preview not found.")
    return page


# Routers must be added before api.urls is first accessed (in urls.py).
api.add_router("/writings/", writings_router)
api.add_router("/about/", about_router)
api.add_router("/preview/", preview_router)

