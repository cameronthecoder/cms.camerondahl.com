from django.http import Http404
from rest_framework.response import Response
from wagtail.api.v2.router import WagtailAPIRouter
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.documents.api.v2.views import DocumentsAPIViewSet
from wagtail.images.api.v2.views import ImagesAPIViewSet

from blog.models import BlogPage


class WritingsAPIViewSet(PagesAPIViewSet):
    model = BlogPage

    # Required by DRF's get_object(), which get_serializer_class() calls: the
    # slug route in urls.py supplies a `slug` kwarg rather than `pk`.
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
        # The router only generates an <int:pk> detail route, so slug lookups
        # arrive via the explicit path in urls.py and need the router attached
        # by hand.
        if not hasattr(request, 'wagtailapi_router'):
            request.wagtailapi_router = api_router

        if slug:
            instance = self.get_queryset().filter(slug=slug).first()
            if not instance:
                raise Http404("Writing not found")
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        return super().detail_view(request, pk)


api_router = WagtailAPIRouter('wagtailapi')
api_router.register_endpoint('pages', PagesAPIViewSet)
api_router.register_endpoint('writings', WritingsAPIViewSet)
api_router.register_endpoint('images', ImagesAPIViewSet)
api_router.register_endpoint('documents', DocumentsAPIViewSet)
