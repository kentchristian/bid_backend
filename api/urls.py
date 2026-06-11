from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InventoryViewSet, 
    SaleViewSet, 
    CategoryViewSet,
    SalesReportViewSet,
    InventoryReportViewSet,
    AIAssistantViewSet
)


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("category", CategoryViewSet, basename="category")
router.register("sales_report", SalesReportViewSet, basename="sales_report")
router.register("inventory_report", InventoryReportViewSet, basename="inventory_report")
router.register('ai', AIAssistantViewSet, basename='ai_assistant')



urlpatterns = [
    path("", include(router.urls)),
]
