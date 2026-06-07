from django.urls import path

from .views import BarDetailView, BarListView

urlpatterns = [
    path("", BarListView.as_view(), name="bar-list"),
    path("<int:pk>/", BarDetailView.as_view(), name="bar-detail"),
]
