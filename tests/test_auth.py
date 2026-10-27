"""注册、密码与会话回归；真实 Postgres 检查由 CI 的独立测试库运行。"""

from collections import deque
import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend import auth
from backend.main import app


HEADERS = {"Origin": "http://testserver", "X-CareerLens-Client": "browser"}
PASSWORD = "ValidPass2026!"


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "accounts.sqlite3")
        self.environment = patch.dict(os.environ, {
            "DATABASE_URL": "", "RENDER": "", "RENDER_EXTERNAL_URL": "",
            "CAREERLENS_AUTH_DB_PATH": self.path, "AUTH_ALLOWED_ORIGINS": "",
        })
        self.environment.start()
        self.limits = patch.object(auth, "_limits", auth.RateLimits())
        self.limits.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.limits.stop()
        self.environment.stop()
        auth._store_for.cache_clear()
        self.directory.cleanup()

    def register(self, username="student1", password=PASSWORD):
        return self.client.post("/api/auth/register", headers=HEADERS, json={"username": username, "password": password})

    def login(self, username="student1", password=PASSWORD):
        return self.client.post("/api/auth/login", headers=HEADERS, json={"username": username, "password": password})

    def test_registration_stores_only_a_salted_password_hash(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()["user"]), {"id", "username"})
        self.assertNotIn(PASSWORD, response.text)
        self.assertNotIn("set-cookie", response.headers)
        row = auth.get_store().find_user("student1")
        self.assertNotEqual(row["password_hash"], PASSWORD)
        self.assertTrue(auth.verify_password(PASSWORD, row["password_hash"]))
        self.assertFalse(auth.verify_password("wrongpass", row["password_hash"]))

    def test_same_password_gets_distinct_salts(self):
        self.assertEqual(self.register("student1").status_code, 201)
        self.assertEqual(self.register("student2").status_code, 201)
        self.assertNotEqual(auth.get_store().find_user("student1")["password_hash"], auth.get_store().find_user("student2")["password_hash"])

    def test_duplicate_username_is_atomic_and_case_insensitive(self):
        self.assertEqual(self.register(" Student1 ").status_code, 201)
        self.assertEqual(self.register("STUDENT1").status_code, 409)
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM careerlens_users").fetchone()[0], 1)

    def test_login_restores_user_and_keeps_token_out_of_response(self):
        self.register()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        token = self.client.cookies.get(auth.COOKIE_NAME)
        self.assertEqual(len(token), 43)
        self.assertNotIn(token, response.text)
        cookie = response.headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Path=/api/auth", cookie)
        self.assertTrue(self.client.get("/api/auth/me").json()["authenticated"])
        with sqlite3.connect(self.path) as connection:
            saved = connection.execute("SELECT token_hash FROM careerlens_sessions").fetchone()[0]
        self.assertNotEqual(saved, token)
        self.assertEqual(saved, auth.sha256(token.encode()).hexdigest())

    def test_bad_password_and_unknown_user_have_same_error(self):
        self.register()
        wrong = self.login(password="WrongPass2026!")
        unknown = self.login(username="unknown1")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json(), unknown.json())
        self.assertNotIn("set-cookie", wrong.headers)

    def test_logout_revokes_copied_session_token(self):
        self.register()
        self.login()
        token = self.client.cookies.get(auth.COOKIE_NAME)
        self.assertEqual(self.client.post("/api/auth/logout", headers=HEADERS).status_code, 200)
        other = TestClient(app)
        other.cookies.set(auth.COOKIE_NAME, token)
        self.assertFalse(other.get("/api/auth/me").json()["authenticated"])
        other.close()

    def test_new_login_rotates_and_invalidates_previous_cookie(self):
        self.register()
        self.login()
        token = self.client.cookies.get(auth.COOKIE_NAME)
        self.login()
        self.assertNotEqual(self.client.cookies.get(auth.COOKIE_NAME), token)
        other = TestClient(app)
        other.cookies.set(auth.COOKIE_NAME, token)
        self.assertFalse(other.get("/api/auth/me").json()["authenticated"])
        other.close()

    def test_expired_sessions_are_rejected(self):
        self.register()
        self.login()
        with sqlite3.connect(self.path) as connection:
            connection.execute("UPDATE careerlens_sessions SET expires_at = 0")
        response = self.client.get("/api/auth/me")
        self.assertFalse(response.json()["authenticated"])
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_forged_cookie_is_not_a_login(self):
        for token in ["student1", "a" * 43]:
            self.client.cookies.set(auth.COOKIE_NAME, token)
            self.assertFalse(self.client.get("/api/auth/me").json()["authenticated"])

    def test_user_and_session_survive_store_recreation(self):
        self.register()
        self.login()
        auth._store_for.cache_clear()
        self.assertEqual(self.client.get("/api/auth/me").json()["user"]["username"], "student1")

    def test_registration_rejects_unsafe_or_invalid_username(self):
        for name in ["short", "x" * 21, "username'--", "用户名123456"]:
            with self.subTest(name=name):
                self.assertEqual(self.register(name).status_code, 422)

    def test_invalid_password_never_echoes_in_validation_errors(self):
        for password in ["secret", "X" * 129, " " * 8]:
            response = self.register(password=password)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(password, response.text)
            self.assertNotIn('"input"', response.text)

    def test_password_whitespace_and_unicode_are_not_silently_changed(self):
        password = " 开始测试Password! "
        self.assertEqual(self.register(password=password).status_code, 201)
        self.assertEqual(self.login(password=password.strip()).status_code, 401)
        self.assertEqual(self.login(password=password).status_code, 200)

    def test_all_auth_mutations_require_same_origin_and_custom_header(self):
        for path in ["register", "login", "logout"]:
            for headers in [{}, {"Origin": "http://testserver"}, {"Origin": "https://outside.invalid", "X-CareerLens-Client": "browser"}]:
                with self.subTest(path=path, headers=headers):
                    response = self.client.post("/api/auth/" + path, headers=headers, json={"username": "student1", "password": PASSWORD})
                    self.assertEqual(response.status_code, 403)

    def test_default_vite_origin_and_explicit_dev_port_are_supported(self):
        self.assertEqual(self.client.post("/api/auth/register", headers={**HEADERS, "Origin": "http://127.0.0.1:5173"}, json={"username": "student1", "password": PASSWORD}).status_code, 201)
        with patch.dict(os.environ, {"AUTH_ALLOWED_ORIGINS": "http://127.0.0.1:5174"}):
            self.assertEqual(self.client.post("/api/auth/login", headers={**HEADERS, "Origin": "http://127.0.0.1:5174"}, json={"username": "student1", "password": PASSWORD}).status_code, 200)

    def test_cloud_does_not_fall_back_to_ephemeral_sqlite(self):
        with patch.dict(os.environ, {"RENDER": "true"}):
            self.assertFalse(self.client.get("/api/auth/status").json()["available"])
            self.assertEqual(self.register().status_code, 503)
            self.assertFalse(Path(self.path).exists())

    def test_invalid_database_url_does_not_leak_credentials(self):
        with patch.dict(os.environ, {"DATABASE_URL": "invalid://example-user:example-password@invalid/db"}):
            response = self.register()
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("example-password", response.text)

    def test_postgres_configuration_selects_postgres_store(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/unused", "RENDER": "true"}):
            self.assertTrue(auth.get_store().postgres)

    def test_https_sessions_use_secure_cookie(self):
        self.register()
        with TestClient(app, base_url="https://testserver") as client:
            response = client.post("/api/auth/login", headers={**HEADERS, "Origin": "https://testserver"}, json={"username": "student1", "password": PASSWORD})
            self.assertEqual(response.status_code, 200)
            self.assertIn("Secure", response.headers["set-cookie"])
            self.assertTrue(client.get("/api/auth/me").json()["authenticated"])

    def test_login_rate_limit_has_retry_header(self):
        auth._limits.entries[("login-ip", "testclient")] = (deque([time.monotonic()] * 30), 300)
        response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["retry-after"], "60")

    def test_password_work_is_bounded(self):
        auth._hash_slots.acquire()
        auth._hash_slots.acquire()
        try:
            self.assertEqual(self.login().status_code, 429)
        finally:
            auth._hash_slots.release()
            auth._hash_slots.release()

    def test_account_database_failure_does_not_break_public_features(self):
        with patch.object(auth, "get_store", side_effect=auth.AuthUnavailable):
            self.assertEqual(self.register().status_code, 503)
            self.assertEqual(self.client.get("/api/overview").status_code, 200)
            self.assertFalse(self.client.get("/api/auth/status").json()["available"])

    def test_auth_responses_are_not_cacheable(self):
        for response in [self.client.get("/api/auth/me"), self.client.get("/api/auth/status"), self.login(), self.register(password="short")]:
            self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_non_auth_validation_keeps_existing_contract(self):
        response = self.client.post("/api/ask", json={"question": ""})
        self.assertEqual(response.status_code, 422)
        self.assertIsInstance(response.json()["detail"], list)


@unittest.skipUnless(os.environ.get("AUTH_TEST_DATABASE_URL"), "独立 Postgres 测试库未配置；CI 会提供")
class PostgresAuthTests(unittest.TestCase):
    def test_real_postgres_registration_session_and_revocation(self):
        username = "pg" + uuid4().hex[:12]
        with patch.dict(os.environ, {"DATABASE_URL": os.environ["AUTH_TEST_DATABASE_URL"], "RENDER": "true"}), patch.object(auth, "_limits", auth.RateLimits()):
            headers = {"Origin": "https://testserver", "X-CareerLens-Client": "browser"}
            payload = {"username": username, "password": PASSWORD}
            with TestClient(app, base_url="https://testserver") as client:
                self.assertTrue(client.get("/api/auth/status").json()["available"])
                self.assertEqual(client.post("/api/auth/register", headers=headers, json=payload).status_code, 201)
                self.assertEqual(client.post("/api/auth/register", headers=headers, json=payload).status_code, 409)
                response = client.post("/api/auth/login", headers=headers, json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(client.get("/api/auth/me").json()["authenticated"])
                self.assertEqual(client.post("/api/auth/logout", headers=headers).status_code, 200)
                self.assertFalse(client.get("/api/auth/me").json()["authenticated"])
                # 只删除本测试创建的账号；不清空表或触碰其他测试数据。
                store = auth.get_store()
                with store.connection() as connection:
                    connection.execute(store.sql("DELETE FROM careerlens_users WHERE username = ?"), (username,))


if __name__ == "__main__":
    unittest.main()
