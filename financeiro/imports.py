from __future__ import annotations

import csv
import struct
import unicodedata
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from http import HTTPStatus
from io import StringIO

from financeiro.categories import ClassificationError, get_or_create_category, get_or_create_subcategory, get_or_create_tag, normalize_name
from financeiro.credit_cards import create_credit_card_transaction
from financeiro.transactions import (
    apply_balance_delta,
    balance_delta,
    convert_to_brl_cents,
    create_transaction,
    get_active_account,
    normalize_tags,
    replace_transaction_tags,
    resolve_exchange_rate_micros,
)
from financeiro.database import get_connection, row_to_dict

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
SYSTEM_IMPORT_ACCOUNT_HEADERS = [
    "data",
    "tipo",
    "descricao",
    "valor",
    "categoria",
    "subcategoria",
    "tags",
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
    "observacoes",
]
END_OF_CHAIN = 0xFFFFFFFE
FREE_SECTOR = 0xFFFFFFFF
HEADER_ALIASES = {
    "data": "date",
    "descrição": "description",
    "descricao": "description",
    "categoria": "category",
    "subcategoria": "subcategory",
    "sub-categoria": "subcategory",
    "valor": "amount",
    "situação": "status",
    "situacao": "status",
    "tags": "tag",
    "tag": "tag",
    "informações adicionais": "notes",
    "informacoes adicionais": "notes",
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


class ImportError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def system_import_template(user_id: int, target: str) -> bytes:
    normalized_target = normalize_import_target(target)
    headers = SYSTEM_IMPORT_CARD_HEADERS if normalized_target == "card" else SYSTEM_IMPORT_ACCOUNT_HEADERS
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="\n")
    writer.writerow(headers)
    if normalized_target == "card":
        writer.writerow(["2026-06-15", "2026-06", "expense", "Exemplo compra no cartão", "123,45", "Alimentação", "Restaurantes / Bares / Delivery", "Organizze; Revisar", "Linha exemplo"])
        writer.writerow(["2026-06-20", "2026-06", "income", "Exemplo estorno", "10,00", "Outras Receitas", "Reembolsos Corporativos", "Organizze", "Linha exemplo"])
    else:
        writer.writerow(["2026-06-15", "expense", "Exemplo mercado", "123,45", "Alimentação", "Supermercado / Feira / Hortifruti", "Organizze; Revisar", "", "", "", "", "Linha exemplo"])
        writer.writerow(["2026-06-15", "income", "Exemplo salário", "1000,00", "Trabalho e Salário", "Salário Líquido", "Organizze", "", "", "", "", "Linha exemplo"])
        writer.writerow(["2026-06-15", "transfer", "Exemplo transferência", "500,00", "", "", "", "2", "", "", "", "Informe conta_destino_id"])
        writer.writerow(["2026-06-15", "exchange", "Exemplo câmbio", "1000,00", "", "", "Câmbio", "3", "197,10", "0,197100", "", "Conta destino em outra moeda"])
    writer.writerow([])
    writer.writerow(["Categorias do sistema"])
    writer.writerow(["grupo", "categoria", "subcategoria"])
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
            writer.writerow([row["group_type"], row["category_name"], row["subcategory_name"] or ""])
        tags = conn.execute(
            "SELECT name FROM tags WHERE user_id = ? ORDER BY name COLLATE NOCASE",
            (user_id,),
        ).fetchall()
    writer.writerow([])
    writer.writerow(["Tags existentes"])
    writer.writerow(["tag"])
    for row in tags:
        writer.writerow([row["name"]])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def import_system_template(user_id: int, target: str, target_id: object, file_bytes: bytes, filename: str) -> dict:
    normalized_target = normalize_import_target(target)
    rows = parse_system_template_file(file_bytes, filename)
    imported = []
    skipped = []
    for raw in rows:
        try:
            if normalized_target == "card":
                payload = normalize_system_card_row(raw, target_id)
                created = create_credit_card_transaction(user_id, payload)
            else:
                payload = normalize_system_account_row(raw, target_id)
                created = create_transaction(user_id, payload)
            imported.append({"row": raw["row"], "id": created["id"], "description": payload["description"]})
        except Exception as exc:
            skipped.append({
                "row": raw.get("row", ""),
                "description": raw.get("descricao") or raw.get("description") or "",
                "reason": getattr(exc, "message", str(exc) or "Nao foi possivel importar a linha."),
            })
    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "total_rows": len(rows),
        "rows": imported,
        "errors": skipped[:50],
    }


def parse_system_template_file(file_bytes: bytes, filename: str) -> list[dict]:
    if not file_bytes:
        raise ImportError("Envie uma planilha modelo preenchida.")
    if not filename.lower().endswith(".csv"):
        raise ImportError("Envie o modelo em CSV UTF-8 separado por ponto e virgula.")
    rows = parse_csv_rows(file_bytes)
    if not rows:
        raise ImportError("Arquivo sem dados para importar.")
    headers = [normalize_template_header(value) for value in rows[0]]
    mapped_rows = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not any(str(value or "").strip() for value in row):
            continue
        if is_template_reference_section(row):
            break
        mapped_rows.append({
            "row": row_number,
            **{header: get_cell(row, index) for index, header in enumerate(headers) if header},
        })
    if not mapped_rows:
        raise ImportError("Nenhuma linha de lancamento encontrada no modelo.")
    return mapped_rows


def normalize_system_account_row(row: dict, account_id: object) -> dict:
    transaction_type = normalize_system_type(row.get("tipo") or row.get("type"))
    if transaction_type == "exchange":
        transaction_type = "transfer"
    payload = {
        "account_id": account_id,
        "type": transaction_type,
        "date": row.get("data") or row.get("date"),
        "description": row.get("descricao") or row.get("description"),
        "amount": row.get("valor") or row.get("amount"),
        "category": row.get("categoria") or row.get("category"),
        "subcategory": row.get("subcategoria") or row.get("subcategory"),
        "tags": row.get("tags") or row.get("tag"),
        "destination_account_id": row.get("conta_destino_id") or row.get("destination_account_id"),
        "destination_amount": row.get("valor_destino") or row.get("destination_amount"),
        "transfer_exchange_rate": row.get("cotacao_cambio") or row.get("transfer_exchange_rate"),
        "exchange_rate_to_brl": row.get("cotacao_brl") or row.get("exchange_rate_to_brl"),
        "notes": row.get("observacoes") or row.get("notes"),
        "series_kind": "single",
    }
    if payload["type"] == "transfer":
        payload["category"] = ""
        payload["subcategory"] = ""
    return payload


def normalize_system_card_row(row: dict, card_id: object) -> dict:
    return {
        "credit_card_id": card_id,
        "type": normalize_card_import_type(row.get("tipo") or row.get("type")),
        "date": row.get("data") or row.get("date"),
        "invoice_month": row.get("competencia_fatura") or row.get("invoice_month"),
        "description": row.get("descricao") or row.get("description"),
        "amount": row.get("valor") or row.get("amount"),
        "category": row.get("categoria") or row.get("category"),
        "subcategory": row.get("subcategoria") or row.get("subcategory"),
        "notes": row.get("observacoes") or row.get("notes"),
    }


def normalize_import_target(value: object) -> str:
    target = normalize_key(value)
    if target in {"card", "cartao", "cartoes", "credit_card"}:
        return "card"
    return "account"


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


def normalize_template_header(value: object) -> str:
    return normalize_key(value).replace(" ", "_").replace("-", "_")


def is_template_reference_section(row: list[object]) -> bool:
    first = normalize_key(get_cell(row, 0))
    return first in {"categorias_do_sistema", "tags_existentes"}


def import_organizze_transactions(user_id: int, account_id: object, file_bytes: bytes, filename: str) -> dict:
    normalized_account_id = normalize_account_id(account_id)
    raw_rows = parse_organizze_file(file_bytes, filename)
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
            category_group, category_name, subcategory_name, tags = resolve_import_classification(conn, user_id, transaction)
            transaction["category"] = category_name
            transaction["subcategory"] = subcategory_name
            transaction["tags"] = tags
            category_id = get_or_create_category(conn, user_id, transaction["category"], category_group)
            subcategory_id = get_or_create_subcategory(conn, user_id, category_id, transaction["subcategory"])
            tag_ids = [get_or_create_tag(conn, user_id, tag) for tag in transaction["tags"]]
            apply_balance_delta(
                conn,
                normalized_account_id,
                balance_delta(transaction["type"], transaction["amount_cents"], "source"),
            )
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    user_id, type, description, amount_cents, exchange_rate_micros, amount_brl_cents, date, account_id,
                    category_id, subcategory_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    transaction["type"],
                    transaction["description"],
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
            replace_transaction_tags(conn, cursor.lastrowid, tag_ids)
            imported.append({"row": raw["row"], "id": cursor.lastrowid, "description": transaction["description"]})
    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "total_rows": len(raw_rows),
        "rows": imported,
        "errors": skipped[:50],
    }


def parse_organizze_file(file_bytes: bytes, filename: str) -> list[dict]:
    if not file_bytes:
        raise ImportError("Envie um arquivo para importar.")
    name = filename.lower()
    if name.endswith(".xls") or file_bytes.startswith(OLE_MAGIC):
        rows = parse_xls_rows(file_bytes)
    elif name.endswith(".csv"):
        rows = parse_csv_rows(file_bytes)
    else:
        raise ImportError("Formato nao suportado. Envie o arquivo .xls exportado pelo Organizze.")
    return rows_to_transactions(rows)


def rows_to_transactions(rows: list[list[object]]) -> list[dict]:
    if not rows:
        raise ImportError("Arquivo sem dados para importar.")
    header_index = find_header_index(rows)
    headers = [normalize_header(value) for value in rows[header_index]]
    positions = {HEADER_ALIASES[header]: index for index, header in enumerate(headers) if header in HEADER_ALIASES}
    required = {"date", "description", "category", "amount", "tag"}
    missing = sorted(required - positions.keys())
    if missing:
        raise ImportError("Arquivo fora do modelo Organizze. Colunas obrigatorias ausentes: " + ", ".join(missing))
    transactions = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(str(value or "").strip() for value in row):
            continue
        transactions.append({
            "row": row_number,
            "date": get_cell(row, positions["date"]),
            "description": get_cell(row, positions["description"]),
            "category": get_cell(row, positions["category"]),
            "subcategory": get_cell(row, positions.get("subcategory")),
            "amount": get_cell(row, positions["amount"]),
            "status": get_cell(row, positions.get("status")),
            "tag": get_cell(row, positions["tag"]),
            "notes": get_cell(row, positions.get("notes")),
        })
    return transactions


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


def normalize_key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join("".join(char if char.isalnum() else " " for char in text).split())


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


def normalize_account_id(value: object) -> int:
    try:
        account_id = int(str(value or "").strip())
    except ValueError as exc:
        raise ImportError("Informe a conta que recebera a importacao.") from exc
    if account_id <= 0:
        raise ImportError("Informe a conta que recebera a importacao.")
    return account_id


def normalize_import_date(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value or "").strip()
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    raise ImportError("Data invalida.")


def normalize_amount(value: object) -> Decimal:
    raw = str(value or "").strip()
    if isinstance(value, (int, float, Decimal)):
        raw = str(value)
    raw = raw.replace("R$", "").replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ImportError("Valor invalido.") from exc


def money_decimal_to_cents(value: Decimal) -> int:
    return int((value * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def find_header_index(rows: list[list[object]]) -> int:
    for index, row in enumerate(rows[:20]):
        normalized = {normalize_header(value) for value in row}
        if {"data", "valor"}.issubset(normalized) and ("descrição" in normalized or "descricao" in normalized):
            return index
    raise ImportError("Nao encontrei o cabecalho do Organizze no arquivo.")


def normalize_header(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def get_cell(row: list[object], index: int | None) -> object:
    if index is None or index >= len(row):
        return ""
    return row[index]


def parse_csv_rows(file_bytes: bytes) -> list[list[object]]:
    text = file_bytes.decode("utf-8-sig")
    sample = text[:2048]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    return [row for row in csv.reader(StringIO(text), delimiter=delimiter)]


def parse_xls_rows(file_bytes: bytes) -> list[list[object]]:
    stream = read_ole_workbook_stream(file_bytes)
    shared_strings = []
    cells = {}
    in_sheet = False
    for record_type, payload in iter_biff_records(stream):
        if record_type == 0x0809 and len(payload) >= 4:
            in_sheet = struct.unpack_from("<H", payload, 2)[0] == 0x0010
        if record_type == 0x00FC:
            shared_strings = parse_shared_strings(payload)
        if not in_sheet:
            continue
        if record_type == 0x00FD:
            row, col, _, shared_index = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = shared_strings[shared_index]
        elif record_type == 0x0204:
            row, col, _ = struct.unpack_from("<HHH", payload, 0)
            length = struct.unpack_from("<H", payload, 6)[0]
            cells[(row, col)] = payload[8 : 8 + length].decode("latin1", "replace")
        elif record_type == 0x0203:
            row, col, _ = struct.unpack_from("<HHH", payload, 0)
            cells[(row, col)] = struct.unpack_from("<d", payload, 6)[0]
        elif record_type == 0x027E:
            row, col, _, raw = struct.unpack_from("<HHHI", payload, 0)
            cells[(row, col)] = decode_rk(raw)
        elif record_type == 0x00BD:
            row, first_col, last_col = struct.unpack_from("<HHH", payload, 0)
            offset = 6
            for col in range(first_col, last_col + 1):
                _, raw = struct.unpack_from("<HI", payload, offset)
                cells[(row, col)] = decode_rk(raw)
                offset += 6
    if not cells:
        return []
    max_row = max(row for row, _ in cells)
    max_col = max(col for _, col in cells)
    return [[cells.get((row, col), "") for col in range(max_col + 1)] for row in range(max_row + 1)]


def read_ole_workbook_stream(file_bytes: bytes) -> bytes:
    if not file_bytes.startswith(OLE_MAGIC):
        raise ImportError("Arquivo .xls invalido.")
    sector_size = 1 << struct.unpack_from("<H", file_bytes, 30)[0]
    fat_sector_count = struct.unpack_from("<I", file_bytes, 44)[0]
    first_dir_sector = struct.unpack_from("<I", file_bytes, 48)[0]
    difat = [
        sector for sector in struct.unpack_from("<109I", file_bytes, 76)
        if sector not in (FREE_SECTOR, END_OF_CHAIN)
    ]
    fat = []
    for sector in difat[:fat_sector_count]:
        offset = sector_offset(sector, sector_size)
        fat.extend(struct.unpack_from(f"<{sector_size // 4}I", file_bytes, offset))
    directory = read_sector_chain(file_bytes, fat, first_dir_sector, sector_size)
    for offset in range(0, len(directory), 128):
        entry = directory[offset : offset + 128]
        if len(entry) < 128:
            continue
        name_length = struct.unpack_from("<H", entry, 64)[0]
        if name_length < 2:
            continue
        name = entry[: name_length - 2].decode("utf-16le", "ignore")
        if name in {"Workbook", "Book"}:
            start_sector = struct.unpack_from("<I", entry, 116)[0]
            size = struct.unpack_from("<Q", entry, 120)[0]
            return read_sector_chain(file_bytes, fat, start_sector, sector_size, size)
    raise ImportError("Nao encontrei a planilha principal dentro do arquivo .xls.")


def read_sector_chain(file_bytes: bytes, fat: list[int], start_sector: int, sector_size: int, size: int | None = None) -> bytes:
    chunks = []
    sector = start_sector
    seen = set()
    while sector not in (END_OF_CHAIN, FREE_SECTOR) and sector < len(fat) and sector not in seen:
        seen.add(sector)
        offset = sector_offset(sector, sector_size)
        chunks.append(file_bytes[offset : offset + sector_size])
        sector = fat[sector]
    data = b"".join(chunks)
    return data[:size] if size is not None else data


def sector_offset(sector: int, sector_size: int) -> int:
    return (sector + 1) * sector_size


def iter_biff_records(stream: bytes):
    position = 0
    while position + 4 <= len(stream):
        record_type, length = struct.unpack_from("<HH", stream, position)
        position += 4
        payload = stream[position : position + length]
        position += length
        yield record_type, payload


def parse_shared_strings(payload: bytes) -> list[str]:
    if len(payload) < 8:
        return []
    _, unique_count = struct.unpack_from("<II", payload, 0)
    position = 8
    values = []
    for _ in range(unique_count):
        value, position = parse_biff_string(payload, position)
        values.append(value)
    return values


def parse_biff_string(payload: bytes, position: int) -> tuple[str, int]:
    char_count = struct.unpack_from("<H", payload, position)[0]
    position += 2
    flags = payload[position]
    position += 1
    is_utf16 = bool(flags & 0x01)
    rich_runs = 0
    extension_size = 0
    if flags & 0x08:
        rich_runs = struct.unpack_from("<H", payload, position)[0]
        position += 2
    if flags & 0x04:
        extension_size = struct.unpack_from("<I", payload, position)[0]
        position += 4
    byte_count = char_count * (2 if is_utf16 else 1)
    raw = payload[position : position + byte_count]
    position += byte_count
    value = raw.decode("utf-16le" if is_utf16 else "latin1", "replace")
    position += rich_runs * 4 + extension_size
    return value, position


def decode_rk(raw: int) -> Decimal:
    divide_by_100 = bool(raw & 0x01)
    is_integer = bool(raw & 0x02)
    if is_integer:
        value = raw & 0xFFFFFFFC
        if value & 0x80000000:
            value -= 0x100000000
        decoded = Decimal(value >> 2)
    else:
        packed = struct.pack("<Q", (raw & 0xFFFFFFFC) << 32)
        decoded = Decimal(str(struct.unpack("<d", packed)[0]))
    return decoded / Decimal(100) if divide_by_100 else decoded
