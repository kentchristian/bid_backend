import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def api_client():
    """A clean API client for every test"""
    return APIClient()

@pytest.fixture
def test_user(db):
    """A standard user fixture to avoid repeating User.objects.create"""
    return User.objects.create_user(
        name="Kent Christian", 
        password="securepassword123",
        email="kent@example.com"
    )

@pytest.fixture
def inactive_user(db):
    """User fixture with is_active=False for inactive login scenario"""
    return User.objects.create_user(
        name="Inactive User",
        password="securepassword123",
        email="inactive@example.com",
        is_active=False,
    )
