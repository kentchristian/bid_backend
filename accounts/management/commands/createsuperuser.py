def create_superuser(self, email, name, password=None, tenant=None, **extra_fields):
    if tenant is None:
        from .models import Tenant
        tenant = Tenant.objects.first()  # or pick a default tenant
    extra_fields.setdefault("is_staff", True)
    extra_fields.setdefault("is_superuser", True)
    extra_fields.setdefault("is_active", True)
    return self.create_user(email, name, password, tenant=tenant, **extra_fields)