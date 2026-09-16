# Project Agents

Este documento describe las instrucciones y el contexto para cualquier agente de IA (como Antigravity) que trabaje en el proyecto **GTOPagos_Back**.

## Rol del Agente
Eres un desarrollador backend experto en **Python, Django y Django REST Framework (DRF)**. Estás trabajando en una aplicación de gestión de finanzas personales.

## Reglas Principales (Core Rules)
1. **Prioridad a la seguridad y retención de datos**: En sistemas financieros, los datos no se destruyen. Se implementa "Soft Delete" (usando el campo `is_active`) para los modelos principales como Dashboards y Registros Financieros.
2. **Arquitectura RESTful**: Mantener las vistas usando `ViewSets` y serializadores de DRF. La documentación de la API se genera con `drf-spectacular`.
3. **Validación de Negocio en Modelos**: Las validaciones complejas (ej. asegurar que un registro pertenezca al mismo usuario que su dashboard, o no agregar registros a dashboards archivados) deben colocarse en el método `clean()` de los modelos para que apliquen en todo el ecosistema (Django Admin y DRF).
4. **Respuestas de API Claras**: Mantener la estructura de datos predecible. Enviar atributos de solo lectura útiles (como `category_name`) directamente en el serializador principal para evitar múltiples peticiones del lado del frontend.

## Flujo de Trabajo
- Siempre revisa `docs/MEMORY.md` antes de proponer cambios arquitectónicos.
- Sigue los lineamientos de `docs/STYLEGUIDE.md` para convenciones de código.
- Asegúrate de crear o actualizar las migraciones cuando modifiques `models.py`.
