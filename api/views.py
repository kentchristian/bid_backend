import uuid
from contextlib import contextmanager

from django.db import connection
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_GET

from storefront.models import Inventory, Sale


def _parse_tenant_id(request):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        return None, HttpResponseForbidden("Missing tenant")
    try:
        uuid.UUID(str(tenant_id))
    except (TypeError, ValueError):
        return None, HttpResponseBadRequest("Invalid tenant")
    return str(tenant_id), None


@contextmanager
def _tenant_context(tenant_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('app.current_tenant', %s, false)",
            [tenant_id],
        )
    try:
        yield
    finally:
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")


@require_GET
def inventory_list(request):
    tenant_id, error = _parse_tenant_id(request)
    if error:
        return error

    with _tenant_context(tenant_id):
        # Intentionally rely on RLS (no explicit tenant filter).
        items = list(
            Inventory.objects.order_by("product_name").values(
                "id",
                "tenant_id",
                "product_name",
                "stock_quantity",
                "reorder_threshold",
                "updated_at",
            ).filter(tenant_id=tenant_id) # filter return 
        )

    return JsonResponse({"count": len(items), "results": items})


@require_GET
def sales_list(request):
    tenant_id, error = _parse_tenant_id(request)
    if error:
        return error

    with _tenant_context(tenant_id):
        # Intentionally rely on RLS (no explicit tenant filter).
        items = list(
            Sale.objects.order_by("-sold_at").values(
                "id",
                "tenant_id",
                "product_id",
                "quantity",
                "unit_price",
                "total_price",
                "sold_at",
                "created_by_id",
            )
        )

    return JsonResponse({"count": len(items), "results": items})
