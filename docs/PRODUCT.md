# Documento de Requerimientos de Producto (PRD) - GTOPagos Backend

## 🎯 Descripción del Producto
**GTOPagos Backend** es el motor central de servicios REST que alimenta la plataforma financiera GTOPagos. Su objetivo es procesar, estructurar, calcular y servir de manera segura, rápida y consistente la información sobre presupuestos, transacciones bancarias, metas de ahorro, compromisos de crédito y reportes analíticos para clientes web y móviles.

---

## 💎 Capacidades y Funcionalidades del Sistema

### 1. Modo Demo Inmediato para Invitados
- Generación bajo demanda y sin fricción de sesiones de demostración (`POST /api/demo-login/`).
- Poblado automático e idempotente de datos enriquecidos (tableros, movimientos reales simulados, compras a meses sin intereses, gastos recurrentes y metas de ahorro).
- Ideal para reclutadores, evaluadores de portafolio y visitas de demostración sin persistencia residual en cuentas reales.

### 2. Gestión de Tableros Multi-presupuesto (`UserFinanceDashboard`)
- Soporte para clasificar presupuestos en tres modalidades operativas: `EXPENSES` (Solo gastos), `INCOME` (Solo ingresos) o `BOTH` (Presupuesto balanceado).
- Aislamiento estricto de balances, movimientos y cálculos financieros por usuario y tablero.

### 3. Registro Transaccional Avanzado (`FinancialRecord`)
- Soporte para gastos (`EXPENSE`), ingresos (`INCOME`) y transferencias (`TRANSFER`).
- Control de modalidad de liquidación: Contado (`DEBIT`) y Crédito (`CREDIT`).
- Rastreo de cuotas y meses sin intereses (MSI): campos `current_installment` y `total_installments`.
- Marcado de pagos recurrentes periódicos (`is_recurrent`).
- Estados de liquidación (`Pagado`, `Pendiente`) y asignación de método de pago.

### 4. Metas Financieras y Fondos de Ahorro (`FinancialGoal`)
- Definición de metas financieras con monto objetivo, monto acumulado y fecha estimada.
- Enlace directo opcional entre transacciones individuales y metas para auditoría de ahorro.

### 5. Motor de Importación y Detección Automática de Categorías
- Carga y previsualización de extractos bancarios en hojas de cálculo Excel (`.xlsx`).
- Detección contextual de categorías mediante matching de palabras clave (`CategoryKeyword`).
- Mapeo masivo y confirmación atómica hacia los tableros seleccionados por el usuario.

### 6. Analítica y Exportación Multi-formato
- Cálculo optimizado en base de datos para balances, tasas de ahorro y distribución de gastos por categoría.
- Descarga de reportes ejecutivos en formato **PDF** y hojas de cálculo **Excel** (`.xlsx`).

### 7. Perfil y Preferencias de Notificaciones
- Configuración de datos personales, teléfono y referencias de ingresos.
- Preferencias granulares de notificaciones: alertas de presupuesto, recordatorios de pago, avisos de metas y reportes periódicos.

---

## 📋 Catálogo de Endpoints de la API REST

### Módulo `users`
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/login/` | Autenticación con email y contraseña, retorna JWT. |
| `POST` | `/api/demo-login/` | Inicio de sesión instantáneo con usuario demo y datos simulados. |
| `POST` | `/api/register/` | Registro de nueva cuenta de usuario. |
| `POST` | `/api/token/refresh/` | Renovación de access token mediante refresh token. |
| `GET` | `/api/token/validate/` | Verificación de validez del token en sesión. |
| `POST` | `/api/logout/` | Cierre de sesión e invalidación de tokens. |
| `GET / PUT` | `/api/profile/` | Lectura y actualización de perfil y preferencias de alerta. |
| `POST` | `/api/change-password/` | Cambio autenticado de contraseña. |
| `POST` | `/api/forgot-password/` | Solicitud de correo de recuperación de contraseña. |
| `POST` | `/api/reset-password/` | Confirmación de nueva contraseña con token temporal. |
| `GET` | `/api/currencies/` | Catálogo de divisas soportadas. |
| `GET` | `/api/income-frequencies/` | Catálogo de frecuencias de ingreso salarial. |

### Módulo `dashboard`
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET / POST` | `/api/dashboards/` | Listado y creación de tableros del usuario. |
| `GET / PUT / DELETE` | `/api/dashboards/<id>/` | Detalle, actualización y borrado lógico de un tablero. |
| `GET` | `/api/dashboard/current/` | Resumen acumulado del tablero activo con balance y KPIs. |
| `GET` | `/api/dashboard/recent-transactions/` | Historial consolidado de movimientos recientes. |
| `GET` | `/api/dashboard/upcoming-due/` | Lista de compromisos financieros próximos a vencer. |
| `GET` | `/api/dashboards/<id>/records/` | Listado paginado de movimientos de un tablero específico. |

### Módulo `finance`
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET / POST` | `/api/financial-records/` | Listado y registro de movimientos de gasto o ingreso. |
| `GET / PUT / DELETE` | `/api/financial-records/<id>/` | Detalle, edición y borrado lógico de un movimiento. |
| `GET / POST` | `/api/finance-categories/` | Gestión de categorías de ingresos y gastos. |
| `GET` | `/api/financial-record-types/` | Catálogo de tipos de movimiento (`INCOME`, `EXPENSE`). |
| `GET / POST` | `/api/goals/` | Listado y creación de metas de ahorro financiero. |
| `GET / PUT / DELETE` | `/api/goals/<id>/` | Detalle, actualización de ahorro y eliminación de metas. |
| `POST` | `/api/transactions/detect-category` | Deducción automática de categoría según descripción. |
| `POST` | `/api/import/preview/` | Carga preliminar y extracción inteligente de archivo Excel. |
| `POST` | `/api/import/confirm/` | Confirmación masiva de importación de movimientos. |
| `GET` | `/api/reports/data/` | Métricas y desglose analítico para reportes periódicos. |
| `GET` | `/api/reports/download/` | Descarga de reportes en documentos PDF o libros Excel. |
| `GET` | `/api/export/` | Exportación completa del estado financiero de un tablero. |

### Módulo `payments`
| Método | Endpoint | Descripción |
| :--- | :--- | :--- |
| `GET` | `/api/payment-methods/` | Catálogo de métodos de pago (Efectivo, Tarjeta, etc.). |
| `GET` | `/api/payment-statuses/` | Catálogo de estados de pago (Pagado, Pendiente). |

---

## 🔒 Requerimientos No Funcionales

- **Seguridad:** Autenticación obligatoria mediante encabezado `Authorization: Bearer <token>` en todas las rutas privadas. Contraseñas protegidas mediante algoritmos de hash PBKDF2 / Argon2.
- **Rendimiento:** Tiempos de respuesta inferiores a $150\text{ ms}$ en consultas agregadas gracias a selectores con agregación directa en base de datos y prevención de N+1.
- **Trazabilidad:** Borrado lógico (Soft Delete) generalizado para prevenir pérdida accidental de registros contables.
- **Portabilidad:** Empaquetado completo en contenedores Docker y configuración de variables mediante `.env.example`.

