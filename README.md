Raw Documentation Planning and Learning notes: 
[DOCUMENTATION](https://docs.google.com/document/d/1lm-urvtgi0kvx1TILRmogWYFOAwT6IB4sA6JiF9t08g/edit?usp=sharing)
Raw Weekly Sprint: 
[SPRINT](url): https://docs.google.com/spreadsheets/d/11tFKn0aQsHmz-CdOrRBYxLLHYuSRU18gk6iSYKiSDsw/edit?usp=sharing




######### 
DOCKER -- production select file
docker compose --env-file .env.prod up # to up docker
docker compose --env-file .env.prod up --build # rebuild when new depencies added

Seeders (run after migrations, in order)
docker compose --env-file .env.prod exec backend python manage.py seed_permissions
docker compose --env-file .env.prod exec backend python manage.py seed_production_accounts
docker compose --env-file .env.prod exec backend python manage.py seed_role_permissions

Sample data seeders (run after core seeders, any order)
docker compose --env-file .env.prod exec backend python manage.py seed_production_month
docker compose --env-file .env.prod exec backend python manage.py seed_storefront
docker compose --env-file .env.prod exec backend python manage.py seed_sales_recent

Notes
seed_role_permissions expects permissions to exist (run seed_permissions first).
seed_production_accounts requires SEED_TENANT_1_ADMIN_PASSWORD and SEED_TENANT_2_ADMIN_PASSWORD env vars (or pass the flags).
seed_production_month wraps seed_sales_inventory_month (no need to run both).
seed_production_accounts defaults admin passwords to Admin123! (tenant 1) and Test123! (tenant 2) if not provided.

# PING REDIS

docker compose --env-file .env.prod exec redis redis-cli ping

# See Celery Tasks

docker compose --env-file .env.prod exec worker celery -A bid_config inspect registered

# RUN THE TEST IN DOCKER

docker compose --env-file .env.prod exec backend pytest
docker compose --env-file .env.prod exec backend pytest auth/tests/test_login.py
