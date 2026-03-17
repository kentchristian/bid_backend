
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
