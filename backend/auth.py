from collections import deque
from contextlib import contextmanager
from functools import lru_cache
from hashlib import pbkdf2_hmac, sha256
from pathlib import Path
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


BASE_DIR = Path(__file__).resolve().parent.parent
COOKIE_NAME = "careerlens_session"
COOKIE_PATH = "/api/auth"
SESSION_SECONDS = 7 * 24 * 60 * 60
PASSWORD_ITERATIONS = 600_000
UNAVAILABLE_MESSAGE = "账号服务暂不可用，请稍后重试；仍可通过访客入口使用平台。"
NO_CACHE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
_hash_slots = threading.BoundedSemaphore(2)


class AuthUnavailable(Exception):
    """只向浏览器返回通用错误，不暴露连接串、数据库路径或密码。"""


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    username: str = Field(min_length=6, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    password: SecretStr = Field(min_length=8, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value):
        if not value.get_secret_value().strip():
            raise ValueError("密码不能全部为空白字符")
        return value


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        count = int(iterations)
        if algorithm != "pbkdf2_sha256" or not 600_000 <= count <= 2_000_000:
            return False
        if len(salt) != 32 or len(expected) != 64:
            return False
        actual = pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), count)
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError, AttributeError):
        return False

_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


class AuthStore:
    def __init__(self, database_url: str = "", sqlite_path: str = ""):
        self.database_url = database_url
        self.sqlite_path = sqlite_path
        self.postgres = bool(database_url)
        self._ready = False
        self._schema_lock = threading.Lock()

    def sql(self, query):
        return query.replace("?", "%s") if self.postgres else query

    @contextmanager
    def connection(self):
        connection = None
        try:
            if self.postgres:
                import psycopg
                from psycopg.rows import dict_row

                connection = psycopg.connect(
                    self.database_url, connect_timeout=5, row_factory=dict_row,
                    options="-c statement_timeout=5000 -c lock_timeout=3000",
                )
            else:
                path = Path(self.sqlite_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                connection = sqlite3.connect(str(path), timeout=5)
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        except Exception:
            raise AuthUnavailable() from None
        finally:
            if connection is not None:
                connection.close()

    def ensure_schema(self):
        if self._ready:
            return
        with self._schema_lock:
            if self._ready:
                return
            with self.connection() as connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS careerlens_users (
                        id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        created_at BIGINT NOT NULL
                    )
                """)
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS careerlens_sessions (
                        token_hash TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL REFERENCES careerlens_users(id) ON DELETE CASCADE,
                        expires_at BIGINT NOT NULL
                    )
                """)
                connection.execute("""
                    CREATE INDEX IF NOT EXISTS careerlens_sessions_expiry
                    ON careerlens_sessions(expires_at)
                """)
            self._ready = True

    def create_user(self, username, password_hash):
        self.ensure_schema()
        user = {"id": str(uuid4()), "username": username}
        with self.connection() as connection:
            result = connection.execute(self.sql("""
                INSERT INTO careerlens_users(id, username, password_hash, created_at)
                VALUES (?, ?, ?, ?) ON CONFLICT(username) DO NOTHING
            """), (user["id"], username, password_hash, int(time.time())))
            return user if result.rowcount == 1 else None

    def find_user(self, username):
        self.ensure_schema()
        with self.connection() as connection:
            result = connection.execute(self.sql("""
                SELECT id, username, password_hash FROM careerlens_users WHERE username = ?
            """), (username,)).fetchone()
            return dict(result) if result else None

    def create_session(self, user_id, token_hash, old_token_hash=None):
        self.ensure_schema()
        with self.connection() as connection:
            connection.execute(self.sql("DELETE FROM careerlens_sessions WHERE expires_at <= ?"), (int(time.time()),))
            if old_token_hash:
                connection.execute(self.sql("DELETE FROM careerlens_sessions WHERE token_hash = ?"), (old_token_hash,))
            connection.execute(self.sql("""
                INSERT INTO careerlens_sessions(token_hash, user_id, expires_at) VALUES (?, ?, ?)
            """), (token_hash, user_id, int(time.time()) + SESSION_SECONDS))

    def session_user(self, token_hash):
        self.ensure_schema()
        with self.connection() as connection:
            result = connection.execute(self.sql("""
                SELECT u.id, u.username FROM careerlens_sessions s
                JOIN careerlens_users u ON u.id = s.user_id
                WHERE s.token_hash = ? AND s.expires_at > ?
            """), (token_hash, int(time.time()))).fetchone()
            return dict(result) if result else None

    def revoke_session(self, token_hash):
        self.ensure_schema()
        with self.connection() as connection:
            connection.execute(self.sql("DELETE FROM careerlens_sessions WHERE token_hash = ?"), (token_hash,))


@lru_cache(maxsize=4)
def _store_for(database_url, sqlite_path):
    return AuthStore(database_url=database_url, sqlite_path=sqlite_path)


def get_store():
    load_dotenv(BASE_DIR / ".env", override=False)
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        if not database_url.startswith(("postgresql://", "postgres://")):
            raise AuthUnavailable()
        return _store_for(database_url, "")
    # Render 临时文件系统不能保存账号；未配置数据库时明确停用账号服务。
    if os.environ.get("RENDER"):
        raise AuthUnavailable()
    sqlite_path = os.environ.get("CAREERLENS_AUTH_DB_PATH", "").strip()
    path = Path(sqlite_path) if sqlite_path else BASE_DIR / "database" / "careerlens_auth.sqlite3"
    if not path.is_absolute():
        path = BASE_DIR / path
    return _store_for("", str(path))


class RateLimits:
    def __init__(self):
        self.entries = {}
        self.lock = threading.Lock()

    def check(self, bucket, limit, window):
        now = time.monotonic()
        with self.lock:
            # 总容量有界；不同规则各自记录有效期，避免将注册限制提前清空。
            for key in list(self.entries):
                values, duration = self.entries[key]
                while values and values[0] <= now - duration:
                    values.popleft()
                if not values:
                    del self.entries[key]
            if bucket not in self.entries:
                if len(self.entries) >= 4096:
                    raise auth_error(429, "请求较多，请稍后重试。", retry_after=60)
                self.entries[bucket] = (deque(), window)
            values, _ = self.entries[bucket]
            if len(values) >= limit:
                raise auth_error(429, "尝试次数较多，请稍后重试。", retry_after=60)
            values.append(now)


_limits = RateLimits()


def auth_error(status, message, retry_after=None):
    headers = dict(NO_CACHE)
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return HTTPException(status_code=status, detail=message, headers=headers)


def no_cache(response: Response):
    response.headers.update(NO_CACHE)


def origin_of(value):
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        if parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            return ""
        return f"{parsed.scheme}://{parsed.netloc}".lower()
    except ValueError:
        return ""


def validate_browser_request(request: Request):
    # 自定义头配合同源检查阻止跨站登录、注册和退出；SameSite 为额外保护。
    if request.headers.get("x-careerlens-client") != "browser":
        raise auth_error(403, "请通过 CareerLens 页面提交账号操作。")
    allowed = {origin_of(str(request.base_url))}
    render_origin = origin_of(os.environ.get("RENDER_EXTERNAL_URL", ""))
    if render_origin:
        allowed.add(render_origin)
    allowed.update(filter(None, (origin_of(x.strip()) for x in os.environ.get("AUTH_ALLOWED_ORIGINS", "").split(","))))
    if not os.environ.get("RENDER"):
        allowed.update({"http://localhost:5173", "http://127.0.0.1:5173"})
    origin = origin_of(request.headers.get("origin", ""))
    if not origin or origin not in allowed:
        raise auth_error(403, "请求来源不正确，请从本站页面重新操作。")


def session_hash(request):
    value = request.cookies.get(COOKIE_NAME, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", value):
        return None
    return sha256(value.encode("ascii")).hexdigest()


def secure_cookie(request):
    return bool(os.environ.get("RENDER")) or request.url.scheme == "https"


def delete_cookie(request, response):
    response.delete_cookie(COOKIE_NAME, path=COOKIE_PATH, httponly=True, secure=secure_cookie(request), samesite="lax")


router = APIRouter(prefix="/api/auth", tags=["账号"], dependencies=[Depends(no_cache)])


@router.get("/status")
def auth_status():
    try:
        get_store().ensure_schema()
        return {"available": True, "message": ""}
    except AuthUnavailable:
        return {"available": False, "message": UNAVAILABLE_MESSAGE}


@router.get("/me")
def current_user(request: Request, response: Response):
    token_hash = session_hash(request)
    if not token_hash:
        return {"authenticated": False, "user": None}
    try:
        user = get_store().session_user(token_hash)
    except AuthUnavailable:
        raise auth_error(503, UNAVAILABLE_MESSAGE)
    if user is None:
        delete_cookie(request, response)
    return {"authenticated": user is not None, "user": user}


@router.post("/register", status_code=201, dependencies=[Depends(validate_browser_request)])
def register(payload: Credentials, request: Request):
    peer = request.client.host if request.client else "unknown"
    _limits.check(("register", peer), 10, 3600)
    if not _hash_slots.acquire(blocking=False):
        raise auth_error(429, "账号服务正忙，请稍后再试。", retry_after=3)
    try:
        user = get_store().create_user(payload.username, hash_password(payload.password.get_secret_value()))
    except AuthUnavailable:
        raise auth_error(503, UNAVAILABLE_MESSAGE)
    finally:
        _hash_slots.release()
    if user is None:
        raise auth_error(409, "该账号已注册，请直接登录或换一个账号。")
    return {"message": "注册成功，请登录。", "user": user}


@router.post("/login", dependencies=[Depends(validate_browser_request)])
def login(payload: Credentials, request: Request, response: Response):
    peer = request.client.host if request.client else "unknown"
    _limits.check(("login-ip", peer), 30, 300)
    _limits.check(("login-account", sha256(payload.username.encode()).hexdigest()), 20, 300)
    if not _hash_slots.acquire(blocking=False):
        raise auth_error(429, "账号服务正忙，请稍后再试。", retry_after=3)
    try:
        store = get_store()
        user = store.find_user(payload.username)
        encoded = user["password_hash"] if user else _DUMMY_HASH
        valid = verify_password(payload.password.get_secret_value(), encoded)
        if user is None or not valid:
            raise auth_error(401, "账号或密码不正确。")
        token = secrets.token_urlsafe(32)
        store.create_session(user["id"], sha256(token.encode("ascii")).hexdigest(), session_hash(request))
    except AuthUnavailable:
        raise auth_error(503, UNAVAILABLE_MESSAGE)
    finally:
        _hash_slots.release()
    response.set_cookie(
        COOKIE_NAME, token, max_age=SESSION_SECONDS, path=COOKIE_PATH,
        httponly=True, secure=secure_cookie(request), samesite="lax",
    )
    return {"authenticated": True, "user": {"id": user["id"], "username": user["username"]}}


@router.post("/logout", dependencies=[Depends(validate_browser_request)])
def logout(request: Request, response: Response):
    token_hash = session_hash(request)
    if token_hash:
        try:
            get_store().revoke_session(token_hash)
        except AuthUnavailable:
            raise auth_error(503, UNAVAILABLE_MESSAGE)
    delete_cookie(request, response)
    return {"authenticated": False, "user": None}


async def validation_errors(request: Request, exc: RequestValidationError):
    if request.url.path.startswith("/api/auth/"):
        # 不把表单密码或输入值回显到错误响应中。
        return JSONResponse(status_code=422, headers=NO_CACHE, content={
            "detail": "账号须为6至20位字母或数字，密码须为8至128个字符；请检查输入。"
        })
    return await request_validation_exception_handler(request, exc)


def install_auth(app):
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, validation_errors)
