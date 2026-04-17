from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InventoryViewSet, SaleViewSet


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("sales", SaleViewSet, basename="dashboard_metrics")
router.register("sales", SaleViewSet, basename="todays_top_hits")


router.register("inventory", InventoryViewSet, basename="inventory")
router.register("inventory", InventoryViewSet, basename="inventory_metrics")
router.register("inventory", InventoryViewSet, basename="sales_form_options")
router.register("inventory", InventoryViewSet, basename="inventory_by_category")



urlpatterns = [
    path("", include(router.urls)),
]
