# GTO Payments Backend

Backend for the Guanajuato State Government payment system.

## Requirements

- Python 3.13 (recomendado) o Python 3.10+
- PostgreSQL
- Docker (optional)

## Environment Setup

1. Create virtual environment:
```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:
```bash
# Linux/macOS
python3 -m pip install -r requirements.txt

# Windows
python -m pip install -r requirements.txt
```

3. Configure environment variables:
Create a `.env` file in the project root with the following variables:
```
DEBUG=True
DJANGO_SECRET_KEY=your-secret-key

# Database settings
DB_NAME=gtopagos
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# CORS settings for development
CORS_ALLOWED_ORIGINS=["http://localhost:4200", "http://127.0.0.1:4200"]
```

4. Run migrations:
```bash
# Linux/macOS
python3 manage.py migrate

# Windows
python manage.py migrate
```

5. Create superuser:
```bash
# Linux/macOS
python3 manage.py createsuperuser

# Windows
python manage.py createsuperuser
```

6. Start development server:
```bash
# Linux/macOS
python3 manage.py runserver

# Windows
python manage.py runserver
```

## Development Configuration

### CORS Configuration
For local development, you need to configure the allowed origins for CORS. By default, the backend allows the following URLs:
- `http://localhost:4200` (default Angular port)
- `http://127.0.0.1:4200`

If your frontend runs on a different port, you need to add the URL to the `.env` file:
```
CORS_ALLOWED_ORIGINS=["http://localhost:4200", "http://127.0.0.1:4200", "http://your-frontend:port"]
```

### Development Welcome Page
When running in development mode (`DEBUG=True`), a welcome page is available at the root URL (`/`). This page includes:
- Project version
- Quick links to API documentation and admin panel
- Environment information (Django version, Python version, etc.)
- Development mode warning

This page is only available in development mode and will not be accessible in production.

## API Documentation

The API documentation is available at the following endpoints:

- ReDoc: `http://localhost:8000/api/schema/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

### Authentication

The API uses JWT (JSON Web Tokens) for authentication. To access protected endpoints:

1. Register a new user at `/api/register/`
2. Login at `/api/login/` to get your access token
3. Include the token in your requests using the `Authorization` header:
   ```
   Authorization: Bearer <your_access_token>
   ```

### Available Endpoints

#### Users
- `POST /api/register/` - Register a new user
- `POST /api/login/` - Login and get access token
- `POST /api/token/validate/` - Validate JWT token

#### Currencies
- `GET /api/currencies/` - List all available currencies

## Project Structure

- `gtopagos/` - Main project configuration
- `apps/` - Project applications
- `media/` - Media files
- `staticfiles/` - Static files

## Technologies Used

- Django 5.0.2
- Django REST Framework 3.15.0
- PostgreSQL
- Python 3.13
- django-cors-headers 4.3.1
- Pillow 10.2.0
- drf-spectacular 0.27.1 (API Documentation)
- psycopg2-binary 2.9.10