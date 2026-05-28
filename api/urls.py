from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InventoryViewSet, 
    SaleViewSet, 
    CategoryViewSet,
    ReportsViewSet)


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("category", CategoryViewSet, basename="category")
router.register("reports", ReportsViewSet, basename="reports")




urlpatterns = [
    path("", include(router.urls)),
]
