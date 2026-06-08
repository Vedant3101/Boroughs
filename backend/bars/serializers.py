from rest_framework import serializers

from .models import Bar, Rating, Visit


class BarListSerializer(serializers.ModelSerializer):
    """Concise representation for list views and map markers."""

    price_level_display = serializers.CharField(
        source="get_price_level_display", read_only=True
    )
    borough_display = serializers.CharField(
        source="get_borough_display", read_only=True
    )

    class Meta:
        model = Bar
        fields = (
            "id",
            "name",
            "address",
            "borough",
            "borough_display",
            "latitude",
            "longitude",
            "price_level",
            "price_level_display",
            "google_rating",
            "google_rating_count",
        )


class BarDetailSerializer(BarListSerializer):
    """Full bar info, including aggregate stats from our own users."""

    avg_user_rating = serializers.FloatField(read_only=True)
    num_user_ratings = serializers.IntegerField(read_only=True)
    num_visits = serializers.IntegerField(read_only=True)

    class Meta(BarListSerializer.Meta):
        fields = BarListSerializer.Meta.fields + (
            "phone",
            "website",
            "avg_user_rating",
            "num_user_ratings",
            "num_visits",
            "created_at",
            "updated_at",
        )


class VisitSerializer(serializers.ModelSerializer):
    """A user marking they visited a bar. Multiple visits per (user, bar) are allowed."""

    bar_name = serializers.CharField(source="bar.name", read_only=True)

    class Meta:
        model = Visit
        fields = ("id", "bar", "bar_name", "visited_at", "notes", "created_at")
        read_only_fields = ("id", "created_at")


class RatingSerializer(serializers.ModelSerializer):
    """A user's 1-5 rating of a bar. One per (user, bar) — POST upserts."""

    bar_name = serializers.CharField(source="bar.name", read_only=True)

    class Meta:
        model = Rating
        fields = (
            "id",
            "bar",
            "bar_name",
            "score",
            "comment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
