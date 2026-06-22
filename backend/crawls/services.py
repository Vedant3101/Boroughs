"""Pub crawl generation + Google Directions proxy."""
from __future__ import annotations

from decimal import Decimal
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

import requests
from django.conf import settings
from django.core.cache import cache

from bars.models import Bar

# --- Cost model ----------------------------------------------------------

# Estimated cost of one drink at each price level, in US cents
DRINK_COST_CENTS = {
    0: 0,
    1: 800,    # $8 at a dive
    2: 1400,   # $14 mid-range
    3: 2200,   # $22 cocktail bar
    4: 3500,   # $35 a top-shelf room
}
DEFAULT_DRINK_COST_CENTS = 1500  # used when price_level is unknown

# Per-leg travel cost (transit only — NYC subway swipe)
TRANSIT_LEG_COST_CENTS = 290

ALLOWED_MODES = ("walking", "transit", "driving", "bicycling")
EARTH_RADIUS_M = 6_371_000


def drink_cost(bar: Bar) -> int:
    """Estimated cost of one drink at this bar, in cents."""
    if bar.price_level is None:
        return DEFAULT_DRINK_COST_CENTS
    return DRINK_COST_CENTS.get(bar.price_level, DEFAULT_DRINK_COST_CENTS)


def leg_travel_cost(mode: str) -> int:
    return TRANSIT_LEG_COST_CENTS if mode == "transit" else 0


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    lat1, lng1, lat2, lng2 = map(
        lambda x: radians(float(x)), [lat1, lng1, lat2, lng2]
    )
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return EARTH_RADIUS_M * 2 * asin(sqrt(a))


# --- Generator -----------------------------------------------------------


def generate_crawl(
    start_bar: Bar,
    budget_cents: int,
    mode: str,
    max_stops: int = 5,
    search_radius_m: int = 2000,
) -> list[Bar]:
    """
    Greedy "nearest affordable" crawl generator.

    Always returns at least the start bar (even if it exceeds the budget — UI
    can warn the user).
    """
    if mode not in ALLOWED_MODES:
        raise ValueError(f"Invalid mode: {mode}")

    itinerary: list[Bar] = [start_bar]
    remaining = budget_cents - drink_cost(start_bar)
    visited_ids = {start_bar.id}
    current = start_bar

    while len(itinerary) < max_stops and remaining > 0:
        # Bounding-box prefilter (cheap, uses lat/lng index)
        deg_pad = (search_radius_m / EARTH_RADIUS_M) * (180 / 3.14159265358979)
        candidates_qs = Bar.objects.exclude(id__in=visited_ids).filter(
            latitude__gte=float(current.latitude) - deg_pad,
            latitude__lte=float(current.latitude) + deg_pad,
            longitude__gte=float(current.longitude) - deg_pad,
            longitude__lte=float(current.longitude) + deg_pad,
        )

        scored: list[tuple[float, int, Bar]] = []
        for bar in candidates_qs:
            d = haversine_m(
                current.latitude, current.longitude, bar.latitude, bar.longitude
            )
            if d > search_radius_m:
                continue
            step_cost = drink_cost(bar) + leg_travel_cost(mode)
            if step_cost > remaining:
                continue
            scored.append((d, step_cost, bar))

        if not scored:
            break

        # Greedy: nearest affordable bar wins
        scored.sort(key=lambda t: t[0])
        _d, cost, next_bar = scored[0]

        itinerary.append(next_bar)
        visited_ids.add(next_bar.id)
        remaining -= cost
        current = next_bar

    return itinerary


def crawl_cost_estimate(bars: Iterable[Bar], mode: str) -> dict:
    """Compute per-bar drink cost + travel cost totals for a crawl."""
    bars = list(bars)
    drink_total = sum(drink_cost(b) for b in bars)
    travel_total = leg_travel_cost(mode) * max(0, len(bars) - 1)
    return {
        "drink_total_cents": drink_total,
        "travel_total_cents": travel_total,
        "grand_total_cents": drink_total + travel_total,
        "per_bar_cents": {b.id: drink_cost(b) for b in bars},
    }


# --- Google Directions proxy --------------------------------------------

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"


def route_for_crawl(bar_ids: list[int], mode: str) -> dict:
    """
    Fetch a multi-stop route from Google Directions API.

    Returns:
      {
        total_distance_m, total_duration_sec, total_cost_cents,
        polyline,   # overview encoded polyline for the whole route
        legs: [{ from_bar, from_bar_name, to_bar, to_bar_name,
                 distance_m, duration_sec, cost_cents }, ...]
      }
    """
    if mode not in ALLOWED_MODES:
        raise ValueError(f"Invalid mode: {mode}")

    if len(bar_ids) < 2:
        return {
            "total_distance_m": 0,
            "total_duration_sec": 0,
            "total_cost_cents": 0,
            "polyline": "",
            "legs": [],
        }

    bars_map = {b.id: b for b in Bar.objects.filter(id__in=bar_ids)}
    missing = [bid for bid in bar_ids if bid not in bars_map]
    if missing:
        raise ValueError(f"Bars not found: {missing}")

    ordered = [bars_map[bid] for bid in bar_ids]
    api_key = settings.GOOGLE_MAPS_API_KEY
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY is not configured")

    origin = f"{ordered[0].latitude},{ordered[0].longitude}"
    destination = f"{ordered[-1].latitude},{ordered[-1].longitude}"
    waypoints = (
        "|".join(f"{b.latitude},{b.longitude}" for b in ordered[1:-1])
        if len(ordered) > 2
        else ""
    )

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "key": api_key,
    }
    if waypoints:
        params["waypoints"] = waypoints

    response = requests.get(DIRECTIONS_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        raise ValueError(
            f"Directions API status={data.get('status')}: "
            f"{data.get('error_message', '')}"
        )

    route = data["routes"][0]
    leg_payloads = route.get("legs", [])
    cost_per_leg = leg_travel_cost(mode)

    legs: list[dict] = []
    total_distance = 0
    total_duration = 0
    for i, leg in enumerate(leg_payloads):
        from_bar = ordered[i]
        to_bar = ordered[i + 1]
        dm = leg["distance"]["value"]
        ds = leg["duration"]["value"]
        legs.append(
            {
                "from_bar": from_bar.id,
                "from_bar_name": from_bar.name,
                "to_bar": to_bar.id,
                "to_bar_name": to_bar.name,
                "distance_m": dm,
                "duration_sec": ds,
                "cost_cents": cost_per_leg,
            }
        )
        total_distance += dm
        total_duration += ds

    return {
        "total_distance_m": total_distance,
        "total_duration_sec": total_duration,
        "total_cost_cents": cost_per_leg * len(legs),
        "polyline": route.get("overview_polyline", {}).get("points", ""),
        "legs": legs,
    }


def cached_route(bar_ids: list[int], mode: str) -> dict:
    """24h cache around route_for_crawl — same (mode, ordered ids) tuple wins."""
    key = f"crawl_route:{mode}:{','.join(str(b) for b in bar_ids)}"
    hit = cache.get(key)
    if hit is not None:
        return hit
    result = route_for_crawl(bar_ids, mode)
    cache.set(key, result, timeout=60 * 60 * 24)
    return result
