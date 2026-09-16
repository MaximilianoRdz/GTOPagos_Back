# Product Requirements Document (PRD)

## Descripción del Producto
**GTOPagos** es una plataforma de gestión de finanzas personales diseñada para ofrecer a los usuarios control total sobre sus ingresos, gastos y suscripciones. El backend sirve como el motor de datos que consolida la información financiera y la sirve de manera eficiente a los clientes (Frontend web / móvil).

## Funcionalidades Principales

1. **Gestión de Dashboards Multiples**
   - Un usuario puede tener varios "Dashboards" (ej. "Gastos Personales", "Negocio", "Viaje a Japón").
   - Aislamiento de datos: Los gastos se agrupan por Dashboard para no mezclar presupuestos.

2. **Registro Transaccional**
   - Soporte para **Ingresos**, **Gastos** y **Transferencias**.
   - Seguimiento de Estado de Pago (Pendiente, Pagado).
   - Asignación de Métodos de Pago.

3. **Pagos Recurrentes e Instalamentos (MSI)**
   - Soporte para marcar registros como recurrentes (ej. Netflix mensual).
   - Seguimiento de cuotas (`current_installment` / `total_installments`) para compras a meses sin intereses.

4. **Resúmenes Analíticos en Tiempo Real**
   - El sistema calcula instantáneamente balances, sumatorias de ingresos/gastos y agrupaciones por categoría para el mes en curso o el año, listos para ser graficados.

## Objetivos a Futuro
- Implementación de notificaciones de cobro/pago pendiente.
- Sistema automatizado de generación de registros para suscripciones mensuales activas.
- Soporte multimoneda con conversión en tiempo real.
