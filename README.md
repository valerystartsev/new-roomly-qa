# Roomly

Roomly is a client-server meeting room booking application in development. It uses a FastAPI backend and PostgreSQL, with a browser interface for account management.

The current implementation provides local user accounts, administrator and user roles, password management, and initial office, room, and equipment data. The database also contains a preliminary booking and equipment repair schema. **Booking, availability, equipment repair, and office administration are not yet implemented in the API or application interface.**

The original static booking form and its QA tests are retained as a separate legacy exercise; they do not create or persist bookings in the application.

## Requirements

- Docker and Docker Compose v2 for the application and PostgreSQL.
- Python 3.14 and Playwright with Chromium for local browser tests.

## Run locally

1. Create a local configuration file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and replace the example PostgreSQL password, initial administrator email, and initial administrator password. Use a URL-safe database password and an administrator password of at least 12 characters. Do not commit `.env`.

3. Start the application:

   ```bash
   docker compose -f compose.app.yaml --env-file .env up --build -d --wait
   ```

4. Open [account management](http://localhost:8001/account/) and sign in with the initial administrator credentials. The [OpenAPI interface](http://localhost:8001/docs) describes the implemented endpoints.

On startup, the application applies database migrations and initializes missing reference data. The initial administrator is created only when no administrator exists; changing the initial credentials later does not reset an existing account. PostgreSQL data persists in a Docker volume. Each Compose project uses its own volume; changing its name creates a separate database.

To stop the application while keeping its data:

```bash
docker compose -f compose.app.yaml --env-file .env stop
```

The local configuration uses HTTP and disables secure cookies. HTTPS, `COOKIE_SECURE=true`, and a shared login rate limiter are required before production deployment; the current rate limiter is process-local.

## Tests

The application integration tests modify their database. Run them against a separate test database, never against production or a database containing data you need to keep. Create `.env.test` from `.env.example`, set separate test credentials, and add `APP_PORT=8002` to avoid a port conflict with the local application:

```bash
cp .env.example .env.test
# Edit .env.test before starting the test environment.
docker compose -p roomly-test -f compose.app.yaml --env-file .env.test up --build -d --wait
docker compose -p roomly-test -f compose.app.yaml --env-file .env.test exec app python -m pytest -q app_tests
```

The account browser tests require a running test application, the existing Playwright dependencies, and Chromium. Export `APP_URL`, `INITIAL_ADMIN_EMAIL`, and `INITIAL_ADMIN_PASSWORD` matching the test environment, then run:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m pytest -q browser_tests -o addopts=
```

For example, set `APP_URL=http://localhost:8002` when using the test environment above. Do not put real passwords in shell history or committed files.

GitHub Actions runs the application integration and browser tests. The original static-form Python suite is not run in CI; to run it locally:

```bash
docker compose run --build --rm tests
```

## Project structure

- `app/` — API, database models, seed data, and account interface.
- `migrations/` — Alembic database migrations.
- `app_tests/` and `browser_tests/` — application integration and browser tests.
- `compose.app.yaml` and `Dockerfile.app` — local application environment.
- `index.html`, `script.js`, `styles.css`, and `tests/` — original static form and its QA suites.
- `docs/` — specification and technical documentation.

## Documentation

- [Specification and implementation checklist](docs/room-booking-specification.md) (Russian)
- [Database structure](docs/database.md) (Russian)
- [API documentation](docs/api.md) (Russian)
- [Application test catalog](docs/application-tests.md)
- [GitHub Flow](docs/github-flow.md)
