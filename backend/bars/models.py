from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Bar(models.Model):
    """A drinking establishment in NYC."""

    BOROUGH_CHOICES = [
        ("MAN", "Manhattan"),
        ("BRK", "Brooklyn"),
        ("QNS", "Queens"),
        ("BRX", "The Bronx"),
        ("STI", "Staten Island"),
    ]

    PRICE_LEVEL_CHOICES = [
        (0, "Free"),
        (1, "$"),
        (2, "$$"),
        (3, "$$$"),
        (4, "$$$$"),
    ]

    # Google Places identifier — natural key for upserts during seeding
    place_id = models.CharField(max_length=255, unique=True, db_index=True)

    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True)
    borough = models.CharField(
        max_length=3, choices=BOROUGH_CHOICES, blank=True, db_index=True
    )

    # Lat/lng stored as Decimal for portability (no PostGIS dependency)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    price_level = models.IntegerField(
        choices=PRICE_LEVEL_CHOICES,
        null=True,
        blank=True,
        db_index=True,
        help_text="0=free, 4=very expensive (Google Places convention)",
    )

    phone = models.CharField(max_length=32, blank=True)
    website = models.URLField(blank=True, max_length=500)

    # Snapshot of Google's own rating at seed time — for reference, not user data
    google_rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True
    )
    google_rating_count = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self) -> str:
        return self.name


class Visit(models.Model):
    """A user marking that they've been to a bar."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    bar = models.ForeignKey(
        Bar,
        on_delete=models.CASCADE,
        related_name="visits",
    )
    visited_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visited_at"]
        indexes = [
            models.Index(fields=["user", "-visited_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.bar} on {self.visited_at:%Y-%m-%d}"


class Rating(models.Model):
    """A user's 1-5 score for a bar. One rating per (user, bar) — updates in place."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    bar = models.ForeignKey(
        Bar,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "bar"], name="unique_user_bar_rating"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} rated {self.bar} {self.score}/5"
