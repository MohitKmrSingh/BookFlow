# BookFlow frontend

React + TypeScript + Vite frontend for BookFlow.

## Run locally

```bash
cd frontend
npm install
# Optional: set VITE_API_URL in a .env file. Default is http://127.0.0.1:8000
npm run dev
```

Open http://localhost:5173. The API must be running and its CORS origins must include the frontend origin.

## Routes

- `/login` — owner sign in and registration
- `/dashboard` — owner overview, daily appointments, service and team management
- `/book/:slug` — public customer booking page

The browser stores the JWT in localStorage for this first-party MVP. For a higher-security deployment, move authentication to secure, HttpOnly, SameSite cookies with CSRF protection.
