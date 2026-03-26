import pytest
from django.contrib.auth import get_user_model
from rest_framework import status


User = get_user_model()


@pytest.mark.django_db
def test_signup_success(api_client):
    payload = {
        "email": "new.user@example.com",
        "name": "New User",
        "password": "Secur3Passw0rd!",
    }
    response = api_client.post("/auth/signup/", payload, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "Signup successfully"
    assert "id" in response.data

    user = User.objects.get(email="new.user@example.com")
    assert user.name == "New User"
    assert user.check_password("Secur3Passw0rd!")


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload, error_field",
    [
        ({"email": "", "name": "Name", "password": "Secur3Passw0rd!"}, "email"),
        ({"email": "a@b.com", "name": "", "password": "Secur3Passw0rd!"}, "name"),
        ({"email": "a@b.com", "name": "Name", "password": ""}, "password"),
    ],
)
def test_signup_missing_fields(api_client, payload, error_field):
    response = api_client.post("/auth/signup/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert error_field in response.data


@pytest.mark.django_db
def test_signup_invalid_email(api_client):
    payload = {
        "email": "not-an-email",
        "name": "Email Test",
        "password": "Secur3Passw0rd!",
    }
    response = api_client.post("/auth/signup/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


@pytest.mark.django_db
def test_signup_duplicate_email(api_client, test_user):
    payload = {
        "email": "kent@example.com",
        "name": "Another Kent",
        "password": "Secur3Passw0rd!",
    }
    response = api_client.post("/auth/signup/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "email" in response.data


@pytest.mark.django_db
def test_signup_weak_password(api_client):
    payload = {
        "email": "weak.pass@example.com",
        "name": "Weak Pass",
        "password": "short",
    }
    response = api_client.post("/auth/signup/", payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "password" in response.data
