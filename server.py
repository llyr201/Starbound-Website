import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "accounts.sqlite3"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
SESSION_DAYS = 7
PASSWORD_ITERATIONS = 310_000
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
SESSION_COOKIE = "starbound_session"
USER_FIELDS = "id, username, email"
PUBLIC_PAGES = {"index.html", "signup.html"}
MEMBER_PAGES = {
    "home.html",
    "projects.html",
    "about.html",
    "contact.html",
    "game.html",
    "slate_city.html",
}
STATIC_EXTENSIONS = {
    ".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg",
    ".ico", ".woff", ".woff2", ".ttf", ".mp4", ".webm",
}
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def connect_db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def database():
    connection = connect_db()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at);
            """
        )


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def token_digest(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def user_payload(row):
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


class SiteHandler(SimpleHTTPRequestHandler):
    server_version = "StarboundSite/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def log_message(self, format_string, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format_string % args))

    def send_json(self, status, payload, extra_headers=()):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def request_user(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        cookie = cookies.get(SESSION_COOKIE)
        if cookie is None:
            return None
        now = datetime.now(timezone.utc).isoformat()
        with database() as connection:
            row = connection.execute(
                """SELECT users.id, users.username, users.email
                   FROM sessions JOIN users ON users.id = sessions.user_id
                   WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
                (token_digest(cookie.value), now),
            ).fetchone()
        return row

    def session_cookie(self, token, max_age):
        value = f"{SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}"
        if COOKIE_SECURE:
            value += "; Secure"
        return value

    def create_session(self, user_id):
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
        with database() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (datetime.now(timezone.utc).isoformat(),))
            connection.execute(
                "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
                (token_digest(token), user_id, expires.isoformat()),
            )
        return self.session_cookie(token, SESSION_DAYS * 24 * 60 * 60)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path.startswith("/api/"):
            if path == "/api/me":
                user = self.request_user()
                self.send_json(HTTPStatus.OK, {"user": user_payload(user) if user else None})
            else:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return

        user = self.request_user()
        if path == "/":
            self.redirect("/home.html" if user else "/index.html")
            return

        page = path.lstrip("/").lower()
        if page in PUBLIC_PAGES and user:
            self.redirect("/home.html")
            return
        if page in MEMBER_PAGES and not user:
            self.redirect("/index.html")
            return
        if page in PUBLIC_PAGES | MEMBER_PAGES:
            self.path = "/" + page
            super().do_GET()
            return

        relative = Path(path.lstrip("/"))
        candidate = (ROOT / relative).resolve()
        if (
            not relative.parts
            or any(part.startswith(".") for part in relative.parts)
            or not candidate.is_relative_to(ROOT)
            or candidate.suffix.lower() not in STATIC_EXTENSIONS
            or not candidate.is_file()
        ):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path not in {"/api/signup", "/api/login", "/api/logout"}:
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc.lower() != self.headers.get("Host", "").lower():
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "Request origin was not accepted."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 16_384:
                raise ValueError
            payload = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(payload, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid request."})
            return

        if path == "/api/signup":
            self.signup(payload)
        elif path == "/api/login":
            self.login(payload)
        else:
            self.logout()

    def signup(self, payload):
        username = payload.get("username", "")
        email = payload.get("email", "")
        password = payload.get("password", "")
        if not all(isinstance(value, str) for value in (username, email, password)):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Enter valid account details."})
            return
        username = username.strip()
        email = email.strip().lower()
        if not USERNAME_PATTERN.fullmatch(username):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Username must be 3-50 characters using letters, numbers, dots, underscores, or hyphens."})
            return
        if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Enter a valid email address."})
            return
        if len(password) < 12 or len(password) > 1024:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Password must be between 12 and 1024 characters."})
            return

        try:
            with database() as connection:
                cursor = connection.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, hash_password(password)),
                )
                user_id = cursor.lastrowid
                user = connection.execute(
                    f"SELECT {USER_FIELDS} FROM users WHERE id = ?", (user_id,)
                ).fetchone()
        except sqlite3.IntegrityError:
            self.send_json(HTTPStatus.CONFLICT, {"error": "That username or email is already registered."})
            return
        cookie = self.create_session(user_id)
        self.send_json(HTTPStatus.CREATED, {"user": user_payload(user)}, (("Set-Cookie", cookie),))

    def login(self, payload):
        username = payload.get("username", "")
        password = payload.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Enter your username and password."})
            return
        with database() as connection:
            row = connection.execute(
                "SELECT id, username, email, password_hash FROM users WHERE username = ? COLLATE NOCASE",
                (username.strip(),),
            ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "Incorrect username or password."})
            return
        cookie = self.create_session(row["id"])
        self.send_json(HTTPStatus.OK, {"user": user_payload(row)}, (("Set-Cookie", cookie),))

    def logout(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        cookie = cookies.get(SESSION_COOKIE)
        if cookie is not None:
            with database() as connection:
                connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest(cookie.value),))
        expired = self.session_cookie("", 0) + "; Expires=Thu, 01 Jan 1970 00:00:00 GMT"
        self.send_json(HTTPStatus.OK, {"ok": True}, (("Set-Cookie", expired),))

    def do_HEAD(self):
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)


def main():
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), SiteHandler)
    print(f"Starbound Game Labs running at http://{HOST}:{PORT}")
    print(f"SQLite database: {DATABASE_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()