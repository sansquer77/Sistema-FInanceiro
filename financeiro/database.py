from __future__ import annotations

import os
import hashlib
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("SISTEMA_FINANCEIRO_DATA_DIR", ROOT / "data"))
DB_PATH = DATA_DIR / "finance.db"
SQLITE_BUSY_TIMEOUT_MS = 5000
V2_SCHEMA_VERSION = 20000
LEGACY_BACKUP_NAME = "finance-v1.bkp"
MIGRATION_WORK_NAME = ".finance-v2-migration-work.db"
MIGRATION_CANDIDATE_NAME = ".finance-v2-migration-candidate.db"
QUOTE_CACHE_STALE_RETENTION_DAYS = 30
QUOTE_CACHE_MAX_ENTRIES = 1500
QUOTE_CACHE_MAX_ENTRIES_PER_PROVIDER = 1000
QUOTE_CACHE_VACUUM_MIN_FREE_BYTES = 1024 * 1024
QUOTE_CACHE_VACUUM_MIN_FREE_RATIO = 0.20
PERFORMANCE_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, date)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions (account_id)",
    "CREATE INDEX IF NOT EXISTS idx_transactions_user_account_date ON transactions (user_id, account_id, date)",
    (
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_destination_date "
        "ON transactions (user_id, destination_account_id, date)"
    ),
    "CREATE INDEX IF NOT EXISTS idx_transactions_user_series_date ON transactions (user_id, series_id, date)",
    (
        "CREATE INDEX IF NOT EXISTS idx_transactions_user_type_normalized_description "
        "ON transactions (user_id, type, normalized_description)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_credit_card_transactions_user_card_invoice_date "
        "ON credit_card_transactions (user_id, credit_card_id, invoice_month, date)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_credit_card_transactions_user_invoice_date "
        "ON credit_card_transactions (user_id, invoice_month, date)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_credit_card_transactions_user_series_invoice_date "
        "ON credit_card_transactions (user_id, series_id, invoice_month, date)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_card_transactions_user_type_normalized_description "
        "ON credit_card_transactions (user_id, type, normalized_description)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_credit_card_payments_user_card_invoice "
        "ON credit_card_payments (user_id, credit_card_id, invoice_month)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_credit_card_payments_user_date "
        "ON credit_card_payments (user_id, payment_date)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_operations_user "
        "ON investment_operations (user_id, account_id, asset_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_opening_positions_user "
        "ON investment_opening_positions (user_id, account_id, asset_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_redemptions_source "
        "ON investment_redemptions (user_id, source_type, source_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_redemption_summaries_user_date "
        "ON investment_redemption_summaries (user_id, date DESC, id DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_value_overrides_user "
        "ON investment_value_overrides (user_id, account_id, asset_type)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_closed_positions_user "
        "ON investment_closed_positions (user_id, account_id, asset_type, closed_at)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_closed_positions_user_closed "
        "ON investment_closed_positions (user_id, closed_at DESC, id DESC)"
    ),
    "CREATE INDEX IF NOT EXISTS idx_quote_cache_expires_at ON quote_cache (expires_at)",
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_created "
        "ON operation_logs (user_id, created_at DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_module_created "
        "ON operation_logs (user_id, module, created_at DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_type_created "
        "ON operation_logs (user_id, operation_type, created_at DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_account_created "
        "ON operation_logs (user_id, account_id, created_at DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_card_created "
        "ON operation_logs (user_id, credit_card_id, created_at DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_operation_logs_user_batch "
        "ON operation_logs (user_id, operation_batch_id)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_created "
        "ON consultor_analyses (user_id, created_at DESC, id DESC)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_day "
        "ON consultor_analyses (user_id, created_date)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_analysis_created "
        "ON consultor_analyses (user_id, analysis_id, created_at DESC)"
    ),
)


class ManagedConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


class DatabaseMigrationError(RuntimeError):
    pass


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000, factory=ManagedConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def begin_immediate(conn: sqlite3.Connection) -> None:
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DB_PATH.exists():
        _initialize_schema(DB_PATH)
        _set_schema_version(DB_PATH, V2_SCHEMA_VERSION)
        maintain_quote_cache(DB_PATH)
        return

    schema_version = _read_schema_version(DB_PATH)
    if schema_version == V2_SCHEMA_VERSION:
        maintain_quote_cache(DB_PATH)
        return
    if schema_version != 0:
        raise DatabaseMigrationError(
            f"Versao de banco nao suportada: {schema_version}. "
            f"Esta versao do app aceita o schema legado 1.x ou {V2_SCHEMA_VERSION}."
        )
    _migrate_legacy_database()
    maintain_quote_cache(DB_PATH)


def maintain_quote_cache(db_path: Path | None = None, now: datetime | None = None) -> dict:
    """Prune regenerable quote payloads without touching financial records."""
    path = Path(db_path) if db_path is not None else DB_PATH
    reference_time = now or datetime.now()
    stale_cutoff = reference_time - timedelta(days=QUOTE_CACHE_STALE_RETENTION_DAYS)
    result = {"deleted": 0, "vacuumed": False, "free_bytes": 0, "free_ratio": 0.0}
    try:
        with get_connection(path) as conn:
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'quote_cache'"
            ).fetchone()
            if not table_exists:
                return result
            before = int(conn.execute("SELECT COUNT(*) FROM quote_cache").fetchone()[0])
            conn.execute(
                "DELETE FROM quote_cache WHERE datetime(expires_at) < datetime(?)",
                (stale_cutoff.isoformat(),),
            )
            _trim_quote_cache_per_provider(conn, reference_time)
            _trim_quote_cache_total(conn, reference_time)
            after = int(conn.execute("SELECT COUNT(*) FROM quote_cache").fetchone()[0])
            result["deleted"] = before - after

        if result["deleted"] <= 0:
            return result

        with closing(sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            page_size = int(conn.execute("PRAGMA page_size").fetchone()[0])
            page_count = int(conn.execute("PRAGMA page_count").fetchone()[0])
            free_pages = int(conn.execute("PRAGMA freelist_count").fetchone()[0])
        result["free_bytes"] = free_pages * page_size
        result["free_ratio"] = free_pages / page_count if page_count else 0.0
        if (
            result["free_bytes"] >= QUOTE_CACHE_VACUUM_MIN_FREE_BYTES
            and result["free_ratio"] >= QUOTE_CACHE_VACUUM_MIN_FREE_RATIO
        ):
            with closing(sqlite3.connect(path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
                conn.execute("VACUUM")
            result["vacuumed"] = True
    except sqlite3.DatabaseError:
        # spec: persistencia/manutencao-cache-cotacoes v1.0 — critério 8
        # Cache é regenerável e sua manutenção nunca bloqueia a abertura do app.
        return result
    return result


def _trim_quote_cache_per_provider(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute(
        """
        DELETE FROM quote_cache
        WHERE cache_key IN (
            SELECT cache_key
            FROM (
                SELECT
                    cache_key,
                    ROW_NUMBER() OVER (
                        PARTITION BY CASE
                            WHEN instr(cache_key, ':') > 0
                                THEN substr(cache_key, 1, instr(cache_key, ':') - 1)
                            ELSE cache_key
                        END
                        ORDER BY
                            CASE WHEN datetime(expires_at) > datetime(?) THEN 0 ELSE 1 END,
                            datetime(updated_at) DESC,
                            cache_key DESC
                    ) AS position
                FROM quote_cache
            )
            WHERE position > ?
        )
        """,
        (now.isoformat(), QUOTE_CACHE_MAX_ENTRIES_PER_PROVIDER),
    )


def _trim_quote_cache_total(conn: sqlite3.Connection, now: datetime) -> None:
    conn.execute(
        """
        DELETE FROM quote_cache
        WHERE cache_key IN (
            SELECT cache_key
            FROM quote_cache
            ORDER BY
                CASE WHEN datetime(expires_at) > datetime(?) THEN 0 ELSE 1 END,
                datetime(updated_at) DESC,
                cache_key DESC
            LIMIT -1 OFFSET ?
        )
        """,
        (now.isoformat(), QUOTE_CACHE_MAX_ENTRIES),
    )


def _initialize_schema(db_path: Path) -> None:
    with get_connection(db_path) as conn:
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
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
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
                exchange_rate_micros INTEGER NOT NULL DEFAULT 1000000 CHECK (exchange_rate_micros > 0),
                amount_brl_cents INTEGER NOT NULL DEFAULT 0 CHECK (amount_brl_cents >= 0),
                date TEXT NOT NULL,
                invoice_month TEXT NOT NULL,
                series_id TEXT,
                series_kind TEXT NOT NULL DEFAULT 'single',
                installment_index INTEGER,
                installment_count INTEGER,
                recurrence_frequency TEXT,
                use_average INTEGER NOT NULL DEFAULT 0 CHECK (use_average IN (0, 1)),
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
                use_average INTEGER NOT NULL DEFAULT 0 CHECK (use_average IN (0, 1)),
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
                emergency_reserve_eligible INTEGER NOT NULL DEFAULT 0 CHECK (emergency_reserve_eligible IN (0, 1)),
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
                emergency_reserve_eligible INTEGER NOT NULL DEFAULT 0 CHECK (emergency_reserve_eligible IN (0, 1)),
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

            CREATE TABLE IF NOT EXISTS investment_redemption_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                transaction_id INTEGER NOT NULL UNIQUE REFERENCES transactions(id) ON DELETE CASCADE,
                account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
                currency TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                asset_identifier TEXT,
                asset_name TEXT,
                date TEXT NOT NULL,
                redeemed_quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (redeemed_quantity_micros >= 0),
                gross_value_cents INTEGER NOT NULL CHECK (gross_value_cents > 0),
                fees_cents INTEGER NOT NULL DEFAULT 0 CHECK (fees_cents >= 0),
                net_value_cents INTEGER NOT NULL CHECK (net_value_cents > 0),
                redeemed_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (redeemed_cost_cents >= 0),
                realized_result_cents INTEGER NOT NULL DEFAULT 0,
                remaining_quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (remaining_quantity_micros >= 0),
                remaining_cost_cents INTEGER NOT NULL DEFAULT 0 CHECK (remaining_cost_cents >= 0),
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

            CREATE TABLE IF NOT EXISTS portfolio_allocation_goals (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                asset_type TEXT NOT NULL,
                target_percent_micros INTEGER NOT NULL CHECK (target_percent_micros >= 0 AND target_percent_micros <= 100000000),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, asset_type)
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
            );

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
            );

            CREATE TABLE IF NOT EXISTS secure_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                config_type TEXT NOT NULL CHECK (config_type IN ('email', 'ai', 'mais_retorno')),
                payload_enc TEXT NOT NULL,
                source_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, config_type)
            );

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
            );

            CREATE TABLE IF NOT EXISTS consultor_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                analysis_id TEXT NOT NULL,
                period_window TEXT CHECK (period_window IS NULL OR period_window IN ('3m', '6m', '12m', 'ytd')),
                analysis_output TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_date TEXT NOT NULL DEFAULT (date('now'))
            );

            CREATE TABLE IF NOT EXISTS consultor_perfil_complementar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                payload_enc TEXT NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 1 CHECK (schema_version >= 1),
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id)
            );

            CREATE TABLE IF NOT EXISTS notification_reads (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                notification_id TEXT NOT NULL,
                seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, notification_id)
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

            CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_created
            ON consultor_analyses (user_id, created_at DESC, id DESC);

            CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_day
            ON consultor_analyses (user_id, created_date);

            CREATE INDEX IF NOT EXISTS idx_consultor_analyses_user_analysis_created
            ON consultor_analyses (user_id, analysis_id, created_at DESC);
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
        migrate_transaction_type_constraint(conn)
        migrate_transaction_tags(conn)
        migrate_transaction_brl_values(conn)
        backfill_normalized_descriptions(conn)
        ensure_performance_indexes(conn)


def _read_schema_version(db_path: Path) -> int:
    try:
        # spec: migracao-dados/migracao-banco-v2 v1.1 — critério 12
        # A URI mode=ro falha em algumas combinações do SQLite do macOS quando
        # o caminho contém espaços. A conexão normal é aberta sem executar
        # escrita e também consegue consultar bancos configurados em WAL.
        with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise DatabaseMigrationError("Nao foi possivel identificar a versao do banco de dados.") from exc


def _set_schema_version(db_path: Path, version: int) -> None:
    with get_connection(db_path) as conn:
        conn.execute(f"PRAGMA user_version = {int(version)}")


def _migrate_legacy_database() -> None:
    # spec: migracao-dados/migracao-banco-v2 v1.1 — critérios 3, 4, 7, 8 e 11
    backup_path = DB_PATH.with_name(LEGACY_BACKUP_NAME)
    work_path = DB_PATH.with_name(MIGRATION_WORK_NAME)
    candidate_path = DB_PATH.with_name(MIGRATION_CANDIDATE_NAME)
    if backup_path.exists():
        raise DatabaseMigrationError(
            f"A migracao foi bloqueada porque {backup_path.name} ja existe. "
            "O backup legado nunca e sobrescrito automaticamente."
        )

    _remove_migration_artifacts(work_path, candidate_path)
    promoted_legacy = False
    try:
        _checkpoint_database(DB_PATH)
        _copy_database(DB_PATH, work_path)
        _initialize_schema(work_path)
        _set_schema_version(work_path, V2_SCHEMA_VERSION)
        _validate_database(work_path)
        _vacuum_into(work_path, candidate_path)
        _validate_database(candidate_path)
        _validate_table_counts(work_path, candidate_path)

        os.replace(DB_PATH, backup_path)
        promoted_legacy = True
        try:
            os.replace(candidate_path, DB_PATH)
        except OSError:
            os.replace(backup_path, DB_PATH)
            promoted_legacy = False
            raise
    except (OSError, sqlite3.DatabaseError, DatabaseMigrationError) as exc:
        if promoted_legacy and backup_path.exists() and not DB_PATH.exists():
            os.replace(backup_path, DB_PATH)
        if isinstance(exc, DatabaseMigrationError):
            raise
        raise DatabaseMigrationError(
            "Nao foi possivel migrar o banco legado. O arquivo original foi preservado."
        ) from exc
    finally:
        _remove_migration_artifacts(work_path, candidate_path)


def _checkpoint_database(db_path: Path) -> None:
    with closing(sqlite3.connect(db_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if result and int(result[0]) != 0:
            raise DatabaseMigrationError("O banco esta ocupado e nao pode ser migrado agora.")


def _copy_database(source_path: Path, destination_path: Path) -> None:
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as source:
        with closing(sqlite3.connect(destination_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as destination:
            source.backup(destination)


def _vacuum_into(source_path: Path, destination_path: Path) -> None:
    escaped_path = str(destination_path).replace("'", "''")
    with closing(sqlite3.connect(source_path, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        conn.execute(f"VACUUM INTO '{escaped_path}'")


def _validate_database(db_path: Path) -> None:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=SQLITE_BUSY_TIMEOUT_MS / 1000)) as conn:
        integrity_rows = [row[0] for row in conn.execute("PRAGMA integrity_check")]
        if integrity_rows != ["ok"]:
            raise DatabaseMigrationError("A verificacao de integridade do banco candidato falhou.")
        foreign_key_rows = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_rows:
            raise DatabaseMigrationError("O banco candidato possui referencias invalidas.")
        schema_version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if schema_version != V2_SCHEMA_VERSION:
            raise DatabaseMigrationError("O banco candidato nao possui a versao de schema esperada.")


def _validate_table_counts(source_path: Path, destination_path: Path) -> None:
    source_uri = source_path.resolve().as_uri() + "?mode=ro"
    destination_uri = destination_path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(source_uri, uri=True)) as source, closing(
        sqlite3.connect(destination_uri, uri=True)
    ) as destination:
        source_tables = _user_table_names(source)
        destination_tables = _user_table_names(destination)
        if source_tables != destination_tables:
            raise DatabaseMigrationError("As tabelas do banco candidato divergem da origem normalizada.")
        for table_name in source_tables:
            quoted_name = table_name.replace('"', '""')
            source_count = source.execute(f'SELECT COUNT(*) FROM "{quoted_name}"').fetchone()[0]
            destination_count = destination.execute(f'SELECT COUNT(*) FROM "{quoted_name}"').fetchone()[0]
            if source_count != destination_count:
                raise DatabaseMigrationError(
                    f"A contagem da tabela {table_name} diverge no banco candidato."
                )


def _user_table_names(conn: sqlite3.Connection) -> tuple[str, ...]:
    return tuple(
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
    )


def _remove_migration_artifacts(*paths: Path) -> None:
    for path in paths:
        for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
            try:
                candidate.unlink()
            except FileNotFoundError:
                pass


def ensure_performance_indexes(conn: sqlite3.Connection) -> None:
    for statement in PERFORMANCE_INDEXES:
        conn.execute(statement)


def backfill_normalized_descriptions(conn: sqlite3.Connection) -> None:
    from financeiro.classification_suggestions import normalize_description

    for table in ("transactions", "credit_card_transactions"):
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
    # spec: cockpit/alertas-cockpit v0.8 — critério 11
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


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}


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
