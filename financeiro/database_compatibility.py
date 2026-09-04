from __future__ import annotations

import hashlib
import sqlite3

from financeiro.database_schema import PERFORMANCE_INDEXES


def normalize_legacy_schema(conn: sqlite3.Connection) -> None:
    """Apply historical schema normalizations to a copied legacy database.

    This function is idempotent and must only run once against the work copy of
    a legacy database, after the v2 baseline schema has been created and before
    the candidate is promoted. It never opens connections, creates backups,
    renames files or sets the schema version.
    """
    # spec: migracao-dados/migracao-banco-v2 v1.5 — critérios 3, 4, 7, 8 e 11
    # Order matters: later steps may depend on tables/columns ensured earlier.
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
    ensure_column(conn, "transactions", "normalized_description", "TEXT")

    ensure_column(conn, "credit_card_transactions", "reconciled_at", "TEXT")
    ensure_column(conn, "credit_card_transactions", "normalized_description", "TEXT")
    ensure_column(conn, "credit_card_transactions", "exchange_rate_micros", "INTEGER NOT NULL DEFAULT 1000000")
    ensure_column(conn, "credit_card_transactions", "amount_brl_cents", "INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        UPDATE credit_card_transactions
        SET amount_brl_cents = amount_cents
        WHERE amount_brl_cents = 0
        """
    )
    ensure_column(conn, "credit_card_transactions", "series_id", "TEXT")
    ensure_column(conn, "credit_card_transactions", "series_kind", "TEXT NOT NULL DEFAULT 'single'")

    migrate_session_tokens(conn)
    ensure_session_expiration(conn)

    ensure_column(conn, "credit_card_transactions", "installment_index", "INTEGER")
    ensure_column(conn, "credit_card_transactions", "installment_count", "INTEGER")
    ensure_column(conn, "credit_card_transactions", "recurrence_frequency", "TEXT")
    ensure_column(conn, "credit_card_transactions", "use_average", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "transactions", "use_average", "INTEGER NOT NULL DEFAULT 0")

    ensure_column(conn, "credit_cards", "preferred_payment_account_id", "INTEGER REFERENCES checking_accounts(id)")
    ensure_column(conn, "investment_operations", "fixed_income_maturity_date", "TEXT")
    ensure_column(conn, "investment_operations", "emergency_reserve_eligible", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "investment_operations", "savings_anniversaries_json", "TEXT")
    ensure_column(conn, "investment_opening_positions", "fixed_income_maturity_date", "TEXT")
    ensure_column(conn, "investment_opening_positions", "apply_tax_estimate", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "investment_opening_positions", "emergency_reserve_eligible", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "investment_opening_positions", "savings_anniversaries_json", "TEXT")
    ensure_column(conn, "checking_accounts", "account_type", "TEXT NOT NULL DEFAULT 'liquidity'")
    ensure_column(conn, "categories", "group_type", "TEXT NOT NULL DEFAULT 'expense'")

    ensure_operation_logs(conn)
    ensure_ai_settings(conn)
    ensure_secure_configs(conn)
    ensure_consultor_schema(conn)
    ensure_notification_reads(conn)

    migrate_category_unique_constraint(conn)

    # A recriação de transactions depende de colunas que podem não existir em
    # bancos v1 antigos; garantimos todas antes de reconstruir a tabela.
    ensure_column(conn, "transactions", "destination_amount_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "transactions", "exchange_rate_micros", "INTEGER NOT NULL DEFAULT 1000000")
    ensure_column(conn, "transactions", "transfer_exchange_rate_micros", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "transactions", "amount_brl_cents", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "transactions", "destination_account_id", "INTEGER REFERENCES checking_accounts(id)")
    ensure_column(conn, "transactions", "category_id", "INTEGER REFERENCES categories(id)")
    ensure_column(conn, "transactions", "subcategory_id", "INTEGER REFERENCES subcategories(id)")
    ensure_column(conn, "transactions", "tag_id", "INTEGER REFERENCES tags(id)")
    ensure_column(conn, "transactions", "series_id", "TEXT")
    ensure_column(conn, "transactions", "series_kind", "TEXT NOT NULL DEFAULT 'single'")
    ensure_column(conn, "transactions", "installment_index", "INTEGER")
    ensure_column(conn, "transactions", "installment_count", "INTEGER")
    ensure_column(conn, "transactions", "recurrence_frequency", "TEXT")
    ensure_column(conn, "transactions", "use_average", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "transactions", "normalized_description", "TEXT")
    ensure_column(conn, "transactions", "reconciled_at", "TEXT")
    ensure_column(conn, "transactions", "notes", "TEXT")
    ensure_column(conn, "transactions", "archived_at", "TEXT")
    ensure_column(conn, "transactions", "updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    migrate_transaction_type_constraint(conn)
    migrate_transaction_tags(conn)
    migrate_transaction_brl_values(conn)
    backfill_normalized_descriptions(conn)
    ensure_performance_indexes(conn)


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def migrate_session_tokens(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "token" not in columns:
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        rows = conn.execute("SELECT token, user_id, created_at FROM sessions").fetchall()
        conn.executescript(
            """
            CREATE TABLE sessions_new (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            "INSERT INTO sessions_new (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, datetime(?, '+30 days'))",
            ((hashlib.sha256(row["token"].encode("utf-8")).hexdigest(), row["user_id"], row["created_at"], row["created_at"]) for row in rows),
        )
        conn.executescript("DROP TABLE sessions; ALTER TABLE sessions_new RENAME TO sessions;")
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def ensure_session_expiration(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "expires_at" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
        conn.execute("UPDATE sessions SET expires_at = datetime(created_at, '+30 days')")


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
                use_average INTEGER NOT NULL DEFAULT 0 CHECK (use_average IN (0, 1)),
                normalized_description TEXT,
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
                use_average, normalized_description, reconciled_at, notes, archived_at, created_at, updated_at
            )
            SELECT
                id, user_id, type, description, amount_cents, destination_amount_cents,
                exchange_rate_micros, transfer_exchange_rate_micros, amount_brl_cents, date,
                account_id, destination_account_id, category_id, subcategory_id, tag_id,
                series_id, series_kind, installment_index, installment_count, recurrence_frequency,
                use_average, normalized_description, reconciled_at, notes, archived_at, created_at, updated_at
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


def backfill_normalized_descriptions(conn: sqlite3.Connection) -> None:
    from financeiro.classification_suggestions import normalize_description

    for table in ("transactions", "credit_card_transactions"):
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        if not table_exists:
            continue
        rows = conn.execute(
            f"SELECT id, description FROM {table} WHERE normalized_description IS NULL"
        ).fetchall()
        if rows:
            conn.executemany(
                f"UPDATE {table} SET normalized_description = ? WHERE id = ?",
                [(normalize_description(row["description"]), row["id"]) for row in rows],
            )


def ensure_operation_logs(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS operation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            operation_batch_id TEXT,
            module TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT,
            account_id INTEGER REFERENCES checking_accounts(id) ON DELETE SET NULL,
            credit_card_id INTEGER REFERENCES credit_cards(id) ON DELETE SET NULL,
            description TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ensure_column(conn, "operation_logs", "operation_batch_id", "TEXT")
    ensure_column(conn, "operation_logs", "account_id", "INTEGER REFERENCES checking_accounts(id) ON DELETE SET NULL")
    ensure_column(conn, "operation_logs", "credit_card_id", "INTEGER REFERENCES credit_cards(id) ON DELETE SET NULL")


def ensure_ai_settings(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_ai_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
            provider TEXT NOT NULL DEFAULT 'custom' CHECK (provider IN ('openai', 'anthropic', 'google', 'custom', 'local')),
            base_url TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            auth_type TEXT NOT NULL DEFAULT 'bearer' CHECK (auth_type IN ('none', 'bearer')),
            timeout_seconds INTEGER NOT NULL DEFAULT 10 CHECK (timeout_seconds BETWEEN 1 AND 60),
            temperature_micros INTEGER NOT NULL DEFAULT 200000 CHECK (temperature_micros BETWEEN 0 AND 2000000),
            max_tokens INTEGER NOT NULL DEFAULT 700 CHECK (max_tokens BETWEEN 1 AND 4000),
            secret_config_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id)
        )
        """
    )
    ensure_column(conn, "user_ai_settings", "enabled", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "user_ai_settings", "provider", "TEXT NOT NULL DEFAULT 'custom'")
    ensure_column(conn, "user_ai_settings", "base_url", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "user_ai_settings", "model", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "user_ai_settings", "auth_type", "TEXT NOT NULL DEFAULT 'bearer'")
    ensure_column(conn, "user_ai_settings", "timeout_seconds", "INTEGER NOT NULL DEFAULT 10")
    ensure_column(conn, "user_ai_settings", "temperature_micros", "INTEGER NOT NULL DEFAULT 200000")
    ensure_column(conn, "user_ai_settings", "max_tokens", "INTEGER NOT NULL DEFAULT 700")
    ensure_column(conn, "user_ai_settings", "secret_config_path", "TEXT NOT NULL DEFAULT ''")


def ensure_secure_configs(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS secure_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            config_type TEXT NOT NULL CHECK (config_type IN ('email', 'ai', 'mais_retorno')),
            payload_enc TEXT NOT NULL,
            source_path TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, config_type)
        )
        """
    )
    ensure_column(conn, "secure_configs", "source_path", "TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_secure_configs_user_type
        ON secure_configs (user_id, config_type)
        """
    )


def ensure_consultor_schema(conn: sqlite3.Connection) -> None:
    # spec: consultor/consultor v2.0 - criterio 23
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consultor_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            consultor_enabled INTEGER NOT NULL DEFAULT 0 CHECK (consultor_enabled IN (0, 1)),
            investor_profile TEXT NOT NULL DEFAULT 'moderado' CHECK (investor_profile IN ('conservador', 'moderado', 'arrojado')),
            data_access_consent INTEGER NOT NULL DEFAULT 0 CHECK (data_access_consent IN (0, 1)),
            consented_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id)
        )
        """
    )
    ensure_column(conn, "consultor_settings", "consultor_enabled", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "consultor_settings", "investor_profile", "TEXT NOT NULL DEFAULT 'moderado'")
    ensure_column(conn, "consultor_settings", "data_access_consent", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(conn, "consultor_settings", "consented_at", "TEXT")
    ensure_column(conn, "consultor_settings", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "consultor_settings", "updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_consultor_settings_user
        ON consultor_settings (user_id)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consultor_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            analysis_id TEXT NOT NULL,
            period_window TEXT CHECK (period_window IS NULL OR period_window IN ('3m', '6m', '12m', 'ytd')),
            analysis_output TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_date TEXT NOT NULL DEFAULT (date('now'))
        )
        """
    )
    ensure_column(conn, "consultor_analyses", "analysis_id", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "consultor_analyses", "period_window", "TEXT")
    ensure_column(conn, "consultor_analyses", "analysis_output", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "consultor_analyses", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "consultor_analyses", "created_date", "TEXT NOT NULL DEFAULT ''")
    conn.execute(
        """
        UPDATE consultor_analyses
        SET created_date = substr(created_at, 1, 10)
        WHERE created_date = ''
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_created
        ON consultor_analyses (user_id, created_at DESC, id DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_day
        ON consultor_analyses (user_id, created_date)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_analysis_created
        ON consultor_analyses (user_id, analysis_id, created_at DESC)
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consultor_perfil_complementar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            payload_enc TEXT NOT NULL,
            schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id)
        )
        """
    )
    ensure_column(conn, "consultor_perfil_complementar", "payload_enc", "TEXT NOT NULL DEFAULT ''")
    ensure_column(conn, "consultor_perfil_complementar", "schema_version", "INTEGER NOT NULL DEFAULT 1")
    ensure_column(conn, "consultor_perfil_complementar", "atualizado_em", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "consultor_perfil_complementar", "created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    ensure_column(conn, "consultor_perfil_complementar", "updated_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_consultor_perfil_complementar_user
        ON consultor_perfil_complementar (user_id)
        """
    )


def ensure_notification_reads(conn: sqlite3.Connection) -> None:
    # spec: cockpit/alertas-cockpit v1.1 — critério 11
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_reads (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            notification_id TEXT NOT NULL,
            seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, notification_id)
        )
        """
    )


def ensure_performance_indexes(conn: sqlite3.Connection) -> None:
    for statement in PERFORMANCE_INDEXES:
        conn.execute(statement)
