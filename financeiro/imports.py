"""Orquestração do fluxo de importação de lançamentos."""
from __future__ import annotations

import uuid
from decimal import Decimal
from difflib import SequenceMatcher

from financeiro.accounts import recompute_account_balance
from financeiro.categories import (
    ClassificationError,
    get_or_create_category,
    get_or_create_subcategory,
    get_or_create_tag,
    list_categories,
    list_tags,
    normalize_name,
)
from financeiro.classification_suggestions import normalize_description
from financeiro.credit_cards import (
    create_credit_card_transaction_with_conn,
    get_active_credit_card,
    replace_credit_card_transaction_tags,
)
from financeiro.database import begin_immediate, get_connection, row_to_dict
from financeiro.identifiers import positive_int_id
from financeiro.import_adjustments import (
    LEARNABLE_IMPORT_FIELDS,
    find_import_adjustment,
    save_import_adjustment,
)
from financeiro.import_ofx import (
    first_ofx_value,
    format_ofx_date,
    parse_ofx_rows,
)
from financeiro.import_parsers import (
    HEADER_ALIASES,
    MAX_XLSX_CELLS,
    MAX_XLSX_COLUMNS,
    MAX_XLSX_ROWS,
    MAX_XLSX_SHARED_STRINGS,
    OLE_MAGIC,
    decode_rk,
    excel_serial_to_date,
    find_header_index,
    get_cell,
    iter_biff_records,
    normalize_header,
    parse_biff_string,
    parse_csv_rows,
    parse_shared_strings,
    parse_system_template_file,
    parse_xls_rows,
    parse_xlsx_rows,
    read_ole_workbook_stream,
    read_sector_chain,
    rows_to_transactions,
    sector_offset,
    xlsx_cell_is_date,
    xlsx_cell_text,
    xlsx_column_index,
    xlsx_complexity_error,
    xlsx_date_style_indexes,
    xlsx_shared_strings,
    xlsx_sheet_path,
    xlsx_uses_1904_date_system,
)
from financeiro.import_templates import (
    create_xlsx_workbook,
    xlsx_app_props,
    xlsx_column_name,
    xlsx_content_types,
    xlsx_core_props,
    xlsx_root_rels,
    xlsx_sheet_xml,
    xlsx_styles_xml,
    xlsx_workbook_rels,
    xlsx_workbook_xml,
)
from financeiro.import_utils import (
    ImportError,
    money_decimal_to_cents,
    normalize_account_id,
    normalize_amount,
    normalize_import_date,
    normalize_import_flag,
    normalize_import_money_for_form,
    normalize_import_month,
    normalize_import_target,
    normalize_key,
    normalize_optional_import_money_for_form,
    normalize_template_header,
)
from financeiro.transactions import (
    convert_to_brl_cents,
    create_transaction_with_conn,
    get_active_account,
    normalize_tags,
    replace_transaction_tags,
    resolve_exchange_rate_micros,
)


# Reexports de compatibilidade para consumidores legados.
# As implementações vivem nos módulos especializados; estas referências
# preservam importações existentes em testes e em financeiro.market_calendar.
ImportError = ImportError
HEADER_ALIASES = HEADER_ALIASES
MAX_XLSX_CELLS = MAX_XLSX_CELLS
MAX_XLSX_COLUMNS = MAX_XLSX_COLUMNS
MAX_XLSX_ROWS = MAX_XLSX_ROWS
MAX_XLSX_SHARED_STRINGS = MAX_XLSX_SHARED_STRINGS
OLE_MAGIC = OLE_MAGIC
SYSTEM_IMPORT_ACCOUNT_HEADERS = [
    "data",
    "tipo",
    "descricao",
    "valor",
    "categoria",
    "subcategoria",
    "tags",
    "repeticao",
    "parcelas",
    "recorrencia",
    "media",
    "conta_destino_id",
    "valor_destino",
    "cotacao_cambio",
    "cotacao_brl",
    "observacoes",
]
SYSTEM_IMPORT_CARD_HEADERS = [
    "data",
    "competencia_fatura",
    "tipo",
    "descricao",
    "valor",
    "categoria",
    "subcategoria",
    "tags",
    "repeticao",
    "parcelas",
    "recorrencia",
    "media",
    "observacoes",
]
SERIES_KIND_ALIASES = {
    "avulso": "single",
    "single": "single",
    "parcelado": "installment",
    "installment": "installment",
    "recorrente": "recurring",
    "recurring": "recurring",
}
RECURRENCE_FREQUENCY_ALIASES = {
    "semanal": "weekly",
    "weekly": "weekly",
    "mensal": "monthly",
    "monthly": "monthly",
    "trimestral": "quarterly",
    "quarterly": "quarterly",
    "semestral": "semiannual",
    "semiannual": "semiannual",
    "anual": "annual",
    "annual": "annual",
}
INVESTMENT_TAG_CATEGORY_ALIASES = {
    "previdencia": ("Previdência Privada", "PGBL (Plano Gerador de Benefício Livre)"),
    "pgbl": ("Previdência Privada", "PGBL (Plano Gerador de Benefício Livre)"),
    "vgbl": ("Previdência Privada", "VGBL (Vida Gerador de Benefício Livre)"),
    "fii": ("Renda Variável", "Fundos de Investimento Imobiliário (FIIs)"),
    "etf": ("Renda Variável", "ETFs (Exchange Traded Funds)"),
    "itub4": ("Renda Variável", "Ações (Bolsa de Valores - B3)"),
    "vale3": ("Renda Variável", "Ações (Bolsa de Valores - B3)"),
    "isae4": ("Renda Variável", "Ações (Bolsa de Valores - B3)"),
    "tesouro direto": ("Renda Fixa", "Tesouro Direto (Selic, IPCA+, Prefixado)"),
    "cdb": ("Renda Fixa", "CDB / RDB / LC (Certificados de Depósito)"),
    "lca": ("Renda Fixa", "LCI / LCA (Letras de Crédito Imobiliário/Agrícola)"),
    "lci": ("Renda Fixa", "LCI / LCA (Letras de Crédito Imobiliário/Agrícola)"),
    "cra": ("Renda Fixa", "CRI / CRA / Debêntures (Crédito Privado)"),
    "cri": ("Renda Fixa", "CRI / CRA / Debêntures (Crédito Privado)"),
    "poupanca": ("Renda Fixa", "Poupança (Fundo de Emergência antigo)"),
    "cofrinho": ("Renda Fixa", "Poupança (Fundo de Emergência antigo)"),
    "fundos": ("Fundos de Investimentos", "Fundos Multimercado"),
    "cripto": ("Criptoativos", "Outras Altcoins (Solana, Cardano, etc.)"),
    "bitcoin": ("Criptoativos", "Bitcoin (BTC)"),
    "btc": ("Criptoativos", "Bitcoin (BTC)"),
    "ethereum": ("Criptoativos", "Ethereum (ETH)"),
    "eth": ("Criptoativos", "Ethereum (ETH)"),
    "avenue": ("Renda Variável", "BDRs / Investimentos no Exterior"),
    "wise": ("Renda Variável", "BDRs / Investimentos no Exterior"),
}
EXPENSE_CATEGORY_ALIASES = {
    "alimentacao": ("Alimentação", None),
    "bares e restaurantes": ("Alimentação", "Restaurantes / Bares / Delivery"),
    "casa": ("Habitação", None),
    "eletricidade": ("Habitação", "Energia Elétrica (Luz)"),
    "gas": ("Habitação", "Gás (Encanado ou Botijão)"),
    "celular": ("Assinaturas e Serviços", "Celular"),
    "assinaturas e servicos": ("Assinaturas e Serviços", None),
    "impostos e taxas": ("Serviços Financeiros e Impostos", None),
    "pagamento de fatura": ("Serviços Financeiros e Impostos", "Pagamento de Fatura de Cartão"),
    "familia e filhos": ("Dependentes e Filhos", None),
    "presentes e doacoes": ("Outras Despesas", "Presentes para Amigos e Família"),
    "cuidados pessoais": ("Cuidados Pessoais", None),
    "roupas": ("Cuidados Pessoais", "Vestuário (Roupas, Calçados e Underwear)"),
    "viagem": ("Lazer e Estilo de Vida", "Viagens, Passagens e Hospedagens (Férias)"),
    "lazer e hobbies": ("Lazer e Estilo de Vida", "Hobbies, Passatempos e Jogos"),
    "dividas e emprestimos": ("Empréstimos", None),
    "emprestimos": ("Empréstimos", None),
    "outros": ("Outras Despesas", "Imprevistos e Emergências Domésticas"),
}
EXPENSE_HINT_ALIASES = {
    "enel": ("Habitação", "Energia Elétrica (Luz)"),
    "comgas": ("Habitação", "Gás (Encanado ou Botijão)"),
    "condominio": ("Habitação", "Condomínio"),
    "iptu": ("Habitação", "IPTU"),
    "faxina": ("Habitação", "Empregada Doméstica / Diarista"),
    "seguro": ("Serviços Financeiros e Impostos", "Seguro de Vida / Previdência do Estado"),
    "irpf": ("Serviços Financeiros e Impostos", "Imposto de Renda a Pagar (IRPF)"),
    "ipva": ("Transporte", "IPVA / Licenciamento / DPVAT"),
    "multas": ("Transporte", "IPVA / Licenciamento / DPVAT"),
    "carros": ("Transporte", "Manutenção, Revisão e Troca de Óleo"),
    "estacionamento": ("Transporte", "Estacionamento e Pedágio"),
    "uber": ("Transporte", "Aplicativos de Transporte (Uber, 99)"),
    "taxi": ("Transporte", "Aplicativos de Transporte (Uber, 99)"),
    "celular": ("Assinaturas e Serviços", "Celular"),
    "netflix": ("Assinaturas e Serviços", "Streaming de Vídeo (Netflix, Disney+, Prime, etc.)"),
}
INCOME_CATEGORY_ALIASES = {
    "salario": ("Trabalho e Salário", "Salário Líquido"),
    "outuras receitas": ("Outras Receitas", None),
    "outras receitas": ("Outras Receitas", None),
    "investimentos": ("Rendimentos e Investimentos", None),
    "emprestimos": ("Empréstimos", None),
}
INCOME_HINT_ALIASES = {
    "ferias": ("Trabalho e Salário", "Férias"),
    "plr": ("Trabalho e Salário", "Bônus / PLR"),
    "salario": ("Trabalho e Salário", "Salário Líquido"),
    "irpf": ("Outras Receitas", "Restituição de Imposto de Renda"),
    "reembolso": ("Outras Receitas", "Reembolsos Corporativos"),
    "dividendos": ("Rendimentos e Investimentos", "Dividendos / JCP"),
    "jcp": ("Rendimentos e Investimentos", "Dividendos / JCP"),
    "juros": ("Rendimentos e Investimentos", "Rendimento de Renda Fixa"),
    "tesouro direto": ("Rendimentos e Investimentos", "Rendimento de Renda Fixa"),
    "cdb": ("Rendimentos e Investimentos", "Rendimento de Renda Fixa"),
    "lca": ("Rendimentos e Investimentos", "Rendimento de Renda Fixa"),
    "poupanca": ("Rendimentos e Investimentos", "Rendimento de Renda Fixa"),
}


def system_import_template(user_id: int, target: str) -> bytes:
    normalized_target = normalize_import_target(target)
    headers = SYSTEM_IMPORT_CARD_HEADERS if normalized_target == "card" else SYSTEM_IMPORT_ACCOUNT_HEADERS
    launch_rows = [headers]
    if normalized_target == "card":
        launch_rows.append(["15.06.2026", "2026-06", "expense", "Exemplo compra no cartão", "123,45", "Alimentação", "Restaurantes / Bares / Delivery", "Importado; Revisar", "parcelado", "3", "", "", "Linha exemplo"])
        launch_rows.append(["2026-06-20", "2026-06", "income", "Exemplo estorno", "10,00", "Outras Receitas", "Reembolsos Corporativos", "Importado", "", "", "", "", "Linha exemplo"])
    else:
        launch_rows.append(["15.06.2026", "expense", "Exemplo mercado", "123,45", "Alimentação", "Supermercado / Feira / Hortifruti", "Importado; Revisar", "parcelado", "3", "", "", "", "", "", "", "Linha exemplo"])
        launch_rows.append(["2026-06-15", "income", "Exemplo salário", "1000,00", "Trabalho e Salário", "Salário Líquido", "Importado", "", "", "", "", "", "", "", "", "Linha exemplo"])
        launch_rows.append(["2026-06-15", "transfer", "Exemplo transferência", "500,00", "", "", "", "", "", "", "", "2", "", "", "", "Informe conta_destino_id"])
        launch_rows.append(["2026-06-15", "exchange", "Exemplo câmbio", "1000,00", "", "", "Câmbio", "", "", "", "", "3", "197,10", "0,197100", "", "Conta destino em outra moeda"])
    category_rows = [["grupo", "categoria", "subcategoria"]]
    with get_connection() as conn:
        categories = conn.execute(
            """
            SELECT categories.group_type, categories.name AS category_name, subcategories.name AS subcategory_name
            FROM categories
            LEFT JOIN subcategories ON subcategories.category_id = categories.id
            WHERE categories.user_id = ?
            ORDER BY categories.group_type, categories.name COLLATE NOCASE, subcategories.name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
        for row in categories:
            category_rows.append([row["group_type"], row["category_name"], row["subcategory_name"] or ""])
        tags = conn.execute(
            "SELECT name FROM tags WHERE user_id = ? ORDER BY name COLLATE NOCASE",
            (user_id,),
        ).fetchall()
    tag_rows = [["tag"]]
    for row in tags:
        tag_rows.append([row["name"]])
    account_rows = [["id", "nome", "tipo", "moeda"]]
    with get_connection() as conn:
        accounts = conn.execute(
            """
            SELECT id, name, account_type, currency
            FROM checking_accounts
            WHERE user_id = ? AND archived_at IS NULL
            ORDER BY name COLLATE NOCASE
            """,
            (user_id,),
        ).fetchall()
    for row in accounts:
        account_rows.append([row["id"], row["name"], row["account_type"], row["currency"]])
    return create_xlsx_workbook([
        ("Lançamentos", launch_rows),
        ("Categorias", category_rows),
        ("Tags", tag_rows),
        ("Contas", account_rows),
    ])


def preview_system_template(user_id: int, target: str, target_id: object, file_bytes: bytes, filename: str) -> dict:
    normalized_target = normalize_import_target(target)
    rows = parse_system_template_file(file_bytes, filename)
    source_type = "credit_card" if normalized_target == "card" else "account"
    preview_rows = []
    errors = []
    with get_connection() as conn:
        for raw in rows:
            original_raw = dict(raw)
            try:
                if normalized_target == "card":
                    payload = normalize_system_card_row(raw, target_id)
                else:
                    payload = normalize_system_account_row(raw, target_id)
                adjustment = find_import_adjustment(
                    conn,
                    user_id,
                    source_type,
                    int(target_id),
                    original_raw.get("descricao") or original_raw.get("description"),
                    payload["type"],
                )
                if adjustment:
                    apply_import_adjustment_to_row(raw, adjustment)
                    if normalized_target == "card":
                        payload = normalize_system_card_row(raw, target_id)
                    else:
                        payload = normalize_system_account_row(raw, target_id)
                preview_rows.append({
                    "row": original_raw.get("row", ""),
                    "selected": True,
                    "raw": original_raw,
                    "values": preview_row_from_payload(
                        payload,
                        original_raw.get("descricao") or original_raw.get("description"),
                    ),
                    "learned_adjustment": adjustment is not None,
                })
            except (ImportError, ValueError) as exc:
                errors.append({
                    "row": raw.get("row", ""),
                    "description": raw.get("descricao") or raw.get("description") or "",
                    "reason": getattr(exc, "message", str(exc)),
                })
        duplicate_rows = find_preview_duplicate_matches(
            conn,
            user_id,
            source_type,
            int(target_id),
            preview_rows,
            is_legacy=False,
        )
    for preview_row, matches in zip(preview_rows, duplicate_rows):
        preview_row["duplicate_matches"] = matches
    return {
        "preview": preview_rows,
        "errors": errors[:50],
        "total_rows": len(rows),
        "imported": 0,
        "skipped": 0,
        "selected_rows": len(preview_rows),
        "classification_options": {
            "categories": list_categories(user_id),
            "tags": list_tags(user_id),
        },
    }


def import_system_template(user_id: int, target: str, target_id: object, file_bytes: bytes, filename: str, selected_rows: list[dict] | None = None) -> dict:
    normalized_target = normalize_import_target(target)
    rows = parse_system_template_file(file_bytes, filename) if selected_rows is None else [coerce_preview_row_to_raw(row) for row in selected_rows if row.get("selected", True)]
    operation_batch_id = str(uuid.uuid4())
    imported = []
    skipped = []
    for raw in rows:
        with get_connection() as conn:
            begin_immediate(conn)
            conn.execute("SAVEPOINT import_row")
            try:
                if normalized_target == "card":
                    payload = normalize_system_card_row(raw, target_id)
                    if raw.get("_preview_reviewed"):
                        _, payload["category"], payload["subcategory"] = validate_reviewed_classification(
                            conn,
                            user_id,
                            payload["category"],
                            payload["subcategory"],
                            payload["type"],
                        )
                    # spec: importacao/importacao-dados v1.16 — critérios 14 a 17
                    if raw.get("_duplicate_action") == "ignore":
                        if not has_import_duplicate(
                            conn, user_id, "credit_card", int(target_id), payload["type"], payload["date"],
                            money_decimal_to_cents(normalize_amount(payload["amount"])),
                            payload["category"], payload["subcategory"],
                        ):
                            raise ImportError("A duplicidade não está mais presente; revise a linha antes de ignorar.")
                        learn_import_adjustment_from_row(
                            conn, user_id, "credit_card", int(target_id), raw, payload["type"],
                            payload["description"], payload["category"], payload["subcategory"], payload["tags"],
                        )
                        conn.execute("RELEASE SAVEPOINT import_row")
                        skipped.append({
                            "row": raw.get("row", ""),
                            "description": payload["description"],
                            "reason": "Linha ignorada conforme sua escolha.",
                        })
                        continue
                    if raw.get("_duplicate_action") == "replace":
                        created = replace_duplicate_import(
                            conn,
                            user_id,
                            "credit_card",
                            int(target_id),
                            raw,
                            payload["type"],
                            payload["date"],
                            money_decimal_to_cents(normalize_amount(payload["amount"])),
                            payload["category"],
                            payload["subcategory"],
                            payload["description"],
                            payload["tags"],
                            payload["notes"],
                        )
                    elif has_import_duplicate(
                        conn,
                        user_id,
                        "credit_card",
                        int(target_id),
                        payload["type"],
                        payload["date"],
                        money_decimal_to_cents(normalize_amount(payload["amount"])),
                        payload["category"],
                        payload["subcategory"],
                    ):
                        raise ImportError("Linha duplicada; escolha substituir ou ignorar na prévia.")
                    else:
                        created = create_credit_card_transaction_with_conn(conn, user_id, payload)
                else:
                    payload = normalize_system_account_row(raw, target_id)
                    if raw.get("_preview_reviewed"):
                        _, payload["category"], payload["subcategory"] = validate_reviewed_classification(
                            conn,
                            user_id,
                            payload["category"],
                            payload["subcategory"],
                            payload["type"],
                        )
                    # spec: importacao/importacao-dados v1.16 — critérios 14 a 17
                    if raw.get("_duplicate_action") == "ignore":
                        if not has_import_duplicate(
                            conn, user_id, "account", int(target_id), payload["type"], payload["date"],
                            money_decimal_to_cents(normalize_amount(payload["amount"])),
                            payload["category"], payload["subcategory"],
                        ):
                            raise ImportError("A duplicidade não está mais presente; revise a linha antes de ignorar.")
                        learn_import_adjustment_from_row(
                            conn, user_id, "account", int(target_id), raw, payload["type"],
                            payload["description"], payload["category"], payload["subcategory"], payload["tags"],
                        )
                        conn.execute("RELEASE SAVEPOINT import_row")
                        skipped.append({
                            "row": raw.get("row", ""),
                            "description": payload["description"],
                            "reason": "Linha ignorada conforme sua escolha.",
                        })
                        continue
                    if raw.get("_duplicate_action") == "replace":
                        created = replace_duplicate_import(
                            conn,
                            user_id,
                            "account",
                            int(target_id),
                            raw,
                            payload["type"],
                            payload["date"],
                            money_decimal_to_cents(normalize_amount(payload["amount"])),
                            payload["category"],
                            payload["subcategory"],
                            payload["description"],
                            payload["tags"],
                            payload["notes"],
                        )
                    elif has_import_duplicate(
                        conn,
                        user_id,
                        "account",
                        int(target_id),
                        payload["type"],
                        payload["date"],
                        money_decimal_to_cents(normalize_amount(payload["amount"])),
                        payload["category"],
                        payload["subcategory"],
                    ):
                        raise ImportError("Linha duplicada; escolha substituir ou ignorar na prévia.")
                    else:
                        created = create_transaction_with_conn(conn, user_id, payload)
                learn_import_adjustment_from_row(
                    conn,
                    user_id,
                    "credit_card" if normalized_target == "card" else "account",
                    int(target_id),
                    raw,
                    payload["type"],
                    payload["description"],
                    payload["category"],
                    payload["subcategory"],
                    payload["tags"],
                )
                conn.execute("RELEASE SAVEPOINT import_row")
                imported.append({
                    "row": raw["row"],
                    "id": created["id"],
                    "description": payload["description"],
                    "replaced": raw.get("_duplicate_action") == "replace",
                })
            except Exception as exc:
                conn.execute("ROLLBACK TO SAVEPOINT import_row")
                conn.execute("RELEASE SAVEPOINT import_row")
                skipped.append({
                    "row": raw.get("row", ""),
                    "description": raw.get("descricao") or raw.get("description") or "",
                    "reason": getattr(exc, "message", str(exc) or "Nao foi possivel importar a linha."),
                })
    return {
        "operation_batch_id": operation_batch_id,
        "imported": len(imported),
        "skipped": len(skipped),
        "total_rows": len(rows),
        "rows": imported,
        "errors": skipped,
    }


def preview_row_from_payload(payload: dict, original_description: object = None) -> dict:
    return {
        "data": payload.get("date") or "",
        "tipo": payload.get("type") or "",
        "descricao_original": original_description or payload.get("description") or "",
        "descricao": payload.get("description") or "",
        "valor": payload.get("amount") or "",
        "categoria": payload.get("category") or "",
        "subcategoria": payload.get("subcategory") or "",
        "tags": payload.get("tags") or "",
        "repeticao": payload.get("series_kind") or "single",
        "parcelas": payload.get("installment_count") or "",
        "recorrencia": payload.get("recurrence_frequency") or "",
        "media": "sim" if payload.get("use_average") else "nao",
        "observacoes": payload.get("notes") or "",
        "competencia_fatura": payload.get("invoice_month") or "",
        "conta_destino_id": payload.get("destination_account_id") or "",
        "valor_destino": payload.get("destination_amount") or "",
        "cotacao_cambio": payload.get("transfer_exchange_rate") or "",
        "cotacao_brl": payload.get("exchange_rate_to_brl") or "",
    }


def coerce_preview_row_to_raw(row: dict) -> dict:
    values = dict(row.get("values") or {})
    raw = dict(row.get("raw") or {})
    raw["row"] = row.get("row", raw.get("row", ""))
    raw["_import_original"] = dict(row.get("raw") or {})
    raw["_preview_reviewed"] = True
    raw["_duplicate_action"] = row.get("duplicate_action")
    raw["_duplicate_target_id"] = row.get("duplicate_target_id")
    edited_fields = row.get("edited_fields", [])
    raw["_edited_fields"] = [
        field for field in edited_fields
        if field in LEARNABLE_IMPORT_FIELDS
    ] if isinstance(edited_fields, list) else []
    for key, value in values.items():
        if key == "descricao_original":
            continue
        if value == "":
            raw[key] = ""
        else:
            raw[key] = value
    return raw


def apply_import_adjustment_to_row(row: dict, adjustment: dict) -> None:
    field_names = {
        "description": ("descricao", "description"),
        "category": ("categoria", "category"),
        "subcategory": ("subcategoria", "subcategory"),
        "tags": ("tags", "tag"),
    }
    for field, value in adjustment.items():
        if field not in field_names:
            continue
        candidates = field_names[field]
        key = next((candidate for candidate in candidates if candidate in row), candidates[0])
        row[key] = "; ".join(value) if field == "tags" else value


# spec: importacao/importacao-dados v1.16 — critérios 14 a 17
def learn_import_adjustment_from_row(
    conn,
    user_id: int,
    source_type: str,
    source_id: int,
    row: dict,
    transaction_type: str,
    description: object,
    category: object,
    subcategory: object,
    tags: list[str],
) -> None:
    original = row.get("_import_original")
    edited_fields = row.get("_edited_fields")
    if not isinstance(original, dict) or not isinstance(edited_fields, list):
        return
    if not LEARNABLE_IMPORT_FIELDS.intersection(edited_fields):
        return
    original_description = original.get("description") or original.get("descricao")
    if not str(original_description or "").strip():
        return
    normalized_tags = tags if isinstance(tags, list) else (
        normalize_tags(tags) if str(tags or "").strip() else []
    )
    save_import_adjustment(
        conn,
        user_id,
        source_type,
        source_id,
        original_description,
        transaction_type,
        description,
        category,
        subcategory,
        normalized_tags,
    )


def normalize_system_account_row(row: dict, account_id: object) -> dict:
    transaction_type = normalize_system_type(row.get("tipo") or row.get("type"))
    if transaction_type == "exchange":
        transaction_type = "transfer"
    payload = {
        "account_id": account_id,
        "type": transaction_type,
        "date": normalize_import_date(row.get("data") or row.get("date")),
        "description": row.get("descricao") or row.get("description"),
        "amount": normalize_import_money_for_form(row.get("valor") or row.get("amount")),
        "category": row.get("categoria") or row.get("category"),
        "subcategory": row.get("subcategoria") or row.get("subcategory"),
        "tags": row.get("tags") or row.get("tag"),
        "destination_account_id": row.get("conta_destino_id") or row.get("destination_account_id"),
        "destination_amount": normalize_optional_import_money_for_form(row.get("valor_destino") or row.get("destination_amount")),
        "transfer_exchange_rate": row.get("cotacao_cambio") or row.get("transfer_exchange_rate"),
        "exchange_rate_to_brl": row.get("cotacao_brl") or row.get("exchange_rate_to_brl"),
        "notes": row.get("observacoes") or row.get("notes"),
        **normalize_system_series(row),
    }
    if payload["type"] == "transfer":
        payload["category"] = ""
        payload["subcategory"] = ""
        # spec: importacao/importacao-dados v1.16 — regras de repetição
        # (transferencias e cambio sao sempre avulsos, mesmo se a linha trouxer repeticao)
        payload["series_kind"] = "single"
        payload["installment_count"] = None
        payload["recurrence_frequency"] = None
    return payload


def normalize_system_card_row(row: dict, card_id: object) -> dict:
    transaction_date = normalize_import_date(row.get("data") or row.get("date"))
    return {
        "credit_card_id": card_id,
        "type": normalize_card_import_type(row.get("tipo") or row.get("type")),
        "date": transaction_date,
        "invoice_month": normalize_import_month(row.get("competencia_fatura") or row.get("invoice_month") or transaction_date),
        "description": row.get("descricao") or row.get("description"),
        "amount": normalize_import_money_for_form(row.get("valor") or row.get("amount")),
        "category": row.get("categoria") or row.get("category"),
        "subcategory": row.get("subcategoria") or row.get("subcategory"),
        "tags": row.get("tags") or row.get("tag"),
        "notes": row.get("observacoes") or row.get("notes"),
        **normalize_system_series(row),
    }


def normalize_system_series(row: dict) -> dict:
    # spec: importacao/importacao-dados v1.16 — regras de repetição
    # (avulso padrao; parcelado exige parcelas 2-120; recorrente exige frequencia;
    #  media so se aplica a recorrentes)
    series_kind = SERIES_KIND_ALIASES.get(normalize_key(row.get("repeticao") or row.get("series_kind")), "single")
    installment_count = None
    recurrence_frequency = None
    use_average = normalize_import_flag(row.get("media") or row.get("use_average"))
    if series_kind == "installment":
        raw_count = str(row.get("parcelas") or row.get("installment_count") or "").strip()
        try:
            installment_count = int(raw_count)
        except ValueError as exc:
            raise ImportError("Informe a quantidade de parcelas (coluna parcelas).") from exc
        if installment_count < 2 or installment_count > 120:
            raise ImportError("Informe entre 2 e 120 parcelas (coluna parcelas).")
    if series_kind == "recurring":
        recurrence_frequency = RECURRENCE_FREQUENCY_ALIASES.get(normalize_key(row.get("recorrencia") or row.get("recurrence_frequency")))
        if recurrence_frequency is None:
            raise ImportError("Informe a frequencia da recorrencia (coluna recorrencia): semanal, mensal, trimestral, semestral ou anual.")
    return {
        "series_kind": series_kind,
        "installment_count": installment_count,
        "recurrence_frequency": recurrence_frequency,
        "use_average": use_average,
    }


def normalize_system_type(value: object) -> str:
    key = normalize_key(value)
    aliases = {
        "despesa": "expense",
        "expense": "expense",
        "receita": "income",
        "income": "income",
        "transferencia": "transfer",
        "transfer": "transfer",
        "cambio": "exchange",
        "exchange": "exchange",
        "investimento": "investment",
        "investment": "investment",
    }
    if key not in aliases:
        raise ImportError("Tipo invalido. Use expense, income, transfer, exchange ou investment.")
    return aliases[key]


def normalize_card_import_type(value: object) -> str:
    key = normalize_system_type(value)
    if key not in {"expense", "income"}:
        raise ImportError("Cartao aceita apenas expense ou income.")
    return key


def is_template_reference_section(row: list[object]) -> bool:
    first = normalize_key(get_cell(row, 0))
    return first in {"categorias_do_sistema", "tags_existentes"}


def parse_legacy_file(file_bytes: bytes, filename: str) -> list[dict]:
    if not file_bytes:
        raise ImportError("Envie um arquivo para importar.")
    name = filename.lower()
    if name.endswith(".ofx") or name.endswith(".qfx"):
        return parse_ofx_rows(file_bytes)
    if name.endswith(".xls") or file_bytes.startswith(OLE_MAGIC):
        rows = parse_xls_rows(file_bytes)
    elif name.endswith(".csv"):
        rows = parse_csv_rows(file_bytes)
    else:
        raise ImportError("Formato nao suportado. Envie um arquivo .xls, .csv ou .ofx para importacao.")
    return rows_to_transactions(rows)


def import_legacy_transactions(
    user_id: int,
    account_id: object,
    file_bytes: bytes,
    filename: str,
    selected_rows: list[dict] | None = None,
) -> dict:
    normalized_account_id = normalize_account_id(account_id)
    raw_rows = (
        parse_legacy_file(file_bytes, filename)
        if selected_rows is None
        else [legacy_preview_row_to_raw(row) for row in selected_rows if row.get("selected", True)]
    )
    operation_batch_id = str(uuid.uuid4())
    imported = []
    skipped = []
    with get_connection() as conn:
        account = get_active_account(conn, user_id, normalized_account_id)
    for raw in raw_rows:
        try:
            transaction = normalize_imported_transaction(raw)
            exchange_rate_micros = resolve_exchange_rate_micros(account["currency"], transaction["date"], None)
            amount_brl_cents = convert_to_brl_cents(transaction["amount_cents"], exchange_rate_micros)
        except ImportError as exc:
            skipped.append({"row": raw["row"], "description": raw.get("description", ""), "reason": exc.message})
            continue
        except Exception as exc:
            message = getattr(exc, "message", "Nao foi possivel consolidar o valor em reais.")
            skipped.append({"row": raw["row"], "description": raw.get("description", ""), "reason": message})
            continue
        with get_connection() as conn:
            begin_immediate(conn)
            conn.execute("SAVEPOINT import_row")
            try:
                if raw.get("_preview_reviewed"):
                    category_group, category_name, subcategory_name = validate_reviewed_classification(
                        conn,
                        user_id,
                        transaction["category"],
                        transaction["subcategory"],
                        transaction["type"],
                    )
                    tags = transaction["tags"]
                else:
                    category_group, category_name, subcategory_name, tags = resolve_import_classification(conn, user_id, transaction)
                transaction["category"] = category_name
                transaction["subcategory"] = subcategory_name
                transaction["tags"] = tags
                duplicate_action = raw.get("_duplicate_action")
                if duplicate_action == "ignore":
                    # spec: importacao/importacao-dados v1.16 — critério 43
                    if not get_import_duplicate_candidates(
                        conn, user_id, "account", normalized_account_id, transaction["type"], transaction["date"],
                        transaction["amount_cents"], transaction["category"], transaction["subcategory"],
                    ):
                        raise ImportError("A duplicidade não está mais presente; revise a linha antes de ignorar.")
                    learn_import_adjustment_from_row(
                        conn, user_id, "account", normalized_account_id, raw, transaction["type"],
                        transaction["description"], transaction["category"], transaction["subcategory"],
                        transaction["tags"],
                    )
                    conn.execute("RELEASE SAVEPOINT import_row")
                    skipped.append({
                        "row": raw.get("row", ""),
                        "description": transaction["description"],
                        "reason": "Linha ignorada conforme sua escolha.",
                    })
                    continue
                if duplicate_action == "replace":
                    created = replace_duplicate_import(
                        conn,
                        user_id,
                        "account",
                        normalized_account_id,
                        raw,
                        transaction["type"],
                        transaction["date"],
                        transaction["amount_cents"],
                        transaction["category"],
                        transaction["subcategory"],
                        transaction["description"],
                        transaction["tags"],
                        transaction["notes"],
                    )
                else:
                    duplicate_matches = get_import_duplicate_candidates(
                        conn,
                        user_id,
                        "account",
                        normalized_account_id,
                        transaction["type"],
                        transaction["date"],
                        transaction["amount_cents"],
                        transaction["category"],
                        transaction["subcategory"],
                    )
                    if duplicate_matches:
                        raise ImportError("Linha duplicada; escolha substituir ou ignorar na prévia.")
                    category_id = get_or_create_category(conn, user_id, transaction["category"], category_group)
                    subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
                    tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
                    cursor = conn.execute(
                        """
                        INSERT INTO transactions (
                            user_id, type, description, normalized_description, amount_cents, exchange_rate_micros, amount_brl_cents, date, account_id,
                            category_id, subcategory_id, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            transaction["type"],
                            transaction["description"],
                            normalize_description(transaction["description"]),
                            transaction["amount_cents"],
                            exchange_rate_micros,
                            amount_brl_cents,
                            transaction["date"],
                            normalized_account_id,
                            category_id,
                            subcategory_id,
                            transaction["notes"],
                        ),
                    )
                    created = {"id": cursor.lastrowid}
                    replace_transaction_tags(conn, cursor.lastrowid, tag_ids)
                    recompute_account_balance(conn, user_id, normalized_account_id)
                learn_import_adjustment_from_row(
                    conn,
                    user_id,
                    "account",
                    normalized_account_id,
                    raw,
                    transaction["type"],
                    transaction["description"],
                    transaction["category"],
                    transaction["subcategory"],
                    transaction["tags"],
                )
                conn.execute("RELEASE SAVEPOINT import_row")
                imported.append({
                    "row": raw["row"],
                    "id": created["id"],
                    "description": transaction["description"],
                    "replaced": duplicate_action == "replace",
                })
            except Exception as exc:
                conn.execute("ROLLBACK TO SAVEPOINT import_row")
                conn.execute("RELEASE SAVEPOINT import_row")
                skipped.append({
                    "row": raw.get("row", ""),
                    "description": raw.get("description", ""),
                    "reason": getattr(exc, "message", str(exc) or "Nao foi possivel importar a linha."),
                })
    return {
        "operation_batch_id": operation_batch_id,
        "imported": len(imported),
        "skipped": len(skipped),
        "total_rows": len(raw_rows),
        "rows": imported,
        "errors": skipped,
    }


def preview_legacy_transactions(user_id: int, account_id: object, file_bytes: bytes, filename: str) -> dict:
    normalized_account_id = normalize_account_id(account_id)
    with get_connection() as conn:
        get_active_account(conn, user_id, normalized_account_id)
    raw_rows = parse_legacy_file(file_bytes, filename)
    preview_rows = []
    errors = []
    adjustments = {}
    with get_connection() as conn:
        for index, raw in enumerate(raw_rows):
            try:
                amount = normalize_amount(raw.get("amount"))
            except ImportError:
                continue
            transaction_type = "income" if amount > 0 else "expense"
            adjustment = find_import_adjustment(
                conn,
                user_id,
                "account",
                normalized_account_id,
                raw.get("description"),
                transaction_type,
            )
            if adjustment:
                adjustments[index] = adjustment
    for index, raw in enumerate(raw_rows):
        try:
            original_raw = dict(raw)
            adjustment = adjustments.get(index)
            if adjustment:
                apply_import_adjustment_to_row(raw, adjustment)
            transaction = normalize_imported_transaction(raw)
            signed_amount = transaction["amount_cents"] * (1 if transaction["type"] == "income" else -1)
            preview_rows.append({
                "row": raw["row"],
                "selected": True,
                "raw": original_raw,
                "values": {
                    "data": transaction["date"],
                    "descricao_original": original_raw.get("description") or "",
                    "descricao": transaction["description"],
                    "valor": f"{Decimal(signed_amount) / Decimal(100):.2f}".replace(".", ","),
                    "categoria": transaction["category"],
                    "subcategoria": transaction["subcategory"] or "",
                    "tags": "; ".join(transaction["tags"]),
                    "observacoes": transaction["notes"] or "",
                },
                "learned_adjustment": adjustment is not None,
            })
        except ImportError as exc:
            errors.append({
                "row": raw.get("row", ""),
                "description": raw.get("description", ""),
                "reason": exc.message,
            })
    with get_connection() as conn:
        duplicate_rows = find_preview_duplicate_matches(
            conn,
            user_id,
            "account",
            normalized_account_id,
            preview_rows,
            is_legacy=True,
        )
    for preview_row, matches in zip(preview_rows, duplicate_rows):
        preview_row["duplicate_matches"] = matches
    return {
        "preview": preview_rows,
        "errors": errors[:50],
        "total_rows": len(raw_rows),
        "imported": 0,
        "skipped": len(errors),
        "selected_rows": len(preview_rows),
        "classification_options": {
            "categories": list_categories(user_id),
            "tags": list_tags(user_id),
        },
    }


def find_preview_duplicate_matches(
    conn,
    user_id: int,
    source_type: str,
    source_id: int,
    preview_rows: list[dict],
    *,
    is_legacy: bool,
) -> list[list[dict]]:
    matches_by_row = []
    for row in preview_rows:
        try:
            raw = legacy_preview_row_to_raw(row) if is_legacy else coerce_preview_row_to_raw(row)
            if is_legacy:
                payload = normalize_imported_transaction(raw)
                transaction_type = payload["type"]
                transaction_date = payload["date"]
                amount_cents = payload["amount_cents"]
                category = payload["category"]
                subcategory = payload["subcategory"]
            else:
                payload = (
                    normalize_system_card_row(raw, source_id)
                    if source_type == "credit_card"
                    else normalize_system_account_row(raw, source_id)
                )
                transaction_type = payload["type"]
                transaction_date = payload["date"]
                amount_cents = money_decimal_to_cents(normalize_amount(payload["amount"]))
                category = payload["category"]
                subcategory = payload["subcategory"]
            if not category:
                matches_by_row.append([])
                continue
            _, category, subcategory = validate_reviewed_classification(
                conn,
                user_id,
                category,
                subcategory,
                transaction_type,
            )
            matches = get_import_duplicate_candidates(
                conn,
                user_id,
                source_type,
                source_id,
                transaction_type,
                transaction_date,
                amount_cents,
                category,
                subcategory,
            )
            matches_by_row.append(matches)
        except (ImportError, ValueError):
            matches_by_row.append([])
    return matches_by_row


def check_import_duplicates(
    user_id: int,
    target: str,
    target_id: object,
    preview_rows: list[dict],
    *,
    is_legacy: bool = False,
) -> list[dict]:
    normalized_target = normalize_import_target(target)
    normalized_id = positive_int_id(target_id)
    source_type = "credit_card" if normalized_target == "card" else "account"
    with get_connection() as conn:
        if normalized_target == "card":
            get_active_credit_card(conn, user_id, normalized_id)
        else:
            get_active_account(conn, user_id, normalized_id)
        matches = find_preview_duplicate_matches(
            conn,
            user_id,
            source_type,
            normalized_id,
            preview_rows,
            is_legacy=is_legacy,
        )
    return [
        {"row": row.get("row"), "matches": row_matches}
        for row, row_matches in zip(preview_rows, matches)
    ]


def legacy_preview_row_to_raw(row: dict) -> dict:
    values = row.get("values")
    original = row.get("raw")
    if not isinstance(values, dict) or (original is not None and not isinstance(original, dict)):
        raise ImportError("Dados de revisão inválidos para importação.")
    raw = dict(original or {})
    raw["_import_original"] = dict(original or {})
    raw["_preview_reviewed"] = True
    raw["_duplicate_action"] = row.get("duplicate_action")
    raw["_duplicate_target_id"] = row.get("duplicate_target_id")
    edited_fields = row.get("edited_fields", [])
    raw["_edited_fields"] = [
        field for field in edited_fields
        if field in LEARNABLE_IMPORT_FIELDS
    ] if isinstance(edited_fields, list) else []
    raw.update({
        "row": row.get("row", raw.get("row", "")),
        "date": values.get("data", ""),
        "description": values.get("descricao", ""),
        "amount": values.get("valor", ""),
        "category": values.get("categoria", ""),
        "subcategory": values.get("subcategoria", ""),
        "tag": values.get("tags", ""),
        "notes": values.get("observacoes", ""),
    })
    return raw


def normalize_imported_transaction(row: dict) -> dict:
    status = str(row.get("status") or "").strip().lower()
    if status and status != "pago":
        raise ImportError("Lancamento ignorado porque a situacao nao esta como Pago.")
    amount = normalize_amount(row.get("amount"))
    if amount == 0:
        raise ImportError("Valor precisa ser diferente de zero.")
    description = " ".join(str(row.get("description") or "").strip().split())
    if not description:
        raise ImportError("Informe a descricao.")
    try:
        category_value = row.get("category")
        if normalize_key(category_value) in {"transferencia", "transferencias"}:
            raise ImportError("Transferencia ignorada porque o arquivo nao informa a conta de destino.")
        if not str(category_value or "").strip() and "fatura" in normalize_key(description):
            category_value = "Pagamento de fatura"
        category, subcategory = normalize_category_parts(category_value, row.get("subcategory"))
        tags = normalize_import_tags(row.get("tag"))
    except ClassificationError as exc:
        raise ImportError(exc.message) from exc
    except Exception as exc:
        message = getattr(exc, "message", "Informe ao menos uma tag.")
        raise ImportError(message) from exc
    notes = " ".join(str(row.get("notes") or "").strip().split()) or None
    return {
        "type": "income" if amount > 0 else "expense",
        "description": description,
        "amount_cents": money_decimal_to_cents(abs(amount)),
        "date": normalize_import_date(row.get("date")),
        "category": category,
        "subcategory": subcategory,
        "tags": tags,
        "notes": notes,
        "raw_category": str(row.get("category") or "").strip(),
        "raw_subcategory": str(row.get("subcategory") or "").strip(),
    }


def resolve_import_classification(conn, user_id: int, transaction: dict) -> tuple[str, str, str | None, list[str]]:
    raw_category = transaction.get("raw_category") or transaction["category"]
    raw_subcategory = transaction.get("raw_subcategory") or transaction["subcategory"]
    tags = transaction["tags"]
    hint = classification_hint(raw_category, raw_subcategory, transaction["description"], tags)
    if is_investment_import(raw_category, tags, transaction["description"]):
        group = "investment" if transaction["type"] == "expense" else "income"
        category, subcategory = investment_classification(transaction, hint)
    elif transaction["type"] == "income":
        group = "income"
        category, subcategory = semantic_classification(
            raw_category,
            raw_subcategory,
            hint,
            INCOME_CATEGORY_ALIASES,
            INCOME_HINT_ALIASES,
            transaction["category"],
            transaction["subcategory"],
        )
    else:
        group = "expense"
        category, subcategory = semantic_classification(
            raw_category,
            raw_subcategory,
            hint,
            EXPENSE_CATEGORY_ALIASES,
            EXPENSE_HINT_ALIASES,
            transaction["category"],
            transaction["subcategory"],
        )
    category = match_existing_category(conn, user_id, group, category)
    subcategory = match_existing_subcategory(conn, user_id, group, category, subcategory)
    tags = [match_existing_tag(conn, user_id, tag) for tag in tags]
    return group, category, subcategory, tags


# spec: importacao/importacao-dados v1.16 — critério 33
def validate_reviewed_classification(
    conn,
    user_id: int,
    category_name: object,
    subcategory_name: object,
    transaction_type: str,
) -> tuple[str, str, str | None]:
    if transaction_type in {"transfer", "exchange"} and not str(category_name or "").strip():
        return "expense", "", None

    normalized_category = normalize_key(category_name)
    allowed_groups = {
        "income": {"income"},
        "investment": {"investment"},
        "expense": {"expense"},
    }.get(transaction_type, set())
    categories = conn.execute(
        "SELECT id, name, group_type FROM categories WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    category = next(
        (
            item
            for item in categories
            if item["group_type"] in allowed_groups
            and normalize_key(item["name"]) == normalized_category
        ),
        None,
    )
    if category is None:
        raise ImportError("Escolha uma categoria existente compatível com o tipo do lançamento.")

    normalized_subcategory = normalize_key(subcategory_name)
    if not normalized_subcategory:
        return category["group_type"], category["name"], None
    subcategory = conn.execute(
        """
        SELECT name
        FROM subcategories
        WHERE user_id = ? AND category_id = ?
        """,
        (user_id, category["id"]),
    ).fetchall()
    matched_subcategory = next(
        (item["name"] for item in subcategory if normalize_key(item["name"]) == normalized_subcategory),
        None,
    )
    if matched_subcategory is None:
        raise ImportError("Escolha uma subcategoria existente para a categoria selecionada.")
    return category["group_type"], category["name"], matched_subcategory


# spec: importacao/importacao-dados v1.16 — critérios 34 e 38
def get_import_duplicate_candidates(
    conn,
    user_id: int,
    source_type: str,
    source_id: int,
    transaction_type: str,
    transaction_date: str,
    amount_cents: int,
    category_name: object,
    subcategory_name: object,
) -> list[dict]:
    if transaction_type not in {"income", "expense", "investment"}:
        return []
    category_id = None
    subcategory_id = None
    if str(category_name or "").strip():
        category_group = {
            "income": "income",
            "expense": "expense",
            "investment": "investment",
        }[transaction_type]
        category = conn.execute(
            """
            SELECT id FROM categories
            WHERE user_id = ? AND group_type = ? AND name = ? COLLATE NOCASE
            """,
            (user_id, category_group, str(category_name).strip()),
        ).fetchone()
        if category is None:
            return []
        category_id = category["id"]
        if str(subcategory_name or "").strip():
            subcategory = conn.execute(
                """
                SELECT id FROM subcategories
                WHERE user_id = ? AND category_id = ? AND name = ? COLLATE NOCASE
                """,
                (user_id, category_id, str(subcategory_name).strip()),
            ).fetchone()
            if subcategory is None:
                return []
            subcategory_id = subcategory["id"]

    if source_type == "account":
        table = "transactions"
        source_column = "account_id"
    elif source_type == "credit_card":
        table = "credit_card_transactions"
        source_column = "credit_card_id"
    else:
        return []
    rows = conn.execute(
        f"""
        SELECT
            existing.id,
            existing.description,
            existing.date,
            existing.amount_cents,
            existing.type,
            categories.name AS category,
            subcategories.name AS subcategory
        FROM {table} AS existing
        LEFT JOIN categories ON categories.id = existing.category_id
        LEFT JOIN subcategories ON subcategories.id = existing.subcategory_id
        WHERE existing.user_id = ? AND existing.{source_column} = ?
            AND existing.archived_at IS NULL
            AND existing.type = ? AND existing.date = ? AND existing.amount_cents = ?
            AND existing.category_id IS ? AND existing.subcategory_id IS ?
        ORDER BY existing.id
        """,
        (
            user_id,
            source_id,
            transaction_type,
            transaction_date,
            amount_cents,
            category_id,
            subcategory_id,
        ),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def has_import_duplicate(
    conn,
    user_id: int,
    source_type: str,
    source_id: int,
    transaction_type: str,
    transaction_date: str,
    amount_cents: int,
    category_name: object,
    subcategory_name: object,
    selected_id: object = None,
) -> bool:
    candidates = get_import_duplicate_candidates(
        conn,
        user_id,
        source_type,
        source_id,
        transaction_type,
        transaction_date,
        amount_cents,
        category_name,
        subcategory_name,
    )
    if selected_id is None or selected_id == "":
        return bool(candidates)
    try:
        normalized_id = positive_int_id(selected_id)
    except ValueError:
        return False
    return any(candidate["id"] == normalized_id for candidate in candidates)


# spec: importacao/importacao-dados v1.16 — critérios 35 a 37
def replace_duplicate_import(
    conn,
    user_id: int,
    source_type: str,
    source_id: int,
    raw: dict,
    transaction_type: str,
    transaction_date: str,
    amount_cents: int,
    category_name: object,
    subcategory_name: object,
    description: object,
    tags: object,
    notes: object,
) -> dict:
    selected_id = raw.get("_duplicate_target_id")
    candidates = get_import_duplicate_candidates(
        conn,
        user_id,
        source_type,
        source_id,
        transaction_type,
        transaction_date,
        amount_cents,
        category_name,
        subcategory_name,
    )
    try:
        selected_id = positive_int_id(selected_id)
    except ValueError as exc:
        raise ImportError("Selecione o lançamento duplicado que deseja substituir.") from exc
    if not any(candidate["id"] == selected_id for candidate in candidates):
        raise ImportError("O lançamento escolhido não corresponde mais à duplicidade detectada.")

    category_group, normalized_category, normalized_subcategory = validate_reviewed_classification(
        conn,
        user_id,
        category_name,
        subcategory_name,
        transaction_type,
    )
    category_id = get_or_create_category(conn, user_id, normalized_category, category_group)
    subcategory_id = get_or_create_subcategory(conn, user_id, category_id, normalized_subcategory)
    if isinstance(tags, list):
        normalized_tags = tags
    elif not str(tags or "").strip():
        normalized_tags = []
    else:
        normalized_tags = normalize_tags(tags)
    tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in normalized_tags]
    if source_type == "account":
        conn.execute(
            """
            UPDATE transactions
            SET description = ?, normalized_description = ?, category_id = ?, subcategory_id = ?,
                notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND account_id = ? AND archived_at IS NULL
            """,
            (
                " ".join(str(description or "").split()),
                normalize_description(description),
                category_id,
                subcategory_id,
                " ".join(str(notes or "").split()) or None,
                selected_id,
                user_id,
                source_id,
            ),
        )
        replace_transaction_tags(conn, selected_id, tag_ids)
    else:
        conn.execute(
            """
            UPDATE credit_card_transactions
            SET description = ?, normalized_description = ?, category_id = ?, subcategory_id = ?,
                notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ? AND credit_card_id = ? AND archived_at IS NULL
            """,
            (
                " ".join(str(description or "").split()),
                normalize_description(description),
                category_id,
                subcategory_id,
                " ".join(str(notes or "").split()) or None,
                selected_id,
                user_id,
                source_id,
            ),
        )
        replace_credit_card_transaction_tags(conn, selected_id, tag_ids)
    return {"id": selected_id}


def semantic_classification(raw_category, raw_subcategory, hint, category_aliases, hint_aliases, fallback_category, fallback_subcategory):
    category_key = normalize_key(raw_category)
    hint_key = normalize_key(hint)
    category, subcategory = category_aliases.get(category_key, (fallback_category, fallback_subcategory))
    for key, target in hint_aliases.items():
        if key in hint_key:
            category, subcategory = target
            break
    return category, subcategory or fallback_subcategory


def investment_classification(transaction: dict, hint: str) -> tuple[str, str | None]:
    hint_key = normalize_key(hint)
    if transaction["type"] == "income":
        if any(key in hint_key for key in ("dividendo", "jcp", "fii", "itub4", "vale3", "isae4", "etf")):
            return "Rendimentos e Investimentos", "Dividendos / JCP"
        return "Rendimentos e Investimentos", "Rendimento de Renda Fixa"
    for key, target in INVESTMENT_TAG_CATEGORY_ALIASES.items():
        if key in hint_key:
            return target
    return "Outros Investimentos", None


def is_investment_import(raw_category: object, tags: list[str], description: str) -> bool:
    hint = normalize_key(classification_hint(raw_category, "", description, tags))
    return "investimento" in normalize_key(raw_category) or any(key in hint for key in INVESTMENT_TAG_CATEGORY_ALIASES)


def classification_hint(raw_category: object, raw_subcategory: object, description: str, tags: list[str]) -> str:
    return " ".join([
        str(raw_category or ""),
        str(raw_subcategory or ""),
        description or "",
        " ".join(tags),
    ])


def normalize_import_tags(value: object) -> list[str]:
    if not str(value or "").strip():
        return []
    return normalize_tags(value)


def match_existing_category(conn, user_id: int, group: str, name: str) -> str:
    rows = conn.execute(
        "SELECT name FROM categories WHERE user_id = ? AND group_type = ?",
        (user_id, group),
    ).fetchall()
    return best_existing_name(rows, name)


def match_existing_subcategory(conn, user_id: int, group: str, category_name: str, subcategory_name: str | None) -> str | None:
    if not subcategory_name:
        return None
    rows = conn.execute(
        """
        SELECT subcategories.name
        FROM subcategories
        JOIN categories ON categories.id = subcategories.category_id
        WHERE categories.user_id = ? AND categories.group_type = ? AND categories.name = ?
        """,
        (user_id, group, category_name),
    ).fetchall()
    return best_existing_name(rows, subcategory_name)


def match_existing_tag(conn, user_id: int, name: str) -> str:
    rows = conn.execute("SELECT name FROM tags WHERE user_id = ?", (user_id,)).fetchall()
    return best_existing_name(rows, name)


def best_existing_name(rows, proposed: str) -> str:
    names = [row_to_dict(row)["name"] for row in rows]
    proposed_key = normalize_key(proposed)
    for name in names:
        if normalize_key(name) == proposed_key:
            return name
    scored = [
        (SequenceMatcher(None, proposed_key, normalize_key(name)).ratio(), name)
        for name in names
    ]
    if scored:
        score, name = max(scored, key=lambda item: item[0])
        if score >= 0.84:
            return name
    return proposed


def normalize_category_parts(category_value: object, subcategory_value: object) -> tuple[str, str | None]:
    raw_category = str(category_value or "").strip()
    raw_subcategory = str(subcategory_value or "").strip()
    if not raw_subcategory:
        for separator in (" > ", " / ", " - "):
            if separator in raw_category:
                category_part, subcategory_part = raw_category.split(separator, 1)
                raw_category = category_part
                raw_subcategory = subcategory_part
                break
    category = normalize_name(raw_category, "Informe a categoria.")
    subcategory = normalize_name(raw_subcategory, "Informe a subcategoria.") if raw_subcategory else None
    return category, subcategory
