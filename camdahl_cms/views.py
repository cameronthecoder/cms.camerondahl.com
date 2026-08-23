from django.shortcuts import render

from .api import api_router

# Extra routes that exist outside api_router (registered by hand in urls.py)
# and so wouldn't otherwise show up from introspecting the router alone.
EXTRA_API_ROUTES = [
    {
        "path": "api/v2/writings/<slug>/",
        "description": "Detail view for a single blog post, looked up by slug instead of id.",
    },
]


def api_routes_view(request):
    # WagtailAPIRouter has no public accessor for its registered endpoints,
    # only register_endpoint() to add them — so this reads the same private
    # dict get_urlpatterns() builds from.
    endpoints = [
        {
            "name": name,
            "path": f"api/v2/{name}/",
            "model": viewset.model,
        }
        for name, viewset in sorted(api_router._endpoints.items())
    ]
    return render(
        request,
        "wagtailadmin/api_routes.html",
        {"endpoints": endpoints, "extra_routes": EXTRA_API_ROUTES},
    )
