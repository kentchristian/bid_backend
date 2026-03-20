from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from storefront.models import Inventory, Sale
from .serializers import InventorySerializer, SaleSerializer
from .permissions import RolePermissionRequired


# import service
from .services.sales_service import (
    get_total_revenue, 
    get_total_units_sold, 
    get_sales_trend, 
    get_money_in_sales,
    get_todays_top_hits
)
from .services.inventory_service import (
    get_items_below_threshold, get_inventory_health
)
from rest_framework.decorators import action
from rest_framework.response import Response

class TenantScopedQuerysetMixin:
    def get_tenant(self):
        user = self.request.user
        if user and user.is_authenticated:
            return user.tenant
        return None

    def get_queryset(self):
        tenant = self.get_tenant()
        if not tenant:
            return self.queryset.none()
        return self.queryset.filter(tenant=tenant)


class SaleViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated, RolePermissionRequired]
    permission_map = {
        "list": "view_sale",
        "retrieve": "view_sale",
        "create": "create_sale",
        "update": "edit_sale",
        "partial_update": "edit_sale",
        "destroy": "delete_sale",

        # Function Based Permission
        "dashboard_metrics": "view_sale",
        "todays_top_hits": "view_sale",
    }

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        if not tenant:
            raise PermissionDenied("Tenant is required.")
        serializer.save(tenant=tenant, created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path='dashboard_metrics')
    def dashboard_metrics(self, request):
        sales = self.get_queryset()
        
        # Return everything in one dictionary
        return Response({
            "total_revenue": get_total_revenue(sales),
            "total_items": get_total_units_sold(sales),
            "trend_sales": get_sales_trend(sales),
            "money_in_sales": get_money_in_sales(sales),
        })
    
    @action(detail=False, methods=["get"], url_path='todays_top_hits')
    def todays_top_hits(self, request):
        sales = self.get_queryset()
        return Response({
            "todays_top_hits": get_todays_top_hits(sales),
        })
        


class InventoryViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, RolePermissionRequired]
    permission_map = {
        "list": "view_inventory",
        "retrieve": "view_inventory",
        "create": "create_inventory",
        "update": "edit_inventory",
        "partial_update": "edit_inventory",
        "destroy": "delete_inventory",


        #Function Based Permissions
        "inventory_metrics": "view_inventory"
    }

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        if not tenant:
            raise PermissionDenied("Tenant is required.")
        serializer.save(tenant=tenant)

    
    @action(detail=False, methods=["get"], url_path="inventory_metrics")
    def inventory_metrics(self, request):
        inventory = self.get_queryset()

        return Response({
            "items_below_threshold": get_items_below_threshold(inventory),
            "inventory_health": get_inventory_health(inventory),
        })

    @action(detail=False, methods=["get"], url_path="warehouse_status_inventory")
    def warehouse_status_inventory(self, request):
        inventory = self.get_queryset()

        return Response({
            "warehouse_stataus_inventory": ""
        })

    



