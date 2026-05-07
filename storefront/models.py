import uuid
from accounts.models import Tenant, User
from django.db import models



class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=50, null=True)

    class Meta:
        unique_together = ('tenant', 'name')
    
    def __str__(self):
        return self.name

# ===== INVENTORY =====
class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    stock_quantity = models.IntegerField()
    max_quantity = models.IntegerField()
    reorder_threshold = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    updated_at = models.DateTimeField(auto_now=True)
    # TODO: isDeleted -- soft Delete
    

    class Meta:
        indexes = [
            models.Index(fields=['tenant']),
        ]

# ===== SALES =====
class Sale(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(max_length=255, null=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    sold_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant']),
        ]
