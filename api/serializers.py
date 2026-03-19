from rest_framework import serializers

from storefront.models import Inventory, Sale, Tenant

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name"]


class SaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sale
        fields = [
            "id",
            "tenant",
            "inventory",
            "quantity",
            "unit_price",
            "total_price",
            "sold_at",
            "created_by",
        ]
        read_only_fields = ["id", "tenant", "created_by"]


class InventorySerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "tenant",
            "product_name",
            "stock_quantity",
            "reorder_threshold",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
