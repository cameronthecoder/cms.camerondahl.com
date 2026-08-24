from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import api_routes_view, server_health_view


@hooks.register("register_admin_urls")
def register_api_routes_url():
    return [
        path("api-routes/", api_routes_view, name="api_routes"),
        path("server-health/", server_health_view, name="server_health"),
    ]


@hooks.register("register_settings_menu_item")
def register_api_routes_menu_item():
    return MenuItem(
        _("API routes"),
        reverse("api_routes"),
        icon_name="code",
        order=900,
    )


@hooks.register("register_settings_menu_item")
def register_server_health_menu_item():
    return MenuItem(
        _("Server health"),
        reverse("server_health"),
        icon_name="desktop",
        order=910,
    )
