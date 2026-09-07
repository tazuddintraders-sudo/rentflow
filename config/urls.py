from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("properties/", include("apps.properties.urls")),
    path("payments/", include("apps.payments.urls")),
]

# Media is always served by Django (the desktop app has no separate web server).
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve, kwargs={"document_root": settings.MEDIA_ROOT}),
]

# When packaged with PyInstaller (DEBUG=False), static files are collected into
# staticfiles/ and served the same way.
if not settings.DEBUG:
    urlpatterns += [
        re_path(r"^static/(?P<path>.*)$", serve,
                kwargs={"document_root": settings.STATIC_ROOT}),
    ]
