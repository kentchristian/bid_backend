
from django.utils import timezone
from api.utils.get_total_sales_specific_day import get_total_sales_specific_day
from api.serializers import MoneyInSalesSerializer, TodaysTopHitsSerializer, InventorySerializer

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


def get_sales_trend(sales):
  today_date = timezone.now().date()

  today_index = today_date.weekday()

  # Days ago on rcent Sunday
  days_since_sunday = (today_index + 1) % 7

  data = []

  for i in range(7):
    target_date = today_date + timezone.timedelta(days=(-days_since_sunday + i))

    print(target_date)
    
    # Get Sales total within target day 
    raw_sales = get_total_sales_specific_day(sales, target_date, 'total_price')
    
    data.append({
        "day": target_date.strftime("%a").capitalize(),
        "sales": raw_sales if raw_sales is not None else 0
    })

  
  return data


def get_money_in_sales(sales):
  today = timezone.now().date()
  today_sales = sales.filter(sold_at__date=today)

  return MoneyInSalesSerializer(today_sales, many=True).data


def get_todays_top_hits(sales):
  top_3_sales = sales.order_by(
    '-total_price',
    '-quantity',
    '-unit_price',
    '-sold_at',
  )[:3]


  def count_product_item(product_name):
    product = sales.filter(inventory__product_name=product_name)
    return product.count()
  
  data = TodaysTopHitsSerializer(top_3_sales, many=True).data

  for index, item in enumerate(data):
        item['rank'] = index + 1 #Add Rank to attribute
        item['count_product_item'] = count_product_item(data[index]['inventory']['product_name'])
        
  return data
