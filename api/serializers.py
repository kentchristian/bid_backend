from rest_framework import serializers

from storefront.models import Inventory, Sale, Category
from accounts.models import User, Tenant
from .utils import field_lookup


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name"]

class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    class Meta: 
        model = User 
        fields = ['id', 'name', 'email', 'tenant', 'role', 'is_active']

class CategorySerializer(serializers.ModelSerializer):
  class Meta:
    model = Category
    fields = [
      "id",
      "name",
      "color",
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
    created_by = UserSerializer(read_only=True)
    class Meta:
        model = Sale
        fields = [
            "id",
            "transaction_id",
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



### POST Serializers

class CreateSalesSerializer(serializers.ModelSerializer):
    inventory = serializers.SlugRelatedField(
      slug_field='id', 
      queryset=Inventory.objects.none()
    )
    tenant = serializers.SlugRelatedField(
      slug_field='id', 
      queryset=Tenant.objects.none()
    )

    class Meta: 
        model = Sale
        fields = [
          'tenant', 
          'inventory',
          'transaction_id',
          'created_by', 
          'quantity', 
          'unit_price', 
          'total_price', 
          'sold_at'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request') # checs the request meta data
        if request and hasattr(request, 'user'): # checs i user exist in request -- basically if logged in
            # SECURITY: Limit the "menu" of choices to this tenant only
            user_tenant = request.user.tenant 
            self.fields['inventory'].queryset = Inventory.objects.filter(tenant=user_tenant)
            self.fields['tenant'].queryset = Tenant.objects.filter(id=user_tenant.id)

    def validate_quantity(self, value):
        # FIELD VALIDATION: Basic sanity check
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate(self, data):
        # OBJECT-LEVEL VALIDATION: Business Logic
        # Since we filtered the queryset in __init__, 'data["inventory"]' 
        # is guaranteed to belong to the correct tenant already.
        inventory_item = data['inventory']
        
        if data['quantity'] > inventory_item.stock_quantity:
            raise serializers.ValidationError({
                "quantity": f"Insufficient stock. Available: {inventory_item.stock_quantity}"
            })
            
        return data