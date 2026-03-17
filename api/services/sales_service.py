
from django.utils import timezone
from api.utils.get_total_sales_specific_day import get_total_sales_specific_day


def get_total_revenue(sales):
  #Get the instance query set filtered 
  today = timezone.now().date()
  yesterday = today - timezone.timedelta(days=1)

  today_total = get_total_sales_specific_day(sales, today, 'total_price')
  yesterday_total = get_total_sales_specific_day(sales, yesterday, 'total_price')

  return {
    "today_total": today_total,
    "yesterday_total": yesterday_total,
  }


def get_total_units_sold(sales):
  today = timezone.now().date()
  yesterday = today - timezone.timedelta(days=1)

  sales_today = sales.filter(sold_at__date=today)
  sales_yesterday = sales.filter(sold_at__date=yesterday)

  today_total_items = len(sales_today)
  yesterday_total_items = len(sales_yesterday)
  items = []

  for item in sales_today:
    items.append(item.inventory.product_name)

  return {
    "today_total_items": today_total_items,
    "yesterday_total_items": yesterday_total_items,
    "items": items
  }




  
  


