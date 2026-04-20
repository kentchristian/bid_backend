from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied

from storefront.models import Inventory, Sale
from .serializers import (
    InventorySerializer, 
    SaleSerializer, 
    CreateSalesSerializer
)
from .permissions import RolePermissionRequired
from django.db import transaction

# Tenant Cache Helpers
from .utils.tenant_cache import (
    set_cache_key,
    get_tenant_cache,
    set_tenant_cache,
)

# import service
from .services.sales_service import (
    get_todays_top_hits
)
from .services.inventory_service import (
    get_sales_form_options,
    get_inventory_by_category,
    update_inventory_stock,
)
from .services.metrics_service import (
    compute_dashboard_metrics,
    compute_inventory_metrics,
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
        "sales_transaction": "create_sale",
    }

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        if not tenant:
            raise PermissionDenied("Tenant is required.")
        serializer.save(tenant=tenant, created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path='dashboard_metrics')
    def dashboard_metrics(self, request):
        #TODO Info -- Apply FilterBackground when scaling features, such as search and ordering
        sales = self.filter_queryset(self.get_queryset())

        tenant_id = request.user.tenant.id
        
        cache_key = set_cache_key("dashboard_metrics", tenant_id)
        cached = get_tenant_cache(cache_key)

        if cached is not None:
            return Response(cached) # Return cache if it hits match
        
        data = compute_dashboard_metrics(sales)
        set_tenant_cache(cache_key, data, 60) # Hold Data for 30 seconds
        #TODO: Invalidate cache on Create, Update, Delete Sales | Inventory 
        
        return Response(data)

    @action(detail=False, methods=["get"], url_path='todays_top_hits')
    def todays_top_hits(self, request):
        sales = self.get_queryset()
        return Response({
            "todays_top_hits": get_todays_top_hits(sales),
        })
    


    # Create Sales 
    @action(detail=False, methods=["post"], url_path='sales_transaction')
    def sales_transaction(self, request):
        #Transform data to flat_list 

        sold_at = request.data.get('sold_at')
        created_by = request.data.get('created_by')
        items_data = request.data.get('items')

        # inject header to every items
        for item in items_data:
            item['sold_at'] = sold_at
            item['created_by'] = created_by
        
        # Feed transformed data to serializer
        serializer = CreateSalesSerializer(
            data=items_data, 
            many=True, 
            context={'request': request}
        )

        # Perform validations
        if serializer.is_valid(raise_exception=True):
            with transaction.atomic():
                # 1. Bulk Create Sales
                
                data_to_create = [
                    Sale(**item) for item in serializer.validated_data
                ]

                # Bulk Application
                Sale.objects.bulk_create(data_to_create)
                
                # 2. Update Inventory and Collect Results
                summary = []
                for item in serializer.validated_data:
                    updated_inventory = update_inventory_stock(
                        inventory_id=item['inventory'].id,
                        quantity_change=item['quantity'],
                        tenant=request.user.tenant
                    )
                    
                    summary.append({
                        "product_name": updated_inventory.product_name,
                        "quantity_sold": item['quantity'],
                        "new_stock_level": updated_inventory.stock_quantity
                    })
            
            return Response({
                "message": "Transaction successfully created!",
                "updates": summary
            }, status=status.HTTP_201_CREATED)

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
        "inventory_metrics": "view_inventory",
        "sales_form_options": "view_inventory",
        "inventory_by_category": "view_inventory"
    }

    def perform_create(self, serializer):
        tenant = self.get_tenant()
        if not tenant:
            raise PermissionDenied("Tenant is required.")
        serializer.save(tenant=tenant)

    
    @action(detail=False, methods=["get"], url_path="inventory_metrics")
    def inventory_metrics(self, request):
        #TODO Info -- Apply FilterBackground when scaling features, such as search and ordering
        inventory = self.filter_queryset(self.get_queryset())

        tenant_id = request.user.tenant.id
        
        cache_key = set_cache_key("inventory_metrics", tenant_id)
        cached = get_tenant_cache(cache_key)

        if cached is not None:
            return Response(cached) # Return cache if it hits match
        data = compute_inventory_metrics(inventory)
        set_tenant_cache(cache_key, data, 60) # Hold Data for 60 seconds
        #TODO: Invalidate cache on Create, Update, Delete Sales | Inventory 
        
        return Response(data)

    # Sales Form Options [Categories, Users]
    @action(detail=False, methods=["get"], url_path="sales_form_options")
    def sales_form_options(self, request):
        inventory = self.filter_queryset(self.get_queryset())
        tenant_id = request.user.tenant.id
        data = get_sales_form_options(inventory)

        return Response(data)

    @action(detail=False, methods=["get"], url_path="inventory_by_category")
    def inventory_by_category(self, request):
        inventory = self.filter_queryset(self.get_queryset())
        tenant_id = request.user.tenant.id



        category = request.query_params.get('category')
        data = get_inventory_by_category(inventory, category)

        return Response(data)
       

    



