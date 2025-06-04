# GTO Payments Backend

Backend for the Guanajuato State Government payment system.

## Requirements

- Python 3.10+
- PostgreSQL
- Docker (optional)

## Environment Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
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
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create superuser:
```bash
python manage.py createsuperuser
```

6. Start development server:
```bash
python manage.py runserver
```

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
- Python 3.10+
- django-cors-headers 4.3.1
- Pillow 10.2.0
- drf-spectacular 0.27.1 (API Documentation)