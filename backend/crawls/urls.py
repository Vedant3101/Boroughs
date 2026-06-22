from django.urls import path

from .views import GenerateCrawlView, RouteView

urlpatterns = [
    path("generate/", GenerateCrawlView.as_view(), name="crawl-generate"),
    path("route/", RouteView.as_view(), name="crawl-route"),
]
