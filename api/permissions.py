from rest_framework.permissions import BasePermission

from accounts.models import RolePermission


class RolePermissionRequired(BasePermission):
    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True

        permission_map = getattr(view, "permission_map", {})
        required = permission_map.get(getattr(view, "action", None))
        if not required:
            return False

        user = request.user
        if not user or not user.is_authenticated:
            return False
        if not user.role_id or not user.tenant_id:
            return False
        if user.role.tenant_id != user.tenant_id:
            return False

        return RolePermission.objects.filter(
            role=user.role, permission__name=required
        ).exists()
