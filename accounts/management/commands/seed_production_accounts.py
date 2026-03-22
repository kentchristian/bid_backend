import os

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from accounts.models import Role, Tenant, User


PLAN_CHOICES = [choice[0] for choice in Tenant.PLAN_CHOICES]


class Command(BaseCommand):
    help = "Seed two tenants and their superuser accounts for production."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-1-name", default=None)
        parser.add_argument("--tenant-2-name", default=None)
        parser.add_argument("--tenant-1-plan", default=None, choices=PLAN_CHOICES)
        parser.add_argument("--tenant-2-plan", default=None, choices=PLAN_CHOICES)

        parser.add_argument("--tenant-1-admin-name", default=None)
        parser.add_argument("--tenant-2-admin-name", default=None)
        parser.add_argument("--tenant-1-admin-email", default=None)
        parser.add_argument("--tenant-2-admin-email", default=None)
        parser.add_argument("--tenant-1-admin-password", default=None)
        parser.add_argument("--tenant-2-admin-password", default=None)

        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords for existing admin users in the same tenant.",
        )

    def handle(self, *args, **options):
        configs = [
            self._build_config(1, options),
            self._build_config(2, options),
        ]

        for config in configs:
            tenant = self._ensure_tenant(config)
            self._set_current_tenant(tenant.id)
            try:
                with transaction.atomic():
                    role = self._ensure_admin_role(tenant)
                    self._ensure_admin_user(
                        tenant,
                        role,
                        config,
                        reset_passwords=options["reset_passwords"],
                    )
            finally:
                self._reset_current_tenant()

    def _build_config(self, index, options):
        defaults = {
            "name": f"Tenant {index}",
            "plan": "pro",
            "admin_name": f"Tenant {index} Admin",
            "admin_email": f"tenant{index}.admin@example.com",
        }

        name = self._resolve_value(
            options[f"tenant_{index}_name"],
            f"SEED_TENANT_{index}_NAME",
            default=defaults["name"],
        )
        plan = self._resolve_value(
            options[f"tenant_{index}_plan"],
            f"SEED_TENANT_{index}_PLAN",
            default=defaults["plan"],
        )
        if plan not in PLAN_CHOICES:
            raise CommandError(
                f"Invalid plan '{plan}' for tenant {index}. "
                f"Choose from: {', '.join(PLAN_CHOICES)}."
            )

        admin_name = self._resolve_value(
            options[f"tenant_{index}_admin_name"],
            f"SEED_TENANT_{index}_ADMIN_NAME",
            default=defaults["admin_name"],
        )
        admin_email = self._resolve_value(
            options[f"tenant_{index}_admin_email"],
            f"SEED_TENANT_{index}_ADMIN_EMAIL",
            default=defaults["admin_email"],
        )
        admin_password = self._resolve_value(
            options[f"tenant_{index}_admin_password"],
            f"SEED_TENANT_{index}_ADMIN_PASSWORD",
            required=True,
        )

        if not admin_password:
            raise CommandError(
                f"Missing admin password for tenant {index}. "
                f"Set --tenant-{index}-admin-password or "
                f"SEED_TENANT_{index}_ADMIN_PASSWORD."
            )

        return {
            "index": index,
            "name": name,
            "plan": plan,
            "admin_name": admin_name,
            "admin_email": admin_email,
            "admin_password": admin_password,
        }

    def _resolve_value(self, cli_value, env_key, default=None, required=False):
        if cli_value:
            return cli_value
        env_value = os.getenv(env_key)
        if env_value:
            return env_value
        if required:
            return None
        return default

    def _ensure_tenant(self, config):
        tenant, created = Tenant.objects.get_or_create(
            name=config["name"],
            defaults={"plan": config["plan"]},
        )
        if not created and tenant.plan != config["plan"]:
            tenant.plan = config["plan"]
            tenant.save(update_fields=["plan"])
            self.stdout.write(
                f"Updated plan for tenant '{tenant.name}' to '{tenant.plan}'."
            )
        if created:
            self.stdout.write(
                f"Created tenant '{tenant.name}' with plan '{tenant.plan}'."
            )
        return tenant

    def _ensure_admin_role(self, tenant):
        role, created = Role.objects.get_or_create(tenant=tenant, name="admin")
        if created:
            self.stdout.write(
                f"Created admin role for tenant '{tenant.name}'."
            )
        return role

    def _ensure_admin_user(self, tenant, role, config, reset_passwords=False):
        email = User.objects.normalize_email(config["admin_email"])
        user = User.objects.filter(email=email).first()

        if user:
            if user.tenant_id != tenant.id:
                raise CommandError(
                    f"Admin email '{email}' already exists on a different tenant."
                )
            changed_fields = []
            if user.role_id != role.id:
                user.role = role
                changed_fields.append("role")
            if not user.is_staff:
                user.is_staff = True
                changed_fields.append("is_staff")
            if not user.is_superuser:
                user.is_superuser = True
                changed_fields.append("is_superuser")
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            if reset_passwords:
                user.set_password(config["admin_password"])
                changed_fields.append("password")
            if changed_fields:
                user.save()
                self.stdout.write(
                    f"Updated admin user '{email}' "
                    f"({', '.join(changed_fields)})."
                )
            else:
                self.stdout.write(
                    f"Admin user '{email}' already exists."
                )
            return

        User.objects.create_superuser(
            email=email,
            name=config["admin_name"],
            password=config["admin_password"],
            tenant=tenant,
            role=role,
        )
        self.stdout.write(
            f"Created admin user '{email}' for tenant '{tenant.name}'."
        )

    def _set_current_tenant(self, tenant_id):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('app.current_tenant', %s, false)",
                [str(tenant_id)],
            )

    def _reset_current_tenant(self):
        if connection.vendor != "postgresql":
            return
        with connection.cursor() as cursor:
            cursor.execute("RESET app.current_tenant")
