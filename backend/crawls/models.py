from django.conf import settings
from django.db import models

from bars.models import Bar


class PubCrawl(models.Model):
    """A user-generated pub crawl: starting bar, budget, ordered stops."""

    MODE_CHOICES = [
        ("walking", "Walking"),
        ("transit", "Transit"),
        ("driving", "Driving"),
        ("bicycling", "Bicycling"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="crawls",
    )
    name = models.CharField(max_length=200, blank=True)
    start_bar = models.ForeignKey(
        Bar,
        on_delete=models.PROTECT,
        related_name="crawls_starting_here",
    )
    budget_cents = models.PositiveIntegerField(
        help_text="Total budget for the crawl, in US cents",
    )
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="walking")

    # Cached totals computed when legs are generated
    total_distance_m = models.PositiveIntegerField(default=0)
    total_duration_sec = models.PositiveIntegerField(default=0)
    total_cost_cents = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name or f"Crawl #{self.pk} ({self.user})"


class CrawlLeg(models.Model):
    """One leg of a pub crawl: travel from one bar to the next."""

    crawl = models.ForeignKey(
        PubCrawl,
        on_delete=models.CASCADE,
        related_name="legs",
    )
    order = models.PositiveSmallIntegerField(
        help_text="0-indexed position within the crawl",
    )
    from_bar = models.ForeignKey(
        Bar,
        on_delete=models.PROTECT,
        related_name="legs_starting_here",
    )
    to_bar = models.ForeignKey(
        Bar,
        on_delete=models.PROTECT,
        related_name="legs_ending_here",
    )
    distance_m = models.PositiveIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)
    cost_cents = models.PositiveIntegerField(
        default=0,
        help_text="Travel cost (e.g. subway fare); does not include drinks",
    )
    polyline = models.TextField(
        blank=True,
        help_text="Encoded polyline string from the routing API",
    )

    class Meta:
        ordering = ["crawl", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["crawl", "order"], name="unique_crawl_leg_order"
            ),
        ]

    def __str__(self) -> str:
        return f"Leg {self.order}: {self.from_bar} → {self.to_bar}"
