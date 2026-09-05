from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 20000


AUTH_SCHEMA_SQL = """
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
"""


ACCOUNTS_SCHEMA_SQL = """
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
"""


CARDS_SCHEMA_SQL = """
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
    normalized_description TEXT,
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

CREATE TABLE IF NOT EXISTS credit_card_transaction_tags (
    credit_card_transaction_id INTEGER NOT NULL REFERENCES credit_card_transactions(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (credit_card_transaction_id, tag_id)
);
"""


CATEGORIES_SCHEMA_SQL = """
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
"""


TRANSACTIONS_SCHEMA_SQL = """
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
    normalized_description TEXT,
    reconciled_at TEXT,
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
"""


PORTFOLIO_SCHEMA_SQL = """
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

CREATE TABLE IF NOT EXISTS investment_monthly_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    snapshot_month TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    account_id INTEGER NOT NULL REFERENCES checking_accounts(id) ON DELETE CASCADE,
    currency TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'other',
    asset_identifier TEXT NOT NULL DEFAULT '',
    asset_name TEXT NOT NULL DEFAULT '',
    quantity_micros INTEGER NOT NULL DEFAULT 0 CHECK (quantity_micros >= 0),
    unit_price_cents INTEGER NOT NULL DEFAULT 0 CHECK (unit_price_cents >= 0),
    market_value_cents INTEGER NOT NULL DEFAULT 0 CHECK (market_value_cents >= 0),
    cost_basis_cents INTEGER NOT NULL DEFAULT 0 CHECK (cost_basis_cents >= 0),
    contribution_cents INTEGER NOT NULL DEFAULT 0,
    redemption_cents INTEGER NOT NULL DEFAULT 0,
    dividend_cents INTEGER NOT NULL DEFAULT 0,
    quote_source TEXT NOT NULL DEFAULT 'not_available',
    valuation_status TEXT NOT NULL DEFAULT 'approximate' CHECK (valuation_status IN ('observed', 'approximate')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, snapshot_month, account_id, currency, asset_type, asset_identifier, asset_name)
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
"""


LIMITS_SCHEMA_SQL = """
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
"""


CACHE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS quote_cache (
    cache_key TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


MARKET_CALENDAR_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS market_holidays (
    holiday_date TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'ANBIMA'
);

CREATE TABLE IF NOT EXISTS market_calendar_state (
    source TEXT PRIMARY KEY,
    imported_at TEXT,
    last_attempt_at TEXT,
    checked_year INTEGER,
    content_sha256 TEXT,
    row_count INTEGER NOT NULL DEFAULT 0 CHECK (row_count >= 0)
);
"""


AUDIT_SCHEMA_SQL = """
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
"""


CONFIG_SCHEMA_SQL = """
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
"""


CONSULTOR_TABLES_SQL = """
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
"""


CONSULTOR_INDEXES_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_consultor_settings_user
ON consultor_settings (user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_consultor_perfil_complementar_user
ON consultor_perfil_complementar (user_id);
"""


NOTIFICATIONS_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notification_reads (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_id TEXT NOT NULL,
    seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, notification_id)
);
"""


INDEX_SCHEMA_SQL = """
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
        "CREATE INDEX IF NOT EXISTS idx_investment_monthly_snapshots_user_month "
        "ON investment_monthly_snapshots (user_id, snapshot_month, currency)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_investment_monthly_snapshots_user_asset "
        "ON investment_monthly_snapshots (user_id, account_id, asset_type, asset_identifier)"
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


TABLES_BLOCKS = (
    AUTH_SCHEMA_SQL,
    ACCOUNTS_SCHEMA_SQL,
    CARDS_SCHEMA_SQL,
    CATEGORIES_SCHEMA_SQL,
    TRANSACTIONS_SCHEMA_SQL,
    PORTFOLIO_SCHEMA_SQL,
    LIMITS_SCHEMA_SQL,
    CACHE_SCHEMA_SQL,
    MARKET_CALENDAR_SCHEMA_SQL,
    AUDIT_SCHEMA_SQL,
    CONFIG_SCHEMA_SQL,
    CONSULTOR_TABLES_SQL,
    NOTIFICATIONS_SCHEMA_SQL,
)


INDEXES_BLOCKS = (
    CONSULTOR_INDEXES_SQL,
    INDEX_SCHEMA_SQL,
)


BASELINE_TABLES_SQL = "\n".join(TABLES_BLOCKS)
BASELINE_INDEXES_SQL = "\n".join(INDEXES_BLOCKS)
BASELINE_SCHEMA_SQL = BASELINE_TABLES_SQL + "\n" + BASELINE_INDEXES_SQL


def create_baseline_tables(conn: sqlite3.Connection) -> None:
    """Apply only the table and constraint definitions of the v2 baseline.

    Indexes that may depend on columns added during legacy compatibility
    normalization are created separately by create_baseline_indexes().
    """
    conn.executescript(BASELINE_TABLES_SQL)


def create_baseline_indexes(conn: sqlite3.Connection) -> None:
    """Apply all baseline indexes, including performance indexes."""
    conn.executescript(BASELINE_INDEXES_SQL)
    for statement in PERFORMANCE_INDEXES:
        conn.execute(statement)


def create_baseline_schema(conn: sqlite3.Connection) -> None:
    """Apply the canonical v2 baseline schema to an empty connection."""
    create_baseline_tables(conn)
    create_baseline_indexes(conn)
