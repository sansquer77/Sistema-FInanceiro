from __future__ import annotations

from http import HTTPStatus

from financeiro.database import get_connection
from financeiro.database import row_to_dict

GROUP_TYPES = {"income", "expense", "investment"}
GROUP_ALIASES = {
    "receita": "income",
    "receitas": "income",
    "income": "income",
    "despesa": "expense",
    "despesas": "expense",
    "expense": "expense",
    "investimento": "investment",
    "investimentos": "investment",
    "investment": "investment",
}


class ClassificationError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def get_or_create_category(conn, user_id: int, name: str, group_type: object = "expense") -> int:
    return get_or_create_named_item(conn, "categories", user_id, name, "Informe a categoria.", group_type)


def get_or_create_subcategory(conn, user_id: int, category_id: int, name: str | None) -> int | None:
    if not str(name or "").strip():
        return None
    ensure_category_exists(conn, user_id, category_id)
    normalized = normalize_name(name, "Informe a subcategoria.")
    row = conn.execute(
        """
        SELECT id
        FROM subcategories
        WHERE user_id = ? AND category_id = ? AND name = ?
        """,
        (user_id, category_id, normalized),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        """
        INSERT INTO subcategories (user_id, category_id, name)
        VALUES (?, ?, ?)
        """,
        (user_id, category_id, normalized),
    )
    return cursor.lastrowid


def get_or_create_tag(conn, user_id: int, name: str) -> int:
    return get_or_create_named_item(conn, "tags", user_id, name, "Informe a tag.")


def list_categories(user_id: int, group_type: object | None = None) -> list[dict]:
    return list_named_items("categories", user_id, group_type)


def list_tags(user_id: int) -> list[dict]:
    return list_named_items("tags", user_id)


def create_category(user_id: int, name: str, group_type: object = "expense") -> dict:
    return create_named_item("categories", user_id, name, "Informe a categoria.", group_type)


def create_subcategory(user_id: int, category_id: object, name: str) -> dict:
    normalized_category_id = normalize_item_id(category_id, "Informe a categoria.")
    normalized = normalize_name(name, "Informe a subcategoria.")
    try:
        with get_connection() as conn:
            ensure_category_exists(conn, user_id, normalized_category_id)
            cursor = conn.execute(
                """
                INSERT INTO subcategories (user_id, category_id, name)
                VALUES (?, ?, ?)
                """,
                (user_id, normalized_category_id, normalized),
            )
            return fetch_subcategory(conn, user_id, cursor.lastrowid)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe uma subcategoria com este nome nesta categoria.", HTTPStatus.CONFLICT) from exc
        raise


def create_tag(user_id: int, name: str) -> dict:
    return create_named_item("tags", user_id, name, "Informe a tag.")


def update_category(user_id: int, item_id: str, name: str) -> dict:
    return update_category_name(user_id, item_id, name)


def update_subcategory(user_id: int, item_id: str, name: str) -> dict:
    normalized_id = normalize_item_id(item_id, "Subcategoria nao encontrada.")
    normalized = normalize_name(name, "Informe a subcategoria.")
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE subcategories
                SET name = ?
                WHERE id = ? AND user_id = ?
                """,
                (normalized, normalized_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)
            return fetch_subcategory(conn, user_id, normalized_id)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe uma subcategoria com este nome nesta categoria.", HTTPStatus.CONFLICT) from exc
        raise


def update_tag(user_id: int, item_id: str, name: str) -> dict:
    return update_named_item("tags", user_id, item_id, name, "Informe a tag.")


def delete_category(user_id: int, item_id: str) -> None:
    delete_named_item("categories", user_id, item_id)


def delete_subcategory(user_id: int, item_id: str) -> None:
    normalized_id = normalize_item_id(item_id, "Subcategoria nao encontrada.")
    with get_connection() as conn:
        used = subcategory_usage_count(conn, user_id, normalized_id)
        if used:
            raise ClassificationError("Nao e possivel excluir uma subcategoria usada em lancamentos.")
        clear_archived_subcategory_references(conn, user_id, normalized_id)
        cursor = conn.execute(
            """
            DELETE FROM subcategories
            WHERE id = ? AND user_id = ?
            """,
            (normalized_id, user_id),
        )
        if cursor.rowcount == 0:
            raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)


def delete_tag(user_id: int, item_id: str) -> None:
    delete_named_item("tags", user_id, item_id)


def list_named_items(table: str, user_id: int, group_type: object | None = None) -> list[dict]:
    ensure_allowed_table(table)
    normalized_group = normalize_group_type(group_type, required=False) if table == "categories" else None
    category_group_filter = "AND items.group_type = ?" if normalized_group else ""
    params = [user_id, user_id, user_id] if table == "categories" else [user_id, user_id]
    if normalized_group:
        params.append(normalized_group)
    usage_sql = {
        "categories": category_usage_count_sql("items.id"),
        "tags": """
            SELECT (
                SELECT COUNT(*)
                FROM transaction_tags
                JOIN transactions ON transactions.id = transaction_tags.transaction_id
                WHERE transaction_tags.tag_id = items.id
                    AND transactions.user_id = ?
                    AND transactions.archived_at IS NULL
            ) + (
                SELECT COUNT(*)
                FROM credit_card_transaction_tags
                JOIN credit_card_transactions
                    ON credit_card_transactions.id = credit_card_transaction_tags.credit_card_transaction_id
                WHERE credit_card_transaction_tags.tag_id = items.id
                    AND credit_card_transactions.user_id = ?
                    AND credit_card_transactions.archived_at IS NULL
            )
        """,
    }[table]
    params = [user_id, user_id, user_id] if table == "tags" else params
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                items.id,
                items.name,
                {"items.group_type," if table == "categories" else ""}
                items.created_at,
                ({usage_sql}) AS transaction_count
            FROM {table} AS items
            WHERE items.user_id = ? {category_group_filter}
            ORDER BY items.name COLLATE NOCASE
            """,
            tuple(params),
        ).fetchall()
        items = [row_to_dict(row) for row in rows]
        if table == "categories":
            attach_subcategories(conn, user_id, items)
    return items


def attach_subcategories(conn, user_id: int, categories: list[dict]) -> None:
    if not categories:
        return
    rows = conn.execute(
        """
        SELECT
            subcategories.id,
            subcategories.category_id,
            subcategories.name,
            subcategories.created_at,
            (
                SELECT COUNT(*)
                FROM transactions
                WHERE transactions.subcategory_id = subcategories.id
                    AND transactions.user_id = subcategories.user_id
                    AND transactions.archived_at IS NULL
            ) + (
                SELECT COUNT(*)
                FROM credit_card_transactions
                WHERE credit_card_transactions.subcategory_id = subcategories.id
                    AND credit_card_transactions.user_id = subcategories.user_id
                    AND credit_card_transactions.archived_at IS NULL
            ) AS transaction_count
        FROM subcategories
        WHERE subcategories.user_id = ?
        ORDER BY subcategories.name COLLATE NOCASE
        """,
        (user_id,),
    ).fetchall()
    by_category = {category["id"]: [] for category in categories}
    for row in rows:
        subcategory = row_to_dict(row)
        if subcategory["category_id"] in by_category:
            by_category[subcategory["category_id"]].append(subcategory)
    for category in categories:
        category["subcategories"] = by_category[category["id"]]


def create_named_item(table: str, user_id: int, name: str, required_message: str, group_type: object = "expense") -> dict:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    normalized_group = normalize_group_type(group_type) if table == "categories" else None
    try:
        with get_connection() as conn:
            if table == "categories":
                cursor = conn.execute(
                    "INSERT INTO categories (user_id, name, group_type) VALUES (?, ?, ?)",
                    (user_id, normalized, normalized_group),
                )
                row = conn.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (cursor.lastrowid, user_id)).fetchone()
                return row_to_dict(row)
            cursor = conn.execute(
                f"INSERT INTO {table} (user_id, name) VALUES (?, ?)",
                (user_id, normalized),
            )
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (cursor.lastrowid, user_id)).fetchone()
            return row_to_dict(row)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            message = "Ja existe uma categoria com este nome neste grupo." if table == "categories" else "Ja existe um item com este nome."
            raise ClassificationError(message, HTTPStatus.CONFLICT) from exc
        raise


def update_category_name(user_id: int, item_id: str, name: str) -> dict:
    normalized_id = normalize_item_id(item_id, "Categoria nao encontrada.")
    normalized = normalize_name(name, "Informe a categoria.")
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE categories
                SET name = ?
                WHERE id = ? AND user_id = ?
                """,
                (normalized, normalized_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ClassificationError("Categoria nao encontrada.", HTTPStatus.NOT_FOUND)
            row = conn.execute(
                "SELECT * FROM categories WHERE id = ? AND user_id = ?",
                (normalized_id, user_id),
            ).fetchone()
            return row_to_dict(row)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe uma categoria com este nome neste grupo.", HTTPStatus.CONFLICT) from exc
        raise


def update_named_item(table: str, user_id: int, item_id: str, name: str, required_message: str) -> dict:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE {table} SET name = ? WHERE id = ? AND user_id = ?",
                (normalized, item_id, user_id),
            )
            if cursor.rowcount == 0:
                raise ClassificationError("Item nao encontrado.", HTTPStatus.NOT_FOUND)
            row = conn.execute(f"SELECT * FROM {table} WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
            return row_to_dict(row)
    except ClassificationError:
        raise
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ClassificationError("Ja existe um item com este nome.", HTTPStatus.CONFLICT) from exc
        raise


def delete_named_item(table: str, user_id: int, item_id: str) -> None:
    ensure_allowed_table(table)
    normalized_id = normalize_item_id(item_id, "Item nao encontrado.")
    usage_query = {
        "categories": f"SELECT ({category_usage_count_sql('?')}) AS total",
        "tags": """
            SELECT (
                SELECT COUNT(*)
                FROM transaction_tags
                JOIN transactions ON transactions.id = transaction_tags.transaction_id
                WHERE transaction_tags.tag_id = ?
                    AND transactions.user_id = ?
                    AND transactions.archived_at IS NULL
            ) + (
                SELECT COUNT(*)
                FROM credit_card_transaction_tags
                JOIN credit_card_transactions
                    ON credit_card_transactions.id = credit_card_transaction_tags.credit_card_transaction_id
                WHERE credit_card_transaction_tags.tag_id = ?
                    AND credit_card_transactions.user_id = ?
                    AND credit_card_transactions.archived_at IS NULL
            ) AS total
        """,
    }[table]
    with get_connection() as conn:
        usage_params = (normalized_id, user_id, normalized_id, user_id) if table == "tags" else (normalized_id, user_id, normalized_id, user_id)
        used = conn.execute(usage_query, usage_params).fetchone()["total"]
        if used:
            raise ClassificationError("Nao e possivel excluir um item usado em lancamentos.")
        if table == "categories":
            clear_archived_category_references(conn, user_id, normalized_id)
        cursor = conn.execute(f"DELETE FROM {table} WHERE id = ? AND user_id = ?", (normalized_id, user_id))
        if cursor.rowcount == 0:
            raise ClassificationError("Item nao encontrado.", HTTPStatus.NOT_FOUND)


def category_usage_count_sql(category_expression: str) -> str:
    return f"""
        (
            SELECT COUNT(*)
            FROM transactions
            WHERE transactions.category_id = {category_expression}
                AND transactions.user_id = ?
                AND transactions.archived_at IS NULL
        ) + (
            SELECT COUNT(*)
            FROM credit_card_transactions
            WHERE credit_card_transactions.category_id = {category_expression}
                AND credit_card_transactions.user_id = ?
                AND credit_card_transactions.archived_at IS NULL
        )
    """


def subcategory_usage_count(conn, user_id: int, subcategory_id: int) -> int:
    return conn.execute(
        """
        SELECT (
            SELECT COUNT(*)
            FROM transactions
            WHERE subcategory_id = ? AND user_id = ? AND archived_at IS NULL
        ) + (
            SELECT COUNT(*)
            FROM credit_card_transactions
            WHERE subcategory_id = ? AND user_id = ? AND archived_at IS NULL
        ) AS total
        """,
        (subcategory_id, user_id, subcategory_id, user_id),
    ).fetchone()["total"]


def clear_archived_category_references(conn, user_id: int, category_id: int) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET category_id = NULL, subcategory_id = NULL
        WHERE user_id = ? AND category_id = ? AND archived_at IS NOT NULL
        """,
        (user_id, category_id),
    )
    conn.execute(
        """
        UPDATE credit_card_transactions
        SET category_id = NULL, subcategory_id = NULL
        WHERE user_id = ? AND category_id = ? AND archived_at IS NOT NULL
        """,
        (user_id, category_id),
    )


def clear_archived_subcategory_references(conn, user_id: int, subcategory_id: int) -> None:
    conn.execute(
        """
        UPDATE transactions
        SET subcategory_id = NULL
        WHERE user_id = ? AND subcategory_id = ? AND archived_at IS NOT NULL
        """,
        (user_id, subcategory_id),
    )
    conn.execute(
        """
        UPDATE credit_card_transactions
        SET subcategory_id = NULL
        WHERE user_id = ? AND subcategory_id = ? AND archived_at IS NOT NULL
        """,
        (user_id, subcategory_id),
    )


def ensure_category_exists(conn, user_id: int, category_id: int) -> None:
    row = conn.execute(
        """
        SELECT id
        FROM categories
        WHERE id = ? AND user_id = ?
        """,
        (category_id, user_id),
    ).fetchone()
    if not row:
        raise ClassificationError("Categoria nao encontrada.", HTTPStatus.NOT_FOUND)


def fetch_subcategory(conn, user_id: int, subcategory_id: int) -> dict:
    row = conn.execute(
        """
        SELECT
            subcategories.id,
            subcategories.user_id,
            subcategories.category_id,
            subcategories.name,
            subcategories.created_at,
            (
                SELECT COUNT(*)
                FROM transactions
                WHERE transactions.subcategory_id = subcategories.id
                    AND transactions.user_id = subcategories.user_id
                    AND transactions.archived_at IS NULL
            ) + (
                SELECT COUNT(*)
                FROM credit_card_transactions
                WHERE credit_card_transactions.subcategory_id = subcategories.id
                    AND credit_card_transactions.user_id = subcategories.user_id
                    AND credit_card_transactions.archived_at IS NULL
            ) AS transaction_count
        FROM subcategories
        WHERE subcategories.id = ? AND subcategories.user_id = ?
        """,
        (subcategory_id, user_id),
    ).fetchone()
    if not row:
        raise ClassificationError("Subcategoria nao encontrada.", HTTPStatus.NOT_FOUND)
    return row_to_dict(row)


def get_or_create_named_item(conn, table: str, user_id: int, name: str, required_message: str, group_type: object = "expense") -> int:
    ensure_allowed_table(table)
    normalized = normalize_name(name, required_message)
    normalized_group = normalize_group_type(group_type) if table == "categories" else None
    if table == "categories":
        row = conn.execute(
            "SELECT id FROM categories WHERE user_id = ? AND group_type = ? AND name = ?",
            (user_id, normalized_group, normalized),
        ).fetchone()
        if row:
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO categories (user_id, name, group_type) VALUES (?, ?, ?)",
            (user_id, normalized, normalized_group),
        )
        return cursor.lastrowid
    row = conn.execute(
        f"SELECT id FROM {table} WHERE user_id = ? AND name = ?",
        (user_id, normalized),
    ).fetchone()
    if row:
        return row["id"]
    cursor = conn.execute(
        f"INSERT INTO {table} (user_id, name) VALUES (?, ?)",
        (user_id, normalized),
    )
    return cursor.lastrowid


def format_classification(row) -> dict | None:
    return row_to_dict(row)


def normalize_name(name: object, required_message: str) -> str:
    normalized = " ".join(str(name or "").strip().split())
    if not normalized:
        raise ClassificationError(required_message)
    if len(normalized) > 80:
        raise ClassificationError("Categoria ou tag deve ter ate 80 caracteres.")
    return normalized


def normalize_group_type(value: object, required: bool = True) -> str | None:
    raw = " ".join(str(value or "").strip().lower().split())
    if not raw and not required:
        return None
    normalized = GROUP_ALIASES.get(raw, raw)
    if normalized not in GROUP_TYPES:
        raise ClassificationError("Grupo de categoria invalido.")
    return normalized


def normalize_item_id(value: object, message: str) -> int:
    try:
        normalized = int(str(value or "").strip())
    except ValueError as exc:
        raise ClassificationError(message) from exc
    if normalized <= 0:
        raise ClassificationError(message)
    return normalized


def ensure_allowed_table(table: str) -> None:
    if table not in {"categories", "tags"}:
        raise ClassificationError("Classificacao invalida.")


DEFAULT_CATEGORIES = {
    "expense": {
        "Alimentação": [
            "Feira, Sacolão e Peixaria",
            "Lanches, Padaria e Cafés",
            "Restaurantes / Bares / Delivery",
            "Supermercado / Despensa",
        ],
        "Animais de Estimação (Pets)": [
            "Banho, Tosa e Estética",
            "Brinquedos, Caminhas e Acessórios Pet",
            "Consultas Veterinárias e Hospital Vet",
            "Medicamentos, Antipulgas e Vacinas",
            "Ração, Petiscos e Alimentação Natural",
        ],
        "Assinaturas e Serviços": [
            "Armazenamento em Nuvem e Softwares (iCloud, Drive, Office)",
            "Assinaturas de Jornais / Revistas / Portais",
            "Celular",
            "Clubes de Assinatura (Livros, Vinhos, Cafés, etc.)",
            "Streaming de Música (Spotify, Deezer, Apple Music)",
            "Streaming de Vídeo (Netflix, Disney+, Prime, etc.)",
        ],
        "Compras": [],
        "Cuidados Pessoais": [
            "Academia, Estúdio de Pilates e Esportes",
            "Acessórios, Joias e Relógios",
            "Cosméticos, Maquiagem e Perfumaria",
            "Salão de Beleza / Barbearia",
            "Vestuário (Roupas, Calçados e Underwear)",
        ],
        "Dependentes e Filhos": [
            "Atividades Extracurriculares (Futebol, Ballet, etc.)",
            "Brinquedos, Jogos e Recreação",
            "Fraldas, Fórmulas e Artigos Infantis",
            "Mensalidade Escolar / Creche (Filhos)",
            "Mesada dos Filhos",
            "Vestuário Infantil / Uniformes",
        ],
        "Educação": [
            "Cursos Livres, Workshops e Certificações",
            "Eventos Acadêmicos e Congressos",
            "Idiomas e Intercâmbio",
            "Livros, Apostilas e Material Escolar",
            "Mensalidade Escolar / Faculdade / Pós",
        ],
        "Empréstimos": [],
        "Habitação": [
            "Aluguel / Prestação do Imóvel",
            "Condomínio",
            "Empregada Doméstica / Diarista",
            "Energia Elétrica (Luz)",
            "Gás (Encanado ou Botijão)",
            "IPTU",
            "Internet / TV a Cabo / Telefone Fixo",
            "Manutenção, Reparos e Reformas",
            "Móveis e Decoração",
            "Seguro Residencial",
            "Água e Saneamento",
        ],
        "Lazer e Estilo de Vida": [
            "Baladas, Festas e Grandes Eventos",
            "Cinema, Teatro, Shows e Eventos",
            "Clubes, Parques e Associações",
            "Hobbies, Passatempos e Jogos",
            "Viagens, Passagens e Hospedagens (Férias)",
        ],
        "Outras Despesas": [
            "Doações, Dízimos e Ações Sociais",
            "Imprevistos e Emergências Domésticas",
            "Multas de Trânsito / Juros por Atraso",
            "Presentes para Amigos e Família",
        ],
        "Saúde": [
            "Consultas Médicas / Terapias / Psicólogo",
            "Dentista e Tratamento Odontológico",
            "Exames Clínicos e Laboratoriais",
            "Medicamentos e Farmácia",
            "Plano de Saúde / Seguro Saúde",
            "Ótica (Óculos, Lentes de Contato)",
        ],
        "Serviços Financeiros e Impostos": [
            "Anuidade de Cartão de Crédito",
            "Imposto de Renda a Pagar (IRPF)",
            "IOF",
            "Juros, Empréstimos e Financiamentos",
            "Seguro de Vida / Previdência do Estado",
            "Tarifas e Taxas de Conta Corrente",
        ],
        "Trabalho": [
            "Impostos MEI",
        ],
        "Transporte": [
            "Aplicativos de Transporte (Uber, 99)",
            "Combustível",
            "Estacionamento",
            "IPVA / Licenciamento / DPVAT",
            "Lavagem e Cuidados com o Carro",
            "Manutenção, Revisão e Troca de Óleo",
            "Parcela do carro",
            "Pedágio",
            "Recarga",
            "Seguro Auto",
            "Tag",
            "Transporte Público (Ônibus, Metrô, Trem)",
        ],
    },
    "income": {
        "Empréstimos": [],
        "Freelance e Autônomo": [
            "Comissões",
            "Consultorias",
            "Projetos / Serviços Prestados",
        ],
        "Outras Receitas": [
            "Estornos",
            "Presentes / Doações Recebidas",
            "Prêmios / Sorteios / Loterias",
            "Reembolso médico",
            "Reembolsos Corporativos",
            "Restituição de Imposto de Renda",
            "Venda de Bens (Móveis, Carro, etc.)",
        ],
        "Rendimentos e Investimentos": [
            "Aluguéis Recebidos",
            "Dividendos / JCP",
            "Rendimento de Renda Fixa",
        ],
        "Trabalho e Salário": [
            "Bônus / PLR",
            "Décimo Terceiro (13º)",
            "Férias",
            "Horas Extras / Adicionais",
            "Salário Líquido",
        ],
    },
    "investment": {
        "Criptoativos": [
            "Bitcoin (BTC)",
            "Ethereum (ETH)",
            "Outras Altcoins (Solana, Cardano, etc.)",
            "Stablecoins (USDT, USDC)",
        ],
        "Fundos de Investimentos": [
            "Cambial",
            "Fundos Multimercado",
            "Renda Fixa",
        ],
        "Outros Investimentos": [
            "Aportes em Negócios Próprios / Startups / Equity",
            "Imóveis Físicos (Foco em Valorização/Construção)",
        ],
        "Previdência Privada": [
            "PGBL (Plano Gerador de Benefício Livre)",
            "VGBL (Vida Gerador de Benefício Livre)",
        ],
        "Renda Fixa": [
            "CDB / RDB / LC (Certificados de Depósito)",
            "CRI / CRA / Debêntures (Crédito Privado)",
            "LCI / LCA (Letras de Crédito Imobiliário/Agrícola)",
            "Poupança (Fundo de Emergência antigo)",
            "Tesouro Direto (Selic, IPCA+, Prefixado)",
        ],
        "Renda Variável": [
            "Ações (Bolsa de Valores - B3)",
            "BDRs / Investimentos no Exterior",
            "ETFs (Exchange Traded Funds)",
            "Fundos de Investimento Imobiliário (FIIs)",
            "Mercado de Opções / Contratos Futuros",
            "Real Estate Investment Trust (REIT)",
        ],
    },
}

def seed_default_categories(conn, user_id: int) -> None:
    for group_type, categories in DEFAULT_CATEGORIES.items():
        for category_name, subcategories in categories.items():
            cursor = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, ?, ?)",
                (user_id, category_name, group_type)
            )
            category_id = cursor.lastrowid
            for subcategory_name in subcategories:
                conn.execute(
                    "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, ?)",
                    (user_id, category_id, subcategory_name)
                )
