# Changelog - GTOPagos Backend

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/), y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [Unreleased]

### Planned
- Tareas programadas periódicas en segundo plano con Celery / Redis para automatizar el cobro y generación de suscripciones recurrentes.
- Integración de proveedores de pago e interfaces bancarias (Open Banking / Plaid).
- Notificaciones push mediante Webhooks o Firebase Cloud Messaging (FCM).

---

## [0.2.0] - 2026-09-16

### Added
- **Modo Demo Dinámico (`POST /api/demo-login/`)**:
  - Endpoint público y generador aislado `users/demo_data.py` que crea o inicializa de forma idempotente un usuario de prueba (`demo@gtopagos.com`).
  - Siembra integral de datos financieros de ejemplo: tableros de presupuestos, categorías personalizadas, movimientos al contado y a crédito, compras en cuotas (MSI), gastos recurrentes y metas de ahorro.
  - Generación y retorno de tokens JWT válidos (`access` y `refresh`) para que evaluadores de portafolio e invitados interactúen sin necesidad de registro previo.
- **Módulo de Metas Financieras (`FinancialGoal`)**:
  - Nuevo modelo `FinancialGoal` en la app `finance` para registrar objetivos de ahorro con monto meta (`target_amount`), saldo acumulado (`saved_amount`) y fecha estimada (`target_date`).
  - ViewSet completo `FinancialGoalViewSet` registrado en `/api/finance/goals/` con validaciones de usuario, cálculo de progreso y ordenamiento.
  - Relación foránea `financial_goal` en `FinancialRecord` para vincular aportaciones individuales de ahorro a metas específicas.
- **Motor Inteligente de Detección de Categorías (`CategoryKeyword`)**:
  - Modelo relacional `CategoryKeyword` para asociar palabras clave normalizadas a categorías financieras.
  - Servicio `category_detector_service.py` que analiza cadenas de texto extraídas de descripciones o estados de cuenta y deduce automáticamente la categoría correspondiente.
  - Endpoint `POST /api/finance/transactions/detect-category`.
- **Arquitectura de Capa de Servicios (`finance/services/`)**:
  - `import_engine.py`: Motor de importación masiva de estados de cuenta con parsing, deduplicación y mapeo hacia tableros.
  - `recurrence_service.py`: Lógica para procesar movimientos recurrentes y proyección de pagos.
  - `report_export_service.py`: Generador de exportables en formatos **PDF** y **Excel** (`.xlsx`).
- **Arquitectura de Patrón de Selectores (`selectors/`)**:
  - `finance/selectors/report_selectors.py`: Consultas agregadas especializadas para reportes analíticos mensuales, anuales y distribución de gastos.
  - `dashboard/selectors/dashboard_selectors.py`: Consultas optimizadas con agregaciones del ORM (`Sum`, `Count`, `Case`, `When`) para resúmenes de tablero, métricas de pagos pendientes y transacciones recientes.
- **Endpoints Analíticos y de Exportación**:
  - `POST /api/finance/import/preview/` y `POST /api/finance/import/confirm/`: Previsualización y confirmación de importación masiva.
  - `GET /api/finance/reports/data/`: Datos analíticos consolidados por rango temporal.
  - `GET /api/finance/reports/download/`: Descarga de reportes estructurados en PDF o Excel.
  - `GET /api/finance/export/`: Exportación completa de tableros.
  - `GET /api/dashboard/recent-transactions/`: Historial transversal de últimas transacciones.
  - `GET /api/dashboard/upcoming-due/`: Listado de pagos y cuotas próximas a vencer.
- **Ampliación de Perfil de Usuario (`UserProfile`)**:
  - Campos de teléfono (`phone`), salario (`salary`), moneda preferida (`currency`) y frecuencia de ingresos (`income_frequency`).
  - Preferencias de notificación: `budget_alerts`, `goal_reminders`, `weekly_reports`, `monthly_reports`, `transaction_alerts`, `payment_reminders` y método preferido (`email`, `sms`, `both`).
- **Infraestructura y Contenedores**:
  - `Dockerfile` optimizado con Python 3.12 y Gunicorn.
  - `docker-compose.yml` para orquestación de servicios locales (Django, PostgreSQL).

### Changed
- Refactorización de ViewSets hacia controladores delgados ("thin views"), delegando la lógica de agregación a los selectores y la persistencia compleja a los servicios.
- Estandarización de documentación OpenAPI 3 mediante decoradores `@extend_schema` y `@extend_schema_view` de `drf-spectacular`.

---

## [0.1.0] - 2026-07-25

### Added
- **Soft Delete** implementado para Dashboards y Registros Financieros. Se agregó el campo `is_active` en `UserFinanceDashboard` y `FinancialRecord`.
- Desactivación en cascada: Al desactivar (archivar) un Dashboard, automáticamente se desactivan todos sus registros asociados.
- Nuevo campo de solo lectura `category_name` en `FinancialRecordSerializer` para optimizar las peticiones del frontend.
- Validación de negocio en `FinancialRecord.clean()` para evitar asignar gastos/ingresos a Dashboards inactivos.

### Changed
- `DashboardViewSet` y `FinancialRecordViewSet` ahora filtran automáticamente los registros inactivos (`is_active=False`) en sus listados y operaciones.
- `CurrentDashboardView` fue actualizado para excluir registros eliminados en el cálculo del balance, total de ingresos y egresos.
- Comportamiento de los endpoints `DELETE`: ahora retornan un 204 No Content y ocultan el dato lógicamente en lugar de borrarlo físicamente.
