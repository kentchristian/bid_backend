# core/middleware.py
from django.db import connection
from django.http import HttpResponseForbidden

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _resolve_tenant_id(self, request):
        # Example: header-based
        return request.headers.get("X-Tenant-ID")

    def __call__(self, request):
        tenant_id = self._resolve_tenant_id(request)
        if not tenant_id:
            return HttpResponseForbidden("Missing tenant")

        # Set per-connection setting
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant', %s, false)",
                [str(tenant_id)]
            )

        try:
            return self.get_response(request)
        finally:
            # Always clear to avoid tenant leak across pooled connections
            with connection.cursor() as cursor:
                cursor.execute("RESET app.current_tenant")
