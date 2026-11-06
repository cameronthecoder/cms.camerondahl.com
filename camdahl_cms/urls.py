from django.conf import settings
from django.urls import include, path

from wagtail.admin import urls as wagtailadmin_urls
from wagtail import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

from .accounts import request_magic_link
from .api import api

urlpatterns = [
    path("api/v3/", api.urls),
    path("documents/", include(wagtaildocs_urls)),
    path("login-link/", request_magic_link, name="request_magic_link"),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns = urlpatterns + [
    # The Wagtail admin lives at the site root. It must come after the API,
    # documents and static/media routes above: the admin ends in its own
    # `^.*/$` catch-all (login redirect when signed out, 404 when signed in),
    # so anything listed after it is unreachable.
    path("", include(wagtailadmin_urls)),
    # Never actually served (the admin catch-all above wins), but kept so the
    # "wagtail_serve" route name still reverses — Page.url / get_full_url()
    # and the v3 API's meta.html_url depend on it.
    path("", include(wagtail_urls)),
]
