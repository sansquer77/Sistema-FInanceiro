from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "finance.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS checking_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                branch TEXT,
                account_number TEXT,
                account_type TEXT NOT NULL DEFAULT 'liquidity' CHECK (account_type IN ('liquidity', 'investment')),
                currency TEXT NOT NULL DEFAULT 'BRL',
                initial_balance_cents INTEGER NOT NULL DEFAULT 0,
                current_balance_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS subcategories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (category_id, name)
            );

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                exchange_rate_micros INTEGER NOT NULL DEFAULT 1000000 CHECK (exchange_rate_micros > 0),
                amount_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_brl_cents >= 0),
                date TEXT NOT NULL,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id),
                destination_account_id INTEGER REFERENCES checking_accounts(id),
                category_id INTEGER REFERENCES categories(id),
                subcategory_id INTEGER REFERENCES subcategories(id),
                tag_id INTEGER REFERENCES tags(id),
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transaction_tags (
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (transaction_id, tag_id)
            );

            CREATE INDEX IF NOT EXISTS idx_transactions_user_date
            ON transactions (user_id, date);

            CREATE INDEX IF NOT EXISTS idx_transactions_account
            ON transactions (account_id);

            CREATE INDEX IF NOT EXISTS idx_subcategories_category
            ON subcategories (category_id);

            CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag
            ON transaction_tags (tag_id);

            CREATE INDEX IF NOT EXISTS idx_password_resets_token
            ON password_resets (token_hash, used_at, expires_at);
            """
        )
        ensure_column(conn, "transactions", "category_id", "INTEGER REFERENCES categories(id)")
        ensure_column(conn, "transactions", "subcategory_id", "INTEGER REFERENCES subcategories(id)")
        ensure_column(conn, "transactions", "tag_id", "INTEGER REFERENCES tags(id)")
        ensure_column(conn, "transactions", "exchange_rate_micros", "INTEGER NOT NULL DEFAULT 1000000")
        ensure_column(conn, "transactions", "amount_brl_cents", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "checking_accounts", "account_type", "TEXT NOT NULL DEFAULT 'liquidity'")
        migrate_transaction_tags(conn)
        migrate_transaction_brl_values(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_transaction_tags(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id)
        SELECT id, tag_id
        FROM transactions
        WHERE tag_id IS NOT NULL
        """
    )


def migrate_transaction_brl_values(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET amount_brl_cents = amount_cents
        WHERE amount_brl_cents = 0
        """
    )
