"""Pub crawl generator + routing endpoint tests."""
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bars.models import Bar
from crawls.services import (
    crawl_cost_estimate,
    drink_cost,
    generate_crawl,
    haversine_m,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="a@example.com", password="verysecret123!"
    )


@pytest.fixture
def auth(user: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=user)
    return c


@pytest.fixture
def bars(db) -> dict[str, Bar]:
    """A tight cluster of bars in the East Village with varying prices."""
    def make(name, lat, lng, price):
        return Bar.objects.create(
            place_id=f"test_{name.replace(' ', '_').lower()}",
            name=name,
            address=f"{name} address",
            borough="MAN",
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
            price_level=price,
        )

    return {
        "start":      make("Start Bar",     40.7257, -73.9837, 2),
        "nearby_1":   make("Nearby One",    40.7260, -73.9830, 1),
        "nearby_2":   make("Nearby Two",    40.7265, -73.9842, 2),
        "nearby_3":   make("Nearby Three",  40.7270, -73.9820, 3),
        "expensive":  make("Pricey Place",  40.7252, -73.9850, 4),
        "far":        make("Far Away",      40.8200, -73.9100, 1),  # ~10km away
    }


# --- Services ------------------------------------------------------------


def test_haversine_known_distance():
    # Empire State Building → Statue of Liberty ≈ 8.4 km
    d = haversine_m(40.7484, -73.9857, 40.6892, -74.0445)
    assert 8000 < d < 9000


def test_drink_cost_by_price_level():
    b = Bar(price_level=1)
    assert drink_cost(b) == 800
    b = Bar(price_level=4)
    assert drink_cost(b) == 3500
    b = Bar(price_level=None)
    assert drink_cost(b) == 1500  # default


@pytest.mark.django_db
def test_generate_crawl_returns_start_alone_if_max_stops_one(bars):
    result = generate_crawl(
        start_bar=bars["start"], budget_cents=10_000, mode="walking", max_stops=1
    )
    assert result == [bars["start"]]


@pytest.mark.django_db
def test_generate_crawl_picks_nearest_affordable_first(bars):
    result = generate_crawl(
        start_bar=bars["start"], budget_cents=10_000, mode="walking", max_stops=3
    )
    # Should start at Start Bar and pick by proximity
    assert result[0] == bars["start"]
    assert len(result) >= 2
    # First hop should be one of the nearby bars (not the far one)
    assert result[1] in (bars["nearby_1"], bars["nearby_2"], bars["nearby_3"])


@pytest.mark.django_db
def test_generate_crawl_respects_search_radius(bars):
    """The 'far' bar is 10km away — it should never appear with default radius."""
    result = generate_crawl(
        start_bar=bars["start"],
        budget_cents=100_000,
        mode="walking",
        max_stops=10,
        search_radius_m=2000,
    )
    assert bars["far"] not in result


@pytest.mark.django_db
def test_generate_crawl_respects_budget(bars):
    """A budget that fits only ~2 cheap drinks should stop after a couple stops."""
    # Budget = $10 (1000c). Start is price 2 ($14 estimate = 1400c).
    # That alone is over budget but algorithm still returns the start.
    result = generate_crawl(
        start_bar=bars["start"], budget_cents=1000, mode="walking", max_stops=5
    )
    assert result == [bars["start"]]


@pytest.mark.django_db
def test_crawl_cost_estimate(bars):
    estimate = crawl_cost_estimate(
        [bars["start"], bars["nearby_1"], bars["nearby_3"]], "walking"
    )
    # 1400 + 800 + 2200 = 4400 drinks, 0 travel walking
    assert estimate["drink_total_cents"] == 4400
    assert estimate["travel_total_cents"] == 0
    assert estimate["grand_total_cents"] == 4400


@pytest.mark.django_db
def test_crawl_cost_estimate_transit_adds_per_leg_fare(bars):
    estimate = crawl_cost_estimate(
        [bars["start"], bars["nearby_1"], bars["nearby_3"]], "transit"
    )
    # 2 legs × 290 = 580
    assert estimate["travel_total_cents"] == 580
    assert estimate["grand_total_cents"] == 4400 + 580


# --- /api/crawls/generate ------------------------------------------------


@pytest.mark.django_db
def test_generate_requires_auth(bars):
    client = APIClient()
    response = client.post(
        reverse("crawl-generate"),
        {"start_bar": bars["start"].id, "budget_cents": 5000},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_generate_returns_ordered_bars(auth: APIClient, bars):
    response = auth.post(
        reverse("crawl-generate"),
        {
            "start_bar": bars["start"].id,
            "budget_cents": 10_000,
            "mode": "walking",
            "max_stops": 3,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["bars"][0]["id"] == bars["start"].id
    assert len(response.data["bars"]) >= 2
    assert "grand_total_cents" in response.data


@pytest.mark.django_db
def test_generate_404_for_missing_bar(auth: APIClient):
    response = auth.post(
        reverse("crawl-generate"),
        {"start_bar": 99999, "budget_cents": 5000},
        format="json",
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_generate_rejects_budget_below_start_drink_cost(
    auth: APIClient, bars
):
    response = auth.post(
        reverse("crawl-generate"),
        {"start_bar": bars["start"].id, "budget_cents": 500, "mode": "walking"},
        format="json",
    )
    assert response.status_code == 400


# --- /api/crawls/route ---------------------------------------------------


def fake_directions_response():
    return {
        "status": "OK",
        "routes": [
            {
                "overview_polyline": {"points": "encoded_polyline_stub"},
                "legs": [
                    {
                        "distance": {"value": 500, "text": "500 m"},
                        "duration": {"value": 360, "text": "6 mins"},
                    },
                    {
                        "distance": {"value": 700, "text": "700 m"},
                        "duration": {"value": 510, "text": "8 mins"},
                    },
                ],
            }
        ],
    }


@pytest.mark.django_db
def test_route_requires_auth(bars):
    client = APIClient()
    response = client.post(
        reverse("crawl-route"),
        {"bar_ids": [bars["start"].id, bars["nearby_1"].id]},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
@patch("crawls.services.requests.get")
def test_route_returns_aggregates_and_polyline(
    mock_get, auth: APIClient, bars
):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = fake_directions_response()
    mock_get.return_value.raise_for_status = lambda: None

    response = auth.post(
        reverse("crawl-route"),
        {
            "bar_ids": [
                bars["start"].id,
                bars["nearby_1"].id,
                bars["nearby_2"].id,
            ],
            "mode": "walking",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["total_distance_m"] == 1200
    assert response.data["total_duration_sec"] == 870
    assert response.data["polyline"] == "encoded_polyline_stub"
    assert len(response.data["legs"]) == 2
    assert response.data["legs"][0]["from_bar"] == bars["start"].id
    assert response.data["legs"][0]["to_bar"] == bars["nearby_1"].id


@pytest.mark.django_db
@patch("crawls.services.requests.get")
def test_route_transit_includes_fare_per_leg(mock_get, auth: APIClient, bars):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = fake_directions_response()
    mock_get.return_value.raise_for_status = lambda: None

    response = auth.post(
        reverse("crawl-route"),
        {
            "bar_ids": [bars["start"].id, bars["nearby_1"].id, bars["nearby_2"].id],
            "mode": "transit",
        },
        format="json",
    )
    assert response.status_code == 200
    # 2 legs × 290c = 580c
    assert response.data["total_cost_cents"] == 580
    assert response.data["legs"][0]["cost_cents"] == 290


@pytest.mark.django_db
@patch("crawls.services.requests.get")
def test_route_caches_results(mock_get, auth: APIClient, bars):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = fake_directions_response()
    mock_get.return_value.raise_for_status = lambda: None

    body = {
        "bar_ids": [bars["start"].id, bars["nearby_1"].id, bars["nearby_2"].id],
        "mode": "walking",
    }
    r1 = auth.post(reverse("crawl-route"), body, format="json")
    r2 = auth.post(reverse("crawl-route"), body, format="json")
    assert r1.status_code == 200 and r2.status_code == 200
    # Second call should be served from cache, not hit the API
    assert mock_get.call_count == 1


@pytest.mark.django_db
def test_route_rejects_short_input(auth: APIClient, bars):
    response = auth.post(
        reverse("crawl-route"),
        {"bar_ids": [bars["start"].id], "mode": "walking"},
        format="json",
    )
    assert response.status_code == 400
