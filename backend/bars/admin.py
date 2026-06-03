from django.contrib import admin

from .models import Bar, Rating, Visit


@admin.register(Bar)
class BarAdmin(admin.ModelAdmin):
    list_display = ("name", "borough", "price_level", "google_rating", "updated_at")
    list_filter = ("borough", "price_level")
    search_fields = ("name", "address", "place_id")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("user", "bar", "visited_at", "created_at")
    list_filter = ("visited_at",)
    search_fields = ("user__username", "bar__name")
    autocomplete_fields = ("user", "bar")
    date_hierarchy = "visited_at"


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("user", "bar", "score", "updated_at")
    list_filter = ("score",)
    search_fields = ("user__username", "bar__name")
    autocomplete_fields = ("user", "bar")
