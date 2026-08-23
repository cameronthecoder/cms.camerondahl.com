from django.conf import settings


def magic_link_login_only(request):
    return {"magic_link_login_only": settings.MAGIC_LINK_LOGIN_ONLY}
