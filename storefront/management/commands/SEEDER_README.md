# Seeder Instructions

This seeder guide is Docker-first and follows the production command signature:

```bash
docker compose --env-file .env.prod exec backend python manage.py <command>
```

The storefront seeders create inventory rows first and then create `Sale` rows with a shared `transaction_id` per grouped transaction.

## Prerequisites

- Start the containers with `docker compose --env-file .env.prod up` or `docker compose --env-file .env.prod up --build`.
- Run migrations before running any seeders.
- Make sure tenants already exist before storefront sample data is seeded.
- Make sure each tenant has at least one user so seeded sales can populate `created_by`.

## Core Seeder Order

Run these first and in this order:

1. `docker compose --env-file .env.prod exec backend python manage.py seed_permissions`
2. `docker compose --env-file .env.prod exec backend python manage.py seed_production_accounts`
3. `docker compose --env-file .env.prod exec backend python manage.py seed_role_permissions`

## Storefront Sample Data Order

Run these after the core seeders:

1. Reset storefront seed data if needed.
2. Seed the main month dataset with `seed_production_month` or `seed_sales_inventory_month`.
3. Add optional extra sample data with `seed_storefront`.
4. Append recent activity with `seed_sales_recent`.

## Reset Storefront Seeder Data

Open the database shell from Docker:

```bash
docker compose --env-file .env.prod exec backend python manage.py dbshell
```

Then run:

```sql
TRUNCATE TABLE storefront_sale, storefront_inventory, storefront_category CASCADE;
```

This clears storefront categories, inventory, and sales so the sample dataset can be seeded again from a clean state.

## Seeder Commands

### Production Month Wrapper

Recommended for normal month seeding:

```bash
docker compose --env-file .env.prod exec backend python manage.py seed_production_month --inventory-total 500 --sales-total 500 --tenants 2 --year 2026 --month 4 --transaction-group-sizes 5,10,20
```

### Direct Month Seeder

Use this only if you want direct control instead of the wrapper:

```bash
docker compose --env-file .env.prod exec backend python manage.py seed_sales_inventory_month --inventory-total 500 --sales-total 500 --tenants 2 --year 2026 --month 4 --transaction-group-sizes 5,10,20
```

### Legacy Storefront Seeder

Use this when you want extra generic storefront sample data:

```bash
docker compose --env-file .env.prod exec backend python manage.py seed_storefront --per-tenant 50 --transaction-group-sizes 5,10,20
```

### Recent Sales Seeder

Adds inventory and sales for today and yesterday:

```bash
docker compose --env-file .env.prod exec backend python manage.py seed_sales_recent --per-tenant 10 --tenants 2 --transaction-group-sizes 5,10,20
```

## Notes

- `seed_role_permissions` expects permissions to exist, so run `seed_permissions` first.
- `seed_production_accounts` requires `SEED_TENANT_1_ADMIN_PASSWORD` and `SEED_TENANT_2_ADMIN_PASSWORD` env vars unless flags are provided.
- `seed_production_accounts` defaults admin passwords to `Admin123!` for tenant 1 and `Test123!` for tenant 2 when not provided.
- `seed_production_month` wraps `seed_sales_inventory_month`, so there is usually no need to run both.

## Transaction Grouping

- Every seeded `Sale` row gets a `transaction_id`.
- Multiple sale lines share the same `transaction_id` to simulate one flat transaction with multiple items.
- Default group sizes are `5`, `10`, and `20`.
- If the remaining sales count is smaller than those values, the last transaction uses the remaining item count.

You can change the grouping pattern with:

```bash
docker compose --env-file .env.prod exec backend python manage.py seed_production_month --transaction-group-sizes 3,6,12
```
