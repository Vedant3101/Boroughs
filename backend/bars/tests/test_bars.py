"""Bar API endpoint tests."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bars.models import Bar, Rating, Visit

User = get_user_model()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def bars(db) -> dict[str, Bar]:
    """A small fixture set covering price levels and Manhattan neighborhoods."""
    death_and_co = Bar.objects.create(
        place_id="test_death_and_co",
        name="Death & Co",
        address="433 E 6th St, New York, NY",
        borough="MAN",
        latitude=Decimal("40.7257"),
        longitude=Decimal("-73.9837"),
        price_level=3,
        google_rating=Decimal("4.5"),
    )
    employees_only = Bar.objects.create(
        place_id="test_employees_only",
        name="Employees Only",
        address="510 Hudson St, New York, NY",
        borough="MAN",
        latitude=Decimal("40.7331"),
        longitude=Decimal("-74.0050"),
        price_level=3,
        google_rating=Decimal("4.3"),
    )
    cheap_dive = Bar.objects.create(
        place_id="test_cheap_dive",
        name="Cheap Dive",
        address="100 Avenue A, New York, NY",
        borough="MAN",
        latitude=Decimal("40.7270"),
        longitude=Decimal("-73.9830"),
        price_level=1,
        google_rating=Decimal("4.0"),
    )
    fancy_lounge = Bar.objects.create(
        place_id="test_fancy_lounge",
        name="Fancy Lounge",
        address="1 W 67th St, New York, NY",
        borough="MAN",
        latitude=Decimal("40.7740"),
        longitude=Decimal("-73.9810"),
        price_level=4,
        google_rating=Decimal("4.7"),
    )
    return {
        "death_and_co": death_and_co,
        "employees_only": employees_only,
        "cheap_dive": cheap_dive,
        "fancy_lounge": fancy_lounge,
    }


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="a@example.com", password="verysecret123!"
    )


# --- list ----------------------------------------------------------------


@pytest.mark.django_db
def test_list_returns_all_bars(client: APIClient, bars: dict):
    response = client.get(reverse("bar-list"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 4


@pytest.mark.django_db
def test_list_filter_by_search(client: APIClient, bars: dict):
    response = client.get(reverse("bar-list"), {"search": "Death"})
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["name"] == "Death & Co"


@pytest.mark.django_db
def test_list_filter_by_price_range(client: APIClient, bars: dict):
    response = client.get(reverse("bar-list"), {"price_min": 1, "price_max": 2})
    assert response.status_code == status.HTTP_200_OK
    names = [b["name"] for b in response.data["results"]]
    assert "Cheap Dive" in names
    assert "Death & Co" not in names  # price 3
    assert "Fancy Lounge" not in names  # price 4


@pytest.mark.django_db
def test_list_filter_by_radius(client: APIClient, bars: dict):
    # Center on Death & Co; 1km radius should grab nearby East Village bars
    response = client.get(
        reverse("bar-list"),
        {"lat": 40.7257, "lng": -73.9837, "radius": 1000},
    )
    assert response.status_code == status.HTTP_200_OK
    names = [b["name"] for b in response.data["results"]]
    assert "Death & Co" in names
    assert "Cheap Dive" in names
    # West Village + Upper West are >1km away
    assert "Employees Only" not in names
    assert "Fancy Lounge" not in names


@pytest.mark.django_db
def test_list_ordering_by_distance(client: APIClient, bars: dict):
    response = client.get(
        reverse("bar-list"),
        {"lat": 40.7257, "lng": -73.9837, "radius": 50000, "ordering": "distance"},
    )
    assert response.status_code == status.HTTP_200_OK
    names = [b["name"] for b in response.data["results"]]
    # Death & Co is at the center → first
    assert names[0] == "Death & Co"


# --- detail --------------------------------------------------------------


@pytest.mark.django_db
def test_detail_returns_full_info_with_aggregates(
    client: APIClient, bars: dict, user: User
):
    bar = bars["death_and_co"]
    Rating.objects.create(user=user, bar=bar, score=5)
    Visit.objects.create(user=user, bar=bar, visited_at="2026-01-01T20:00:00Z")

    response = client.get(reverse("bar-detail", args=[bar.id]))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == "Death & Co"
    assert response.data["avg_user_rating"] == 5.0
    assert response.data["num_user_ratings"] == 1
    assert response.data["num_visits"] == 1


@pytest.mark.django_db
def test_detail_returns_zero_aggregates_for_untouched_bar(
    client: APIClient, bars: dict
):
    bar = bars["fancy_lounge"]
    response = client.get(reverse("bar-detail", args=[bar.id]))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["avg_user_rating"] is None
    assert response.data["num_user_ratings"] == 0
    assert response.data["num_visits"] == 0


@pytest.mark.django_db
def test_detail_404_for_missing_bar(client: APIClient):
    response = client.get(reverse("bar-detail", args=[99999]))
    assert response.status_code == status.HTTP_404_NOT_FOUND
