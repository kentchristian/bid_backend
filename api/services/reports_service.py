

from django.db.models import Sum, DecimalField, IntegerField
from django.db.models.functions import Coalesce
from decimal import Decimal


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


