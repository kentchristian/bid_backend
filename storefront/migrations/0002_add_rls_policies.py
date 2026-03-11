

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('storefront', '0001_initial'),
    ]

    operations = [
        # Add RLS policies to Sale table
        migrations.RunSQL("""
            ALTER TABLE storefront_sale ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation_policy
            ON storefront_sale
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
        """),
        
        # Add RLS policies to Inventory table
        migrations.RunSQL("""
            ALTER TABLE storefront_inventory ENABLE ROW LEVEL SECURITY;

            CREATE POLICY tenant_isolation_policy
            ON storefront_inventory
            USING (tenant_id = current_setting('app.current_tenant')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant')::uuid);
        """)
    ]