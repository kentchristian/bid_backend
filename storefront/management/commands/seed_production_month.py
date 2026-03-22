from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = (
        "Seed production inventory and sales for a specific month "
        "(wrapper around seed_sales_inventory_month)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--inventory-total",
            type=int,
            default=500,
            help="Total inventory rows across selected tenants (default: 500).",
        )
        parser.add_argument(
            "--sales-total",
            type=int,
            default=500,
            help="Total sales rows across selected tenants (default: 500).",
        )
        parser.add_argument(
            "--tenants",
            type=int,
            default=2,
            help="Number of tenants to seed (default: 2).",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Year to seed (requires --month). Defaults to current year.",
        )
        parser.add_argument(
            "--month",
            type=int,
            default=None,
            help="Month (1-12) to seed (requires --year). Defaults to current month.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for deterministic data generation (default: 42).",
        )

    def handle(self, *args, **options):
        inventory_total = options["inventory_total"]
        sales_total = options["sales_total"]
        tenants = options["tenants"]
        seed = options["seed"]
        year = options["year"]
        month = options["month"]

        if (year is None) != (month is None):
            raise CommandError("--year and --month must be provided together.")
        if month is not None and (month < 1 or month > 12):
            raise CommandError("--month must be between 1 and 12.")

        if year is None:
            today = timezone.localdate()
            year = today.year
            month = today.month

        call_command(
            "seed_sales_inventory_month",
            inventory_total=inventory_total,
            sales_total=sales_total,
            tenants=tenants,
            seed=seed,
            year=year,
            month=month,
        )

        self.stdout.write(
            f"Production month seed complete for {date(year, month, 1):%B %Y}."
        )
