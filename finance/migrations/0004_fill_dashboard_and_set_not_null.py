from django.db import migrations, models
import django.db.models.deletion


def assign_default_dashboards(apps, schema_editor):
    FinancialRecord = apps.get_model('finance', 'FinancialRecord')
    Dashboard = apps.get_model('dashboard', 'UserFinanceDashboard')

    # For each record without dashboard, attach one dashboard per user
    records = FinancialRecord.objects.filter(dashboard__isnull=True).select_related('user')
    by_user = {}
    for rec in records:
        dash = by_user.get(rec.user_id)
        if dash is None:
            # Try to reuse an existing dashboard for the user or create a new one
            dash = Dashboard.objects.filter(user_id=rec.user_id).first()
            if dash is None:
                dash = Dashboard.objects.create(user_id=rec.user_id)
            by_user[rec.user_id] = dash
        rec.dashboard_id = dash.id
        rec.save(update_fields=['dashboard'])


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_alter_userfinancedashboard_options_and_more'),
        ('finance', '0003_financialrecord_dashboard_and_more'),
    ]

    operations = [
        migrations.RunPython(assign_default_dashboards, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='financialrecord',
            name='dashboard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='financial_records', to='dashboard.userfinancedashboard'),
        ),
    ]

