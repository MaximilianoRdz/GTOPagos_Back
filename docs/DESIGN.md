# Design

Este documento explica las decisiones de diseño a nivel de esquemas de bases de datos y arquitectura de la API.

## Diseño de Base de Datos (Esquema)

*(Referencia visual: ver `db_uml.png` en la raíz del proyecto).*

### Entidades Principales:
- **`User`**: (De la app `users`). Autenticación y relación dueña de la información.
- **`UserFinanceDashboard`**: Contenedor lógico. Se relaciona 1 a N con `FinancialRecord`.
- **`FinancialRecord`**: La tabla central. Contiene monto, fecha, descripciones y flags de cuotas. Posee múltiples llaves foráneas apuntando a catálogos para mantener normalización.
- **`FinancialRecordMetadata`**: Extensión 1 a 1 de `FinancialRecord`. Almacena datos complejos de temporalidad y frecuencias (útil para que consultas estándar sean rápidas al no cargar estos campos extra si no son necesarios).

### Catálogos de Dominio (Lookups):
- `FinancialRecordType`: Fijo. Determina el comportamiento (INCOME, EXPENSE, TRANSFER).
- `Category`: Dependiente de `FinancialRecordType`. Un gasto no puede usar una categoría de ingreso.
- `PaymentMethod` / `PaymentStatus`: Flexibilidad para marcar cosas pendientes de pagar.

## Diseño de API (API Design)

1. **Respuestas Predecibles**
   - Uso de Django REST Framework `ModelViewSet` garantiza estándares para verbos HTTP (GET, POST, PUT, PATCH, DELETE).
   
2. **Documentación Automática**
   - Decoradores `@extend_schema` y `@extend_schema_view` de `drf-spectacular` se utilizan extensamente en `views.py`. Esto provee tipos exactos para parámetros, variables de consulta (ej. `period=month`) y mapeo de respuestas 200/201, permitiendo generación automática de clientes frontend.

3. **Arquitectura No Destructiva (Soft Delete)**
   - El diseño del sistema no permite el borrado físico (Hard Delete). Todo DELETE HTTP actúa como un PATCH en la base de datos para `is_active=False`.

4. **Paginación**
   - Listados de gran tamaño (como `DashboardRecordsView`) utilizan `StandardResultsSetPagination` para evitar saturación de red.
