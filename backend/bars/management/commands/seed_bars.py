"""
Seed the Bar table from Google Places API (Nearby Search, v1).

We search several points across each NYC borough and upsert by place_id.
Run with:
    python manage.py seed_bars               # all boroughs
    python manage.py seed_bars --borough MAN # only Manhattan
    python manage.py seed_bars --dry-run     # don't write to DB
"""
from __future__ import annotations

import time
from decimal import Decimal
from typing import Iterable

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bars.models import Bar

PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.shortFormattedAddress",
        "places.location",
        "places.priceLevel",
        "places.rating",
        "places.userRatingCount",
        "places.nationalPhoneNumber",
        "places.websiteUri",
    ]
)

# Google's new Places API returns priceLevel as a string enum.
PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

# Place types we count as "bars" for our purposes.
INCLUDED_TYPES = ["bar", "pub", "night_club", "wine_bar", "bar_and_grill"]

# Search points across Manhattan. Each ~1000m radius circle. Overlap is fine, dedupe by place_id.
# Other boroughs are commented out — uncomment to expand coverage later.
SEARCH_POINTS: list[tuple[str, str, float, float]] = [
    # (borough_code, label, lat, lng)
    ("MAN", "Financial District", 40.7075, -74.0090),
    ("MAN", "Tribeca", 40.7195, -74.0066),
    ("MAN", "SoHo", 40.7235, -74.0030),
    ("MAN", "NoLita", 40.7222, -73.9956),
    ("MAN", "Chinatown", 40.7160, -73.9970),
    ("MAN", "Lower East Side", 40.7180, -73.9870),
    ("MAN", "East Village", 40.7282, -73.9842),
    ("MAN", "Alphabet City", 40.7253, -73.9779),
    ("MAN", "Greenwich Village", 40.7336, -74.0027),
    ("MAN", "West Village", 40.7358, -74.0036),
    ("MAN", "Meatpacking", 40.7398, -74.0079),
    ("MAN", "Chelsea", 40.7465, -74.0014),
    ("MAN", "Flatiron", 40.7411, -73.9897),
    ("MAN", "Gramercy", 40.7368, -73.9845),
    ("MAN", "Kips Bay", 40.7426, -73.9794),
    ("MAN", "Murray Hill", 40.7479, -73.9755),
    ("MAN", "Hell's Kitchen", 40.7638, -73.9918),
    ("MAN", "Midtown East", 40.7549, -73.9700),
    ("MAN", "Midtown West", 40.7549, -73.9840),
    ("MAN", "Times Square", 40.7580, -73.9855),
    ("MAN", "Upper East Side South", 40.7700, -73.9620),
    ("MAN", "Upper East Side North", 40.7795, -73.9525),
    ("MAN", "Upper West Side South", 40.7790, -73.9810),
    ("MAN", "Upper West Side North", 40.7910, -73.9720),
    ("MAN", "Morningside Heights", 40.8075, -73.9626),
    ("MAN", "Harlem", 40.8116, -73.9465),
    ("MAN", "East Harlem", 40.7957, -73.9389),
    ("MAN", "Washington Heights", 40.8417, -73.9393),
    ("MAN", "Inwood", 40.8676, -73.9212),
]

DEFAULT_RADIUS_M = 1000
DEFAULT_MAX_RESULTS = 20


class Command(BaseCommand):
    help = "Seed the Bar table from Google Places API."

    def add_arguments(self, parser):
        parser.add_argument(
            "--borough",
            choices=[code for code, *_ in {(c, l) for c, l, *_ in SEARCH_POINTS}],
            help="Only seed one borough (MAN/BRK/QNS/BRX/STI). Default: all.",
        )
        parser.add_argument(
            "--radius",
            type=int,
            default=DEFAULT_RADIUS_M,
            help=f"Search radius in meters (default {DEFAULT_RADIUS_M}).",
        )
        parser.add_argument(
            "--max-results",
            type=int,
            default=DEFAULT_MAX_RESULTS,
            help=f"Max results per search point (default {DEFAULT_MAX_RESULTS}, API cap 20).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and parse, but don't write to the DB.",
        )
        parser.add_argument(
            "--skip-text-search",
            action="store_true",
            help="Skip the Text Search pass (Nearby Search only).",
        )

    def handle(self, *args, **options):
        api_key = settings.GOOGLE_MAPS_API_KEY
        if not api_key:
            raise CommandError("GOOGLE_MAPS_API_KEY is not set in .env")

        borough_filter = options.get("borough")
        radius = options["radius"]
        max_results = min(options["max_results"], 20)
        dry_run = options["dry_run"]
        skip_text = options["skip_text_search"]

        points = [
            p for p in SEARCH_POINTS if not borough_filter or p[0] == borough_filter
        ]

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Seeding from {len(points)} search points "
                f"(radius={radius}m, max={max_results}/point, dry_run={dry_run})"
            )
        )

        created = 0
        updated = 0
        seen_place_ids: set[str] = set()

        for borough, label, lat, lng in points:
            self.stdout.write(f"  → {label} ({borough}) at ({lat}, {lng})")

            # Pass 1: Nearby Search (catches places where bar is a primary type)
            self._run_pass(
                label=f"    nearby",
                fetcher=lambda: self._fetch_nearby(api_key, lat, lng, radius, max_results),
                borough=borough,
                seen=seen_place_ids,
                dry_run=dry_run,
                stats=(c := [0, 0, 0]),  # [new_count, created, updated]
            )
            created += c[1]
            updated += c[2]

            # Pass 2+: Text Search variations (catches the long tail Nearby Search misses)
            if not skip_text:
                for query in (
                    f"bars in {label} Manhattan",
                    f"cocktail bars in {label} Manhattan",
                ):
                    self._run_pass(
                        label=f"    text [{query[:32]}…]",
                        fetcher=lambda q=query: self._fetch_text(
                            api_key, q, lat, lng, radius, max_results
                        ),
                        borough=borough,
                        seen=seen_place_ids,
                        dry_run=dry_run,
                        stats=(c := [0, 0, 0]),
                    )
                    created += c[1]
                    updated += c[2]

            # Be polite to the API
            time.sleep(0.2)

        summary = (
            f"Done. {len(seen_place_ids)} unique bars "
            f"(created={created}, updated={updated}, dry_run={dry_run})"
        )
        self.stdout.write(self.style.SUCCESS(summary))

    # --- helpers -----------------------------------------------------------

    def _run_pass(self, label, fetcher, borough, seen, dry_run, stats):
        """Execute one fetch + upsert pass. Mutates `seen` and `stats` in place."""
        try:
            places = fetcher()
        except requests.HTTPError as e:
            self.stderr.write(
                self.style.ERROR(
                    f"{label} HTTP error: {e.response.status_code} {e.response.text[:200]}"
                )
            )
            return
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"{label} request failed: {e}"))
            return

        new_this_round = 0
        for raw in places:
            place_id = raw.get("id")
            if not place_id or place_id in seen:
                continue
            seen.add(place_id)

            fields = self._parse_place(raw, borough)
            if not fields:
                continue

            if dry_run:
                new_this_round += 1
                stats[0] += 1
                continue

            _, was_created = Bar.objects.update_or_create(
                place_id=place_id, defaults=fields
            )
            if was_created:
                stats[1] += 1
            else:
                stats[2] += 1
            new_this_round += 1
            stats[0] += 1

        self.stdout.write(f"{label}: +{new_this_round} new")

    def _fetch_nearby(
        self, api_key: str, lat: float, lng: float, radius: int, max_results: int
    ) -> Iterable[dict]:
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }
        body = {
            "includedTypes": INCLUDED_TYPES,
            "maxResultCount": max_results,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": float(radius),
                }
            },
        }
        response = requests.post(PLACES_NEARBY_URL, headers=headers, json=body, timeout=15)
        response.raise_for_status()
        return response.json().get("places", [])

    def _fetch_text(
        self,
        api_key: str,
        query: str,
        lat: float,
        lng: float,
        radius: int,
        max_results: int,
    ) -> Iterable[dict]:
        """Paginated text search — fetches up to 3 pages (60 results) per query."""
        # Text Search supports pageToken with FieldMask requiring nextPageToken
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": f"{FIELD_MASK},nextPageToken",
        }
        all_places: list[dict] = []
        page_token: str | None = None

        for _ in range(3):
            body: dict = {
                "textQuery": query,
                "maxResultCount": max_results,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": float(radius),
                    }
                },
            }
            if page_token:
                body["pageToken"] = page_token
                # Google's nextPageToken sometimes needs a moment to become valid
                time.sleep(1)

            response = requests.post(
                PLACES_TEXT_URL, headers=headers, json=body, timeout=15
            )
            response.raise_for_status()
            data = response.json()
            all_places.extend(data.get("places", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_places

    def _parse_place(self, raw: dict, borough: str) -> dict | None:
        loc = raw.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is None or lng is None:
            return None

        name = (raw.get("displayName") or {}).get("text") or "Unknown"

        return {
            "name": name[:255],
            "address": (raw.get("formattedAddress") or raw.get("shortFormattedAddress") or "")[:500],
            "borough": borough,
            "latitude": Decimal(str(lat)).quantize(Decimal("0.000001")),
            "longitude": Decimal(str(lng)).quantize(Decimal("0.000001")),
            "price_level": PRICE_LEVEL_MAP.get(raw.get("priceLevel")),
            "phone": (raw.get("nationalPhoneNumber") or "")[:32],
            "website": (raw.get("websiteUri") or "")[:500],
            "google_rating": (
                Decimal(str(raw["rating"])).quantize(Decimal("0.1"))
                if raw.get("rating") is not None
                else None
            ),
            "google_rating_count": raw.get("userRatingCount"),
        }
