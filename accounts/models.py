from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid
from django.db import models
# ===== TENANT MODEL ===== # GLobal
class Tenant(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


# ===== ROLE MODEL ===== # Tenant-specific
class Role(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


# ===== PERMISSIONS =====
class Permission(models.Model):
    PERMISSION_CHOICES = [
        # Tenant
        ("view_tenant", "View Tenant"),
        ("create_tenant", "Create Tenant"),
        ("edit_tenant", "Edit Tenant"),
        ("delete_tenant", "Delete Tenant"),

        # Role
        ("view_role", "View Role"),
        ("create_role", "Create Role"),
        ("edit_role", "Edit Role"),
        ("delete_role", "Delete Role"),

        # Permission
        ("view_permission", "View Permission"),
        ("create_permission", "Create Permission"),
        ("edit_permission", "Edit Permission"),
        ("delete_permission", "Delete Permission"),

        # RolePermission
        ("view_role_permission", "View Role Permission"),
        ("create_role_permission", "Create Role Permission"),
        ("edit_role_permission", "Edit Role Permission"),
        ("delete_role_permission", "Delete Role Permission"),

        # User
        ("view_user", "View User"),
        ("create_user", "Create User"),
        ("edit_user", "Edit User"),
        ("delete_user", "Delete User"),

        # Sale
        ("view_sale", "View Sale"),
        ("create_sale", "Create Sale"),
        ("edit_sale", "Edit Sale"),
        ("delete_sale", "Delete Sale"),

        # Inventory
        ("view_inventory", "View Inventory"),
        ("create_inventory", "Create Inventory"),
        ("edit_inventory", "Edit Inventory"),
        ("delete_inventory", "Delete Inventory"),

        # ActivityLog (often view‑only, but CRUD listed for completeness)
        ("view_activity_log", "View Activity Log"),
        ("create_activity_log", "Create Activity Log"),
        ("edit_activity_log", "Edit Activity Log"),
        ("delete_activity_log", "Delete Activity Log"),

        ("view_category", "View Category"),
        ("create_category", "Create Category"),
        ("edit_category", "Edit Category"),
        ("delete_category", "Delete Category"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=PERMISSION_CHOICES)

    def __str__(self):
        return self.name


# ===== ROLE PERMISSION MAPPING =====
class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('role', 'permission')





# ===== USER MANAGER =====
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, name, password, **extra_fields)



# ===== USER MODEL ===== # Tenant-specific
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="users")
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    role = models.ForeignKey("Role", on_delete=models.SET_NULL, null=True, related_name="users")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()  # replace default Manager

    def __str__(self):
        tenant_name = self.tenant.name if self.tenant else "No Tenant"
        return f"{self.email} ({tenant_name})"


