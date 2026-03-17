from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InventoryViewSet, SaleViewSet


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("sales/total_revenue", SaleViewSet, basename="total_revenue")


router.register("inventory", InventoryViewSet, basename="inventory")



urlpatterns = [
    path("", include(router.urls)),
]
