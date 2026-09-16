# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/).

## [Unreleased]

### Added
- **Soft Delete** implementado para Dashboards y Registros Financieros. Se agregó el campo `is_active` en `UserFinanceDashboard` y `FinancialRecord`.
- Desactivación en cascada: Al desactivar (archivar) un Dashboard, automáticamente se desactivan todos sus registros asociados.
- Nuevo campo de solo lectura `category_name` en `FinancialRecordSerializer` para optimizar las peticiones del frontend.
- Validación de negocio en `FinancialRecord.clean()` para evitar asignar gastos/ingresos a Dashboards inactivos.

### Changed
- `DashboardViewSet` y `FinancialRecordViewSet` ahora filtran automáticamente los registros inactivos (`is_active=False`) en sus listados y operaciones.
- `CurrentDashboardView` fue actualizado para excluir registros eliminados en el cálculo del balance, total de ingresos y egresos.
- Comportamiento de los endpoints `DELETE`: ahora retornan un 204 No Content y ocultan el dato lógicamente en lugar de borrarlo físicamente.
