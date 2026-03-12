from django.db import connection


class CurrentTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            self._set_current_tenant(request)
            return self.get_response(request)
        finally:
            self._reset_current_tenant()

    def _set_current_tenant(self, request):
        if connection.vendor != "postgresql":
            return
        user = getattr(request, "user", None)
        tenant_id = None
        if user and user.is_authenticated and user.tenant_id:
            tenant_id = str(user.tenant_id)
        if not tenant_id:
            return
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant', %s, false)",
                [tenant_id],
            )

    def _reset_current_tenant(self):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")
