from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InventoryViewSet, SaleViewSet


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("sales/dashboard_metrics", SaleViewSet, basename="dashboard_metrics")
router.register("sales/todays_top_hits", SaleViewSet, basename="todays_top_hits")


router.register("inventory", InventoryViewSet, basename="inventory")
router.register("inventory/inventory_metrics", InventoryViewSet, basename="inventory_metrics")




urlpatterns = [
    path("", include(router.urls)),
]
