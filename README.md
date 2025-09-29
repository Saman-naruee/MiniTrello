# MiniTrello

A Trello-inspired project management and collaboration tool built with Django and HTMX. It features real-time updates (soon), role-based permissions, and a modern, responsive interface.

[![Django CI/CD](https://github.com/Saman-naruee/MiniTrello/actions/workflows/ci.yml/badge.svg)](https://github.com/Saman-naruee/MiniTrello/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- Add a compelling screenshot of the main board view here -->
![MiniTrello Board View](./docs/board_main_detail_page.png)

## Key Features

- **Board, List, and Card Management:** Full CRUD operations for organizing your projects.
- **Drag & Drop:** Intuitively move cards between lists to update their status.
- **Role-Based Access Control:** Granular permissions with Owner, Admin, Member, and Viewer roles.
- **Email Invitation System:** Securely invite new members to collaborate on boards.
- **Flexible User Authentication:** Sign up and log in with either a username or an email, powered by `django-allauth`.
- **Production-Ready Setup:** A professional structure with Docker, split settings, and environment variables.
- **Comprehensive Test Suite:** Over 130 tests ensuring code quality and stability.
- **CI/CD Pipeline:** Automated testing with GitHub Actions for every change.

## Tech Stack

| Category | Technology |
| :--- | :--- |
| **Backend** | Python, Django, Django REST Framework, Gunicorn |
| **Frontend** | HTML, CSS, JavaScript, HTMX, Bootstrap |
| **Database** | PostgreSQL |
| **Async Tasks** | Celery, Redis |
| **Testing** | Django's `unittest` |
| **Deployment** | Docker, Docker Compose |

## Getting Started

You can set up the project using Docker (recommended for a quick and consistent setup) or by installing dependencies locally.

### Method 1: Docker (Recommended)

#### Prerequisites
- Docker
- Docker Compose

#### Installation Steps
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Saman-naruee/MiniTrello.git
    cd MiniTrello
    ```
2.  **Create and configure the environment file:**
    ```bash
    cp .env.example .env
    ```
    **Important:** You MUST open the `.env` file and fill in your actual secret values, especially for `SECRET_KEY` and the `GOOGLE_...` variables.
3.  **Build and run the services:**
    This command will start all services (backend, database, celery) in the background.
    ```bash
    docker-compose up --build -d
    ```
4.  **Run database migrations:**
    ```bash
    docker-compose exec backend python manage.py migrate
    ```
5.  **Create a superuser:**
    ```bash
    docker-compose exec backend python manage.py createsuperuser
    ```
6.  **Done!** The application is now running at `http://localhost:8000`.

### Method 2: Local Development (Without Docker)

#### Prerequisites
- Python 3.11+
- PostgreSQL Server
- Redis Server

#### Installation Steps
1.  Clone the repository and navigate into the directory.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv env
    source env/bin/activate  # On Windows: .\env\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create and configure the `.env` file from the example. Ensure your local PostgreSQL and Redis servers are running and the credentials in `.env` match.
5.  Apply database migrations and create a superuser:
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```
6.  Run the development server, Celery worker, and Celery Beat in **three separate terminals**:
    ```bash
    # Terminal 1: Django Server
    python manage.py runserver

    # Terminal 2: Celery Worker
    celery -A MiniTrello worker -l info

    # Terminal 3: Celery Beat (for scheduled tasks)
    celery -A MiniTrello beat -l info
    ```

## Environment Variables

The `.env` file is crucial for configuring the application. It must be created from `.env.example`.

| Variable | Description | Example (for Docker) |
| :--- | :--- | :--- |
| `DJANGO_SETTINGS_MODULE` | Sets the settings file. Use `config.development` or `config.production`. | `config.development` |
| `SECRET_KEY` | Django's secret key. **Generate a new one for production.** | `a-very-long-and-random-secret-string`|
| `DEBUG` | Django's debug mode. `True` for dev, **`False` for production.** | `True` |
| `PREFERRED_DB` | Preferred database engine. Options: 'sqlite' (dev, file-based) or 'postgresql' (prod, requires DB vars). Defaults to 'sqlite' if unset. | `postgresql` |
| `DB_NAME` | Name of the PostgreSQL database. | `minitrello` |
| `DB_USER` | Username for the PostgreSQL database. | `postgres` |
| `DB_PASSWORD` | Password for the PostgreSQL database. | `postgres` |
| `DB_HOST` | Hostname of the database server. For Docker, this is the service name. | `db` |
| `DB_PORT` | Port for the PostgreSQL database. | `5432` |
| `CELERY_BROKER_URL` | Redis URL for Celery. For Docker, use the service name. | `redis://redis:6379/0` |
| `GOOGLE_OAUTH_...` | See detailed setup guide below for these variables. | (values from Google Cloud) |

## Setting Up Google APIs for Authentication & Email

This project uses Google for two distinct features:
1.  **Social Login:** Allowing users to sign up/log in with their Google account (handled by `django-allauth`).
2.  **Sending Real Emails:** Using the Gmail API to send transactional emails like invitations (handled by our custom email backend).

Both features use the same **OAuth 2.0 Client ID**. Follow these steps carefully.

### Step 1: Configure the Google Cloud Project
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2.  Navigate to **"APIs & Services" -> "Library"**.
3.  Search for and **enable** the **"Gmail API"**.

### Step 2: Configure the OAuth Consent Screen
1.  In **"APIs & Services"**, go to the **"OAuth consent screen"**.
2.  Choose **"External"** for User Type and click "Create".
3.  Fill in the required app information (App name, User support email, Developer contact). Click "Save and Continue".
4.  On the **Scopes** screen, click "Add or Remove Scopes". Search for `gmail.send` and add the `.../auth/gmail.send` scope. Click "Save and Continue".
5.  On the **Test users** screen, click **"+ Add Users"** and add the Google email address you will use to authorize the application (e.g., your own personal Gmail address). Click "Save and Continue".
6.  Review the summary and go back to the dashboard.

### Step 3: Create Credentials
1.  Go to **"APIs & Services" -> "Credentials"**.
2.  Click **"Create Credentials" -> "OAuth client ID"**.
3.  Select **"Web application"**.
4.  Under **"Authorized redirect URIs"**, add the following two URIs:
    *   `http://localhost:8000/accounts/google/login/callback/` (for Social Login)
    *   `http://localhost:8080` (for the token generation script)
5.  Click **"Create"**. You will now see your **`Client ID`** and **`Client secret`**, Also can download them as a JSON file.

### Step 4: Generate the Refresh Token (One-time step)
To send emails on your behalf without you having to log in every time, the application needs a long-lived `refresh_token`.

1.  **Update your `.env` file** with the credentials from the previous step:
    ```
    GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
    GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
    GOOGLE_OAUTH_SENDER_EMAIL=the-google-email-you-added-as-a-test-user
    ```
2.  **Run the token generation script** from your terminal:
    ```bash
    python get_refresh_token.py
    ```
3.  A browser window will open. **Log in with the same Google account** you added as a test user and grant the requested permissions.(remember to allow all requested scopes)

Note: If you encounter any issues about authorization, ensure that change project status from testing to production:
You can do this in the Google Cloud Console under "APIs & Services" -> "OAuth consent screen"/"Audience" (May differ based on docs version)

4.  Once authorized, switch back to your terminal. A **`refresh_token`** will be printed.

### Step 5: Final Configuration
1.  Copy the generated `refresh_token` and add it to your `.env` file:
    ```
    GOOGLE_OAUTH_REFRESH_TOKEN=1//0g...
    ```
2.  To enable real email sending, set the settings module in your `.env` file to production:
    ```
    DJANGO_SETTINGS_MODULE=config.production
    ```
3.  Restart your application: `docker-compose up --build`. Your application will now send real emails via your Google account.

## Running Tests

-   Run all tests:
    ```bash
    python manage.py test
    ```
-   Run tests for a specific app:
    ```bash
    python manage.py test apps.boards
    ```

## Contributing

Contributions are welcome! Please open an issue to discuss your idea, then submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
