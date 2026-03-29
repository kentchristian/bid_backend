# from celery import shared_task
# from django.core.cache import cache


# @shared_task
# def build_dashboard_metrics(tenant_id):
#     data = compute_dashboard_metrics(tenant_id)
#     cache.set(f"dashboard_metrics:{tenant_id}", data, timeout=60)

# FOR CELERY WORKERS
# TBD: When Application Scales
