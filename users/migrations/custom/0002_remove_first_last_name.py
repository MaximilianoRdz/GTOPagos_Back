from django.db import migrations


def remove_first_last_name_fields(apps, schema_editor):
    """
    Elimina los campos first_name y last_name si existen en el modelo User.
    """
    User = apps.get_model('users', 'User')
    
    # Eliminar los campos si existen
    for field_name in ['first_name', 'last_name']:
        try:
            field = User._meta.get_field(field_name)
            schema_editor.remove_field(User, field)
        except Exception as e:
            print(f"El campo {field_name} no existe o no se pudo eliminar: {e}")


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_first_last_name_fields),
    ]
