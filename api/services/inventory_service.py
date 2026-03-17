

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