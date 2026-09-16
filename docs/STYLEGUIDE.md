# Styleguide

## Estándares de Código Backend

1. **Convenciones Generales**
   - Sigue PEP 8 para el formato del código Python.
   - Nombres de clases: `PascalCase` (ej. `FinancialRecord`).
   - Funciones, métodos y variables: `snake_case`.
   - Nomenclatura de URLs en DRF: usar `router.register` y dejar que el framework maneje las rutas pluralizadas (ej. `/api/finance/records/`).

2. **Modelos de Django**
   - Definir `__str__` explícitamente en todos los modelos para legibilidad en consola/admin.
   - Validaciones de consistencia de datos deben sobreescribirse en el método `clean()` del modelo (no solo en el serializador).
   - Usa `related_name` descriptivo al declarar `ForeignKey`.

3. **Serializadores**
   - Separar campos de relaciones (`PrimaryKeyRelatedField`) con sufijo `_id` para dejar claro que se espera un ID, y no un objeto anidado en métodos de escritura.
   - Proveer datos enriquecidos (planos) donde sea necesario para simplificar el Frontend (ej. incluir `category_name` en vez de forzar al front a hacer un cruce de IDs).

4. **Consultas a Base de Datos (ORM)**
   - **Regla de Oro:** Si vas a acceder a propiedades de una llave foránea en un loop o un serializador, **debes** usar `select_related()` o `prefetch_related()`.
   - Nunca iterar colecciones grandes en Python si se puede usar `annotate` o `aggregate`.
