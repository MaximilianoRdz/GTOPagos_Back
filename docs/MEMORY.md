# Memory Context

Este documento mantiene un registro del estado mental del proyecto, decisiones de diseño históricas y peculiaridades del código para transferir contexto rápidamente.

## Decisiones de Diseño Importantes

### 1. Sistema de Eliminación (Soft Delete)
- **Contexto:** En aplicaciones financieras, la pérdida accidental de datos es crítica.
- **Implementación:** Se utiliza un patrón de borrado lógico. Tanto `UserFinanceDashboard` como `FinancialRecord` tienen un campo `is_active`.
- **Efectos secundarios:** 
  - Al borrar un Dashboard mediante la API, se desencadena una actualización en cascada que pone `is_active=False` a todos los registros que contiene.
  - Los endpoints de lectura (`GET`) siempre asumen el filtro `is_active=True`.
  - Los modelos impiden (mediante validación) agregar nuevos registros a Dashboards inactivos.

### 2. Cálculos en Base de Datos vs Memoria
- Para el dashboard de resúmenes (`CurrentDashboardView`), se prefirió calcular `total_income`, `total_expense`, saldos pagados y pendientes delegando el esfuerzo al motor de base de datos usando `aggregate` y `annotate` en lugar de iterar objetos en Python. Esto garantiza un mejor rendimiento a medida que crecen los registros de un usuario.

### 3. Metadata de Registros Financieros
- Los pagos recurrentes (suscripciones, cuotas) están separados físicamente. La información de recurrencia y notas extra viven en el modelo `FinancialRecordMetadata` en una relación 1 a 1.
- Esto mantiene la tabla principal `FinancialRecord` ligera, consultando la metadata solo cuando es necesario.

## Bugs Conocidos / Limitaciones Actuales
- Actualmente no hay un "Cron Job" o tarea en segundo plano (Celery) configurada para auto-generar los pagos recurrentes basados en `FinancialRecordMetadata`. Esta es un área futura de desarrollo.
