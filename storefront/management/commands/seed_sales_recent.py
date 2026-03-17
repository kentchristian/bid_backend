import random
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from accounts.models import Tenant, User
from storefront.models import Inventory, Sale


class Command(BaseCommand):
    help = "Seed inventory + sales for today and yesterday (dynamic)."

    def add_arguments(self, parser):
        parser.add_argument("--per-tenant", type=int, default=10)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--tenants", type=int, default=2)

    def handle(self, *args, **options):
        per_tenant = options["per_tenant"]
        seed = options["seed"]
        tenant_count = options["tenants"]

        if per_tenant <= 0:
            raise CommandError("--per-tenant must be positive.")

        tenants = list(Tenant.objects.order_by("created_at")[:tenant_count])
        if not tenants:
            raise CommandError("No tenants found.")

        random.seed(seed)
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        adjectives = ["Fresh", "Organic", "Premium", "Classic", "Everyday"]
        nouns = ["Bundle", "Pack", "Set", "Mix", "Collection"]

        def random_time():
            return time(
                hour=random.randint(0, 23),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
            )

        for tenant in tenants:
            created_by = User.objects.filter(tenant=tenant).order_by("created_at").first()

            inventories = []
            sales = []

            with transaction.atomic():
                # Inventory count stays per_tenant, but sales count varies by day.
                for i in range(per_tenant):
                    product_name = f"{random.choice(adjectives)} {random.choice(nouns)} {i + 1}"
                    inventories.append(
                        Inventory(
                            tenant=tenant,
                            product_name=product_name,
                            stock_quantity=random.randint(10, 200),
                            reorder_threshold=random.randint(5, 30),
                            unit_price=Decimal(random.randint(199, 9999)) / Decimal("100"),
                        )
                    )

                    def build_sale(sold_at):
                        quantity = random.randint(1, 10)
                        unit_price = Decimal(random.randint(199, 9999)) / Decimal("100")
                        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
                        return Sale(
                            tenant=tenant,
                            product_id=uuid.uuid4(),
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            sold_at=sold_at,
                            created_by=created_by,
                        )

                max_per_day = max(1, per_tenant)
                today_count = random.randint(1, max_per_day)
                yesterday_count = random.randint(1, max_per_day)
                if max_per_day > 1 and today_count == yesterday_count:
                    # Ensure different counts between days.
                    yesterday_count = 1 if today_count != 1 else 2

                for _ in range(today_count):
                    sold_at_today = timezone.make_aware(
                        datetime.combine(today, random_time())
                    )
                    sales.append(build_sale(sold_at_today))

                for _ in range(yesterday_count):
                    sold_at_yesterday = timezone.make_aware(
                        datetime.combine(yesterday, random_time())
                    )
                    sales.append(build_sale(sold_at_yesterday))

                Inventory.objects.bulk_create(inventories)
                Sale.objects.bulk_create(sales)

            self.stdout.write(
                f"Seeded tenant '{tenant.name}' with {per_tenant} inventory rows and "
                f"{per_tenant * 2} sales rows (today+yesterday)."
            )
