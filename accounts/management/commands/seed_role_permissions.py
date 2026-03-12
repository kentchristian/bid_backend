from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Permission, Role, RolePermission, Tenant


ROLE_NAMES = ("admin", "manager", "staff")
MANAGER_PREFIXES = ("view_", "create_", "edit_", "change_")
STAFF_PREFIXES = ("view_",)


class Command(BaseCommand):
    help = "Seed RolePermission mappings for admin/manager/staff roles per tenant."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing RolePermission rows for admin/manager/staff before seeding.",
        )

    def handle(self, *args, **options):
        tenants = list(Tenant.objects.order_by("created_at"))
        if not tenants:
            raise CommandError("No tenants found. Create tenants first.")

        permissions = list(Permission.objects.order_by("name"))
        if not permissions:
            raise CommandError(
                "No permissions found. Run `python manage.py seed_permissions` first."
            )

        if options["clear"]:
            deleted_count, _ = RolePermission.objects.filter(
                role__tenant__in=tenants, role__name__in=ROLE_NAMES
            ).delete()
            self.stdout.write(
                f"Cleared {deleted_count} RolePermission rows for admin/manager/staff."
            )

        created = 0
        existing = 0

        with transaction.atomic():
            for tenant in tenants:
                for role_name in ROLE_NAMES:
                    role, _ = Role.objects.get_or_create(
                        tenant=tenant, name=role_name
                    )
                    desired = self._select_permissions(role_name, permissions)
                    for perm in desired:
                        _, was_created = RolePermission.objects.get_or_create(
                            role=role, permission=perm
                        )
                        if was_created:
                            created += 1
                        else:
                            existing += 1

        self.stdout.write(
            f"Seeded role permissions. created={created}, existing={existing}."
        )

    def _select_permissions(self, role_name, permissions):
        if role_name == "admin":
            return permissions
        if role_name == "manager":
            return [
                perm
                for perm in permissions
                if perm.name.startswith(MANAGER_PREFIXES)
            ]
        if role_name == "staff":
            return [
                perm
                for perm in permissions
                if perm.name.startswith(STAFF_PREFIXES)
            ]
        return []
