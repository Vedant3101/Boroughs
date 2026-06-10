"""
End-to-end backend integration test.

Walks through the full Week-1 backend flow that the frontend will mirror:
  1. health check
  2. register a new user
  3. login → token pair
  4. list bars (anonymous OK), then filtered (price + radius)
  5. mark a visit
  6. rate the bar
  7. update the rating (POST upsert)
  8. fetch bar detail → confirm aggregates reflect the visit + rating
  9. fetch /me → confirm we're authenticated
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bars.models import Bar


@pytest.fixture
def seeded_bars(db):
    Bar.objects.create(
        place_id="i_bar_1",
        name="The Local",
        address="100 7th Ave",
        borough="MAN",
        latitude=Decimal("40.7400"),
        longitude=Decimal("-74.0000"),
        price_level=1,
    )
    target = Bar.objects.create(
        place_id="i_bar_2",
        name="The Hideaway",
        address="200 7th Ave",
        borough="MAN",
        latitude=Decimal("40.7405"),
        longitude=Decimal("-74.0005"),
        price_level=3,
    )
    Bar.objects.create(
        place_id="i_bar_3",
        name="Faraway",
        address="999 Broadway",
        borough="MAN",
        latitude=Decimal("40.8000"),
        longitude=Decimal("-73.9000"),
        price_level=2,
    )
    return target


@pytest.mark.django_db
def test_full_backend_flow(seeded_bars):
    target_bar = seeded_bars
    client = APIClient()

    # 1. health
    r = client.get(reverse("health"))
    assert r.status_code == 200
    assert r.data["database"] is True

    # 2. register
    r = client.post(
        reverse("register"),
        {
            "username": "newuser",
            "email": "new@example.com",
            "password": "verysecret123!",
            "password_confirm": "verysecret123!",
        },
        format="json",
    )
    assert r.status_code == status.HTTP_201_CREATED
    access = r.data["access"]

    # 3. login (verify it works independently)
    r = client.post(
        reverse("login"),
        {"username": "newuser", "password": "verysecret123!"},
        format="json",
    )
    assert r.status_code == 200
    access = r.data["access"]

    # 4a. list bars (anonymous) — should work
    r = client.get(reverse("bar-list"))
    assert r.status_code == 200
    assert r.data["count"] == 3

    # 4b. filter by price (only price 1)
    r = client.get(reverse("bar-list"), {"price_max": 1})
    assert r.data["count"] == 1

    # 4c. radius around target bar — should grab The Local + The Hideaway
    r = client.get(
        reverse("bar-list"),
        {"lat": 40.7400, "lng": -74.0000, "radius": 1000, "ordering": "distance"},
    )
    names = [b["name"] for b in r.data["results"]]
    assert "The Local" in names
    assert "The Hideaway" in names
    assert "Faraway" not in names

    # Auth from here on
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    # 5. mark a visit
    r = client.post(
        reverse("visit-list-create"),
        {
            "bar": target_bar.id,
            "visited_at": "2026-01-15T20:00:00Z",
            "notes": "First time here",
        },
        format="json",
    )
    assert r.status_code == status.HTTP_201_CREATED

    # 6. rate the bar
    r = client.post(
        reverse("rating-list-create"),
        {"bar": target_bar.id, "score": 4, "comment": "Solid"},
        format="json",
    )
    assert r.status_code == status.HTTP_201_CREATED

    # 7. update the rating (POST upsert → 200, not 201)
    r = client.post(
        reverse("rating-list-create"),
        {"bar": target_bar.id, "score": 5, "comment": "Actually amazing"},
        format="json",
    )
    assert r.status_code == status.HTTP_200_OK

    # 8. bar detail reflects aggregates
    r = client.get(reverse("bar-detail", args=[target_bar.id]))
    assert r.status_code == 200
    assert r.data["avg_user_rating"] == 5.0
    assert r.data["num_user_ratings"] == 1
    assert r.data["num_visits"] == 1

    # 9. /me works
    r = client.get(reverse("me"))
    assert r.status_code == 200
    assert r.data["username"] == "newuser"
