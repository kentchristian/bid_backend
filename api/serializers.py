from rest_framework import serializers

from storefront.models import Inventory, Sale, Category
from accounts.models import User, Tenant

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name"]

class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    class Meta: 
        model = User 
        fields = ['id', 'name', 'tenant', 'role', 'is_active']

class CategorySerializer(serializers.ModelSerializer):
  class Meta:
    model = Category
    fields = [
      "id",
      "name"
    ]

class InventorySerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "id",
            "tenant",
            "product_name",
            "category",
            "stock_quantity",
            "max_quantity",
            "reorder_threshold",
            "updated_at",
            "unit_price",
        ]
        read_only_fields = ["id", "updated_at"]

class SaleSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(read_only=True)
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
        

class ProductSerializer(serializers.ModelSerializer):
  class Meta:
    model = Inventory
    fields = [
      'id',
      'product_name',
      'category',
      'stock_quantity',
      'reorder_threshold',
      'updated_at',
      'unit_price',
    ]

class MoneyInSalesSerializer(serializers.ModelSerializer):
  tenant = TenantSerializer(read_only=True)
  created_by = UserSerializer(read_only=True)
  inventory = ProductSerializer(read_only=True)
  
  class Meta:
    model = Sale
    fields = [
        'id',
        'tenant',
        'created_by',
        'inventory',
        'sold_at',
        'quantity',
        'total_price',
    ]

class TodaysTopHitsSerializer(serializers.ModelSerializer):
  inventory = InventorySerializer(read_only=True)
  class Meta:
    model = Sale
    fields = [
      'id',
      'inventory',
      'quantity',
      'unit_price',
      'total_price',
      'sold_at'
    ]
    