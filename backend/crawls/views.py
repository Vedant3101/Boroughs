"""Pub crawl + routing views."""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from bars.models import Bar
from bars.serializers import BarListSerializer

from .serializers import GenerateCrawlSerializer, RouteRequestSerializer
from .services import (
    cached_route,
    crawl_cost_estimate,
    generate_crawl,
    drink_cost,
)


class GenerateCrawlView(APIView):
    """POST /api/crawls/generate — given a start bar + budget, return an ordered route."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = GenerateCrawlSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        try:
            start_bar = Bar.objects.get(id=data["start_bar"])
        except Bar.DoesNotExist:
            return Response(
                {"start_bar": "No bar with that id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        budget = data["budget_cents"]
        if drink_cost(start_bar) > budget:
            return Response(
                {
                    "budget_cents": (
                        f"Budget {budget}c is below the estimated drink cost at "
                        f"the starting bar ({drink_cost(start_bar)}c)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        bars = generate_crawl(
            start_bar=start_bar,
            budget_cents=budget,
            mode=data["mode"],
            max_stops=data["max_stops"],
            search_radius_m=data["search_radius_m"],
        )

        return Response(
            {
                "mode": data["mode"],
                "budget_cents": budget,
                "bars": BarListSerializer(bars, many=True).data,
                **crawl_cost_estimate(bars, data["mode"]),
            }
        )


class RouteView(APIView):
    """POST /api/crawls/route — proxy Google Directions for a multi-stop route."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payload = RouteRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        try:
            result = cached_route(list(data["bar_ids"]), data["mode"])
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:  # network errors, etc.
            return Response(
                {"error": f"Routing failed: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(result)
