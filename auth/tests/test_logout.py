import pytest
from rest_framework import status


@pytest.mark.django_db
def test_logout_success(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    response = api_client.post('/auth/logout/', format="json")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["message"] == "Logout successfully"


@pytest.mark.django_db
def test_logout_requires_auth(api_client):
    response = api_client.post('/auth/logout/', format="json")

    # With SessionAuthentication first, DRF returns 403 when unauthenticated
    assert response.status_code == status.HTTP_403_FORBIDDEN
