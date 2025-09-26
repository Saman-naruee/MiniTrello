# Copilot Instructions for MiniTrello

## Project Overview
MiniTrello is an educational Django 5.x project implementing a Trello-like collaborative task management system. Key components:
- **Authentication & Users**: Custom `User` model in `apps/accounts/models.py` extending Django's AbstractUser. Supports email-based login, social auth (Google via allauth), and profile management.
- **Core Domain (Boards App)**: Models in `apps/boards/models.py` - `Board` (owned by user, color-themed), `List` (columns in board), `Card` (tasks with due dates, assignees), `Membership` (board access: owner/member). Data flow: User → Board → Memberships → Lists → Cards.
- **Invitations**: `apps/invitations/models.py` for invite tracking (pending/accepted/rejected). Async email sending via Celery tasks.
- **Other Apps**: `playground` for testing views/URLs; potential future apps like lists/cards if split.
- **Settings**: Split configuration in `config/` - `base.py` (shared: INSTALLED_APPS includes 'apps.*', middleware with HTMX/allauth/CORS; AUTH_USER_MODEL='accounts.User'; limits like MAX_BOARDS_PER_USER=10). Override in `development.py`/`production.py`.
- **Frontend**: Server-rendered Django templates extending `templates/base.html` (Bootstrap 5 layout, Font Awesome icons). Use HTMX for dynamic updates (e.g., `hx-get` for modals/forms), Alpine.js for client-side state (e.g., `x-data` for toggles). No JavaScript frameworks like React.
- **Backend Patterns**: Session authentication primary (`LOGIN_REDIRECT_URL='/'`). Optional DRF API at `/api/` with JWT if `USE_DRF_TOKEN_AUTH=True`. Permissions via `@login_required` and custom checks in `apps/boards/permissions.py` (e.g., `is_owner_or_member` using Q queries).
- **Async & External**: Celery + Redis for background tasks (e.g., email invites in `tasks.py`). Email via django-anymail. DB: SQLite dev, PostgreSQL prod. i18n enabled with `{% trans %}` in templates.

Architecture rationale: Modular apps for domains; settings split for env-specific configs; HTMX/Alpine for progressive enhancement without full SPA complexity.

## Key Conventions & Patterns
- **App Structure**: Apps under `apps/` (e.g., `apps/boards/`). Each has `models.py` (with docstrings for fields), `views.py` (mix CBVs/FBVs with `transaction.atomic` for DB ops), `urls.py` (namespaced, e.g., namespace="boards"), `forms.py` (ModelForms with validation), `admin.py` (nested inlines for Board→List→Card), `templatetags/` (custom filters like `board_extras`), `static/` (app-specific CSS/JS), `templates/<app>/` (partials in `partials/` for HTMX swaps).
- **Business Logic**: Encapsulate in `services.py` per app (e.g., `board_services.create_board(user, title)` enforcing limits via settings). Use `custom_tools.logger.custom_logger` for dev logging with colorama.
- **Permissions & Limits**: Always check ownership/membership before CRUD (e.g., `get_user_board` raises 404 if unauthorized). Enforce config limits (e.g., `Board.objects.filter(owner=user).count() < MAX_BOARDS_PER_USER` before create).
- **Templates**: Blocks for `title`, `content`, `extra_head` (load HTMX/Alpine CDN), `nav_*_active`. Forms use Alpine for validation/submit (fetch POST with FormData, handle errors/redirects). HTMX targets: `#id` for swaps, `hx-trigger="load"` for init.
- **i18n**: `LANGUAGE_CODE='en-us'`, add langs via `makemessages -l <lang>` / `compilemessages`. Use `set_language` view for switching.
- **Static/Media**: Collect to `staticfiles/` for prod. App-specific in `static/<app>/`.
- **Tests**: In `tests/` subdirs (e.g., `boards/tests/views/test_views.py`). Use `TestCase`, `Client`; cover permissions, limits, async (mock Celery). Base classes like `BaseBoardTestCase` for fixtures.
- **Code Style**: PEP8, docstrings for models/views. Avoid raw SQL; use ORM with `select_related`/`prefetch_related` for perf (e.g., board detail queries).

Differing from standard: Apps prefixed 'apps.' in INSTALLED_APPS/apps.py; no separate lists/cards apps (in boards); preference for templates over API unless specified (`PREFFERED_IMPLEMENTATION_FOR_PROJECT_API_OR_WEBPAGES='WEB'`).

## Developer Workflows
- **Setup**: 
  1. `pip install pip-tools; pip-compile requirements.in; pip-sync`.
  2. Copy `.env.example` to `.env` (SECRET_KEY, DB creds, GOOGLE_CLIENT_ID, etc.).
  3. `python manage.py migrate; python manage.py createsuperuser`.
- **Run Dev Server**: `python manage.py runserver 0.0.0.0:8000`. For full: Start Celery worker `celery -A MiniTrello worker --loglevel=info` (Redis required). Use VS Code task "docker-run: debug" for containerized (depends on "docker-build", runs `manage.py runserver --nothreading --noreload`).
- **Build/Deploy**: `docker-compose up --build` (uses `compose.yaml`, Gunicorn in prod). CI/CD via GitLab (testing, build, deploy to Render dev/stage/prod). Set `DJANGO_SETTINGS_MODULE=config.development` for dev.
- **Testing/Debug**: `python manage.py test apps.boards` (or all). Debug with `pdb` in views; check limits/permissions in tests. For errors: Use `get_errors` tool or admin nested views.
- **Adding Features**: For new app (e.g., ai_tools): `python manage.py startapp ai_tools` in `apps/`; set `name='apps.ai_tools'` in `apps.py`; add to INSTALLED_APPS; create models/views. Update URLs in `MiniTrello/urls.py`. For i18n: Add translations, run makemessages.
- **Maintenance**: Enforce limits in services; use `render_partial_response` for HTMX JSON+HTML. Monitor Celery with Flower if needed.

## Integration Points
- **Auth Flow**: Allauth handles signup/login/social (`/accounts/` URLs). Custom views in `apps/accounts/views.py` (e.g., profile update). Adapter `CustomAccountAdapter` for email confirmation.
- **API**: DRF serializers/views if needed (e.g., profile API if `IS_USE_API_FOR_PROFILE=True`). Endpoints under `/api/auth/` (dj-rest-auth).
- **Celery Tasks**: Define in `apps/<app>/tasks.py` (e.g., `send_invite_email.delay(invite_id)`). Broker: Redis (`CELERY_BROKER_URL` in .env).
- **Email**: Configure `EMAIL_BACKEND`/`ANYMAIL` in settings; templates in `templates/account/email/`.
- **Cross-App Comm**: Signals in `apps/accounts/signals.py` (e.g., post-save user). Prefetch in views (e.g., `Board.objects.prefetch_related('memberships__user', 'lists__cards')`).
- **External Deps**: Bootstrap/HTMX/Alpine via CDN in `base.html`; SortableJS for drag-drop in board detail. Google OAuth: Set env vars.

Reference key files: `README.md` (setup/features), `PROJECT_PROMPT.md` (philosophy/guidelines), `apps/boards/permissions.py` (access patterns), `config/base.py` (configs/limits).


## Third-Party Docs
django allauth: https://docs.allauth.org/en/latest/


## Important:!!!
Always Provide existing Tools and Patterns and avoid reinventing the wheel.
Always use the provided utilities and patterns for consistency and maintainability.
Always In first line of each file in chat mention file full path in comment.
