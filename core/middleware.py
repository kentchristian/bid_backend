# core/middleware.py
from django.db import connection

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET app.current_tenant = %s",
                    [str(request.user.tenant_id)]
                )

        response = self.get_response(request)

        # Optional: reset session variable to avoid pooling issues
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")

        return response