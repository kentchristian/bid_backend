

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal


def get_total_sales_specific_day(
    sales, 
    target_day, 
    target_field
):
    return sales.filter(
        sold_at__date=target_day
    ).aggregate(
        total_amount=Coalesce(
            Sum(target_field),
            Decimal('0.00'),
            output_field=DecimalField()
        )
    )['total_amount']