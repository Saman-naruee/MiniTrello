# MiniTrello - Collaborative Task Management System

An educational project demonstrating Django-based task management system implementation with modern web technologies.

## Features

### Core Features
- 🧑💻 User authentication (Session-based)
- 📋 Board management with color customization
- 📌 List and card management (CRUD operations)
- 📧 Email invitations with Celery background processing
- 🌐 Multi-language support (i18n)
- ⚙️ Usage limitations:
  - Max boards per user
  - Max members per board
  - Max memberships per user

### Technical Stack
- **Backend**: Django 5.x
- **Frontend**: Django Templates + Bootstrap 5 + HTMX + Alpine.js
- **Task Queue**: Celery + Redis/RabbitMQ
- **Email**: django-anymail
- **Configuration**: django-environ
- **Deployment**: Docker + Render

## Installation

### Prerequisites
- Python 3.10+
- Redis (for Celery)
- PostgreSQL (recommended for production)

```bash
# Install dependencies
pip install --upgrade pip setuptools wheel
pip install pip-tools
pip install -r requirements.txt
pip-compile requirements.in
pip-sync

# Set up environment
cp .env.example .env  # Update with your values

# Database setup
python manage.py migrate
python manage.py createsuperuser



Development

Running Locally


python manage.py runserver
celery -A MiniTrello worker --loglevel=info


Key Development Patterns

 • Business logic in services.py
 • Celery tasks in tasks.py
 • HTMX partial templates in partials/ directory
 • Alpine.js components in static/js/components/

Adding Translations


django-admin makemessages -l es  # Example for Spanish
django-admin compilemessages



Deployment

Docker Setup


# Use official Dockerfile template from project
docker-compose up --build


GitLab CI/CD

Pipeline configurations included for:

 • Automated testing
 • Container registry
 • Deployment to Render environments (dev/stage/prod)


Project Structure


MiniTrello/
├── accounts/
├── boards/
├── cards/
├── lists/
├── invitations/
└── config/
    ├── base.py
    ├── dev.py
    ├── staging.py
    └── prod.py


Contributing

Follow the project's core philosophy:

 • 🛠 Use existing solutions where possible 
 
 • 📚 Keep code clean and maintainable
 • 🧪 Add tests for critical paths 
 • 📝 Document architectural decisions


License

Educational Use License - Free for learning purposes
