from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet
from blog.models import BlogPage
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from django.contrib.contenttypes.models import ContentType
from django.http import Http404

from wagtail_headless_preview.models import PagePreview
from rest_framework.response import Response


class WritingsAPIViewSet(PagesAPIViewSet):
    model = BlogPage

    lookup_field = 'slug'

    listing_default_fields = PagesAPIViewSet.listing_default_fields + [
        'date',
        'author',
        'intro',
        'body',
        'category',
        'tags',
    ]

    def get_queryset(self):
        return BlogPage.objects.live().public().order_by('-date')

    def detail_view(self, request, pk=None, slug=None):
        # Set the router on the request if called directly (not through the router)
        if not hasattr(request, 'wagtailapi_router'):
            request.wagtailapi_router = api_router

        if slug:
            instance = self.get_queryset().filter(slug=slug).first()
            if not instance:
                raise Http404("Writing not found")
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return super().detail_view(request, pk)

class PagePreviewAPIViewSet(PagesAPIViewSet):
    known_query_parameters = PagesAPIViewSet.known_query_parameters.union(
        ["content_type", "token"]
    )

    def listing_view(self, request):
        # Delegate to detail_view, specifically so there's no
        # difference between serialization formats.
        self.action = "detail_view"
        return self.detail_view(request, 0)

    def detail_view(self, request, pk):
        page = self.get_object()
        serializer = self.get_serializer(page)
        return Response(serializer.data)

    def get_object(self):
        app_label, model = self.request.GET["content_type"].split(".")
        content_type = ContentType.objects.get(app_label=app_label, model=model)

        page_preview = PagePreview.objects.get(
            content_type=content_type, token=self.request.GET["token"]
        )
        page = page_preview.as_page()
        if not page.pk:
            # fake primary key to stop API URL routing from complaining
            page.pk = 0

        return page

api_router = WagtailAPIRouter('wagtailapi')
api_router.register_endpoint("page_preview", PagePreviewAPIViewSet)
api_router.register_endpoint('pages', PagesAPIViewSet)
api_router.register_endpoint('writings', WritingsAPIViewSet)
api_router.register_endpoint('images', ImagesAPIViewSet)
api_router.register_endpoint('documents', DocumentsAPIViewSet)