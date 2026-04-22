
from datetime import datetime
from django.utils import timezone
from api.utils.get_total_sales_specific_day import get_total_sales_specific_day
from api.serializers import (
  MoneyInSalesSerializer, 
  TodaysTopHitsSerializer, 
  InventorySerializer,
  SaleSerializer,
)
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
    
    # Get Sales total within target day 
    raw_sales = get_total_sales_specific_day(sales, target_date, 'total_price')
    
    data.append({
        "day": target_date.strftime("%a").capitalize(),
        "sales": raw_sales if raw_sales is not None else 0
    })

  
  return data


def get_money_in_sales(sales):
  today = timezone.now().date()
  today_sales = (
    sales.filter(sold_at__date=today)
    .select_related("inventory", "tenant", "created_by")
    .order_by("-sold_at", "-id")
  )
  return MoneyInSalesSerializer(today_sales, many=True).data


def get_todays_top_hits(sales):
  today = timezone.now().date()
  today_sales = (
    sales.filter(sold_at__date=today)
    .select_related("inventory", "tenant", "created_by")
  )

  grouped = {}
  for sale in today_sales:
    inventory = sale.inventory
    if not inventory:
      continue
    key = inventory.product_name
    entry = grouped.get(key)
    if entry is None:
      entry = {
        "inventory": inventory,
        "total_revenue": 0,
        "total_quantity": 0,
        "max_unit_price": 0,
        "last_sold_at": None,
        "sales_count": 0,
      }
      grouped[key] = entry

    entry["total_revenue"] += sale.total_price
    entry["total_quantity"] += sale.quantity
    entry["sales_count"] += 1
    if sale.unit_price > entry["max_unit_price"]:
      entry["max_unit_price"] = sale.unit_price
    if entry["last_sold_at"] is None or sale.sold_at > entry["last_sold_at"]:
      entry["last_sold_at"] = sale.sold_at

  ranked = sorted(
    grouped.values(),
    key=lambda item: (
      item["total_revenue"],
      item["total_quantity"],
      item["max_unit_price"],
      item["last_sold_at"] or timezone.make_aware(datetime(1970, 1, 1)),
    ),
    reverse=True,
  )[:3]

  data = []
  for index, item in enumerate(ranked):
    inventory = item["inventory"]
    data.append({
      "id": str(inventory.id),
      "inventory": InventorySerializer(inventory).data,
      "quantity": item["total_quantity"],
      "unit_price": item["max_unit_price"],
      "total_price": item["total_revenue"],
      "sold_at": item["last_sold_at"],
      "rank": index + 1,
      "count_product_item": item["sales_count"],
    })

  return data


def get_transaction_history(sales):
  # Distinct Transactions
  transactions = sales.values("transaction_id", "created_by", "tenant", "sold_at").distinct()
  total_revenue = 0
  units_sold = 0

  for item in transactions:
    # Get Tranasction
    transaction = sales.filter(**item)
    serialized = SaleSerializer(transaction, many=True).data

    item["items_in_transaction"] = len(serialized) # Items Total
    total = sum(float(obj['total_price']) for obj in serialized)
    units = sum(obj['quantity'] for obj in serialized)

    units_sold += units
    
    total_revenue += total # Count Total Revenue sum
    

    item["overall_transaction_amount"] = total # Assign total to overall Transaction amount
    item["items"] = serialized # Append Items Serialized

  return {
    "total_transactions": len(transactions),
    "total_revenue": round(total_revenue, 2),
    "units_sold": units_sold,
    "transactions": transactions,
  }