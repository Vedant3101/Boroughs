"""Auth endpoint tests."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        username="alice", email="alice@example.com", password="verysecret123!"
    )


@pytest.fixture
def auth_client(client: APIClient, user: User) -> APIClient:
    """An API client with a valid access token for `user` attached."""
    response = client.post(
        reverse("login"),
        {"username": "alice", "password": "verysecret123!"},
        format="json",
    )
    assert response.status_code == 200
    access = response.data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


# --- /api/auth/register/ -------------------------------------------------


@pytest.mark.django_db
def test_register_creates_user_and_returns_tokens(client: APIClient):
    response = client.post(
        reverse("register"),
        {
            "username": "bob",
            "email": "bob@example.com",
            "password": "verysecret123!",
            "password_confirm": "verysecret123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user"]["username"] == "bob"
    assert "access" in response.data
    assert "refresh" in response.data
    assert User.objects.filter(username="bob").exists()


@pytest.mark.django_db
def test_register_rejects_password_mismatch(client: APIClient):
    response = client.post(
        reverse("register"),
        {
            "username": "bob",
            "email": "bob@example.com",
            "password": "verysecret123!",
            "password_confirm": "different!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password_confirm" in response.data


@pytest.mark.django_db
def test_register_rejects_weak_password(client: APIClient):
    response = client.post(
        reverse("register"),
        {
            "username": "bob",
            "email": "bob@example.com",
            "password": "123",
            "password_confirm": "123",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data


@pytest.mark.django_db
def test_register_rejects_duplicate_username(client: APIClient, user: User):
    response = client.post(
        reverse("register"),
        {
            "username": "alice",
            "email": "different@example.com",
            "password": "verysecret123!",
            "password_confirm": "verysecret123!",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# --- /api/auth/login/ ----------------------------------------------------


@pytest.mark.django_db
def test_login_returns_token_pair(client: APIClient, user: User):
    response = client.post(
        reverse("login"),
        {"username": "alice", "password": "verysecret123!"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_login_rejects_bad_password(client: APIClient, user: User):
    response = client.post(
        reverse("login"),
        {"username": "alice", "password": "wrong"},
        format="json",
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# --- /api/auth/refresh/ --------------------------------------------------


@pytest.mark.django_db
def test_refresh_returns_new_access_token(client: APIClient, user: User):
    login = client.post(
        reverse("login"),
        {"username": "alice", "password": "verysecret123!"},
        format="json",
    )
    refresh_token = login.data["refresh"]

    response = client.post(
        reverse("token_refresh"), {"refresh": refresh_token}, format="json"
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data


# --- /api/auth/me/ -------------------------------------------------------


@pytest.mark.django_db
def test_me_requires_auth(client: APIClient):
    response = client.get(reverse("me"))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_returns_current_user(auth_client: APIClient, user: User):
    response = auth_client.get(reverse("me"))
    assert response.status_code == status.HTTP_200_OK
    assert response.data["username"] == "alice"
    assert response.data["email"] == "alice@example.com"
    assert response.data["id"] == user.id
