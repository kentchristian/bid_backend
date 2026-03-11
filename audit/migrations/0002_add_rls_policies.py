

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        # Add RLS policies to Users table
        migrations.RunSQL("""
            ALTER TABLE audit_activitylog ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation_policy
            ON audit_activitylog
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
        """)
    ]