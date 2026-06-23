from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from http import HTTPStatus

from financeiro.database import get_connection, row_to_dict
from financeiro.emailer import send_password_reset_email

RESET_TOKEN_MINUTES = 15


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
            from financeiro.categories import seed_default_categories
            seed_default_categories(conn, user_id)
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


def clear_user_launches(user_id: int, current_password: str) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(current_password, row["password_hash"]):
            raise AuthError("Senha atual invalida.", HTTPStatus.UNAUTHORIZED)
        conn.execute("DELETE FROM credit_card_payments WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM credit_card_transactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM investment_value_overrides WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM investment_closed_positions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM investment_opening_positions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM transaction_tags WHERE transaction_id IN (SELECT id FROM transactions WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        conn.execute(
            """
            UPDATE checking_accounts
            SET current_balance_cents = initial_balance_cents,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (user_id,),
        )


def request_password_reset(email: str) -> dict:
    normalized_email = email.strip().lower()
    validate_email(normalized_email)
    token = None
    with get_connection() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (normalized_email,)).fetchone()
        if user:
            token = secrets.token_urlsafe(24)
            conn.execute(
                """
                UPDATE password_resets
                SET used_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND used_at IS NULL
                """,
                (user["id"],),
            )
            conn.execute(
                """
                INSERT INTO password_resets (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
                """,
                (user["id"], hash_reset_token(token), reset_expiration()),
            )
            send_password_reset_email(normalized_email, token, RESET_TOKEN_MINUTES)
    return {
        "ok": True,
        "expires_in_minutes": RESET_TOKEN_MINUTES,
    }


def reset_password(token: str, new_password: str) -> None:
    normalized_token = str(token or "").strip()
    if len(new_password) < 8:
        raise AuthError("A nova senha precisa ter pelo menos 8 caracteres.")
    if not normalized_token:
        raise AuthError("Informe o codigo de recuperacao.")
    token_hash = hash_reset_token(normalized_token)
    now = current_timestamp()
    with get_connection() as conn:
        reset = conn.execute(
            """
            SELECT *
            FROM password_resets
            WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (token_hash, now),
        ).fetchone()
        if not reset:
            raise AuthError("Codigo de recuperacao invalido ou expirado.", HTTPStatus.UNAUTHORIZED)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), reset["user_id"]),
        )
        conn.execute(
            "UPDATE password_resets SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (reset["id"],),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (reset["user_id"],))


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


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def reset_expiration() -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_MINUTES)
    return expires_at.replace(microsecond=0).isoformat()


def current_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
