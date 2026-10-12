# Council 10930

Public site and members area for Knights of Columbus Council 10930. The members area requires a membership ID and password.

## Run locally

PostgreSQL must be running. The default connection is `postgresql://postgres:postgres@localhost:5432/koc10930`.

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE koc10930"
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d koc10930 -f backend\schema.sql
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\seed_member.py
.\.venv\Scripts\uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm run dev
```

Open http://localhost:5173 and use Sign in.

Set `DATABASE_URL` if PostgreSQL is not on the default host, user, or password. Set `JWT_SECRET` to a long random string before any shared deployment. Set `COOKIE_SECURE=true` when the site is served over HTTPS.

## Test member

| Field | Value |
| --- | --- |
| Membership ID | `1000000` |
| Password | `Password123!` |

The API creates this member on startup when the row is missing. `backend\seed_member.py` does the same thing and exits with an error if PostgreSQL cannot be reached. If membership id `1000000` already has a different password, the stored password is left as it is.

## Authentication

- Passwords are hashed with bcrypt (cost 12). The database stores the hash, not the password.
- Login is `POST /api/auth/login` with JSON `{ "memberid", "password" }`. A wrong id or password both return `401` with the same message.
- A successful login sets two httpOnly cookies: a 15-minute access token and a 7-day refresh token. JavaScript cannot read them. The refresh cookie is only sent to `/api/auth`.
- `POST /api/auth/refresh` rotates the refresh token. Reusing an already rotated token revokes that member's refresh tokens.
- `POST /api/auth/logout` revokes the refresh token and clears both cookies.
- `GET /api/pages/member` and `PUT /api/pages/member` require a valid access token, from the cookie or an `Authorization: Bearer` header.
- The members page redirects to `/login` until `GET /api/auth/me` succeeds. The access cookie is refreshed once when it has expired and the refresh cookie is still valid.
- Cookies use `SameSite=Lax`. They are marked `Secure` only when `COOKIE_SECURE=true`, so local HTTP still works.
