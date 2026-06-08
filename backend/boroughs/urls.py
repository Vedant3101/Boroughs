"""Top-level URL configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/bars/", include("bars.urls")),
    path("api/visits/", include("bars.visit_urls")),
    path("api/ratings/", include("bars.rating_urls")),
    path("api/crawls/", include("crawls.urls")),
]
