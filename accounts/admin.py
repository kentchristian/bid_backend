from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Permission, Role, RolePermission, Tenant, User

# Optional: Custom form to handle foreign keys
class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"  # include all fields including tenant and role

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tenant = None
        if self.data.get("tenant"):
            tenant = Tenant.objects.filter(pk=self.data.get("tenant")).first()
        elif self.instance and self.instance.tenant_id:
            tenant = self.instance.tenant

        role_field = self.fields.get("role")
        if not role_field:
            return

        if tenant:
            role_field.queryset = Role.objects.filter(tenant=tenant).order_by("name")
        else:
            role_field.queryset = Role.objects.none()
            role_field.help_text = "Select a tenant first to see available roles."

# Admins for Tenant and Role with search_fields
@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ["name", "plan", "created_at", "deleted_at"]
    list_filter = ["plan"]
    ordering = ["name"]
    search_fields = ["name"]  # <-- required for autocomplete

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "tenant", "permissions_count", "created_at"]
    list_filter = ["tenant", "name"]
    ordering = ["tenant__name", "name"]
    search_fields = ["name", "tenant__name"]  # <-- required for autocomplete
    list_select_related = ["tenant"]
    autocomplete_fields = ["tenant"]

    def permissions_count(self, obj):
        return obj.permissions.count()

    permissions_count.short_description = "Permissions"


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0
    autocomplete_fields = ["permission"]


RoleAdmin.inlines = [RolePermissionInline]

# Custom UserAdmin
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm  # use custom form
    ordering = ["email"]
    list_display = [
        "email",
        "name",
        "tenant_display",
        "role_display",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    ]
    list_filter = ["tenant", "role", "is_active", "is_staff", "is_superuser"]
    search_fields = ["email", "name", "tenant__name", "role__name"]
    list_select_related = ["tenant", "role"]
    autocomplete_fields = ["tenant", "role"]  # now works properly
    filter_horizontal = ("groups", "user_permissions")

    # Fields when editing an existing user
    readonly_fields = ("created_at", "updated_at", "deleted_at")  # make timestamps read-only
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "tenant", "role")}),
        ("Access", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("created_at", "updated_at", "deleted_at")}),
    )

    # Fields when adding a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "tenant", "role", "is_staff", "is_superuser"),
        }),
    )

    def tenant_display(self, obj):
        return obj.tenant.name if obj.tenant else "No tenant"

    tenant_display.short_description = "Tenant"
    tenant_display.admin_order_field = "tenant__name"

    def role_display(self, obj):
        return obj.role.name if obj.role else "No role"

    role_display.short_description = "Role"
    role_display.admin_order_field = "role__name"
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ["role", "permission"]
    list_filter = ["role__tenant", "role__name", "permission__name"]
    search_fields = ["role__name", "role__tenant__name", "permission__name"]
    autocomplete_fields = ["role", "permission"]
    list_select_related = ["role", "permission"]
