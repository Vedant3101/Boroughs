from django.contrib import admin

from .models import CrawlLeg, PubCrawl


class CrawlLegInline(admin.TabularInline):
    model = CrawlLeg
    extra = 0
    fields = ("order", "from_bar", "to_bar", "distance_m", "duration_sec", "cost_cents")
    autocomplete_fields = ("from_bar", "to_bar")
    ordering = ("order",)


@admin.register(PubCrawl)
class PubCrawlAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "user",
        "start_bar",
        "mode",
        "budget_cents",
        "total_duration_sec",
        "created_at",
    )
    list_filter = ("mode", "created_at")
    search_fields = ("name", "user__username", "start_bar__name")
    autocomplete_fields = ("user", "start_bar")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CrawlLegInline]


@admin.register(CrawlLeg)
class CrawlLegAdmin(admin.ModelAdmin):
    list_display = ("crawl", "order", "from_bar", "to_bar", "duration_sec", "distance_m")
    search_fields = ("crawl__name", "from_bar__name", "to_bar__name")
    autocomplete_fields = ("crawl", "from_bar", "to_bar")
