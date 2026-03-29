# Metrics Related fuctions modularized


from .sales_service import (
  get_total_revenue,
  get_total_units_sold,
  get_sales_trend,
  get_money_in_sales
)

def compute_dashboard_metrics(sales_queryset):
  return {
    "total_revenue": get_total_revenue(sales_queryset),
    "total_items": get_total_units_sold(sales_queryset),
    "trend_sales": get_sales_trend(sales_queryset),
    "money_in_sales": get_money_in_sales(sales_queryset),
  }