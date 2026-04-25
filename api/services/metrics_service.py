# Metrics Related fuctions modularized


from .sales_service import (
  get_total_revenue,
  get_total_units_sold,
  get_sales_trend,
  get_money_in_sales
)

from .inventory_service import (
    get_items_below_threshold, 
    get_inventory_health,
    get_stock_valuation,
)
def compute_dashboard_metrics(sales_queryset):
  return {
    "total_revenue": get_total_revenue(sales_queryset),
    "total_items": get_total_units_sold(sales_queryset),
    "trend_sales": get_sales_trend(sales_queryset),
    "money_in_sales": get_money_in_sales(sales_queryset),
  }


def compute_inventory_metrics(inventory_queryset):
  return {
    "stock_valuation": get_stock_valuation(inventory_queryset),
    "items_below_threshold": get_items_below_threshold(inventory_queryset),
    "inventory_health": get_inventory_health(inventory_queryset),
  }