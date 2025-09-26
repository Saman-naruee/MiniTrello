# MiniTrello

A Trello-inspired project management and collaboration tool built with Django and HTMX. It features real-time updates (soon), role-based permissions, and a modern, responsive interface.

[![CI/CD](https://github.com/Saman-naruee/MiniTrello/workflows/ci.yml/badge.svg)](https://github.com/Saman-naruee/MiniTrello/actions)
<!-- [![Test Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](https://github.com/Saman-naruee/MiniTrello) -->
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![MiniTrello Board View](./documents/board_main_detail_page.png)

## Key Features

- Board, List, and Card Management (CRUD operations)
- Drag & Drop functionality for moving cards between lists
- Role-Based Access Control (Owner, Admin, Member, Viewer)
- Email-based Invitation System for adding new members
- Flexible User Authentication (Username and Email) powered by `django-allauth`
- Production-Ready Setup with Docker and split settings
- Comprehensive Test Suite (>100 tests)
- CI/CD pipeline with GitHub Actions

## Tech Stack

### Backend
- Python
- Django
- Django REST Framework

### Frontend
- HTML
- CSS
- JavaScript
- HTMX
- Bootstrap

### Database
- PostgreSQL

### Asynchronous Tasks
- Celery
- Redis

### Testing
- Django's `unittest`
- `factory-boy` (soon)

### Deployment
- Docker
- Docker Compose
- Gunicorn

## Getting Started

### Method 1: Docker (Recommended)

#### Prerequisites
- Docker
- Docker Compose

#### Installation Steps
1. Clone the repository:
   ```
   git clone https://github.com/Saman-naruee/MiniTrello.git
   ```
2. Navigate to the project directory:
   ```
   cd MiniTrello
   ```
3. Copy the environment file and edit it with your secrets:
   ```
   cp .env.example .env
   ```
   **Note:** You MUST edit `.env` with your actual values before proceeding.
4. Build and start the services in the background:
   ```
   docker-compose up --build -d
   ```
5. Run database migrations:
   ```
   docker-compose exec backend python manage.py migrate
   ```
6. Create a superuser:
   ```
   docker-compose exec backend python manage.py createsuperuser
   ```
7. The application is now running at `http://localhost:8000`.

### Method 2: Local Development (Without Docker)

#### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis

#### Installation Steps
1. Clone the repository:
   ```
   git clone https://github.com/Saman-naruee/MiniTrello.git
   ```
2. Navigate to the project directory:
   ```
   cd MiniTrello
   ```
3. Create a virtual environment:
   ```
   python -m venv env
   ```
4. Activate the virtual environment:
   - On Unix/macOS:
     ```
     source env/bin/activate
     ```
   - On Windows:
     ```
     .\env\Scripts\activate
     ```
5. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
6. Copy the environment file and edit it with your secrets:
   ```
   cp .env.example .env
   ```
   **Note:** You MUST edit `.env` with your actual values before proceeding. Also, ensure your local PostgreSQL and Redis servers are running.
7. Run database migrations:
   ```
   python manage.py makemigrations
   ```
   
   ```
   python manage.py migrate
   ```
8. Create a superuser:
   ```
   python manage.py createsuperuser
   ```
9. Start the development server (in one terminal):
   ```
   python manage.py runserver
   ```
10. Start the Celery worker (in a second terminal):
    ```
    celery -A MiniTrello worker -l info
    ```

## Environment Variables

The `.env` file contains configuration variables. Copy `.env.example` to `.env` and fill in the values. **DO NOT commit this file with real values for sensitive variables like `SECRET_KEY` and `GOOGLE_CLIENT_SECRET`.**

| Variable              | Description                                                                 | Example                          |
|-----------------------|-----------------------------------------------------------------------------|----------------------------------|
| `SECRET_KEY`          | Django's secret key for cryptographic signing. Generate a secure one.       | `django-insecure-...`            |
| `DEBUG`               | Set to `True` for development, `False` for production.                      | `True`                           |
| `ALLOWED_HOSTS`       | Hosts/domains allowed to serve the app. Comma-separated.                    | `localhost,127.0.0.1,.example.com` |
| `DATABASE_URL`        | PostgreSQL database connection URL.                                         | `postgresql://user:pass@localhost/dbname` |
| `CELERY_BROKER_URL`   | Redis URL for Celery task broker.                                           | `redis://localhost:6379/0`       |
| `GOOGLE_CLIENT_ID`    | Google OAuth client ID for social authentication.                           | `your-google-client-id.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET`| Google OAuth client secret. **DO NOT commit real values.**                  | `your-google-client-secret`      |

## Setting up Google OAuth

To enable Google social authentication using django-allauth, follow these steps:

### Prerequisites
- A Google account.
- Access to the [Google Cloud Console](https://console.cloud.google.com/).

### Steps
1. **Create a Google Cloud Project**:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Click on the project dropdown at the top and select "New Project" or choose an existing one.

2. **Enable the Google+ API** (if not already enabled):
   - Navigate to "APIs & Services" > "Library".
   - Search for "Google+ API" and enable it. (Note: For modern OAuth, you might use Google Identity services, but Google+ API is still used for profile/email scopes in allauth.)

3. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials".
   - Click "Create Credentials" > "OAuth client ID".
   - Select "Web application" as the application type.
   - Add the following under "Authorized JavaScript origins":
     - `http://localhost:8000` (for development)
     - Your production domain (e.g., `https://yourdomain.com`)
   - Add the following under "Authorized redirect URIs":
     - `http://localhost:8000/accounts/google/login/callback/` (for development)
     - Your production callback URL (e.g., `https://yourdomain.com/accounts/google/login/callback/`)
   - Click "Create".

4. **Obtain Client ID and Secret**:
   - Copy the "Client ID" and "Client secret" from the created credentials.
   - Also you can download the informations manually in json formatted file.
   - Add them to your `.env` file:
     ```
     GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
     GOOGLE_CLIENT_SECRET=your-client-secret
     ```

5. **Configure django-allauth** (if needed):
   - The project already includes the necessary allauth configuration in `config/base.py`.
   - Ensure `SOCIALACCOUNT_PROVIDERS` is set for Google scopes (profile and email).

6. **Test the Setup**:
   - Restart your development server.
   - Navigate to the login page (`http://localhost:8000/accounts/login/`).
   - You should see a "Sign in with Google" option.
   - Test the flow to ensure it redirects back correctly.

**Note:** For production, update the origins and URIs to match your deployed domain. Also, verify the app in Google Console if required for sensitive scopes.

## Running Tests

To run the test suite:

- All tests:
  ```
  python manage.py test
  ```

- Tests for a specific app (e.g., boards):
  ```
  python manage.py test apps.boards
  ```

- Tests for a specific file:
  ```
  python manage.py test apps.boards.tests.views.test_card_views
  ```

## Contributing

Contributions are welcome! Please open an issue to discuss your idea, then submit a pull request with your changes. Ensure your code follows PEP 8 and includes tests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

