from django.db.models import F, Q
from api.serializers import InventorySerializer


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
