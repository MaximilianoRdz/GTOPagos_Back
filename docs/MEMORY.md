# Memoria Técnica del Proyecto - GTOPagos Backend

Este documento mantiene un registro del estado mental del proyecto, decisiones de diseño técnico, patrones arquitectónicos y peculiaridades de la base de código.

---

## 💡 Decisiones de Diseño Importantes

### 1. Sistema de Eliminación No Destructiva (Soft Delete)
- **Contexto:** En aplicaciones financieras, la pérdida accidental de datos históricos o fiscales es crítica.
- **Implementación:** Tanto `UserFinanceDashboard` como `FinancialRecord` poseen el campo indexado `is_active=BooleanField(default=True, db_index=True)`.
- **Comportamiento:**
  - Al solicitar la eliminación de un Dashboard, se ejecuta una desactivación en cascada que marca `is_active=False` en todos sus movimientos asociados dentro de una transacción atómica.
  - Los endpoints de consulta (`GET`) y selectores aplican de manera predeterminada el filtro `is_active=True`.
  - La validación en `FinancialRecord.clean()` impide asignar movimientos a tableros inactivos.

### 2. Adopción del Patrón de Servicios y Selectores
- **Contexto:** Prevenir el antipatrón de vistas saturadas ("fat views") o modelos sobrecargados ("fat models").
- **Implementación:**
  - **Selectores (`selectors/`):** Funciones puras encargadas de consultar la base de datos mediante el ORM de Django (`dashboard_selectors.py`, `report_selectors.py`). Centralizan agrupaciones analíticas, sumatorias condicionales (`Sum(Case(When(...))))`) y optimizaciones con `select_related()` / `prefetch_related()`.
  - **Servicios (`services/`):** Módulos que orquestan lógica transaccional de negocio: importación masiva (`import_engine.py`), detección de categorías (`category_detector_service.py`), proyecciones de recurrencia (`recurrence_service.py`) y exportación binaria de documentos PDF/XLSX (`report_export_service.py`).

### 3. Generador Idempotente de Modo Demo (`users/demo_data.py`)
- **Contexto:** Proveer una experiencia inmediata a reclutadores, evaluadores de portafolio y visitantes sin requerir registro manual ni comprometer datos de producción.
- **Implementación:**
  - `DemoLoginView` invoca `get_or_create_demo_user()`.
  - Si el usuario demo existe, se reinician o rellenan sus datos con un conjunto balanceado y coherente: tableros para "Finanzas Personales" y "Negocio", categorías con íconos y colores, movimientos al contado y compras a plazos (MSI), gastos fijos recurrentes y metas de ahorro con progreso tangible.
  - Retorna un par de tokens JWT (`access` y `refresh`) estándar para que el frontend navegue sin fricción.

### 4. Detección Inteligente de Categorías (`CategoryKeyword`)
- **Contexto:** Facilitar la importación masiva desde extractos bancarios en Excel.
- **Implementación:**
  - Las palabras clave se normalizan automáticamente a minúsculas y sin espacios residuales en el método `clean()` del modelo `CategoryKeyword`.
  - El servicio `category_detector_service.py` analiza tokens descriptivos de transacciones contra la tabla de palabras clave asociadas a categorías del usuario o globales, asignando la categoría con mayor correlación.

### 5. Metas Financieras Vinculadas (`FinancialGoal`)
- **Contexto:** Permitir que los usuarios destinen ahorro hacia objetivos tangibles (fondos de emergencia, compras mayores).
- **Implementación:**
  - El modelo `FinancialGoal` registra montos objetivos, acumulados y fechas límite.
  - Los movimientos (`FinancialRecord`) poseen una clave foránea opcional `financial_goal` con política `SET_NULL`, lo que permite asociar abonos a una meta sin peligro de borrado destructivo si la meta se elimina.

---

## ⚠️ Limitaciones Actuales y Deuda Técnica

1. **Automatización de Recurrencias en Segundo Plano:**
   - La proyección de movimientos recurrentes existe a nivel de lógica de servicio, pero requiere la integración de un despachador periódico (Celery Beat con Redis) para materializar automáticamente las transacciones cada mes.
2. **Tokens Demo Concurrentes:**
   - Múltiples evaluadores navegando simultáneamente en Modo Demo comparten el usuario `demo@gtopagos.com`. Para entornos de prueba intensiva, convendrá rotar prefijos temporales de sesión.

---

## 🔮 Roadmap Futuro

- Implementación de tareas asíncronas con Celery & Redis.
- Conexión con proveedores de agregación bancaria abierta (Open Banking / Plaid / Belvo).
- Alertas automatizadas por correo y mensajería instantánea.

