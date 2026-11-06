import os
import shutil
import sys
import time

import django
import psutil
import wagtail
from django.conf import settings
from django.db import connection
from django.shortcuts import render

from .api import api

# Approximates how long this worker process has been running — set once at
# import time, so each gunicorn worker reports its own start, not a shared
# "server" uptime.
WORKER_START_TIME = time.time()

# Tags for the routes this project adds in api.py, as opposed to the ones
# Wagtail registers itself. Shown first on the API routes page.
PROJECT_API_TAGS = ("writings", "about", "preview")


def api_routes_view(request):
    # Built from the same OpenAPI schema that /api/v3/docs/ renders, so this
    # page can't drift from the routes that are actually mounted.
    schema = api.get_openapi_schema(path_prefix="/api/v3/")
    routes = [
        {
            "method": method.upper(),
            "path": path,
            "tag": (op.get("tags") or [""])[0],
            "summary": op.get("summary", ""),
        }
        for path, ops in schema["paths"].items()
        for method, op in ops.items()
    ]
    project_routes = [r for r in routes if r["tag"] in PROJECT_API_TAGS]
    wagtail_routes = [r for r in routes if r["tag"] not in PROJECT_API_TAGS]
    return render(
        request,
        "wagtailadmin/api_routes.html",
        {
            "project_routes": project_routes,
            "wagtail_routes": wagtail_routes,
            "docs_url": "/api/v3/docs/",
        },
    )


def _humanize_bytes(num):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def _humanize_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = [f"{n}{unit}" for n, unit in ((days, "d"), (hours, "h"), (minutes, "m")) if n]
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _dir_size(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def server_health_view(request):
    db_config = settings.DATABASES["default"]
    db_ok, db_error = True, None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as exc:
        db_ok, db_error = False, str(exc)

    db_size = None
    if "sqlite3" in db_config["ENGINE"] and os.path.exists(db_config["NAME"]):
        db_size = _humanize_bytes(os.path.getsize(db_config["NAME"]))

    disk = shutil.disk_usage(settings.BASE_DIR)
    mem = psutil.virtual_memory()
    load1, load5, load15 = psutil.getloadavg()

    context = {
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "django_version": django.get_version(),
        "wagtail_version": wagtail.__version__,
        "debug": settings.DEBUG,
        "db_engine": db_config["ENGINE"].rsplit(".", 1)[-1],
        "db_ok": db_ok,
        "db_error": db_error,
        "db_size": db_size,
        "disk_total": _humanize_bytes(disk.total),
        "disk_used": _humanize_bytes(disk.used),
        "disk_free": _humanize_bytes(disk.free),
        "disk_percent": round(disk.used / disk.total * 100, 1),
        "media_size": _humanize_bytes(_dir_size(settings.MEDIA_ROOT)),
        "static_size": _humanize_bytes(_dir_size(settings.STATIC_ROOT)),
        "cpu_count": psutil.cpu_count(),
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "mem_total": _humanize_bytes(mem.total),
        "mem_used": _humanize_bytes(mem.used),
        "mem_percent": mem.percent,
        "load1": round(load1, 2),
        "load5": round(load5, 2),
        "load15": round(load15, 2),
        "system_uptime": _humanize_duration(time.time() - psutil.boot_time()),
        "worker_uptime": _humanize_duration(time.time() - WORKER_START_TIME),
    }
    return render(request, "wagtailadmin/server_health.html", context)
