# Diseño de Base de Datos y API - GTOPagos Backend

Este documento detalla las decisiones de diseño técnico respecto al esquema de datos relacional, la integridad referencial y las directivas de construcción de la API REST.

---

## 🗄️ Diseño de Base de Datos (Esquema Relacional)

### 1. Entidades Principales

- **`User` (`users.models`)**:
  - Modelo de usuario personalizado que utiliza `email` como identificador único (`USERNAME_FIELD`).
  - Implementa `PermissionsMixin` e índices en `email` y `created_at`.
- **`UserProfile` (`users.models`)**:
  - Relación 1 a 1 obligatoria con `User`.
  - Almacena nombre completo, teléfono (`phone`), salario estimado (`salary`), moneda preferida (`Currency`) y frecuencia de cobro (`IncomeFrequency`).
  - Banderas de preferencias de notificación: `budget_alerts`, `goal_reminders`, `weekly_reports`, `monthly_reports`, `transaction_alerts`, `payment_reminders` y método de contacto (`email`, `sms`, `both`).
- **`UserFinanceDashboard` (`dashboard.models`)**:
  - Contenedor de presupuestos por usuario.
  - Campos: `name`, `description`, `dashboard_type` (`EXPENSES`, `INCOME`, `BOTH`), `is_active` (soft delete).
  - Relación 1 a N con `FinancialRecord`.
- **`FinancialRecord` (`finance.models`)**:
  - Transacción individual (ingreso o gasto).
  - Campos: `amount`, `description`, `record_date`, `is_recurrent`, `current_installment`, `total_installments`, `is_active`.
  - Llaves foráneas a `UserFinanceDashboard`, `FinancialRecordType`, `Category`, `PaymentMethod`, `PaymentStatus` y opcionalmente a `FinancialGoal`.
- **`FinancialGoal` (`finance.models`)**:
  - Objetivos de ahorro con `name`, `target_amount`, `saved_amount`, `target_date` y relación inversa a movimientos vinculados (`linked_records`).
- **`CategoryKeyword` (`finance.models`)**:
  - Diccionario de palabras clave asociadas a cada categoría para el motor de deducción automática.
  - Limpieza de datos en `clean()` para garantizar términos en minúsculas y sin espacios.

### 2. Catálogos de Dominio (Lookups)
- **`FinancialRecordType`**: Define el comportamiento transaccional (`INCOME`, `EXPENSE`, `TRANSFER`).
- **`Category`**: Clasificación jerárquica con soporte para iconos, colores y categorías personalizadas por usuario.
- **`PaymentMethod`**: Métodos aceptados (Efectivo, Débito, Crédito, Transferencia bancaria).
- **`PaymentStatus`**: Estados de liquidación (`paid`, `pending`).
- **`Currency`**: Catálogo de monedas internacionales (Código ISO, Símbolo, Orden).
- **`IncomeFrequency`**: Periodicidades de ingreso (Semanal, Quincenal, Mensual).

---

## 🌐 Diseño y Estándares de la API REST

### 1. Respuestas Predecibles y Verbos HTTP
- Implementación basada en `ModelViewSet` y `APIView` de Django REST Framework respetando los estándares RFC:
  - `GET`: Lectura de recursos (200 OK con payload paginado o plano).
  - `POST`: Creación de recursos (201 Created) o invocación de procesos funcionales (200 OK).
  - `PUT / PATCH`: Modificación idempotente o parcial (200 OK).
  - `DELETE`: Borrado lógico (204 No Content, aplicando `is_active=False`).

### 2. Documentación Automatizada con OpenAPI 3
- Todas las vistas y acciones personalizadas utilizan decoradores `@extend_schema` y `@extend_schema_view` de `drf-spectacular`.
- Parámetros de consulta tipados (ej. filtros temporales `start_date`, `end_date`, `period`), esquemas de solicitud multipart/form-data para cargas de Excel y tipado riguroso de esquemas de respuesta.

### 3. Paginación Uniforme
- Las colecciones extensas implementan `StandardResultsSetPagination` (tamaño de página predeterminado de 10 a 20 elementos), retornando la estructura estándar:
  ```json
  {
    "count": 120,
    "next": "http://localhost:8000/api/financial-records/?page=2",
    "previous": null,
    "results": [...]
  }
  ```

### 4. Formato de Respuestas de Error
- Validaciones de entrada procesadas por serializadores devuelven formato uniforme `400 Bad Request`:
  ```json
  {
    "campo": ["Descripción del error de validación."]
  }
  ```
- Accesos denegados o no autorizados retornan `401 Unauthorized` o `403 Forbidden` coordinados con el `ErrorInterceptor` del cliente frontend.

