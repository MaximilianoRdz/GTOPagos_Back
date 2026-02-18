from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_alter_incomefrequency_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE users_currency
            ADD COLUMN IF NOT EXISTS sort_order integer DEFAULT 100;
            """,
            reverse_sql="""
            ALTER TABLE users_currency
            DROP COLUMN IF EXISTS sort_order;
            """,
        ),
    ]

