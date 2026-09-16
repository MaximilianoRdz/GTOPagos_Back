# Guía de Estilo y Convenciones de Código - GTOPagos Backend

Este documento establece las directivas de desarrollo, convenciones arquitectónicas de Python/Django y buenas prácticas para mantener la calidad en el repositorio **GTOPagos_Back**.

---

## 🐍 Convenciones Generales de Python & PEP 8

1. **Nomenclatura**:
   - Clases y Modelos: `PascalCase` (ej. `FinancialRecord`, `CategoryKeyword`).
   - Funciones, métodos, variables y atributos: `snake_case` (ej. `detect_category`, `is_recurrent`).
   - Constantes de configuración o choices: `UPPER_SNAKE_CASE` (ej. `BEHAVIOR_CHOICES`).
2. **Anotación de Tipos (Type Hints)**:
   - Aplica type hints en todas las funciones y métodos dentro de `services/` y `selectors/`:
     ```python
     def get_dashboard_summary(dashboard_id: int, user: User) -> dict:
         ...
     ```
3. **Orden de Importaciones (isort standard)**:
   - Librerías estándar de Python (`os`, `sys`, `decimal`, `datetime`).
   - Framework Django (`django.db`, `django.utils`, `django.shortcuts`).
   - Django REST Framework y extensiones (`rest_framework`, `drf_spectacular`).
   - Aplicaciones y módulos locales del proyecto (`users`, `finance`, `dashboard`).

---

## 🏛️ Directivas de Arquitectura por Capas

### 1. Controladores Delgados (`views.py`)
- Los `ViewSets` y `APIViews` actúan exclusivamente como adaptadores de transporte HTTP:
  - Extraen y autentican la petición.
  - Validan la carga útil con un `Serializer`.
  - Delegan la ejecución a un **Selector** (si es lectura) o a un **Servicio** (si es escritura o cálculo de negocio).
  - Retornan una respuesta estructurada con el código HTTP apropiado.

### 2. Capa de Selectores (`selectors/`)
- Funciones de solo lectura responsables de consultar y transformar colecciones del ORM:
  - Nunca mutan la base de datos (no ejecutan `.save()`, `.create()`, `.update()`, `.delete()`).
  - Utilizan `select_related()` y `prefetch_related()` para evitar el problema de N+1 consultas.
  - Delegan agregaciones masivas al motor de base de datos (`Sum`, `Count`, `Avg`, `Case`, `When`).

### 3. Capa de Servicios (`services/`)
- Encapsulan las reglas de negocio transaccionales:
  - Utilizan el decorador `@transaction.atomic` cuando involucren modificaciones en múltiples tablas o inserciones masivas.
  - Aíslan la manipulación de archivos y librerías de terceros (`openpyxl`, `reportlab`).
  - Lanzan excepciones de negocio o `rest_framework.exceptions.ValidationError` cuando las reglas de dominio no se cumplan.

---

## 🗄️ Modelos y Persistencia

1. **Método `__str__` Obligatorio**:
   - Todos los modelos deben definir una representación en cadena clara para visualización en consola y Django Admin.
2. **Validación de Consistencia en `clean()`**:
   - Las reglas que involucren múltiples campos del modelo deben implementarse en el método `clean()` (ej. validar que la fecha objetivo sea futura o que no se registren gastos en un tablero inactivo).
3. **Políticas de Eliminación**:
   - Prohibido el uso de `on_delete=models.CASCADE` hacia modelos principales si puede ocasionar pérdida accidental de registros contables. Prefiere `PROTECT` o `SET_NULL` combinado con la lógica de borrado lógico (`is_active=False`).

---

## 📜 Documentación de la API (drf-spectacular)

- Todo endpoint debe quedar documentado mediante `@extend_schema`:
  ```python
  @extend_schema(
      summary="Obtener resumen del tablero activo",
      description="Calcula ingresos, total a pagar, pendiente de pago y balance del corte mensual actual.",
      responses={200: DashboardSummarySerializer},
      tags=["Dashboard"]
  )
  def get(self, request, *args, **kwargs):
      ...
  ```

