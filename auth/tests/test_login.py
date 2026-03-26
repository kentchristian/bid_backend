import pytest
from rest_framework import status


# Happy Path  
@pytest.mark.django_db
def test_login_success(api_client, test_user):
    payload = {
        "email": "kent@example.com",
        "password": "securepassword123"
    }
    response = api_client.post('/auth/login/', payload, format="json")
    
    # Simple Pytest Assertions
    assert response.status_code == status.HTTP_200_OK
    assert response.data['message'] == "Login successfully"


  
# Probabilities 
@pytest.mark.django_db
@pytest.mark.parametrize(
    "email, password, expected_status",
    [
        ("kent@example.com", "wrong_pass", status.HTTP_401_UNAUTHORIZED),   # Wrong Password
        ("something@example.com", "securepassword123", status.HTTP_401_UNAUTHORIZED), # Wrong User
        ("", "", status.HTTP_400_BAD_REQUEST), # Empty Fields
    ]
)
def test_login_failure_scenarios(api_client, test_user, email, password, expected_status):
    """Runs 3 times with the different data sets above!"""
    payload = {"email": email, "password": password}
    response = api_client.post('/auth/login/', payload, format="json")
    
    assert response.status_code == expected_status

    # Standard DRF error payload uses "detail" for auth failures
    if expected_status == status.HTTP_401_UNAUTHORIZED:
        assert "detail" in response.data


@pytest.mark.django_db
def test_login_inactive_user(api_client, inactive_user):
    payload = {"email": "inactive@example.com", "password": "securepassword123"}
    response = api_client.post('/auth/login/', payload, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED # 401 By design and production choice don't allow user to authenticate if is_active=False
    assert response.data["detail"] == "Invalid credentials" 
