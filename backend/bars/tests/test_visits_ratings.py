"""Tests for /api/visits/ and /api/ratings/."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from bars.models import Bar, Rating, Visit

User = get_user_model()


@pytest.fixture
def bar(db) -> Bar:
    return Bar.objects.create(
        place_id="test_bar",
        name="Test Bar",
        address="1 Test St",
        borough="MAN",
        latitude=Decimal("40.7257"),
        longitude=Decimal("-73.9837"),
        price_level=2,
    )


@pytest.fixture
def other_bar(db) -> Bar:
    return Bar.objects.create(
        place_id="test_bar_2",
        name="Another Bar",
        address="2 Test St",
        borough="MAN",
        latitude=Decimal("40.7258"),
        longitude=Decimal("-73.9838"),
        price_level=2,
    )


@pytest.fixture
def alice(db) -> User:
    return User.objects.create_user(
        username="alice", email="a@example.com", password="verysecret123!"
    )


@pytest.fixture
def bob(db) -> User:
    return User.objects.create_user(
        username="bob", email="b@example.com", password="verysecret123!"
    )


@pytest.fixture
def auth(alice: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=alice)
    return c


@pytest.fixture
def auth_bob(bob: User) -> APIClient:
    c = APIClient()
    c.force_authenticate(user=bob)
    return c


# --- /api/visits/ ---------------------------------------------------------


@pytest.mark.django_db
def test_visits_require_auth():
    client = APIClient()
    assert client.get(reverse("visit-list-create")).status_code == 401
    assert client.post(reverse("visit-list-create"), {}).status_code == 401


@pytest.mark.django_db
def test_post_visit_creates_record(auth: APIClient, alice: User, bar: Bar):
    response = auth.post(
        reverse("visit-list-create"),
        {"bar": bar.id, "visited_at": "2026-01-01T20:00:00Z", "notes": "Great place"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Visit.objects.filter(user=alice, bar=bar).count() == 1
    assert response.data["bar_name"] == "Test Bar"


@pytest.mark.django_db
def test_visits_list_returns_only_own(
    auth: APIClient, alice: User, bob: User, bar: Bar
):
    Visit.objects.create(user=alice, bar=bar, visited_at="2026-01-01T20:00:00Z")
    Visit.objects.create(user=bob, bar=bar, visited_at="2026-01-01T20:00:00Z")
    response = auth.get(reverse("visit-list-create"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_delete_visit_removes_only_own(
    auth: APIClient, alice: User, bob: User, bar: Bar
):
    mine = Visit.objects.create(user=alice, bar=bar, visited_at="2026-01-01T20:00:00Z")
    not_mine = Visit.objects.create(
        user=bob, bar=bar, visited_at="2026-01-01T20:00:00Z"
    )
    assert auth.delete(reverse("visit-detail", args=[mine.id])).status_code == 204
    # Can't delete someone else's visit (it's not in queryset → 404)
    assert auth.delete(reverse("visit-detail", args=[not_mine.id])).status_code == 404
    assert Visit.objects.filter(id=not_mine.id).exists()


# --- /api/ratings/ --------------------------------------------------------


@pytest.mark.django_db
def test_ratings_require_auth():
    client = APIClient()
    assert client.get(reverse("rating-list-create")).status_code == 401
    assert client.post(reverse("rating-list-create"), {}).status_code == 401


@pytest.mark.django_db
def test_post_rating_creates_new(auth: APIClient, alice: User, bar: Bar):
    response = auth.post(
        reverse("rating-list-create"),
        {"bar": bar.id, "score": 5, "comment": "Loved it"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert Rating.objects.filter(user=alice, bar=bar).count() == 1
    assert response.data["score"] == 5


@pytest.mark.django_db
def test_post_rating_upserts_existing(auth: APIClient, alice: User, bar: Bar):
    """POSTing the same (user, bar) twice updates instead of creating a duplicate."""
    auth.post(
        reverse("rating-list-create"),
        {"bar": bar.id, "score": 3},
        format="json",
    )
    response = auth.post(
        reverse("rating-list-create"),
        {"bar": bar.id, "score": 5, "comment": "Changed my mind"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK  # 200, not 201, on update
    assert Rating.objects.filter(user=alice, bar=bar).count() == 1
    rating = Rating.objects.get(user=alice, bar=bar)
    assert rating.score == 5
    assert rating.comment == "Changed my mind"


@pytest.mark.django_db
def test_patch_rating_partial_update(auth: APIClient, alice: User, bar: Bar):
    rating = Rating.objects.create(user=alice, bar=bar, score=3, comment="meh")
    response = auth.patch(
        reverse("rating-detail", args=[rating.id]),
        {"score": 4},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    rating.refresh_from_db()
    assert rating.score == 4
    assert rating.comment == "meh"  # untouched


@pytest.mark.django_db
def test_ratings_list_returns_only_own(
    auth: APIClient, alice: User, bob: User, bar: Bar
):
    Rating.objects.create(user=alice, bar=bar, score=5)
    Rating.objects.create(user=bob, bar=bar, score=2)
    response = auth.get(reverse("rating-list-create"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_rating_score_validation(auth: APIClient, bar: Bar):
    response = auth.post(
        reverse("rating-list-create"),
        {"bar": bar.id, "score": 7},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_bar_detail_aggregates_reflect_ratings_and_visits(
    auth: APIClient, alice: User, bob: User, bar: Bar
):
    Rating.objects.create(user=alice, bar=bar, score=5)
    Rating.objects.create(user=bob, bar=bar, score=3)
    Visit.objects.create(user=alice, bar=bar, visited_at="2026-01-01T20:00:00Z")
    response = auth.get(reverse("bar-detail", args=[bar.id]))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["avg_user_rating"] == 4.0
    assert response.data["num_user_ratings"] == 2
    assert response.data["num_visits"] == 1
