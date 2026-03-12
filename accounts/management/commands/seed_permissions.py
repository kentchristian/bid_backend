from django.core.management.base import BaseCommand

from accounts.models import Permission


# Uses the Permission Choices for Seeders
class Command(BaseCommand):
    help = "Seed Permission table using Permission.PERMISSION_CHOICES."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing Permission rows before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted_count, _ = Permission.objects.all().delete()
            self.stdout.write(f"Cleared {deleted_count} Permission rows.")

        created = 0
        existing = 0

        for code, _label in Permission.PERMISSION_CHOICES:
            obj, was_created = Permission.objects.get_or_create(name=code)
            if was_created:
                created += 1
            else:
                existing += 1

        self.stdout.write(
            f"Seeded permissions. created={created}, existing={existing}."
        )
