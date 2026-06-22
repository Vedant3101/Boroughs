from rest_framework import serializers

from .services import ALLOWED_MODES


class GenerateCrawlSerializer(serializers.Serializer):
    start_bar = serializers.IntegerField()
    budget_cents = serializers.IntegerField(min_value=100)  # at least $1
    mode = serializers.ChoiceField(choices=ALLOWED_MODES, default="walking")
    max_stops = serializers.IntegerField(min_value=2, max_value=10, default=5)
    search_radius_m = serializers.IntegerField(
        min_value=200, max_value=10_000, default=2_000
    )


class RouteRequestSerializer(serializers.Serializer):
    bar_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=2,
        max_length=10,
    )
    mode = serializers.ChoiceField(choices=ALLOWED_MODES, default="walking")
