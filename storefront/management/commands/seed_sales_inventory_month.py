import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from accounts.models import Tenant, User
from storefront.models import Category, Inventory, Sale
from storefront.management.commands._seeder_utils import (
    assign_transaction_ids,
    parse_transaction_group_sizes,
)


class Command(BaseCommand):
    help = "Seed inventory and sales for the current month with structured data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--inventory-total",
            type=int,
            default=500,
            help="Total inventory rows to create across selected tenants (default: 500).",
        )
        parser.add_argument(
            "--sales-total",
            type=int,
            default=500,
            help="Total sales rows to create across selected tenants (default: 500).",
        )
        parser.add_argument(
            "--tenants",
            type=int,
            default=None,
            help="Number of tenants to seed (default: all tenants).",
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
        parser.add_argument(
            "--low-stock-ratio",
            type=float,
            default=0.08,
            help=(
                "Fraction of inventory items that should end below the reorder threshold "
                "(default: 0.08)."
            ),
        )
        parser.add_argument(
            "--out-of-stock-ratio",
            type=float,
            default=0.04,
            help=(
                "Fraction of inventory items that should end at zero stock "
                "(default: 0.04)."
            ),
        )
        parser.add_argument(
            "--transaction-group-sizes",
            type=str,
            default="5,10,20",
            help=(
                "Comma-separated sale-line counts to group under one transaction_id "
                "(default: 5,10,20)."
            ),
        )

    def handle(self, *args, **options):
        inventory_total = options["inventory_total"]
        sales_total = options["sales_total"]
        tenant_limit = options["tenants"]
        seed = options["seed"]
        year = options["year"]
        month = options["month"]
        low_stock_ratio = options["low_stock_ratio"]
        out_of_stock_ratio = options["out_of_stock_ratio"]
        transaction_group_sizes_raw = options["transaction_group_sizes"]

        if inventory_total <= 0:
            raise CommandError("--inventory-total must be a positive integer.")
        if sales_total <= 0:
            raise CommandError("--sales-total must be a positive integer.")

        if (year is None) != (month is None):
            raise CommandError("--year and --month must be provided together.")
        if month is not None and (month < 1 or month > 12):
            raise CommandError("--month must be between 1 and 12.")
        if low_stock_ratio < 0 or out_of_stock_ratio < 0:
            raise CommandError("Stock ratios must be zero or positive.")
        if low_stock_ratio > 1 or out_of_stock_ratio > 1:
            raise CommandError("Stock ratios must be between 0 and 1.")
        try:
            transaction_group_sizes = parse_transaction_group_sizes(
                transaction_group_sizes_raw
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        tenants_qs = Tenant.objects.order_by("created_at")
        if tenant_limit:
            tenants_qs = tenants_qs[:tenant_limit]
        tenants = list(tenants_qs)
        if not tenants:
            raise CommandError("No tenants found.")

        rng = random.Random(seed)
        anchor_date = (
            date(year, month, 1) if year is not None else timezone.localdate()
        )
        month_start, month_end = self._month_bounds(anchor_date)
        dates, date_weights = self._build_date_weights(month_start, month_end)
        dayparts = self._dayparts()
        category_defs = self._category_defs()
        brand_names = self._brands()

        inventory_counts = self._distribute(inventory_total, len(tenants))
        sales_counts = self._distribute(sales_total, len(tenants))
        inventory_counts = self._ensure_inventory_for_sales(
            inventory_counts, sales_counts
        )

        category_popularity = {item["name"]: item["popularity"] for item in category_defs}
        category_qty_range = {item["name"]: item["qty_range"] for item in category_defs}

        for tenant_index, tenant in enumerate(tenants):
            self._set_current_tenant(tenant.id)
            try:
                with transaction.atomic():
                    created_by = (
                        User.objects.filter(tenant=tenant)
                        .order_by("created_at")
                        .first()
                    )

                    categories = {}
                    for cat_def in category_defs:
                        category, _ = Category.objects.get_or_create(
                            tenant=tenant, name=cat_def["name"]
                        )
                        categories[cat_def["name"]] = category

                    inventory_target = inventory_counts[tenant_index]
                    sales_target = sales_counts[tenant_index]

                    inventory_items = []
                    stock_remaining = {}
                    sold_by_inventory = {}
                    target_remaining = {}

                    low_count, out_count = self._allocate_special_counts(
                        inventory_target, low_stock_ratio, out_of_stock_ratio
                    )
                    special_indices = list(range(inventory_target))
                    rng.shuffle(special_indices)
                    out_indices = set(special_indices[:out_count])
                    low_indices = set(
                        special_indices[out_count : out_count + low_count]
                    )

                    for i in range(inventory_target):
                        cat_def = category_defs[i % len(category_defs)]
                        category = categories[cat_def["name"]]
                        item = cat_def["items"][i % len(cat_def["items"])]
                        variant = cat_def["variants"][
                            (i // len(cat_def["items"])) % len(cat_def["variants"])
                        ]
                        size_index = (
                            i
                            // (len(cat_def["items"]) * len(cat_def["variants"]))
                        ) % len(cat_def["sizes"])
                        size = cat_def["sizes"][size_index]
                        brand = brand_names[(i + tenant_index) % len(brand_names)]
                        sku = f"{cat_def['code']}-{tenant_index + 1:02d}-{i + 1:04d}"
                        product_name = f"{brand} {item} {variant} {size} {sku}"

                        unit_price = self._price_for(cat_def, size_index, rng)
                        base_stock = rng.randint(*cat_def["stock_range"])
                        max_quantity = base_stock + rng.randint(20, 180)
                        reorder_threshold = max(
                            5, int(max_quantity * rng.choice([0.12, 0.18, 0.25]))
                        )
                        if max_quantity > 1:
                            reorder_threshold = min(reorder_threshold, max_quantity - 1)
                        is_out = i in out_indices
                        is_low = i in low_indices
                        stock_quantity, desired_remaining = self._stock_plan(
                            rng=rng,
                            max_quantity=max_quantity,
                            reorder_threshold=reorder_threshold,
                            is_low=is_low,
                            is_out=is_out,
                        )

                        inventory = Inventory.objects.create(
                            tenant=tenant,
                            category=category,
                            product_name=product_name,
                            stock_quantity=stock_quantity,
                            max_quantity=max_quantity,
                            reorder_threshold=reorder_threshold,
                            unit_price=unit_price,
                        )
                        inventory_items.append(inventory)
                        stock_remaining[inventory.id] = stock_quantity
                        sold_by_inventory[inventory.id] = 0
                        if desired_remaining is not None:
                            target_remaining[inventory.id] = desired_remaining

                    if not inventory_items:
                        self.stdout.write(
                            f"Skipped tenant '{tenant.name}' (no inventory targets)."
                        )
                        continue

                    total_stock_units = sum(stock_remaining.values())
                    if sales_target > total_stock_units:
                        self.stdout.write(
                            "Requested sales rows exceed available stock units; "
                            f"capping sales rows to {total_stock_units}."
                        )
                        sales_target = total_stock_units

                    inventory_weights = [
                        category_popularity.get(inv.category.name, 1.0)
                        for inv in inventory_items
                    ]

                    sales = []
                    tz = timezone.get_current_timezone()

                    def build_sale(inventory, quantity):
                        sale_date = rng.choices(dates, weights=date_weights, k=1)[0]
                        sold_time = self._random_time(rng, dayparts)
                        sold_at = timezone.make_aware(
                            datetime.combine(sale_date, sold_time), tz
                        )
                        unit_price = inventory.unit_price
                        total_price = (unit_price * quantity).quantize(Decimal("0.01"))
                        return Sale(
                            tenant=tenant,
                            inventory=inventory,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            sold_at=sold_at,
                            created_by=created_by,
                        )

                    locked_ids = set()
                    for inventory in inventory_items:
                        if inventory.id not in target_remaining:
                            continue
                        desired_remaining = target_remaining[inventory.id]
                        remaining = stock_remaining.get(inventory.id, 0)
                        if remaining <= desired_remaining:
                            locked_ids.add(inventory.id)
                            continue

                        qty_min, qty_max = category_qty_range.get(
                            inventory.category.name, (1, 4)
                        )
                        while remaining > desired_remaining:
                            max_sell = remaining - desired_remaining
                            qty_cap = min(qty_max, max_sell)
                            if qty_cap <= 0:
                                break
                            if qty_cap < qty_min:
                                quantity = qty_cap
                            else:
                                quantity = rng.randint(qty_min, qty_cap)
                            sales.append(build_sale(inventory, quantity))
                            remaining -= quantity
                            sold_by_inventory[inventory.id] = (
                                sold_by_inventory.get(inventory.id, 0) + quantity
                            )
                        stock_remaining[inventory.id] = remaining
                        locked_ids.add(inventory.id)

                    if len(sales) > sales_target:
                        self.stdout.write(
                            "Generated more sales rows than requested to satisfy "
                            "low/out-of-stock targets."
                        )

                    attempts = 0
                    max_attempts = max(sales_target * 6, sales_target + 10)
                    while len(sales) < sales_target and attempts < max_attempts:
                        attempts += 1
                        inventory = rng.choices(
                            inventory_items, weights=inventory_weights, k=1
                        )[0]
                        if inventory.id in locked_ids:
                            continue
                        remaining = stock_remaining.get(inventory.id, 0)
                        if remaining <= 0:
                            continue

                        qty_min, qty_max = category_qty_range.get(
                            inventory.category.name, (1, 4)
                        )
                        qty_cap = min(qty_max, remaining)
                        if qty_cap <= 0:
                            continue
                        quantity = (
                            qty_cap
                            if qty_cap < qty_min
                            else rng.randint(qty_min, qty_cap)
                        )

                        sales.append(build_sale(inventory, quantity))
                        stock_remaining[inventory.id] = remaining - quantity
                        sold_by_inventory[inventory.id] = (
                            sold_by_inventory.get(inventory.id, 0) + quantity
                        )

                    sales = assign_transaction_ids(
                        sales,
                        rng=rng,
                        group_sizes=transaction_group_sizes,
                    )

                    Sale.objects.bulk_create(sales, batch_size=1000)

                    for inventory in inventory_items:
                        sold_qty = sold_by_inventory.get(inventory.id, 0)
                        inventory.stock_quantity = max(
                            0, inventory.stock_quantity - sold_qty
                        )
                    Inventory.objects.bulk_update(inventory_items, ["stock_quantity"])

                self.stdout.write(
                    f"Seeded tenant '{tenant.name}' with {inventory_target} inventory rows and "
                    f"{len(sales)} sales rows for {month_start:%B %Y}."
                )
            finally:
                self._reset_current_tenant()

    def _month_bounds(self, today):
        start = today.replace(day=1)
        if start.month == 12:
            next_month = date(start.year + 1, 1, 1)
        else:
            next_month = date(start.year, start.month + 1, 1)
        end = next_month - timedelta(days=1)
        return start, end

    def _build_date_weights(self, start, end):
        dates = []
        weights = []
        day = start
        while day <= end:
            weight = 1.0
            if day.weekday() >= 5:
                weight = 1.6
            elif day.weekday() == 4:
                weight = 1.3
            if day.day >= end.day - 5:
                weight += 0.2
            dates.append(day)
            weights.append(weight)
            day += timedelta(days=1)
        return dates, weights

    def _dayparts(self):
        return [
            {"hours": (8, 11), "weight": 0.3},
            {"hours": (12, 15), "weight": 0.4},
            {"hours": (17, 20), "weight": 0.3},
        ]

    def _random_time(self, rng, dayparts):
        weights = [part["weight"] for part in dayparts]
        part = rng.choices(dayparts, weights=weights, k=1)[0]
        hour = rng.randint(part["hours"][0], part["hours"][1])
        minute = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
        second = rng.choice([0, 15, 30, 45])
        return time(hour=hour, minute=minute, second=second)

    def _price_for(self, cat_def, size_index, rng):
        base_price = rng.choice(cat_def["price_points"])
        multiplier = cat_def["size_multipliers"][
            size_index % len(cat_def["size_multipliers"])
        ]
        return (base_price * multiplier).quantize(Decimal("0.01"))

    def _distribute(self, total, buckets):
        base, extra = divmod(total, buckets)
        return [base + (1 if i < extra else 0) for i in range(buckets)]

    def _ensure_inventory_for_sales(self, inventory_counts, sales_counts):
        adjusted = list(inventory_counts)
        for i, sales_count in enumerate(sales_counts):
            if sales_count > 0 and adjusted[i] == 0:
                donor = max(range(len(adjusted)), key=lambda j: adjusted[j])
                if adjusted[donor] <= 1:
                    raise CommandError(
                        "Not enough inventory to distribute sales across tenants."
                    )
                adjusted[donor] -= 1
                adjusted[i] += 1
        return adjusted

    def _category_defs(self):
        return [
            {
                "name": "Beverages",
                "code": "BEV",
                "items": [
                    "Cold Brew",
                    "Green Tea",
                    "Sparkling Water",
                    "Orange Juice",
                    "Cola",
                    "Lemonade",
                ],
                "variants": ["Original", "Zero Sugar", "Lime", "Ginger", "Peach"],
                "sizes": ["250ml", "500ml", "1L", "2L"],
                "price_points": [
                    Decimal("1.25"),
                    Decimal("1.75"),
                    Decimal("2.25"),
                    Decimal("2.75"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.6"),
                    Decimal("2.8"),
                    Decimal("4.8"),
                ],
                "stock_range": (120, 420),
                "qty_range": (1, 6),
                "popularity": 1.4,
            },
            {
                "name": "Snacks",
                "code": "SNK",
                "items": [
                    "Trail Mix",
                    "Potato Chips",
                    "Granola Bar",
                    "Popcorn",
                    "Pretzels",
                    "Crackers",
                ],
                "variants": ["Sea Salt", "BBQ", "Cheddar", "Spicy", "Honey"],
                "sizes": ["Single", "2-Pack", "Family", "Party"],
                "price_points": [
                    Decimal("1.50"),
                    Decimal("2.00"),
                    Decimal("2.50"),
                    Decimal("3.00"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.8"),
                    Decimal("2.8"),
                    Decimal("4.0"),
                ],
                "stock_range": (80, 300),
                "qty_range": (1, 5),
                "popularity": 1.2,
            },
            {
                "name": "Pantry",
                "code": "PAN",
                "items": [
                    "Pasta",
                    "Rice",
                    "Black Beans",
                    "Tomato Sauce",
                    "Cereal",
                    "Olive Oil",
                ],
                "variants": ["Classic", "Whole Grain", "Low Sodium", "Organic"],
                "sizes": ["400g", "800g", "1.5kg"],
                "price_points": [
                    Decimal("1.20"),
                    Decimal("2.00"),
                    Decimal("3.20"),
                    Decimal("5.50"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.7"),
                    Decimal("2.5"),
                ],
                "stock_range": (60, 250),
                "qty_range": (1, 4),
                "popularity": 1.0,
            },
            {
                "name": "Household",
                "code": "HOU",
                "items": [
                    "Dish Soap",
                    "Laundry Detergent",
                    "Paper Towels",
                    "Trash Bags",
                    "All-Purpose Cleaner",
                ],
                "variants": ["Lemon", "Lavender", "Unscented", "Heavy Duty"],
                "sizes": ["500ml", "1L", "2L", "Value Pack"],
                "price_points": [
                    Decimal("2.50"),
                    Decimal("3.50"),
                    Decimal("4.50"),
                    Decimal("6.00"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.6"),
                    Decimal("2.6"),
                    Decimal("3.5"),
                ],
                "stock_range": (50, 200),
                "qty_range": (1, 3),
                "popularity": 0.8,
            },
            {
                "name": "Personal Care",
                "code": "PER",
                "items": [
                    "Shampoo",
                    "Conditioner",
                    "Body Wash",
                    "Toothpaste",
                    "Hand Soap",
                ],
                "variants": ["Moisture", "Fresh", "Sensitive", "Classic"],
                "sizes": ["250ml", "500ml", "1L"],
                "price_points": [
                    Decimal("2.00"),
                    Decimal("3.00"),
                    Decimal("4.00"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.7"),
                    Decimal("2.6"),
                ],
                "stock_range": (50, 180),
                "qty_range": (1, 3),
                "popularity": 0.7,
            },
            {
                "name": "Produce",
                "code": "PRO",
                "items": [
                    "Apples",
                    "Bananas",
                    "Oranges",
                    "Tomatoes",
                    "Potatoes",
                    "Onions",
                ],
                "variants": ["Fresh", "Local", "Seasonal"],
                "sizes": ["500g", "1kg", "2kg"],
                "price_points": [
                    Decimal("1.00"),
                    Decimal("1.50"),
                    Decimal("2.20"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.8"),
                    Decimal("3.2"),
                ],
                "stock_range": (100, 350),
                "qty_range": (1, 6),
                "popularity": 1.3,
            },
            {
                "name": "Dairy",
                "code": "DAI",
                "items": [
                    "Milk",
                    "Yogurt",
                    "Cheese",
                    "Butter",
                    "Cream",
                ],
                "variants": ["Whole", "Low Fat", "Greek", "Salted"],
                "sizes": ["250ml", "500ml", "1L", "Family"],
                "price_points": [
                    Decimal("1.20"),
                    Decimal("1.80"),
                    Decimal("2.60"),
                    Decimal("3.50"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.6"),
                    Decimal("2.8"),
                    Decimal("4.0"),
                ],
                "stock_range": (80, 250),
                "qty_range": (1, 4),
                "popularity": 1.1,
            },
            {
                "name": "Bakery",
                "code": "BAK",
                "items": [
                    "Sourdough Bread",
                    "Bagels",
                    "Croissant",
                    "Muffins",
                    "Brioche",
                ],
                "variants": ["Classic", "Butter", "Honey", "Whole Wheat"],
                "sizes": ["Single", "2-Pack", "4-Pack", "Family"],
                "price_points": [
                    Decimal("1.00"),
                    Decimal("1.60"),
                    Decimal("2.40"),
                    Decimal("3.20"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.8"),
                    Decimal("3.0"),
                    Decimal("4.5"),
                ],
                "stock_range": (60, 200),
                "qty_range": (1, 5),
                "popularity": 0.9,
            },
            {
                "name": "Frozen",
                "code": "FRO",
                "items": [
                    "Frozen Pizza",
                    "Ice Cream",
                    "Mixed Veggies",
                    "Chicken Nuggets",
                    "Fish Fillet",
                ],
                "variants": ["Classic", "Spicy", "Garlic", "Vanilla"],
                "sizes": ["Single", "2-Pack", "Family"],
                "price_points": [
                    Decimal("3.00"),
                    Decimal("4.50"),
                    Decimal("6.00"),
                ],
                "size_multipliers": [
                    Decimal("1.0"),
                    Decimal("1.7"),
                    Decimal("2.8"),
                ],
                "stock_range": (50, 160),
                "qty_range": (1, 3),
                "popularity": 0.8,
            },
        ]

    def _brands(self):
        return [
            "Summit",
            "Riverbend",
            "Harbor",
            "Cedar",
            "GoldenField",
            "Northwind",
            "BrightLeaf",
            "Redstone",
            "BlueHarvest",
            "OakCo",
            "Pinecrest",
            "Lakeside",
        ]

    def _allocate_special_counts(self, total, low_ratio, out_ratio):
        if total <= 0:
            return 0, 0
        out_count = int(round(total * out_ratio))
        low_count = int(round(total * low_ratio))

        if total >= 2:
            if out_ratio > 0:
                out_count = max(1, out_count)
            if low_ratio > 0:
                low_count = max(1, low_count)
        elif total == 1:
            out_count = 1 if out_ratio > 0 else 0
            low_count = 0

        if out_count + low_count > total:
            low_count = max(0, total - out_count)
        if out_count + low_count > total:
            out_count = max(0, total - low_count)

        return low_count, out_count

    def _stock_plan(self, rng, max_quantity, reorder_threshold, is_low, is_out):
        if max_quantity <= 0:
            return 0, 0
        if reorder_threshold < 1:
            reorder_threshold = 1

        if is_out:
            start_max = min(max_quantity, max(3, min(reorder_threshold, 30)))
            start_min = min(start_max, 1)
            starting_stock = rng.randint(start_min, start_max)
            return starting_stock, 0

        if is_low:
            low_min = min(max_quantity, reorder_threshold + 5)
            low_max = min(max_quantity, reorder_threshold + 30)
            if low_min > low_max:
                low_min = low_max
            starting_stock = rng.randint(low_min, low_max)
            if reorder_threshold > 1 and starting_stock > 1:
                target_remaining = rng.randint(
                    1, min(reorder_threshold - 1, starting_stock - 1)
                )
            else:
                target_remaining = 0
            return starting_stock, target_remaining

        healthy_min = max(reorder_threshold + 10, int(max_quantity * 0.6))
        healthy_min = min(healthy_min, max_quantity)
        starting_stock = rng.randint(healthy_min, max_quantity)
        return starting_stock, None

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
