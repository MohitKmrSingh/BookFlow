# BookFlow

BookFlow is a multi-tenant appointment-booking platform for salons, barbershops and other appointment-based small businesses.

Customers can browse a business's public booking page, choose a service, staff member and available time, then book. Owners can manage appointments, services, team members and weekly working hours from the dashboard.

## Current scope

### Included
- Owner registration, login and JWT authentication
- Business-specific tenant scoping
- Service creation, editing, activation and deactivation
- Staff creation, activation and deactivation
- Weekly working-hours management
- Public customer booking page at `/book/{business-slug}`
- Availability calculation using service duration and working hours
- Booking, cancellation, rescheduling and status management APIs
- Past-slot validation and staff-row locking during booking
- Email notifications when SMTP is configured; notification log fallback otherwise
- React owner dashboard and customer booking flow
- Docker Compose deployment baseline
- Backend unit tests and GitHub Actions CI

### Not included in this v1
Online payments, WhatsApp messages, AI features, multiple branches, analytics, customer self-service cancellation/rescheduling, and staff login accounts.

## Technology

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- Authentication: JWT access tokens, bcrypt password hashes
- Frontend: React 18, TypeScript, Vite, React Router
- Deployment: Docker, Docker Compose, Nginx
- Tests: pytest

## Project structure

```text
BookFlow/
├── backend/
│   ├── app/
│   │   ├── core/             settings, JWT, dependencies
│   │   ├── database/         SQLAlchemy engine and models
│   │   ├── routers/          API endpoints
│   │   ├── schemas/          Pydantic request/response models
│   │   └── services/         booking and notification logic
│   ├── alembic/              database migrations
│   ├── tests/                backend tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/                  React app, API client and styles
│   ├── Dockerfile
│   └── README.md
├── .github/workflows/ci.yml
├── docker-compose.yml
├── .env.docker.example
└── README.md
```

## Run locally

### 1. Start PostgreSQL

Create a PostgreSQL database named `bookflow`.

### 2. Configure the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env` with your PostgreSQL URL and a unique random `SECRET_KEY`. Do not commit `.env`.

### 3. Run migrations and API

From the `backend` directory:

```powershell
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

### 4. Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The frontend defaults to `http://127.0.0.1:8000` for the API. To change it, create `frontend/.env` with:

```env
VITE_API_URL=http://127.0.0.1:8000
```

The backend CORS configuration must include the frontend origin, for example `http://localhost:5173`.

## Run tests

From `backend/` with the backend dependencies installed:

```powershell
pytest -q
```

The included tests cover booking time arithmetic, overlap rules, working-hour boundaries, closed days and schema validation. A production release should additionally run end-to-end tests against a disposable PostgreSQL database.

## Docker Compose

From the project root:

```powershell
copy .env.docker.example .env
```

Edit `.env` and set strong, unique values for `POSTGRES_PASSWORD` and `SECRET_KEY`. Then run:

```powershell
docker compose up --build
```

- Frontend: http://localhost:8080
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Docker Compose starts PostgreSQL, runs Alembic migrations before the API starts, and serves the built React app through Nginx. Configure SMTP variables in `.env` to send booking emails. Without SMTP, BookFlow records notifications in the database and logs them.

For a public production deployment, put the services behind HTTPS using a managed TLS reverse proxy or hosting platform, restrict database network access, configure real SMTP credentials, backups, monitoring and domain-specific CORS origins. Do not expose the PostgreSQL port publicly.

## API routes

| Method | Path | Access |
|---|---|---|
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| GET | `/api/auth/me` | Authenticated |
| GET/POST | `/api/services` | Authenticated |
| PATCH/DELETE | `/api/services/{id}` | Owner |
| GET/POST | `/api/staff` | Authenticated / Owner |
| PATCH | `/api/staff/{id}` | Owner |
| PUT | `/api/staff/{id}/working-hours` | Owner |
| GET | `/api/availability` | Authenticated |
| GET/POST | `/api/appointments` | Authenticated |
| POST | `/api/appointments/{id}/cancel` | Authenticated |
| POST | `/api/appointments/{id}/reschedule` | Authenticated |
| PATCH | `/api/appointments/{id}/status` | Owner |
| GET | `/api/public/{slug}` | Public business profile |\n| GET | `/api/public/{slug}/services` | Public |
| GET | `/api/public/{slug}/staff` | Public |
| GET | `/api/public/{slug}/availability` | Public |
| POST | `/api/public/{slug}/appointments` | Public |

Login in Swagger uses the email as `username` because the endpoint uses OAuth2 password form fields.

## Security and release notes

- Owner queries are scoped by `business_id`.
- The production app rejects the default/short JWT secret and wildcard CORS.
- JWTs are stored in browser `localStorage` in this MVP. For a higher-security public deployment, migrate to secure HttpOnly SameSite cookies with CSRF protection.
- Configure HTTPS, SMTP, backups, monitoring and rate limiting before opening registration to the public.
- Booking row locks reduce concurrent double-booking races on PostgreSQL. Verify this behavior with concurrent integration tests before a high-volume launch.
- Do not place real `.env` files, credentials, database dumps or `node_modules` in source archives.
