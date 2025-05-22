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