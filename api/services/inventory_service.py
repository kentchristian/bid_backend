from django.db.models import F, Q
from api.serializers import InventorySerializer, UserSerializer, CategorySerializer
from accounts.models import User
from storefront.models import Category, Inventory
from .users_service import (
  get_users

)
from django.db import transaction

def get_items_below_threshold(inventory):
  below_threshold = inventory.filter(
    Q(stock_quantity__lte=F('reorder_threshold')) | Q(stock_quantity__lte=0)
  )
  items_below_threshold = [
    {
      "product_name": item.product_name,
      "item_threshold": item.reorder_threshold,
      "stock": item.stock_quantity,
    }
    for item in below_threshold
  ]

  return {
    "total": len(items_below_threshold),
    "items": items_below_threshold,
  }


def get_inventory_health(inventory):
  out_of_stocks = inventory.filter(stock_quantity__lte=0)
  low_stocks = inventory.filter(
    stock_quantity__gt=0,
    stock_quantity__lte=F('reorder_threshold')
  )
  healthy_stocks = inventory.filter(
    stock_quantity__gt=F('reorder_threshold')
  ).filter(stock_quantity__gt=0)

  return {
    "stocks_class_total": [
      {"name": "Healthy Stocks", "value": healthy_stocks.count()},
      {"name": "Low Stocks", "value": low_stocks.count()},
      {"name": "Out of Stock", "value": out_of_stocks.count()}
    ],
    "items": {
      "healthy_stock_items": InventorySerializer(healthy_stocks, many=True).data,
      "low_stock": InventorySerializer(low_stocks, many=True).data,
      "empty_stock": InventorySerializer(out_of_stocks, many=True).data,
    }    
  }


def get_sales_form_options(inventory):
  inventory = InventorySerializer(inventory, many=True).data
  tenant = inventory[0]['tenant']['name']

  # get user
  users = get_users(tenant)

  query_set = Category.objects.all().filter(tenant__name=tenant)
  categories = CategorySerializer(query_set, many=True).data

  return {
    "users": users,
    "categories": categories,
  };


def get_inventory_by_category(inventory, category):
  query_set = inventory.filter(stock_quantity__gt=0) #Filter Quantity To show > 0
  if category:
    query_set = inventory.filter(category__name=category, stock_quantity__gt=0)
  
  inventory = InventorySerializer(query_set, many=True).data
  
  return {
    "total_items": len(inventory),
    "inventory": inventory
  }







# UPDATE -- UPDATE THE INVENTORY 



# Updates Stock Quantity
def update_inventory_stock(inventory_id, quantity_change, tenant):
    """
    Job: Adjust stock levels safely.
    One Job: Math + Database Update.
    """
    # Use select_for_update to lock the row so two sales don't 
    # calculate the stock at the same millisecond (Race Condition)
    inventory = Inventory.objects.select_for_update().get(id=inventory_id, tenant=tenant)
    
    inventory.stock_quantity -= quantity_change
    inventory.save(update_fields=['stock_quantity']) # Only updates this specific column

    return inventory