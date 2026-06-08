"""Bar API views."""
from __future__ import annotations

from django.db.models import Avg, Count, F, FloatField, Q, Value
from django.db.models.functions import ACos, Cast, Cos, Radians, Sin
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import Bar, Rating, Visit
from .serializers import (
    BarDetailSerializer,
    BarListSerializer,
    RatingSerializer,
    VisitSerializer,
)

EARTH_RADIUS_M = 6_371_000


class BarListView(generics.ListAPIView):
    """
    GET /api/bars/

    Query params (all optional):
      search      — case-insensitive match against name or address
      borough     — MAN | BRK | QNS | BRX | STI
      price_min   — 0–4
      price_max   — 0–4
      lat, lng    — center point (must come together with radius)
      radius      — meters; filters to bars within this radius of (lat, lng)
      ordering    — name | -name | google_rating | -google_rating | distance
                    ("distance" requires lat/lng; defaults to name)
    """

    serializer_class = BarListSerializer

    def get_queryset(self):
        qs = Bar.objects.all()
        params = self.request.query_params

        search = params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(address__icontains=search))

        borough = params.get("borough")
        if borough:
            qs = qs.filter(borough=borough.upper())

        price_min = _safe_int(params.get("price_min"))
        if price_min is not None:
            qs = qs.filter(price_level__gte=price_min)

        price_max = _safe_int(params.get("price_max"))
        if price_max is not None:
            qs = qs.filter(price_level__lte=price_max)

        lat = _safe_float(params.get("lat"))
        lng = _safe_float(params.get("lng"))
        radius = _safe_float(params.get("radius"))

        if lat is not None and lng is not None and radius is not None:
            qs = _annotate_distance(qs, lat, lng).filter(distance_m__lte=radius)

        ordering = params.get("ordering")
        if ordering:
            if ordering in ("distance", "-distance"):
                if lat is not None and lng is not None:
                    if "distance_m" not in qs.query.annotations:
                        qs = _annotate_distance(qs, lat, lng)
                    qs = qs.order_by(
                        "distance_m" if ordering == "distance" else "-distance_m"
                    )
            elif ordering.lstrip("-") in {"name", "google_rating", "price_level"}:
                qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("name")

        return qs


class BarDetailView(generics.RetrieveAPIView):
    """GET /api/bars/{id}/ — full bar info plus user aggregates."""

    serializer_class = BarDetailSerializer

    def get_queryset(self):
        return Bar.objects.annotate(
            avg_user_rating=Avg("ratings__score"),
            num_user_ratings=Count("ratings", distinct=True),
            num_visits=Count("visits", distinct=True),
        )


# --- Visits ---------------------------------------------------------------


class VisitListCreateView(generics.ListCreateAPIView):
    """GET /api/visits/ — current user's visits. POST creates a new visit."""

    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Visit.objects.filter(user=self.request.user)
            .select_related("bar")
            .order_by("-visited_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class VisitDetailView(generics.RetrieveDestroyAPIView):
    """GET / DELETE a single visit (only the owner can touch it)."""

    serializer_class = VisitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Visit.objects.filter(user=self.request.user)


# --- Ratings --------------------------------------------------------------


class RatingListCreateView(generics.ListCreateAPIView):
    """
    GET /api/ratings/ — current user's ratings.
    POST upserts: if the user already rated this bar, the rating is updated.
    Returns 201 on create, 200 on update.
    """

    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Rating.objects.filter(user=self.request.user)
            .select_related("bar")
            .order_by("-updated_at")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bar = serializer.validated_data["bar"]
        rating, was_created = Rating.objects.update_or_create(
            user=request.user,
            bar=bar,
            defaults={
                "score": serializer.validated_data["score"],
                "comment": serializer.validated_data.get("comment", ""),
            },
        )
        out = self.get_serializer(rating)
        return Response(
            out.data,
            status=status.HTTP_201_CREATED if was_created else status.HTTP_200_OK,
        )


class RatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE a single rating (owner only)."""

    serializer_class = RatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Rating.objects.filter(user=self.request.user)


# --- helpers ---------------------------------------------------------------


def _safe_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _annotate_distance(qs, lat: float, lng: float):
    """Annotate `distance_m` (Haversine, meters) on each bar in `qs`.

    We cast lat/lng to FloatField so the expression doesn't mix Decimal × Float,
    which Django's ORM refuses to type-infer.
    """
    lat_f = Cast(F("latitude"), output_field=FloatField())
    lng_f = Cast(F("longitude"), output_field=FloatField())
    lat_v = Value(lat, output_field=FloatField())
    lng_v = Value(lng, output_field=FloatField())

    return qs.annotate(
        distance_m=Value(EARTH_RADIUS_M, output_field=FloatField())
        * ACos(
            Sin(Radians(lat_f)) * Sin(Radians(lat_v))
            + Cos(Radians(lat_f))
            * Cos(Radians(lat_v))
            * Cos(Radians(lng_f - lng_v)),
            output_field=FloatField(),
        )
    )
