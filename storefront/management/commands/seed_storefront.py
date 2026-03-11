import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Tenant, User
from storefront.models import Inventory, Sale


class Command(BaseCommand):
    help = "Seed inventory and sales data for two tenants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--per-tenant",
            type=int,
            default=50,
            help="Number of inventory and sales rows to create per tenant (default: 50).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic data generation (default: 42).",
        )

    def handle(self, *args, **options):
        per_tenant = options["per_tenant"]
        seed = options["seed"]

        if per_tenant <= 0:
            raise CommandError("--per-tenant must be a positive integer.")

        tenants = list(Tenant.objects.order_by("created_at")[:2])
        if len(tenants) < 2:
            raise CommandError("Expected at least two tenants to seed data.")

        random.seed(seed)
        now = timezone.now()

        adjectives = [
            "Fresh",
            "Organic",
            "Premium",
            "Classic",
            "Everyday",
            "Smart",
            "Eco",
            "Compact",
            "Bold",
            "Essential",
        ]
        nouns = [
            "Blend",
            "Kit",
            "Bundle",
            "Pack",
            "Set",
            "Mix",
            "Series",
            "Collection",
            "Supply",
            "Assortment",
        ]

        for tenant in tenants:
            self._set_current_tenant(tenant.id)
            try:
                with transaction.atomic():
                    created_by = (
                        User.objects.filter(tenant=tenant)
                        .order_by("created_at")
                        .first()
                    )

                    inventories = []
                    sales = []

                    for index in range(per_tenant):
                        product_name = f"{random.choice(adjectives)} {random.choice(nouns)} {index + 1}"
                        stock_quantity = random.randint(0, 500)
                        reorder_threshold = random.randint(5, 50)
                        inventories.append(
                            Inventory(
                                tenant=tenant,
                                product_name=product_name,
                                stock_quantity=stock_quantity,
                                reorder_threshold=reorder_threshold,
                            )
                        )

                        quantity = random.randint(1, 15)
                        unit_price_cents = random.randint(299, 49999)
                        unit_price = (Decimal(unit_price_cents) / Decimal("100")).quantize(
                            Decimal("0.01")
                        )
                        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
                        sold_at = now - timedelta(
                            days=random.randint(0, 120),
                            hours=random.randint(0, 23),
                            minutes=random.randint(0, 59),
                        )

                        sales.append(
                            Sale(
                                tenant=tenant,
                                product_id=uuid.uuid4(),
                                quantity=quantity,
                                unit_price=unit_price,
                                total_price=total_price,
                                sold_at=sold_at,
                                created_by=created_by,
                            )
                        )

                    Inventory.objects.bulk_create(inventories)
                    Sale.objects.bulk_create(sales)

                self.stdout.write(
                    f"Seeded tenant '{tenant.name}' with {per_tenant} inventory rows and {per_tenant} sales rows."
                )
            finally:
                self._reset_current_tenant()

    def _set_current_tenant(self, tenant_id):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant', %s, false)",
                [str(tenant_id)],
            )

    def _reset_current_tenant(self):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")
