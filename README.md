# Starbound Game Labs

## Run locally

From this folder, start the site and backend with:

```powershell
python server.py
```

Open `http://127.0.0.1:5000`. The server creates `data/accounts.sqlite3` on first start. Use the sign-up page to create the first account; accounts can then sign in from the home page.

The backend uses Python's standard library and SQLite, so no package installation is needed. Set `PORT` to use another port or `DATABASE_PATH` to store the database elsewhere.

For production, run behind HTTPS and set `COOKIE_SECURE=1`. The built-in HTTP server is intended for local development, not direct internet exposure.