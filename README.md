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
| Name | David Hernandez (GK, admin, webmaster) |
| Password | `Password123!` |

The API creates this member on startup when the row is missing. `backend\seed_member.py` does the same thing and exits with an error if PostgreSQL cannot be reached. If membership id `1000000` already has a different password, the stored password is left as it is.

That same password is used by sample member `1000001` (Sample Brother, no title, not an admin) and by the test roster `1000100` through `1000149`. Starting the API, or running `backend\seed_member.py`, inserts any of those rows that are missing. Each roster member receives a profile photo when that member row is first created. Removing the photo leaves the default in place. A few of those accounts are also admins: `1000100`, `1000103`, `1000114`, `1000124`, `1000131`, and `1000140`. David Hernandez remains the known webmaster. Admins can edit the site. Only a webmaster can open Logs & activity or grant webmaster access.

The same step loads past honors: 20 Knights of the Month, 20 Families of the Month, 20 Knights of the Year, 20 Families of the Year, and 20 Past Grand Knights. `backend\schema.sql` inserts any missing honor rows as well. If PostgreSQL is down, the API keeps this same roster and these same honors in memory. Several birthdays fall in October and November. A roster member or past-honor row that is still missing is inserted again the next time the API starts. Edits to an existing row are left in place, including a cleared photo.

## Authentication

- Passwords are hashed with bcrypt (cost 12). The database stores the hash, not the password.
- Login is `POST /api/auth/login` with JSON `{ "memberid", "password" }`. A wrong id or password both return `401` with the same message.
- A successful login sets two httpOnly cookies: a 15-minute access token and a 7-day refresh token. JavaScript cannot read them. The refresh cookie is only sent to `/api/auth`.
- `POST /api/auth/refresh` rotates the refresh token. Reusing an already rotated token revokes that member's refresh tokens.
- `POST /api/auth/logout` revokes the refresh token and clears both cookies.
- `GET /api/pages/member` and `PUT /api/pages/member` require a valid access token, from the cookie or an `Authorization: Bearer` header.
- The members page redirects to `/login` until `GET /api/auth/me` succeeds. The access cookie is refreshed once when it has expired and the refresh cookie is still valid.
- Cookies use `SameSite=Lax`. They are marked `Secure` only when `COOKIE_SECURE=true`, so local HTTP still works.
