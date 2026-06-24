from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InventoryViewSet, 
    SaleViewSet, 
    CategoryViewSet,
    SalesReportViewSet,
    InventoryReportViewSet,
    AIAssistantViewSet,
    AIPrompterViewSet,
)


router = DefaultRouter()
router.register("sales", SaleViewSet, basename="sale")
router.register("inventory", InventoryViewSet, basename="inventory")
router.register("category", CategoryViewSet, basename="category")
router.register("sales_report", SalesReportViewSet, basename="sales_report")
router.register("inventory_report", InventoryReportViewSet, basename="inventory_report")
router.register("ai_assistant", AIAssistantViewSet, basename="ai_assistant")
router.register("ai_assisant", AIAssistantViewSet, basename="ai_assistant_legacy")
router.register("ai_prompter", AIPrompterViewSet, basename="ai_prompter")
router.register("bim_prompter", AIPrompterViewSet, basename="bim_prompter_legacy")



urlpatterns = [
    path("", include(router.urls)),
]
