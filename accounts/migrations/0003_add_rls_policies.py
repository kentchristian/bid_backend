

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_tenant'),
    ]

    operations = [
        # Add RLS policies to Users table
        migrations.RunSQL("""
            ALTER TABLE accounts_user ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation_policy
            ON accounts_user
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
        """),
        
        # Add RLS policies to Roles table
        migrations.RunSQL("""
            ALTER TABLE accounts_role ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation_policy
            ON accounts_role
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
        """),
    ]