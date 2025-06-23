import os
import psycopg2
from psycopg2 import sql
from django.conf import settings

def reset_database():
    # Obtener la configuración de la base de datos
    db_settings = settings.DATABASES['default']
    
    # Conectar a la base de datos postgres para poder eliminar la base de datos actual
    conn = psycopg2.connect(
        dbname='postgres',
        user=db_settings['USER'],
        password=db_settings['PASSWORD'],
        host=db_settings['HOST'],
        port=db_settings['PORT']
    )
    conn.autocommit = True
    
    # Crear un cursor
    cursor = conn.cursor()
    
    try:
        # Terminar todas las conexiones a la base de datos
        cursor.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid();
        """, [db_settings['NAME']])
        
        # Eliminar la base de datos si existe
        cursor.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(
                sql.Identifier(db_settings['NAME'])
            )
        )
        
        # Crear una nueva base de datos
        cursor.execute(
            sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_settings['NAME'])
            )
        )
        
        print(f"Base de datos {db_settings['NAME']} ha sido recreada exitosamente.")
        
    except Exception as e:
        print(f"Error al recrear la base de datos: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gtopagos.settings')
    import django
    django.setup()
    reset_database()
