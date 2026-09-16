# Architecture

**GTOPagos_Back** es un backend construido con Python y Django, enfocado en proveer una API REST robusta para una aplicación de finanzas personales.

## Stack Tecnológico
- **Framework Principal:** Django.
- **API Framework:** Django REST Framework (DRF).
- **Documentación de API:** drf-spectacular (Generación de esquema OpenAPI 3).
- **Base de Datos:** Relacional (Soportado por el ORM de Django).

## Estructura de Aplicaciones (Apps)
El monolito está dividido en aplicaciones lógicas y modulares:

1. **`users`**: Gestión de usuarios, autenticación y configuraciones regionales (como `Currency`).
2. **`dashboard`**: Contenedores principales (Dashboards). Permite tener múltiples vistas financieras por usuario. Contiene lógica de resumen y agrupación.
3. **`finance`**: Corazón transaccional. Maneja `FinancialRecord` (gastos, ingresos, transferencias), categorías, tipos de registros y la metadatos (`FinancialRecordMetadata`) para manejar recurrencias y recordatorios.
4. **`payments`**: Catálogos auxiliares como `PaymentMethod` (Efectivo, Tarjeta, etc.) y `PaymentStatus` (Pendiente, Pagado).

## Flujo de Datos
- Las solicitudes HTTP son interceptadas por las rutas en `urls.py`.
- Se validan mediante `IsAuthenticated` para garantizar acceso seguro.
- Los `ViewSets` delegan la transformación de datos a los `Serializers`.
- La lógica de acceso a datos usa intensamente `select_related` y `prefetch_related` para evitar el problema de N+1 consultas en la base de datos.
- Las consultas complejas (agrupaciones mensuales, sumatorias) se manejan utilizando funciones de agregación de la base de datos (`Sum`, `Count`, `Case`, `When`) dentro de las vistas (`CurrentDashboardView`).
