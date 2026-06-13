from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict


class AuthError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def create_user(name: str, email: str, password: str) -> dict:
    name = name.strip()
    email = email.strip().lower()
    validate_user_input(name, email, password)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hash_password(password)),
            )
            user_id = cursor.lastrowid
            row = conn.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
            return row_to_dict(row)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise AuthError("Ja existe um usuario com este email.", HTTPStatus.CONFLICT) from exc
        raise


def login_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise AuthError("Email ou senha invalidos.", HTTPStatus.UNAUTHORIZED)
    return {"id": row["id"], "name": row["name"], "email": row["email"], "created_at": row["created_at"]}


def update_user_email(user_id: int, email: str, current_password: str) -> dict:
    email = email.strip().lower()
    validate_email(email)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(current_password, row["password_hash"]):
            raise AuthError("Senha atual invalida.", HTTPStatus.UNAUTHORIZED)
        try:
            conn.execute("UPDATE users SET email = ? WHERE id = ?", (email, user_id))
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise AuthError("Ja existe um usuario com este email.", HTTPStatus.CONFLICT) from exc
            raise
        updated = conn.execute("SELECT id, name, email, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_dict(updated)


def update_user_password(user_id: int, current_password: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise AuthError("A nova senha precisa ter pelo menos 8 caracteres.")
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(current_password, row["password_hash"]):
            raise AuthError("Senha atual invalida.", HTTPStatus.UNAUTHORIZED)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user_id))


def delete_user_account(user_id: int, current_password: str) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(current_password, row["password_hash"]):
            raise AuthError("Senha atual invalida.", HTTPStatus.UNAUTHORIZED)
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_connection() as conn:
        conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id))
    return token


def get_current_user(token: str | None) -> dict | None:
    if not token:
        return None
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT users.id, users.name, users.email, users.created_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()
    return row_to_dict(row)


def logout_session(token: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def validate_user_input(name: str, email: str, password: str) -> None:
    if len(name) < 2:
        raise AuthError("Informe seu nome.")
    validate_email(email)
    if len(password) < 8:
        raise AuthError("A senha precisa ter pelo menos 8 caracteres.")


def validate_email(email: str) -> None:
    if "@" not in email or "." not in email:
        raise AuthError("Informe um email valido.")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt_b64, digest_b64 = stored_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False
