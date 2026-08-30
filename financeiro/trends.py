from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from http import HTTPStatus

from financeiro.database import get_connection
from financeiro.simulations import account_projected_balance_until, month_end_date
from financeiro.calendar_rules import days_in_month

MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")

# spec: tendencias-saude-financeira v2.22 — critérios 8, 9 e 13
POINT_INCOME_CATEGORIES = {
    "Freelance e Autônomo",
    "Outras Receitas",
}

POINT_INCOME_SUBCATEGORIES = {
    "Bônus / PLR",
    "Férias",
    "Décimo Terceiro (13º)",
    "Restituição de Imposto de Renda",
    "Venda de Bens (Móveis, Carro, etc.)",
    "Prêmios / Sorteios / Loterias",
    "Presentes / Doações Recebidas",
    "Reembolsos Corporativos",
    "Reembolso médico",
    "Comissões",
    "Consultorias",
    "Projetos / Serviços Prestados",
    "Estornos",
}

POINT_EXPENSE_SUBCATEGORIES = {
    "Viagens, Passagens e Hospedagens (Férias)",
    "Imprevistos e Emergências Domésticas",
    "Manutenção, Reparos e Reformas",
}

# spec: tendencias-saude-financeira v2.22 — critério 29
SUBSCRIPTIONS_CATEGORY = "Assinaturas e Serviços"

# spec: tendencias-saude-financeira v2.22 — critério 8 (reforço por palavras-chave)
POINT_EVENT_KEYWORDS = [
    "plr",
    "bonus",
    "ferias",
    "13",
    "decimo terceiro",
    "restituicao",
]

MONTHLY_RECURRENCE_FREQUENCIES = {"monthly"}


class TrendsError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def calculate_trends(user_id: int, month: object | None = None, currency: str = "BRL") -> dict:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 1, 3, 4, 5, 6, 7, 8, 9, 13,
          22, 25, 26, 27, 28 e 29
    Núcleo local de cálculo de tendências: série mensal, Budget x Realizado,
    achados estruturados, eventos pontuais, assinaturas/serviços recorrentes e confiança.
    """
    normalized_month = normalize_month(month)
    with get_connection() as conn:
        series = build_monthly_series(conn, user_id, normalized_month)
        month_summary = series.get(normalized_month, {"income_cents": 0, "expense_cents": 0})
        available_months = sorted([m for m, values in series.items() if m <= normalized_month and (values["income_cents"] > 0 or values["expense_cents"] > 0)])
        previous_months = [m for m in available_months if m < normalized_month]
        confidence = determine_confidence(previous_months)
        comparison = build_comparison_base(series, previous_months, normalized_month, confidence)
        budget_actual = build_budget_vs_actual(conn, user_id, normalized_month)
        point_events = detect_point_events(conn, user_id, normalized_month)
        acceleration = detect_installment_acceleration(conn, user_id, normalized_month)
        subscriptions = detect_recurring_subscriptions(conn, user_id, normalized_month)
        cash_opportunity = detect_cash_opportunity(conn, user_id, normalized_month)
        findings = build_findings(
            normalized_month,
            month_summary,
            comparison,
            budget_actual,
            point_events,
            acceleration,
            subscriptions,
            cash_opportunity,
            previous_months,
            confidence,
        )
        multi_currency = detect_multiple_currencies(conn, user_id, normalized_month)

    summary = build_local_summary(
        normalized_month,
        month_summary,
        comparison,
        findings,
        point_events,
        acceleration,
        subscriptions,
        cash_opportunity,
        confidence,
        multi_currency,
    )

    return {
        "month": normalized_month,
        "currency": currency,
        "base_currency": currency,
        "multi_currency_warning": multi_currency,
        "historico_meses_disponiveis": len(previous_months),
        "confianca": confidence,
        "receitas_mes_cents": month_summary["income_cents"],
        "despesas_mes_cents": month_summary["expense_cents"],
        "saldo_mes_cents": month_summary["income_cents"] - month_summary["expense_cents"],
        "receitas_base_comparacao_cents": comparison["income_cents"],
        "despesas_base_comparacao_cents": comparison["expense_cents"],
        "serie_mensal": [
            {
                "month": m,
                "income_cents": values["income_cents"],
                "expense_cents": values["expense_cents"],
                "balance_cents": values["income_cents"] - values["expense_cents"],
            }
            for m, values in sorted(series.items())
        ],
        "orcamento_realizado": budget_actual,
        "achados": findings,
        "eventos_pontuais": point_events,
        "antecipacao_parcelas": acceleration,
        "assinaturas_e_servicos": subscriptions,
        "oportunidade_caixa": cash_opportunity,
        "resumo_local": summary,
        "resumo_ia": None,
        "ia_ativa": False,
        "ia_fornecedor": None,
    }


def normalize_month(month: object | None) -> str:
    raw = str(month or date.today().strftime("%Y-%m")).strip()
    if not MONTH_PATTERN.fullmatch(raw):
        raise TrendsError("Informe o mes no formato AAAA-MM.")
    year, month_number = map(int, raw.split("-"))
    if month_number < 1 or month_number > 12:
        raise TrendsError("Informe um mes valido.")
    return f"{year:04d}-{month_number:02d}"


def build_monthly_series(conn, user_id: int, month: str) -> dict[str, dict[str, int]]:
    """
    spec: tendencias-saude-financeira v2.22 — critério 3
    Constrói série mensal de receitas e despesas analíticas.
    Conta-corrente usa o mês da data; cartão usa invoice_month.
    Pagamentos de fatura são excluídos das despesas analíticas.
    """
    months_window = trailing_months(month, 12)
    series = {m: {"income_cents": 0, "expense_cents": 0} for m in months_window}
    start_date = f"{months_window[0]}-01"
    end_date = month_bounds(months_window[-1])[1]

    # spec: relatorios/relatorios v2.17 — critério 6
    # (pagamento de fatura em conta-corrente fica fora das despesas analíticas)
    account_rows = conn.execute(
        """
        SELECT
            substr(transactions.date, 1, 7) AS period_month,
            transactions.type,
            COALESCE(SUM(transactions.amount_brl_cents), 0) AS total
        FROM transactions
        LEFT JOIN credit_card_payments
            ON credit_card_payments.transaction_id = transactions.id
            AND credit_card_payments.user_id = transactions.user_id
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.type IN ('income', 'expense')
            AND transactions.date >= ?
            AND transactions.date <= ?
            AND credit_card_payments.id IS NULL
        GROUP BY substr(transactions.date, 1, 7), transactions.type
        """,
        (user_id, start_date, end_date),
    ).fetchall()

    # spec: tendencias-saude-financeira v2.22 — critério 26
    # (lançamentos de cartão entram pela competência da fatura)
    card_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.invoice_month AS period_month,
            credit_card_transactions.type,
            COALESCE(SUM(credit_card_transactions.amount_brl_cents), 0) AS total
        FROM credit_card_transactions
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.type IN ('income', 'expense')
            AND credit_card_transactions.invoice_month IN ({})
        GROUP BY credit_card_transactions.invoice_month, credit_card_transactions.type
        """.format(",".join("?" for _ in months_window)),
        (user_id, *months_window),
    ).fetchall()

    for row in [*account_rows, *card_rows]:
        period = row["period_month"]
        if period not in series:
            continue
        if row["type"] == "income":
            series[period]["income_cents"] += int(row["total"] or 0)
        else:
            series[period]["expense_cents"] += int(row["total"] or 0)

    return series


def build_comparison_base(
    series: dict[str, dict[str, int]],
    previous_months: list[str],
    current_month: str,
    confidence: str,
) -> dict[str, int]:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 6, 22 e 95/96
    Comparação base: média móvel de 3 meses quando histórico suficiente;
    média disponível quando intermediário; mês anterior (ou zero) quando curto.
    """
    if not previous_months:
        return {"income_cents": 0, "expense_cents": 0, "tipo": "sem_historico"}

    if confidence == "alta" and len(previous_months) >= 3:
        window = previous_months[-3:]
        return {
            "income_cents": average_cents([series[m]["income_cents"] for m in window]),
            "expense_cents": average_cents([series[m]["expense_cents"] for m in window]),
            "tipo": "media_3m",
        }

    if len(previous_months) >= 2:
        return {
            "income_cents": average_cents([series[m]["income_cents"] for m in previous_months]),
            "expense_cents": average_cents([series[m]["expense_cents"] for m in previous_months]),
            "tipo": "media_disponivel",
        }

    last = previous_months[-1]
    return {
        "income_cents": series[last]["income_cents"],
        "expense_cents": series[last]["expense_cents"],
        "tipo": "mes_anterior",
    }


def build_budget_vs_actual(conn, user_id: int, month: str) -> list[dict]:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 4 e 5
    Reaproveita limites vigentes do mês e calcula consumo real por
    categoria/subcategoria.
    """
    limits = fetch_effective_limits(conn, user_id, month)
    if not limits:
        return []

    expenses = fetch_expenses_by_limit_key(conn, user_id, month)
    rows = []
    for limit in limits:
        category_id = limit["category_id"]
        subcategory_id = limit["subcategory_id"]
        category_name = limit["category_name"]
        subcategory_name = limit.get("subcategory_name")
        limit_cents = int(limit["limit_amount_cents"] or 0)

        if subcategory_id:
            actual = expenses.get((category_id, subcategory_id), 0)
        else:
            actual = sum(
                value
                for (expense_category_id, _), value in expenses.items()
                if expense_category_id == category_id
            )

        difference = actual - limit_cents
        used_pct = percent_of(actual, limit_cents)
        state = budget_state(used_pct)
        rows.append({
            "category_id": category_id,
            "subcategory_id": subcategory_id,
            "category_name": category_name,
            "subcategory_name": subcategory_name,
            "limite_cents": limit_cents,
            "realizado_cents": actual,
            "diferenca_cents": difference,
            "percentual_usado": used_pct,
            "estado": state,
        })

    rows.sort(key=lambda row: (row["category_name"] or "", row["subcategory_name"] or ""))
    return rows


def fetch_effective_limits(conn, user_id: int, month: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            spending_limits.*,
            categories.name AS category_name,
            subcategories.name AS subcategory_name
        FROM spending_limits
        JOIN categories
            ON categories.id = spending_limits.category_id
            AND categories.user_id = spending_limits.user_id
            AND categories.group_type = 'expense'
        LEFT JOIN subcategories
            ON subcategories.id = spending_limits.subcategory_id
            AND subcategories.user_id = spending_limits.user_id
        WHERE spending_limits.user_id = ?
            AND spending_limits.month <= ?
            AND NOT EXISTS (
                SELECT 1
                FROM spending_limits newer_limits
                WHERE newer_limits.user_id = spending_limits.user_id
                    AND newer_limits.category_id = spending_limits.category_id
                    AND (
                        newer_limits.subcategory_id = spending_limits.subcategory_id
                        OR (
                            newer_limits.subcategory_id IS NULL
                            AND spending_limits.subcategory_id IS NULL
                        )
                    )
                    AND newer_limits.month <= ?
                    AND (
                        newer_limits.month > spending_limits.month
                        OR (
                            newer_limits.month = spending_limits.month
                            AND newer_limits.id > spending_limits.id
                        )
                    )
            )
        ORDER BY categories.name COLLATE NOCASE, subcategories.name COLLATE NOCASE
        """,
        (user_id, month, month),
    ).fetchall()
    return [dict(row) for row in rows]


def fetch_expenses_by_limit_key(conn, user_id: int, month: str) -> dict[tuple[int, int | None], int]:
    start, end = month_bounds(month)
    expenses: dict[tuple[int, int | None], int] = {}

    account_rows = conn.execute(
        """
        SELECT
            transactions.category_id,
            transactions.subcategory_id,
            COALESCE(SUM(transactions.amount_brl_cents), 0) AS total
        FROM transactions
        LEFT JOIN credit_card_payments
            ON credit_card_payments.transaction_id = transactions.id
            AND credit_card_payments.user_id = transactions.user_id
        JOIN categories
            ON categories.id = transactions.category_id
            AND categories.user_id = transactions.user_id
            AND categories.group_type = 'expense'
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND transactions.type = 'expense'
            AND credit_card_payments.id IS NULL
        GROUP BY transactions.category_id, transactions.subcategory_id
        """,
        (user_id, start, end),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.category_id,
            credit_card_transactions.subcategory_id,
            COALESCE(SUM(credit_card_transactions.amount_cents), 0) AS total
        FROM credit_card_transactions
        JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
            AND categories.group_type = 'expense'
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type = 'expense'
        GROUP BY credit_card_transactions.category_id, credit_card_transactions.subcategory_id
        """,
        (user_id, month),
    ).fetchall()

    for row in [*account_rows, *card_rows]:
        key = (int(row["category_id"]), int(row["subcategory_id"]) if row["subcategory_id"] else None)
        expenses[key] = expenses.get(key, 0) + int(row["total"] or 0)

    return expenses


def budget_state(used_pct: float) -> str:
    if used_pct > 100:
        return "Acima do limite"
    if used_pct >= 80:
        return "Atenção"
    return "Dentro do limite"


def detect_cash_opportunity(conn, user_id: int, month: str) -> dict | None:
    planned_expenses_cents = sum(
        int(row.get("limit_amount_cents") or 0)
        for row in fetch_effective_limits(conn, user_id, month)
    )
    if planned_expenses_cents <= 0:
        return None

    accounts = conn.execute(
        """
        SELECT id, currency
        FROM checking_accounts
        WHERE user_id = ?
            AND archived_at IS NULL
            AND account_type IN ('liquidity', 'wallet')
            AND currency = 'BRL'
        """,
        (user_id,),
    ).fetchall()
    projected_balance_cents = sum(
        account_projected_balance_until(conn, user_id, dict(account), month_end_date(month))
        for account in accounts
    )
    if projected_balance_cents < planned_expenses_cents * 2:
        return None

    ratio = projected_balance_cents / planned_expenses_cents
    return {
        "saldo_previsto_fim_mes_cents": projected_balance_cents,
        "despesas_planejadas_cents": planned_expenses_cents,
        "multiplicador": round(ratio, 2),
    }


def detect_point_events(conn, user_id: int, month: str) -> list[dict]:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 8, 9 e 13
    Identifica receitas e despesas candidatas a eventos pontuais usando
    categorias/subcategorias existentes como sinal principal e palavras-chave
    de descrição/tags como reforço.
    """
    events = []
    start, end = month_bounds(month)

    # Receitas em conta-corrente
    account_income_rows = conn.execute(
        """
        SELECT
            transactions.id,
            transactions.description,
            transactions.amount_brl_cents AS amount_cents,
            transactions.series_kind,
            transactions.recurrence_frequency,
            categories.name AS category_name,
            subcategories.name AS subcategory_name,
            GROUP_CONCAT(tags.name, '||') AS tag_names
        FROM transactions
        LEFT JOIN categories
            ON categories.id = transactions.category_id
            AND categories.user_id = transactions.user_id
        LEFT JOIN subcategories
            ON subcategories.id = transactions.subcategory_id
            AND subcategories.user_id = transactions.user_id
        LEFT JOIN transaction_tags
            ON transaction_tags.transaction_id = transactions.id
        LEFT JOIN tags
            ON tags.id = transaction_tags.tag_id
            AND tags.user_id = transactions.user_id
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND transactions.type = 'income'
        GROUP BY transactions.id
        """,
        (user_id, start, end),
    ).fetchall()

    # Despesas em conta-corrente
    account_expense_rows = conn.execute(
        """
        SELECT
            transactions.id,
            transactions.description,
            transactions.amount_brl_cents AS amount_cents,
            categories.name AS category_name,
            subcategories.name AS subcategory_name,
            GROUP_CONCAT(tags.name, '||') AS tag_names
        FROM transactions
        LEFT JOIN categories
            ON categories.id = transactions.category_id
            AND categories.user_id = transactions.user_id
        LEFT JOIN subcategories
            ON subcategories.id = transactions.subcategory_id
            AND subcategories.user_id = transactions.user_id
        LEFT JOIN transaction_tags
            ON transaction_tags.transaction_id = transactions.id
        LEFT JOIN tags
            ON tags.id = transaction_tags.tag_id
            AND tags.user_id = transactions.user_id
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND transactions.type = 'expense'
        GROUP BY transactions.id
        """,
        (user_id, start, end),
    ).fetchall()

    # Cartões
    card_income_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.id,
            credit_card_transactions.description,
            credit_card_transactions.amount_brl_cents AS amount_cents,
            credit_card_transactions.series_kind,
            credit_card_transactions.recurrence_frequency,
            categories.name AS category_name,
            subcategories.name AS subcategory_name,
            GROUP_CONCAT(tags.name, '||') AS tag_names
        FROM credit_card_transactions
        LEFT JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
        LEFT JOIN subcategories
            ON subcategories.id = credit_card_transactions.subcategory_id
            AND subcategories.user_id = credit_card_transactions.user_id
        LEFT JOIN credit_card_transaction_tags
            ON credit_card_transaction_tags.credit_card_transaction_id = credit_card_transactions.id
        LEFT JOIN tags
            ON tags.id = credit_card_transaction_tags.tag_id
            AND tags.user_id = credit_card_transactions.user_id
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type = 'income'
        GROUP BY credit_card_transactions.id
        """,
        (user_id, month),
    ).fetchall()

    card_expense_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.id,
            credit_card_transactions.description,
            credit_card_transactions.amount_brl_cents AS amount_cents,
            categories.name AS category_name,
            subcategories.name AS subcategory_name,
            GROUP_CONCAT(tags.name, '||') AS tag_names
        FROM credit_card_transactions
        LEFT JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
        LEFT JOIN subcategories
            ON subcategories.id = credit_card_transactions.subcategory_id
            AND subcategories.user_id = credit_card_transactions.user_id
        LEFT JOIN credit_card_transaction_tags
            ON credit_card_transaction_tags.credit_card_transaction_id = credit_card_transactions.id
        LEFT JOIN tags
            ON tags.id = credit_card_transaction_tags.tag_id
            AND tags.user_id = credit_card_transactions.user_id
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type = 'expense'
        GROUP BY credit_card_transactions.id
        """,
        (user_id, month),
    ).fetchall()

    for row in account_income_rows:
        event = classify_income_point_event(row)
        if event:
            events.append(event)

    for row in card_income_rows:
        event = classify_income_point_event(row)
        if event:
            events.append(event)

    for row in [*account_expense_rows, *card_expense_rows]:
        event = classify_expense_point_event(row)
        if event:
            events.append(event)

    return events


def classify_income_point_event(row) -> dict | None:
    category = str(row["category_name"] or "").strip()
    subcategory = str(row["subcategory_name"] or "").strip()
    description = str(row["description"] or "").strip()
    tags = str(row["tag_names"] or "").lower()
    series_kind = str(row["series_kind"] or "single").strip()
    recurrence = str(row["recurrence_frequency"] or "").strip().lower()

    is_monthly_recurring = series_kind == "recurring" and recurrence in MONTHLY_RECURRENCE_FREQUENCIES
    if is_monthly_recurring:
        return None

    if category in POINT_INCOME_CATEGORIES:
        return point_event("receita_pontual", "info", category, subcategory, row)

    if subcategory in POINT_INCOME_SUBCATEGORIES:
        return point_event("receita_pontual", "info", category, subcategory, row)

    if keyword_match(description, tags):
        return point_event("receita_pontual", "info", category, subcategory, row)

    return None


def classify_expense_point_event(row) -> dict | None:
    category = str(row["category_name"] or "").strip()
    subcategory = str(row["subcategory_name"] or "").strip()
    description = str(row["description"] or "").strip()
    tags = str(row["tag_names"] or "").lower()

    if subcategory in POINT_EXPENSE_SUBCATEGORIES:
        kind = "ferias" if "Férias" in subcategory else "manutencao_emergencia"
        return point_event(kind, "info", category, subcategory, row)

    if keyword_match(description, tags):
        return point_event("despesa_pontual", "info", category, subcategory, row)

    return None


def point_event(kind: str, severity: str, category: str, subcategory: str, row) -> dict:
    return {
        "tipo": kind,
        "severidade": severity,
        "descricao": str(row["description"] or "").strip(),
        "valor_cents": int(row["amount_cents"] or 0),
        "categoria": category,
        "subcategoria": subcategory or None,
        "motivo": subcategory or category,
    }


def keyword_match(description: str, tags: str) -> bool:
    normalized = f"{description.lower()} {tags}"
    return any(keyword in normalized for keyword in POINT_EVENT_KEYWORDS)


def detect_installment_acceleration(conn, user_id: int, month: str) -> list[dict]:
    """
    spec: tendencias-saude-financeira v2.22 — critério 13
    Detecta antecipações de parcelas registradas no histórico operacional
    como "Lancamento movido para fatura yyyy-mm" e parcelas futuras
    concentradas diretamente na fatura do mês.
    """
    rows = conn.execute(
        """
        SELECT
            operation_logs.id,
            operation_logs.entity_id AS transaction_id,
            operation_logs.description,
            operation_logs.metadata_json,
            operation_logs.created_at,
            credit_card_transactions.description AS transaction_description,
            credit_card_transactions.amount_cents AS transaction_amount_cents
        FROM operation_logs
        LEFT JOIN credit_card_transactions
            ON credit_card_transactions.id = CAST(operation_logs.entity_id AS INTEGER)
            AND credit_card_transactions.user_id = operation_logs.user_id
        WHERE operation_logs.user_id = ?
            AND operation_logs.module = 'cards'
            AND operation_logs.operation_type = 'move'
            AND operation_logs.entity_type = 'credit_card_transaction'
            AND operation_logs.description LIKE ?
        ORDER BY operation_logs.created_at DESC
        """,
        (user_id, f"%movido para fatura {month}%"),
    ).fetchall()

    accelerations = []
    accepted_log_transaction_ids = set()
    for row in rows:
        metadata = safe_parse_metadata(row["metadata_json"])
        previous_month = str(metadata.get("previous_invoice_month") or "").strip()
        target_month = str(metadata.get("target_invoice_month") or metadata.get("invoice_month") or month).strip()
        direction = str(metadata.get("direction") or "").strip()
        is_previous_direction = direction == "previous"
        is_target_before_previous = bool(previous_month and target_month and previous_month > target_month)
        if not (is_previous_direction or is_target_before_previous):
            continue
        amount = int(metadata.get("amount_cents") or row["transaction_amount_cents"] or 0)
        purchase = str(metadata.get("transaction_description") or row["transaction_description"] or "").strip()
        transaction_id = str(metadata.get("transaction_id") or row["transaction_id"] or "").strip()
        if transaction_id:
            accepted_log_transaction_ids.add(transaction_id)
        accelerations.append({
            "tipo": "antecipacao_parcela",
            "severidade": "info",
            "descricao": str(row["description"] or "").strip(),
            "compra": purchase,
            "valor_cents": amount,
            "created_at": str(row["created_at"] or "").strip(),
            "transaction_id": transaction_id,
            "origem": "historico_operacional",
        })

    month_end = month_bounds(month)[1]
    structural_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.id,
            credit_card_transactions.description,
            credit_card_transactions.amount_brl_cents,
            credit_card_transactions.amount_cents,
            credit_card_transactions.date,
            credit_card_transactions.invoice_month,
            credit_card_transactions.series_id,
            credit_card_transactions.installment_index,
            credit_card_transactions.installment_count
        FROM credit_card_transactions
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.type = 'expense'
            AND credit_card_transactions.series_kind = 'installment'
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.date > ?
            AND credit_card_transactions.series_id IS NOT NULL
        ORDER BY credit_card_transactions.series_id, credit_card_transactions.installment_index
        """,
        (user_id, month, month_end),
    ).fetchall()

    for row in structural_rows:
        transaction_id = str(row["id"])
        if transaction_id in accepted_log_transaction_ids:
            continue
        accelerations.append({
            "tipo": "antecipacao_parcela",
            "severidade": "info",
            "descricao": f"Parcela futura concentrada na fatura {month}",
            "compra": str(row["description"] or "").strip(),
            "valor_cents": int(row["amount_brl_cents"] or row["amount_cents"] or 0),
            "created_at": "",
            "transaction_id": transaction_id,
            "origem": "concentracao_parcelas",
        })

    return accelerations


def safe_parse_metadata(value: object) -> dict:
    import json
    try:
        payload = json.loads(str(value or "{}"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def detect_recurring_subscriptions(conn, user_id: int, month: str) -> list[dict]:
    """
    spec: tendencias-saude-financeira v2.22 — critério 29
    Agrega despesas recorrentes mensais da categoria 'Assinaturas e Serviços'
    por subcategoria (conta-corrente e cartão), sinalizando o peso relativo
    no orçamento sem recomendar cancelamento.
    """
    start, end = month_bounds(month)
    results: dict[tuple[int, int | None], dict] = {}

    account_rows = conn.execute(
        """
        SELECT
            transactions.subcategory_id,
            subcategories.name AS subcategory_name,
            COALESCE(SUM(transactions.amount_brl_cents), 0) AS total
        FROM transactions
        JOIN categories
            ON categories.id = transactions.category_id
            AND categories.user_id = transactions.user_id
            AND categories.group_type = 'expense'
        LEFT JOIN subcategories
            ON subcategories.id = transactions.subcategory_id
            AND subcategories.user_id = transactions.user_id
        WHERE transactions.user_id = ?
            AND transactions.archived_at IS NULL
            AND transactions.date BETWEEN ? AND ?
            AND transactions.type = 'expense'
            AND categories.name = ?
            AND transactions.series_kind = 'recurring'
            AND (
                transactions.recurrence_frequency IS NULL
                OR transactions.recurrence_frequency = 'monthly'
            )
        GROUP BY transactions.subcategory_id, subcategories.name
        """,
        (user_id, start, end, SUBSCRIPTIONS_CATEGORY),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT
            credit_card_transactions.subcategory_id,
            subcategories.name AS subcategory_name,
            COALESCE(SUM(credit_card_transactions.amount_brl_cents), 0) AS total
        FROM credit_card_transactions
        JOIN categories
            ON categories.id = credit_card_transactions.category_id
            AND categories.user_id = credit_card_transactions.user_id
            AND categories.group_type = 'expense'
        LEFT JOIN subcategories
            ON subcategories.id = credit_card_transactions.subcategory_id
            AND subcategories.user_id = credit_card_transactions.user_id
        WHERE credit_card_transactions.user_id = ?
            AND credit_card_transactions.archived_at IS NULL
            AND credit_card_transactions.invoice_month = ?
            AND credit_card_transactions.type = 'expense'
            AND categories.name = ?
            AND credit_card_transactions.series_kind = 'recurring'
            AND (
                credit_card_transactions.recurrence_frequency IS NULL
                OR credit_card_transactions.recurrence_frequency = 'monthly'
            )
        GROUP BY credit_card_transactions.subcategory_id, subcategories.name
        """,
        (user_id, month, SUBSCRIPTIONS_CATEGORY),
    ).fetchall()

    for row in [*account_rows, *card_rows]:
        subcategory_id = int(row["subcategory_id"]) if row["subcategory_id"] else None
        subcategory_name = str(row["subcategory_name"] or "Geral").strip()
        key = (subcategory_id, subcategory_name)
        results[key] = results.get(key, {
            "subcategory_id": subcategory_id,
            "subcategory_name": subcategory_name,
            "valor_cents": 0,
        })
        results[key]["valor_cents"] += int(row["total"] or 0)

    return sorted(
        [value for value in results.values() if value["valor_cents"] > 0],
        key=lambda item: item["subcategory_name"],
    )


def build_findings(
    month: str,
    month_summary: dict[str, int],
    comparison: dict[str, int],
    budget_actual: list[dict],
    point_events: list[dict],
    acceleration: list[dict],
    subscriptions: list[dict],
    cash_opportunity: dict | None,
    previous_months: list[str],
    confidence: str,
) -> list[dict]:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 6, 7, 13, 22 e 29
    Lista achados estruturados: variação de receita/despesa, limites excedidos,
    eventos pontuais e assinaturas/serviços recorrentes.
    """
    findings = []
    income_delta = month_summary["income_cents"] - comparison["income_cents"]
    expense_delta = month_summary["expense_cents"] - comparison["expense_cents"]

    if confidence == "baixa":
        findings.append({
            "tipo": "confianca",
            "severidade": "info",
            "titulo": "Histórico curto",
            "descricao": (
                f"Com apenas {len(previous_months)} mês(es) de histórico, a análise tem confiança baixa. "
                "Evite interpretar variações como tendência permanente."
            ),
            "valor_cents": 0,
            "referencia": "historico",
        })
    elif confidence == "intermediaria":
        findings.append({
            "tipo": "confianca",
            "severidade": "info",
            "titulo": "Confiança intermediária",
            "descricao": (
                f"A comparação usa a média dos {len(previous_months)} meses anteriores disponíveis. "
                "A tendência pode se confirmar com mais histórico."
            ),
            "valor_cents": 0,
            "referencia": "historico",
        })

    if comparison["income_cents"] > 0 and abs(income_delta) >= max(1, comparison["income_cents"] // 20):
        direction = "aumentaram" if income_delta > 0 else "diminuiram"
        findings.append({
            "tipo": "receita",
            "severidade": "info" if income_delta > 0 else "atencao",
            "titulo": f"Receitas {direction}",
            "descricao": (
                f"As receitas do mês {direction} em relação à base de comparação "
                f"({format_diff(income_delta, comparison['income_cents'])})."
            ),
            "valor_cents": abs(income_delta),
            "referencia": comparison["tipo"],
        })

    if comparison["expense_cents"] > 0 and abs(expense_delta) >= max(1, comparison["expense_cents"] // 20):
        direction = "aumentaram" if expense_delta > 0 else "diminuiram"
        findings.append({
            "tipo": "despesa",
            "severidade": "atencao" if expense_delta > 0 else "info",
            "titulo": f"Despesas {direction}",
            "descricao": (
                f"As despesas do mês {direction} em relação à base de comparação "
                f"({format_diff(expense_delta, comparison['expense_cents'])})."
            ),
            "valor_cents": abs(expense_delta),
            "referencia": comparison["tipo"],
        })

    for row in budget_actual:
        if row["estado"] == "Acima do limite":
            label = row["subcategory_name"] or row["category_name"]
            findings.append({
                "tipo": "limite",
                "severidade": "atencao",
                "titulo": f"{label}: acima do limite",
                "descricao": (
                    f"O realizado de {label} ({format_cents(row['realizado_cents'])}) "
                    f"superou o limite ({format_cents(row['limite_cents'])}) em {row['percentual_usado']:.0f}%."
                ),
                "valor_cents": row["diferenca_cents"],
                "referencia": "limite_mensal",
            })
        elif row["estado"] == "Atenção":
            label = row["subcategory_name"] or row["category_name"]
            findings.append({
                "tipo": "limite",
                "severidade": "info",
                "titulo": f"{label}: próximo do limite",
                "descricao": (
                    f"O realizado de {label} ({format_cents(row['realizado_cents'])}) "
                    f"atingiu {row['percentual_usado']:.0f}% do limite mensal."
                ),
                "valor_cents": row["diferenca_cents"],
                "referencia": "limite_mensal",
            })

    for event in group_point_events(point_events):
        count = event["count"]
        count_text = f"{count} lançamento(s)" if count > 1 else "1 lançamento"
        examples = event["examples"]
        examples_text = f" Exemplos: {', '.join(examples)}." if examples else ""
        if event["tipo"] == "receita_pontual":
            findings.append({
                "tipo": "evento_pontual",
                "severidade": "info",
                "titulo": f"Receita pontual: {event['motivo']}",
                "descricao": (
                    f"{count_text} em {event['motivo']} podem ser eventos pontuais "
                    f"e explicar parte da variação de receitas.{examples_text}"
                ),
                "valor_cents": event["valor_cents"],
                "referencia": event["subcategoria"] or event["categoria"],
            })
        elif event["tipo"] in {"ferias", "manutencao_emergencia", "despesa_pontual"}:
            label = "Férias/viagem" if event["tipo"] == "ferias" else "Manutenção, reparo ou emergência"
            findings.append({
                "tipo": "evento_pontual",
                "severidade": "info",
                "titulo": f"Despesa pontual: {event['motivo'] or label}",
                "descricao": (
                    f"{count_text} em {event['motivo'] or label} podem distorcer a despesa do mês "
                    f"por serem eventos não recorrentes.{examples_text}"
                ),
                "valor_cents": event["valor_cents"],
                "referencia": event["subcategoria"] or event["categoria"],
            })

    grouped_acceleration = group_installment_accelerations(acceleration)
    for item in grouped_acceleration:
        examples_text = ""
        if item["examples"]:
            examples_text = f" Compras antecipadas: {format_examples(item['examples'], item['examples_total_count'])}."
        findings.append({
            "tipo": "antecipacao_parcela",
            "severidade": "info",
            "titulo": "Antecipação de parcelas",
            "descricao": (
                f"{item['count']} parcela(s) antecipadas para esta fatura, totalizando {format_cents(item['valor_cents'])}. "
                "O aumento de despesa deste mês pode estar ligado a antecipação e pode reduzir faturas futuras."
                f"{examples_text}"
            ),
            "valor_cents": item["valor_cents"],
            "referencia": "historico_operacional",
            "compras": item["examples"],
            "quantidade": item["count"],
        })

    # spec: tendencias-saude-financeira v2.22 — critério 29
    for item in subscriptions:
        label = item["subcategory_name"] or "Assinaturas e Serviços"
        findings.append({
            "tipo": "assinatura_servico",
            "severidade": "info",
            "titulo": f"{label}: custo mensal recorrente",
            "descricao": (
                f"Você tem {format_cents(item['valor_cents'])} mensais em {label}. "
                "Caso o uso esteja baixo, vale revisar se o custo está alinhado com o valor que traz."
            ),
            "valor_cents": item["valor_cents"],
            "referencia": "despesa_recorrente_mensal",
        })

    if cash_opportunity:
        # spec: tendencias-saude-financeira v2.22 — critério 54
        findings.append({
            "tipo": "oportunidade_caixa",
            "severidade": "info",
            "titulo": "Caixa acima do planejado",
            "descricao": (
                "O saldo previsto no fim do mês em contas de liquidez está acima de 2x das despesas planejadas. "
                "Pode ser uma oportunidade para revisar se parte desse caixa deve permanecer disponível, "
                "reforçar a reserva ou ser direcionada a algum objetivo financeiro."
            ),
            "valor_cents": cash_opportunity["saldo_previsto_fim_mes_cents"],
            "referencia": "saldo_previsto_fim_mes",
            "saldo_previsto_fim_mes_cents": cash_opportunity["saldo_previsto_fim_mes_cents"],
            "despesas_planejadas_cents": cash_opportunity["despesas_planejadas_cents"],
            "multiplicador": cash_opportunity["multiplicador"],
        })

    return findings


def group_point_events(point_events: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}
    for event in point_events:
        key = (str(event.get("tipo") or ""), str(event.get("motivo") or event.get("subcategoria") or event.get("categoria") or "Evento pontual"))
        item = grouped.setdefault(key, {
            "tipo": event.get("tipo"),
            "severidade": event.get("severidade", "info"),
            "categoria": event.get("categoria"),
            "subcategoria": event.get("subcategoria"),
            "motivo": event.get("motivo") or key[1],
            "valor_cents": 0,
            "count": 0,
            "examples": [],
        })
        item["valor_cents"] += int(event.get("valor_cents") or 0)
        item["count"] += 1
        description = str(event.get("descricao") or "").strip()
        if description and description not in item["examples"] and len(item["examples"]) < 3:
            item["examples"].append(description)
    return sorted(grouped.values(), key=lambda item: abs(item["valor_cents"]), reverse=True)


def group_installment_accelerations(acceleration: list[dict]) -> list[dict]:
    if not acceleration:
        return []
    examples = []
    for item in acceleration:
        purchase = str(item.get("compra") or "").strip()
        if purchase and purchase not in examples:
            examples.append(purchase)
    return [{
        "valor_cents": sum(int(item.get("valor_cents") or 0) for item in acceleration),
        "count": len(acceleration),
        "examples": examples[:5],
        "examples_total_count": len(examples),
    }]


def format_examples(examples: list[str], total_count: int) -> str:
    visible = [str(example).strip() for example in examples[:5] if str(example).strip()]
    if not visible:
        return ""
    remaining = max(0, total_count - len(visible))
    suffix = f" e mais {remaining} compra(s)" if remaining else ""
    return f"{', '.join(visible)}{suffix}"


def build_local_summary(
    month: str,
    month_summary: dict[str, int],
    comparison: dict[str, int],
    findings: list[dict],
    point_events: list[dict],
    acceleration: list[dict],
    subscriptions: list[dict],
    cash_opportunity: dict | None,
    confidence: str,
    multi_currency: str | None,
) -> str:
    """
    Monta o resumo textual determinístico a partir dos achados estruturados.
    """
    parts = []
    income = month_summary["income_cents"]
    expense = month_summary["expense_cents"]
    balance = income - expense

    parts.append(
        f"Em {month}, receitas foram {format_cents(income)} e despesas {format_cents(expense)}, "
        f"resultando em saldo {format_cents(balance)}."
    )

    if confidence == "baixa":
        parts.append("O histórico ainda é curto, então interprete os números com cautela.")

    if comparison["tipo"] != "sem_historico":
        income_delta = income - comparison["income_cents"]
        expense_delta = expense - comparison["expense_cents"]
        if income_delta != 0:
            direction = "aumentaram" if income_delta > 0 else "diminuíram"
            parts.append(
                "As receitas do mês "
                f"{direction} em relação à base de comparação ({format_diff(income_delta, comparison['income_cents'])})."
            )
        if expense_delta != 0:
            direction = "aumentaram" if expense_delta > 0 else "diminuíram"
            parts.append(
                "As despesas do mês "
                f"{direction} em relação à base de comparação ({format_diff(expense_delta, comparison['expense_cents'])})."
            )

    if subscriptions:
        total = sum(item["valor_cents"] for item in subscriptions)
        labels = ", ".join(
            f"{item['subcategory_name']} ({format_cents(item['valor_cents'])})"
            for item in subscriptions[:3]
        )
        parts.append(
            f"Assinaturas e serviços recorrentes somam {format_cents(total)} neste mês: {labels}."
        )

    if cash_opportunity:
        parts.append(
            "O saldo previsto no fim do mês em contas de liquidez está acima de 2x das despesas planejadas; "
            "vale revisar se parte desse caixa deve permanecer disponível, reforçar a reserva ou ser direcionada "
            "a algum objetivo financeiro."
        )

    parts.append("Estas observações são explicativas e não recomendações personalizadas.")
    if multi_currency:
        parts.append(multi_currency)
    return " ".join(parts)


def determine_confidence(previous_months: list[str]) -> str:
    """
    spec: tendencias-saude-financeira v2.22 — critérios 94, 95 e 96
    """
    count = len(previous_months)
    if count < 3:
        return "baixa"
    if count < 6:
        return "intermediaria"
    return "alta"


def detect_multiple_currencies(conn, user_id: int, month: str) -> str | None:
    """
    spec: tendencias-saude-financeira v2.22 — critério 27
    Detecta se há dados em mais de uma moeda e indica a base usada.
    """
    account_currencies = {
        str(row[0] or "BRL").upper()
        for row in conn.execute(
            "SELECT DISTINCT currency FROM checking_accounts WHERE user_id = ? AND archived_at IS NULL",
            (user_id,),
        ).fetchall()
    }
    card_currencies = {
        str(row[0] or "BRL").upper()
        for row in conn.execute(
            "SELECT DISTINCT currency FROM credit_cards WHERE user_id = ? AND archived_at IS NULL",
            (user_id,),
        ).fetchall()
    }
    currencies = account_currencies | card_currencies
    if len(currencies) > 1:
        return (
            f"Dados encontrados em {', '.join(sorted(currencies))}; a análise usa BRL como moeda base "
            "com os valores normalizados nos lançamentos por cotação manual ou pela última PTAX de venda disponível."
        )
    return None


def trailing_months(month: str, count: int) -> list[str]:
    year, month_number = map(int, normalize_month(month).split("-"))
    months = []
    for offset in range(count - 1, -1, -1):
        total_month = year * 12 + month_number - 1 - offset
        candidate_year, candidate_month_index = divmod(total_month, 12)
        months.append(f"{candidate_year:04d}-{candidate_month_index + 1:02d}")
    return months


def month_bounds(month: str) -> tuple[str, str]:
    normalized = normalize_month(month)
    year, month_number = map(int, normalized.split("-"))
    return f"{normalized}-01", date(year, month_number, days_in_month(year, month_number)).isoformat()


def average_cents(values: list[int]) -> int:
    if not values:
        return 0
    total = sum(values)
    return int((Decimal(total) / Decimal(len(values))).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def percent_of(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    ratio = Decimal(part) / Decimal(whole)
    return float((ratio * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_cents(cents: int) -> str:
    value = Decimal(cents) / Decimal("100")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_diff(delta: int, base: int) -> str:
    if base <= 0:
        return format_cents(abs(delta))
    pct = percent_of(abs(delta), base)
    return f"{format_cents(abs(delta))} ({pct:.0f}%)"
