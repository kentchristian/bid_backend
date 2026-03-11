from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import User, Tenant, Role

# Optional: Custom form to handle foreign keys
class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = "__all__"  # include all fields including tenant and role

# Custom UserAdmin
class UserAdmin(BaseUserAdmin):
    form = UserAdminForm  # use custom form
    ordering = ["email"]
    list_display = ["email", "name", "tenant", "role", "is_staff", "is_superuser"]
    list_filter = ["is_staff", "is_superuser", "is_active", "tenant"]
    search_fields = ["email", "name"]

    # Fields when editing an existing user
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("name", "tenant", "role")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "is_active", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    # Fields when adding a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "tenant", "role", "is_staff", "is_superuser"),
        }),
    )

    autocomplete_fields = ["tenant", "role"]  # optional if you want search dropdowns for large tables

admin.site.register(User)
admin.site.register(Tenant)
admin.site.register(Role)