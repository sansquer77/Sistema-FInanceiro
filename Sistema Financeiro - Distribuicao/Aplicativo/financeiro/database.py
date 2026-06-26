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

            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                identifier TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
                locked_until TEXT,
                last_attempt_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (action, identifier)
            );

            CREATE TABLE IF NOT EXISTS checking_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                branch TEXT,
                account_number TEXT,
                account_type TEXT NOT NULL DEFAULT 'liquidity' CHECK (account_type IN ('liquidity', 'wallet', 'investment')),
                currency TEXT NOT NULL DEFAULT 'BRL',
                initial_balance_cents INTEGER NOT NULL DEFAULT 0,
                current_balance_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                issuer TEXT NOT NULL,
                network TEXT,
                currency TEXT NOT NULL DEFAULT 'BRL',
                limit_cents INTEGER NOT NULL CHECK (limit_cents > 0),
                closing_day INTEGER NOT NULL CHECK (closing_day BETWEEN 1 AND 31),
                due_day INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31),
                preferred_payment_account_id INTEGER REFERENCES checking_accounts(id),
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, name)
            );

            CREATE TABLE IF NOT EXISTS credit_card_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                credit_card_id INTEGER NOT NULL REFERENCES credit_cards(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                date TEXT NOT NULL,
                invoice_month TEXT NOT NULL,
                series_id TEXT,
                series_kind TEXT NOT NULL DEFAULT 'single',
                installment_index INTEGER,
                installment_count INTEGER,
                recurrence_frequency TEXT,
                category_id INTEGER REFERENCES categories(id),
                subcategory_id INTEGER REFERENCES subcategories(id),
                reconciled_at TEXT,
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS credit_card_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                credit_card_id INTEGER NOT NULL REFERENCES credit_cards(id) ON DELETE CASCADE,
                invoice_month TEXT NOT NULL,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id),
                transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                payment_date TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, credit_card_id, invoice_month)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                group_type TEXT NOT NULL DEFAULT 'expense' CHECK (group_type IN ('income', 'expense', 'investment')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, group_type, name)
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
                type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'investment')),
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                destination_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (destination_amount_cents >= 0),
                exchange_rate_micros INTEGER NOT NULL DEFAULT 1000000 CHECK (exchange_rate_micros > 0),
                transfer_exchange_rate_micros INTEGER NOT NULL DEFAULT 0 CHECK (transfer_exchange_rate_micros >= 0),
                amount_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_brl_cents >= 0),
                date TEXT NOT NULL,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id),
                destination_account_id INTEGER REFERENCES checking_accounts(id),
                category_id INTEGER REFERENCES categories(id),
                subcategory_id INTEGER REFERENCES subcategories(id),
                tag_id INTEGER REFERENCES tags(id),
                series_id TEXT,
                series_kind TEXT NOT NULL DEFAULT 'single',
                installment_index INTEGER,
                installment_count INTEGER,
                recurrence_frequency TEXT,
                reconciled_at TEXT,
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS investment_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                asset_type TEXT NOT NULL DEFAULT 'other',
                asset_identifier TEXT,
                asset_name TEXT,
                cnpj TEXT,
                quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (quantity_micros >= 0),
                unit_price_cents INTEGER NOT NULL DEFAULT 0 CHECK (unit_price_cents >= 0),
                invested_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (invested_amount_cents >= 0),
                brokerage_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (brokerage_fee_cents >= 0),
                exchange_fee_cents INTEGER NOT NULL DEFAULT 0 CHECK (exchange_fee_cents >= 0),
                tax_cents INTEGER NOT NULL DEFAULT 0 CHECK (tax_cents >= 0),
                other_costs_cents INTEGER NOT NULL DEFAULT 0 CHECK (other_costs_cents >= 0),
                fixed_income_mode TEXT,
                fixed_income_indexer TEXT,
                fixed_income_rate_micros INTEGER NOT NULL DEFAULT 0 CHECK (fixed_income_rate_micros >= 0),
                fixed_income_maturity_date TEXT,
                savings_anniversaries_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (transaction_id)
            );

            CREATE TABLE IF NOT EXISTS investment_opening_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                asset_type TEXT NOT NULL DEFAULT 'other',
                asset_identifier TEXT,
                asset_name TEXT,
                cnpj TEXT,
                acquisition_date TEXT NOT NULL,
                quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (quantity_micros >= 0),
                unit_price_cents INTEGER NOT NULL DEFAULT 0 CHECK (unit_price_cents >= 0),
                total_cost_cents INTEGER NOT NULL CHECK (total_cost_cents > 0),
                exchange_rate_micros INTEGER NOT NULL DEFAULT 1000000 CHECK (exchange_rate_micros > 0),
                fixed_income_mode TEXT,
                fixed_income_indexer TEXT,
                fixed_income_rate_micros INTEGER NOT NULL DEFAULT 0 CHECK (fixed_income_rate_micros >= 0),
                fixed_income_maturity_date TEXT,
                apply_tax_estimate INTEGER NOT NULL DEFAULT 0 CHECK (apply_tax_estimate IN (0, 1)),
                savings_anniversaries_json TEXT,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS investment_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                transaction_id INTEGER REFERENCES transactions(id) ON DELETE SET NULL,
                source_type TEXT NOT NULL CHECK (source_type IN ('operation', 'opening')),
                source_id INTEGER NOT NULL,
                redeemed_value_cents INTEGER NOT NULL CHECK (redeemed_value_cents > 0),
                redeemed_cost_cents INTEGER NOT NULL CHECK (redeemed_cost_cents >= 0),
                redeemed_quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (redeemed_quantity_micros >= 0),
                date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS investment_value_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                asset_type TEXT NOT NULL DEFAULT 'other',
                asset_identifier TEXT NOT NULL DEFAULT '',
                asset_name TEXT NOT NULL DEFAULT '',
                cnpj TEXT NOT NULL DEFAULT '',
                fixed_income_indexer TEXT NOT NULL DEFAULT '',
                fixed_income_maturity_date TEXT NOT NULL DEFAULT '',
                current_value_cents INTEGER NOT NULL CHECK (current_value_cents >= 0),
                quote_date TEXT NOT NULL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (
                    user_id, account_id, asset_type, asset_identifier, asset_name,
                    cnpj, fixed_income_indexer, fixed_income_maturity_date
                )
            );

            CREATE TABLE IF NOT EXISTS investment_closed_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                currency TEXT NOT NULL,
                asset_type TEXT NOT NULL DEFAULT 'other',
                asset_identifier TEXT NOT NULL DEFAULT '',
                asset_name TEXT NOT NULL DEFAULT '',
                cnpj TEXT NOT NULL DEFAULT '',
                fixed_income_indexer TEXT NOT NULL DEFAULT '',
                fixed_income_maturity_date TEXT NOT NULL DEFAULT '',
                closed_at TEXT NOT NULL,
                source_count INTEGER NOT NULL DEFAULT 0 CHECK (source_count >= 0),
                quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (quantity_micros >= 0),
                total_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (total_cost_cents >= 0),
                total_cost_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (total_cost_brl_cents >= 0),
                closing_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (closing_value_cents >= 0),
                closing_value_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (closing_value_brl_cents >= 0),
                result_brl_cents INTEGER NOT NULL DEFAULT 0,
                result_percent_micros INTEGER NOT NULL DEFAULT 0,
                first_operation_date TEXT,
                last_operation_date TEXT,
                quote_source TEXT,
                notes TEXT,
                position_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (
                    user_id, account_id, asset_type, asset_identifier, asset_name,
                    cnpj, fixed_income_indexer, fixed_income_maturity_date, closed_at
                )
            );

            CREATE TABLE IF NOT EXISTS transaction_tags (
                transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (transaction_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS credit_card_transaction_tags (
                credit_card_transaction_id INTEGER NOT NULL REFERENCES credit_card_transactions(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (credit_card_transaction_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS spending_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                month TEXT NOT NULL,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                subcategory_id INTEGER REFERENCES subcategories(id) ON DELETE CASCADE,
                limit_amount_cents INTEGER NOT NULL CHECK (limit_amount_cents > 0),
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS quote_cache (
                cache_key TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_spending_limits_category
            ON spending_limits (user_id, month, category_id)
            WHERE subcategory_id IS NULL;

            CREATE UNIQUE INDEX IF NOT EXISTS idx_spending_limits_subcategory
            ON spending_limits (user_id, month, category_id, subcategory_id)
            WHERE subcategory_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS idx_transactions_user_date
            ON transactions (user_id, date);

            CREATE INDEX IF NOT EXISTS idx_transactions_account
            ON transactions (account_id);

            CREATE INDEX IF NOT EXISTS idx_investment_operations_user
            ON investment_operations (user_id, account_id, asset_type);

            CREATE INDEX IF NOT EXISTS idx_investment_opening_positions_user
            ON investment_opening_positions (user_id, account_id, asset_type);

            CREATE INDEX IF NOT EXISTS idx_credit_card_transactions_card_month
            ON credit_card_transactions (credit_card_id, invoice_month);

            CREATE INDEX IF NOT EXISTS idx_subcategories_category
            ON subcategories (category_id);

            CREATE INDEX IF NOT EXISTS idx_transaction_tags_tag
            ON transaction_tags (tag_id);

            CREATE INDEX IF NOT EXISTS idx_credit_card_transaction_tags_tag
            ON credit_card_transaction_tags (tag_id);

            CREATE INDEX IF NOT EXISTS idx_password_resets_token
            ON password_resets (token_hash, used_at, expires_at);

            CREATE INDEX IF NOT EXISTS idx_auth_attempts_locked_until
            ON auth_attempts (locked_until);

            CREATE INDEX IF NOT EXISTS idx_quote_cache_expires_at
            ON quote_cache (expires_at);
            """
        )
        ensure_column(conn, "transactions", "category_id", "INTEGER REFERENCES categories(id)")
        ensure_column(conn, "transactions", "subcategory_id", "INTEGER REFERENCES subcategories(id)")
        ensure_column(conn, "transactions", "tag_id", "INTEGER REFERENCES tags(id)")
        ensure_column(conn, "transactions", "destination_amount_cents", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "transactions", "exchange_rate_micros", "INTEGER NOT NULL DEFAULT 1000000")
        ensure_column(conn, "transactions", "transfer_exchange_rate_micros", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "transactions", "amount_brl_cents", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "transactions", "series_id", "TEXT")
        ensure_column(conn, "transactions", "series_kind", "TEXT NOT NULL DEFAULT 'single'")
        ensure_column(conn, "transactions", "installment_index", "INTEGER")
        ensure_column(conn, "transactions", "installment_count", "INTEGER")
        ensure_column(conn, "transactions", "recurrence_frequency", "TEXT")
        ensure_column(conn, "transactions", "reconciled_at", "TEXT")
        ensure_column(conn, "credit_card_transactions", "reconciled_at", "TEXT")
        ensure_column(conn, "credit_card_transactions", "series_id", "TEXT")
        ensure_column(conn, "credit_card_transactions", "series_kind", "TEXT NOT NULL DEFAULT 'single'")
        ensure_column(conn, "credit_card_transactions", "installment_index", "INTEGER")
        ensure_column(conn, "credit_card_transactions", "installment_count", "INTEGER")
        ensure_column(conn, "credit_card_transactions", "recurrence_frequency", "TEXT")
        ensure_column(conn, "credit_cards", "preferred_payment_account_id", "INTEGER REFERENCES checking_accounts(id)")
        ensure_column(conn, "investment_operations", "fixed_income_maturity_date", "TEXT")
        ensure_column(conn, "investment_operations", "savings_anniversaries_json", "TEXT")
        ensure_column(conn, "investment_opening_positions", "fixed_income_maturity_date", "TEXT")
        ensure_column(conn, "investment_opening_positions", "apply_tax_estimate", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(conn, "investment_opening_positions", "savings_anniversaries_json", "TEXT")
        ensure_column(conn, "checking_accounts", "account_type", "TEXT NOT NULL DEFAULT 'liquidity'")
        ensure_column(conn, "categories", "group_type", "TEXT NOT NULL DEFAULT 'expense'")
        migrate_category_unique_constraint(conn)
        migrate_transaction_type_constraint(conn)
        migrate_transaction_tags(conn)
        migrate_transaction_brl_values(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions (account_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_operations_user ON investment_operations (user_id, account_id, asset_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_opening_positions_user ON investment_opening_positions (user_id, account_id, asset_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_redemptions_source ON investment_redemptions (user_id, source_type, source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_value_overrides_user ON investment_value_overrides (user_id, account_id, asset_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_investment_closed_positions_user ON investment_closed_positions (user_id, account_id, asset_type, closed_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_quote_cache_expires_at ON quote_cache (expires_at)")


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_category_unique_constraint(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'categories'
        """
    ).fetchone()
    table_sql = row["sql"] if row else ""
    if "UNIQUE (user_id, group_type, name)" in table_sql:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript(
            """
            CREATE TABLE categories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                group_type TEXT NOT NULL DEFAULT 'expense' CHECK (group_type IN ('income', 'expense', 'investment')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, group_type, name)
            );

            INSERT INTO categories_new (id, user_id, name, group_type, created_at)
            SELECT id, user_id, name, group_type, created_at
            FROM categories;

            DROP TABLE categories;
            ALTER TABLE categories_new RENAME TO categories;
            """
        )
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def migrate_transaction_tags(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO transaction_tags (transaction_id, tag_id)
        SELECT id, tag_id
        FROM transactions
        WHERE tag_id IS NOT NULL
        """
    )


def migrate_transaction_type_constraint(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        """
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table' AND name = 'transactions'
        """
    ).fetchone()
    table_sql = row["sql"] if row else ""
    if "'investment'" in table_sql:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript(
            """
            CREATE TABLE transactions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ('income', 'expense', 'transfer', 'investment')),
                description TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
                destination_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK (destination_amount_cents >= 0),
                exchange_rate_micros INTEGER NOT NULL DEFAULT 1000000 CHECK (exchange_rate_micros > 0),
                transfer_exchange_rate_micros INTEGER NOT NULL DEFAULT 0 CHECK (transfer_exchange_rate_micros >= 0),
                amount_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_brl_cents >= 0),
                date TEXT NOT NULL,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id),
                destination_account_id INTEGER REFERENCES checking_accounts(id),
                category_id INTEGER REFERENCES categories(id),
                subcategory_id INTEGER REFERENCES subcategories(id),
                tag_id INTEGER REFERENCES tags(id),
                series_id TEXT,
                series_kind TEXT NOT NULL DEFAULT 'single',
                installment_index INTEGER,
                installment_count INTEGER,
                recurrence_frequency TEXT,
                reconciled_at TEXT,
                notes TEXT,
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO transactions_new (
                id, user_id, type, description, amount_cents, destination_amount_cents,
                exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents, date,
                account_id, destination_account_id, category_id, subcategory_id, tag_id,
                series_id, series_kind, installment_index, installment_count, recurrence_frequency,
                reconciled_at, notes, archived_at, created_at, updated_at
            )
            SELECT
                id, user_id, type, description, amount_cents, destination_amount_cents,
                exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents, date,
                account_id, destination_account_id, category_id, subcategory_id, tag_id,
                series_id, series_kind, installment_index, installment_count, recurrence_frequency,
                reconciled_at, notes, archived_at, created_at, updated_at
            FROM transactions;

            DROP TABLE transactions;
            ALTER TABLE transactions_new RENAME TO transactions;
            """
        )
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def migrate_transaction_brl_values(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET amount_brl_cents = amount_cents
        WHERE amount_brl_cents = 0
        """
    )
