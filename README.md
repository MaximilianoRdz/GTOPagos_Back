# GTOPagos Backend (API REST) ⚙️🛡️

API RESTful y motor de procesamiento para el ecosistema financiero **GTOPagos**. Construida sobre **Python 3.13**, **Django 5.0** y **Django REST Framework (DRF)**, respaldada por **PostgreSQL**.

---

## 📌 ¿De qué trata el proyecto?

**GTOPagos Backend** es la capa de servicios encargada de gestionar de forma segura, estructurada y resiliente toda la lógica de negocio financiero de GTOPagos. Proporciona los servicios web consumidos por el cliente web y móvil en Angular/Capacitor.

### Capacidades Principales del Backend

- 🔐 **Autenticación y Seguridad JWT**:
  - Registro, inicio de sesión y validación de tokens Bearer (`SimpleJWT`).
  - Soporte para usuarios estándar y cuentas **Demo/Invitado** con persistencia adecuada.
- 🗂️ **Gestión de Tableros Presupuestales (`Dashboards`)**:
  - Control de espacios financieros independientes (gastos, ingresos o combinados).
  - Cálculo consolidado de KPIs (ingresos devengados, total devengado, gastos pagados y saldo pendiente).
  - Políticas de integridad de datos y *Soft Delete* (`is_active`) para prevenir pérdidas accidentales de historial.
- 💳 **Motor de Registros Financieros y Pagos a Cuotas**:
  - Distinción estricta entre operaciones al contado (`DEBIT`) y a crédito (`CREDIT`).
  - Gestión de parcialidades, fechas de corte, estados de liquidación (`PAID`, `PENDING`) y recurrencias.
- 🎯 **Seguimiento de Metas Financieras (`Goals`)**:
  - Registro de objetivos de ahorro, control de aportaciones y trazabilidad de avance monetario y temporal.
- 📑 **Generación y Exportación de Reportes**:
  - Endpoints analíticos con filtros temporales.
  - Generación de estados de cuenta ejecutivos en **PDF** y hojas de cálculo **Excel** mediante plantillas estructuradas.
- 📖 **Documentación OpenAPI / Swagger**:
  - Esquema interactivo generado automáticamente con `drf-spectacular` (ReDoc y Swagger UI).

---

## 🎯 ¿Por qué se llevó a cabo este proyecto?

El desarrollo de este backend se justificó en la necesidad de tener una infraestructura financiera propia, confiable y con altos estándares de seguridad:

1. **Integridad y Trazabilidad de Datos Críticos**: El manejo de dinero no tolera pérdidas de registros ni inconsistencias. La API garantiza que los datos financieros cuenten con validaciones a nivel de modelo (`clean()`), control de transacciones de base de datos y retención mediante eliminación lógica.
2. **Desacoplamiento y Escalabilidad**: Separar el frontend del backend permite que la misma API alimente la versión web para navegadores, la aplicación móvil compilada en Android/iOS o cualquier futura integración con bancos o pasarelas de pago.
3. **Privacidad y Control de la Información**: A diferencia de servicios comerciales de finanzas en la nube que monetizan la información del usuario o dependen de suscripciones costosas, GTOPagos opera de forma completamente autónoma, bajo infraestructura controlada y sin intermediarios.
4. **Respuesta Rápida y Cálculos del Lado del Servidor**: Realizar agregaciones monetarias complejas, proyecciones presupuestales y conciliación de cuotas de manera optimizada directamente en base de datos PostgreSQL.

---

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.13 (compatible con 3.10+).
- **Framework Web**: Django 5.0.
- **API Framework**: Django REST Framework (DRF) 3.15.
- **Base de Datos**: PostgreSQL (conector `psycopg2-binary`).
- **Autenticación**: `djangorestframework-simplejwt`.
- **Documentación de API**: `drf-spectacular` (OpenAPI 3 / ReDoc).
- **Seguridad y CORS**: `django-cors-headers`.
- **Servidor & Contenedores**: Docker, Docker Compose, Nginx (Proxy inverso).

---

## 🚀 Instalación y Puesta en Marcha Local

### Requisitos Previos
- Python 3.10 o superior (recomendado 3.13)
- PostgreSQL
- Docker & Docker Compose *(opcional)*

### 1. Entorno Virtual y Dependencias

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# En Linux/macOS:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración de Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz de `GTOPagos_Back` tomando como base `.env.example`:

```ini
DEBUG=True
DJANGO_SECRET_KEY=clave-secreta-de-desarrollo

# Base de datos PostgreSQL
DB_NAME=gtopagos
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432

# Orígenes CORS permitidos (Frontend Angular)
CORS_ALLOWED_ORIGINS=["http://localhost:4200", "http://127.0.0.1:4200"]
```

### 3. Migraciones y Superusuario

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Iniciar Servidor de Desarrollo

```bash
python manage.py runserver
```

El servidor estará accesible en `http://localhost:8000/`.

---

## 🐳 Ejecución con Docker

Si prefieres levantar el backend y la base de datos de manera aislada con Docker:

```bash
# Construir y levantar contenedores en segundo plano
docker compose up -d --build

# Ver logs
docker compose logs -f backend
```

---

## 📚 Documentación Interactiva de la API

Con el servidor en ejecución en modo desarrollo (`DEBUG=True`), puedes consultar la documentación viva en:

- **ReDoc UI**: `http://localhost:8000/api/schema/redoc/`
- **OpenAPI Schema (JSON/YAML)**: `http://localhost:8000/api/schema/`
- **Página de Bienvenida (Dev Mode)**: `http://localhost:8000/`

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.
