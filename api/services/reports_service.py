

from django.db.models import Sum, Count, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.db.models import F

def get_sales_performance_overview(sales):
  # Default gets the overall Sales
  totals = sales.aggregate(
        sales_revenue=Coalesce(Sum('total_price'), Decimal('0.00'), output_field=DecimalField()),
        total_items=Coalesce(Sum('quantity'), 0, output_field=IntegerField()),
    )
  

  revenues_by_category = sales.values(
    'inventory__category__name', 
    'tenant__name',
    'inventory__category__color',
   ).annotate(
    overall_total=Sum('total_price')
  )

  top_selling_products = (
        sales.values('inventory__id', 'inventory__product_name')  # Groups by inventory and grabs its name
        .annotate(
            total_quantity=Coalesce(
                Sum('quantity'), 
                0, 
                output_field=IntegerField()
            )
        )
        .order_by('-total_quantity')  # <--- The '-' sorts from greater to lesser (Descending)
        [:5]                          # <--- Slices the queryset to return exactly the top 5
    )


  return {
    "totals": totals,
    "revenues_by_category": revenues_by_category,
    "five_top_selling_products": top_selling_products,
  }



def get_inventory_health_report(inventory):
  # Get all inventory items where current stock is less than or equal to the threshold
  low_stock_alerts = list(
        inventory.filter(stock_quantity__lte=F('reorder_threshold'))
        .values('id', 'product_name', 'stock_quantity', 'reorder_threshold')
    )
  return {
    "alerts": {
      "total_alerts": len(low_stock_alerts),
      "low_stock_alerts": low_stock_alerts,
      
    }
    
  }



# TODO: New Feature 
def get_inventory_turnover_ratio(sales):
  # get units sold per product and price per unit
  units_sold = sales.values(
    'inventory__product_name', 
   ).annotate(
    units_sold=Sum('quantity')
  )

  return {
    "units_sold": units_sold
  }


def get_staff_performance_leaderboard(sales):
  # Get Users
  users = sales.values(
    employee=F('created_by__name'),
  ).annotate(
    total_transactions=Count('transaction_id', distinct=True),
    total_sales_revenue=Sum('total_price'),
    
  )

  return {
    "total_sales_revenue": users
  }