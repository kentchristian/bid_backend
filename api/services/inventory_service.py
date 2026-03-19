from django.db.models import F
from api.serializers import InventorySerializer


def get_items_below_threshold(inventory):
  items_below_threshold = []

  for item in inventory:
    if(item.stock_quantity <= item.reorder_threshold):
      items_below_threshold.append(
        {
          "product_name": item.product_name,
          "item_threshold": item.reorder_threshold,
          "stock": item.stock_quantity,
        }
      )
    
  return {
    "total": len(items_below_threshold),
    "items": items_below_threshold,
  }


def get_inventory_health(inventory):
  healthy_stocks  = inventory.filter(stock_quantity__gt=F('reorder_threshold'))
  low_stocks = inventory.filter(stock_quantity__gt=0).filter(stock_quantity__lt=F('reorder_threshold'))
  out_of_stocks = inventory.filter(stock_quantity=0)

  return {
    "stocks_class_total": [
      {"name": "Healthy Stocks", "value": healthy_stocks.count()},
      {"name": "Low Stocks", "value": low_stocks.count()},
      {"name": "Out of Stock", "value": out_of_stocks.count()}
    ],
    "items": {
      "healthy_stock_items": InventorySerializer(healthy_stocks, many=True).data,
      "low_stocks": InventorySerializer(low_stocks, many=True).data,
      "out_of_stocks": InventorySerializer(out_of_stocks, many=True).data,
    }    
  }
