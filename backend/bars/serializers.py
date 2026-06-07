from rest_framework import serializers

from .models import Bar


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
