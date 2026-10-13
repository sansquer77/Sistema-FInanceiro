from __future__ import annotations

import sqlite3
import tempfile
import unittest
import warnings
import zipfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro import xlsx_security
import financeiro.imports as imports_module
from financeiro import import_parsers as import_parsers_module
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.credit_cards import create_credit_card, create_credit_card_transaction
from financeiro.database import get_connection, initialize_database
from financeiro.database_schema import ensure_import_adjustments_schema
from financeiro.import_parsers import parse_xlsx_rows
from financeiro.imports import import_legacy_transactions, import_system_template, preview_legacy_transactions, system_import_template
from financeiro.transactions import create_transaction


class SystemTemplateImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        self.card = create_credit_card(self.user["id"], {
            "name": "Visa",
            "issuer": "Banco",
            "limit": "5000,00",
            "closing_day": "10",
            "due_day": "20",
            "currency": "BRL",
        })

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def import_csv(self, lines: list[str], target: str, target_id: int, filename: str = "modelo.csv") -> dict:
        csv_bytes = "\n".join(lines).encode("utf-8")
        return import_system_template(self.user["id"], target, target_id, csv_bytes, filename)

    def test_import_uses_row_savepoints_and_keeps_partial_success_behavior(self) -> None:
        csv_lines = [
            "data;tipo;descricao;valor;categoria",
            "2026-06-01;expense;Linha 1;10,00;Mercado",
            "2026-06-02;expense;Linha 2;20,00;Mercado",
            "2026-06-03;expense;Linha 3;30,00;Mercado",
        ]
        original_create = imports_module.create_transaction_with_conn
        call_count = 0

        def create_then_fail_second_row(conn, user_id, payload):
            nonlocal call_count
            call_count += 1
            created = original_create(conn, user_id, payload)
            if call_count == 2:
                raise RuntimeError("Falha simulada depois da insercao.")
            return created

        with mock.patch(
            "financeiro.imports.create_transaction_with_conn",
            side_effect=create_then_fail_second_row,
        ):
            result = self.import_csv(csv_lines, "account", self.account["id"])

        with get_connection() as conn:
            transaction_count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            balance = conn.execute(
                "SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                (self.account["id"],),
            ).fetchone()["current_balance_cents"]

        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(transaction_count, 2)
        self.assertEqual(balance, 96000)

    def test_import_accepts_multiple_date_formats(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria",
            "02.05.2026;expense;Formato ponto;10,00;Mercado",
            "03/05/2026;expense;Formato barra;20,00;Mercado",
            "2026-05-04;expense;Formato ISO;30,00;Mercado",
            "02-05-2026;expense;Formato hifen;40,00;Mercado",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 4)
        self.assertEqual(result["skipped"], 0)
        with get_connection() as conn:
            dates = [row["date"] for row in conn.execute(
                "SELECT date FROM transactions ORDER BY id",
            ).fetchall()]
        self.assertEqual(dates, ["2026-05-02", "2026-05-03", "2026-05-04", "2026-05-02"])

    def test_import_rejects_invalid_date_with_reason(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria",
            "32.05.2026;expense;Data invalida;10,00;Mercado",
            "2026-06-01;expense;Data valida;20,00;Mercado",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 1, result)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"][0]["reason"], "Data invalida.")

    def test_import_account_installment_creates_series(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria;repeticao;parcelas",
            "2026-06-01;expense;Compra parcelada;300,00;Mercado;parcelado;3",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 1, result)
        self.assertEqual(result["skipped"], 0)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT series_id, installment_index, installment_count, amount_cents FROM transactions ORDER BY id",
            ).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["installment_index"] for row in rows}, {1, 2, 3})
        self.assertTrue(all(row["series_id"] == rows[0]["series_id"] for row in rows))
        self.assertEqual(sum(row["amount_cents"] for row in rows), 30000)

    def test_import_account_recurring_with_average(self) -> None:
        create_transaction(self.user["id"], {
            "account_id": self.account["id"],
            "type": "expense",
            "date": "2026-05-10",
            "description": "Internet Mensal",
            "amount": "100,00",
            "category": "Assinaturas e Serviços",
        })
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria;repeticao;recorrencia;media",
            "2026-06-15;expense;Internet Mensal;150,00;Assinaturas e Serviços;recorrente;mensal;sim",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 1)
        with get_connection() as conn:
            row = conn.execute(
                "SELECT series_kind, recurrence_frequency, amount_cents FROM transactions ORDER BY id DESC LIMIT 1",
            ).fetchone()
        self.assertEqual(row["series_kind"], "recurring")
        self.assertEqual(row["recurrence_frequency"], "monthly")
        self.assertEqual(row["amount_cents"], 10000)

    def test_import_rejects_missing_installment_count(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria;repeticao",
            "2026-06-01;expense;Compra parcelada;300,00;Mercado;parcelado",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"][0]["reason"], "Informe a quantidade de parcelas (coluna parcelas).")

    def test_import_rejects_missing_recurrence_frequency(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria;repeticao",
            "2026-06-01;expense;Assinatura recorrente;50,00;Assinaturas e Serviços;recorrente",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertIn("recorrencia", result["errors"][0]["reason"])

    def test_import_accepts_ofx_files(self) -> None:
        ofx_content = b'''OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
          <DTSTART>20240601000000[-03:EST]</DTSTART>
          <DTEND>20240630000000[-03:EST]</DTEND>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20240602000000[-03:EST]</DTPOSTED>
            <TRNAMT>-120.50</TRNAMT>
            <NAME>Supermercado</NAME>
            <MEMO>Compra no mercado</MEMO>
          </STMTTRN>
          <STMTTRN>
            <TRNTYPE>CREDIT</TRNTYPE>
            <DTPOSTED>20240612000000[-03:EST]</DTPOSTED>
            <TRNAMT>2500.00</TRNAMT>
            <NAME>Salario</NAME>
          </STMTTRN>
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>'''

        result = import_legacy_transactions(self.user["id"], self.account["id"], ofx_content, "extrato.ofx")

        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["total_rows"], 2)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT type, description, amount_cents, date FROM transactions ORDER BY id",
            ).fetchall()
        self.assertEqual(rows[0][0], "expense")
        self.assertEqual(rows[0][1], "Supermercado")
        self.assertEqual(rows[0][2], 12050)
        self.assertEqual(rows[0][3], "2024-06-02")
        self.assertEqual(rows[1][0], "income")
        self.assertEqual(rows[1][1], "Salario")
        self.assertEqual(rows[1][2], 250000)
        self.assertEqual(rows[1][3], "2024-06-12")

    def test_ofx_preview_edits_rows_and_imports_only_selected_transactions(self) -> None:
        ofx_content = '''OFXHEADER:100
DATA:OFXSGML
VERSION:102
ENCODING:USASCII
CHARSET:1252

<OFX>
<BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260502000000[-03:EST]<TRNAMT>-20.00<NAME>Café original<MEMO>Compra de café</STMTTRN>
<STMTTRN><DTPOSTED>20260503000000<TRNAMT>100.00<NAME>Receita ignorada</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1>
</OFX>'''.encode("cp1252")

        preview = preview_legacy_transactions(
            self.user["id"],
            self.account["id"],
            ofx_content,
            "extrato.ofx",
        )
        self.assertEqual(preview["total_rows"], 2)
        self.assertEqual(preview["selected_rows"], 2)
        self.assertEqual(preview["preview"][0]["values"]["valor"], "-20,00")
        self.assertEqual(preview["preview"][0]["values"]["descricao"], "Café original")
        preview_rows = preview["preview"]
        preview_rows[0]["values"].update({
            "data": "2026-05-04",
            "descricao": "Compra revisada",
            "valor": "-35,50",
            "categoria": "Alimentação",
            "observacoes": "Revisado antes de importar",
        })
        preview_rows[1]["selected"] = False

        result = import_legacy_transactions(
            self.user["id"],
            self.account["id"],
            b"",
            "preview.ofx",
            preview_rows,
        )

        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["skipped"], 0)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT type, description, amount_cents, date, notes FROM transactions",
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "expense")
        self.assertEqual(rows[0][1], "Compra revisada")
        self.assertEqual(rows[0][2], 3550)
        self.assertEqual(rows[0][3], "2026-05-04")
        self.assertEqual(rows[0][4], "Revisado antes de importar")

    def test_ofx_preview_rejects_invalid_file_without_writing_transactions(self) -> None:
        with self.assertRaises(imports_module.ImportError):
            preview_legacy_transactions(
                self.user["id"],
                self.account["id"],
                b"<OFX><BANKMSGSRSV1>",
                "invalido.ofx",
            )
        with get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        self.assertEqual(count, 0)

    def test_successful_ofx_edit_is_learned_for_the_same_account_only(self) -> None:
        ofx_content = b'''<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260502000000<TRNAMT>-20.00<NAME>Loja Caf\xc3\xa9 24</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>'''
        preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], ofx_content, "extrato.ofx",
        )
        row = preview["preview"][0]
        editable_category = next(
            category
            for category in preview["classification_options"]["categories"]
            if category["group_type"] == "expense" and category["subcategories"]
        )
        editable_subcategory = editable_category["subcategories"][0]["name"]
        self.assertEqual(row["values"]["descricao_original"], "Loja Café 24")
        self.assertEqual(row["values"]["descricao"], "Loja Café 24")
        row["values"].update({
            "descricao": "Mercado Central",
            "categoria": editable_category["name"],
            "subcategoria": editable_subcategory,
        })
        row["edited_fields"] = ["descricao", "categoria", "subcategoria"]

        result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [row],
        )
        self.assertEqual(result["imported"], 1, result)
        with get_connection() as conn:
            learned = conn.execute(
                "SELECT normalized_description, normalized_corrected_description, corrected_description FROM import_adjustments",
            ).fetchone()
        self.assertEqual(learned["normalized_description"], "loja cafe 24")
        self.assertEqual(learned["normalized_corrected_description"], "mercado central")
        self.assertEqual(learned["corrected_description"], "Mercado Central")

        case_variant = ofx_content.replace(b"Loja Caf\xc3\xa9 24", b"LOJA CAFE 24")
        next_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], case_variant, "extrato.ofx",
        )
        self.assertTrue(next_preview["preview"][0]["learned_adjustment"])
        self.assertEqual(next_preview["preview"][0]["values"]["descricao"], "Mercado Central")
        self.assertEqual(next_preview["preview"][0]["values"]["categoria"], editable_category["name"])
        self.assertEqual(next_preview["preview"][0]["values"]["subcategoria"], editable_subcategory)

        corrected_text_preview = preview_legacy_transactions(
            self.user["id"],
            self.account["id"],
            ofx_content.replace(b"Loja Caf\xc3\xa9 24", b"MERCADO CENTRAL"),
            "extrato.ofx",
        )
        self.assertTrue(corrected_text_preview["preview"][0]["learned_adjustment"])
        self.assertEqual(
            corrected_text_preview["preview"][0]["values"]["descricao_original"],
            "MERCADO CENTRAL",
        )
        self.assertEqual(
            corrected_text_preview["preview"][0]["values"]["descricao"],
            "Mercado Central",
        )

        other_account = create_checking_account(self.user["id"], {
            "name": "Outra conta",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        other_preview = preview_legacy_transactions(
            self.user["id"],
            other_account["id"],
            case_variant,
            "extrato.ofx",
        )
        self.assertFalse(other_preview["preview"][0]["learned_adjustment"])
        self.assertEqual(other_preview["preview"][0]["values"]["descricao"], "LOJA CAFE 24")

    def test_import_preview_returns_existing_classification_options(self) -> None:
        preview = imports_module.preview_system_template(
            self.user["id"],
            "account",
            self.account["id"],
            b"data;tipo;descricao;valor;categoria\n2026-06-01;expense;Compra;10,00;Outras Despesas",
            "modelo.csv",
        )

        options = preview["classification_options"]
        self.assertTrue(options["categories"])
        self.assertTrue(all(isinstance(category["subcategories"], list) for category in options["categories"]))
        self.assertIsInstance(options["tags"], list)

    def test_existing_import_adjustments_schema_gets_description_alias_column(self) -> None:
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("CREATE TABLE import_adjustments (id INTEGER PRIMARY KEY)")
            ensure_import_adjustments_schema(connection)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(import_adjustments)")
            }
        finally:
            connection.close()

        self.assertIn("normalized_corrected_description", columns)

    def test_reviewed_import_rejects_categories_not_in_existing_options(self) -> None:
        category = imports_module.list_categories(self.user["id"])[0]["name"]
        source = (
            "data;tipo;descricao;valor;categoria\n"
            f"2026-06-01;expense;Compra;10,00;{category}"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        row["values"]["categoria"] = "Categoria digitada"
        row["edited_fields"] = ["categoria"]

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertIn("categoria existente", result["errors"][0]["reason"].lower())
        with get_connection() as conn:
            category_count = conn.execute(
                "SELECT COUNT(*) FROM categories WHERE user_id = ? AND name = ?",
                (self.user["id"], "Categoria digitada"),
            ).fetchone()[0]
        self.assertEqual(category_count, 0)

    def test_reviewed_expense_import_rejects_income_category_instead_of_reclassifying(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "income"
        )
        source = (
            "data;tipo;descricao;valor;categoria;tags\n"
            "2026-06-01;expense;Compra;10,00;Outras Despesas;Importado"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        row["values"]["categoria"] = category["name"]
        row["edited_fields"] = ["categoria"]

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertIn("categoria existente", result["errors"][0]["reason"].lower())

    def test_reviewed_account_import_persists_selected_category_and_subcategory(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        source = (
            "data;tipo;descricao;valor;categoria;subcategoria;tags\n"
            "2026-06-01;expense;Compra classificada;10,00;;;Importado"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        row["values"]["categoria"] = category["name"]
        row["values"]["subcategoria"] = subcategory["name"]
        row["edited_fields"] = ["categoria", "subcategoria"]

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 1, result)
        with get_connection() as conn:
            saved = conn.execute(
                """
                SELECT categories.name AS category, subcategories.name AS subcategory
                FROM transactions
                JOIN categories ON categories.id = transactions.category_id
                LEFT JOIN subcategories ON subcategories.id = transactions.subcategory_id
                WHERE transactions.description = 'Compra classificada'
                """,
            ).fetchone()
        self.assertEqual(saved["category"], category["name"])
        self.assertEqual(saved["subcategory"], subcategory["name"])

    def test_reviewed_legacy_import_persists_selected_category_and_subcategory(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        content = b'''<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260601000000<TRNAMT>-10.00<NAME>Compra classificada</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>'''
        preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], content, "extrato.ofx",
        )
        row = preview["preview"][0]
        row["values"]["categoria"] = category["name"]
        row["values"]["subcategoria"] = subcategory["name"]
        row["edited_fields"] = ["categoria", "subcategoria"]

        result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [row],
        )

        self.assertEqual(result["imported"], 1, result)
        with get_connection() as conn:
            saved = conn.execute(
                """
                SELECT categories.name AS category, subcategories.name AS subcategory
                FROM transactions
                JOIN categories ON categories.id = transactions.category_id
                LEFT JOIN subcategories ON subcategories.id = transactions.subcategory_id
                WHERE transactions.description = 'Compra classificada'
                """,
            ).fetchone()
        self.assertEqual(saved["category"], category["name"])
        self.assertEqual(saved["subcategory"], subcategory["name"])

    def test_learned_ofx_preview_keeps_original_description_and_persists_revised_category(self) -> None:
        content = b'''<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260601000000<TRNAMT>-10.00<NAME>Nome original do arquivo</NAME></STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>'''
        categories = [
            category
            for category in imports_module.list_categories(self.user["id"])
            if category["group_type"] == "expense" and category["subcategories"]
        ]
        learned_category = categories[0]
        revised_category = next(
            category for category in categories
            if category["name"] != learned_category["name"]
        )
        learned_subcategory = learned_category["subcategories"][0]["name"]

        first_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], content, "extrato.ofx",
        )
        first_row = first_preview["preview"][0]
        self.assertEqual(
            first_row["values"]["descricao_original"],
            "Nome original do arquivo",
        )
        first_row["values"]["descricao"] = "Descrição corrigida"
        first_row["values"]["categoria"] = learned_category["name"]
        first_row["values"]["subcategoria"] = learned_subcategory
        first_row["edited_fields"] = ["descricao", "categoria", "subcategoria"]
        first_result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [first_row],
        )
        self.assertEqual(first_result["imported"], 1, first_result)

        revised_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], content, "extrato.ofx",
        )
        revised_row = revised_preview["preview"][0]
        self.assertTrue(revised_row["learned_adjustment"])
        self.assertEqual(
            revised_row["values"]["descricao_original"],
            "Nome original do arquivo",
        )
        self.assertEqual(
            revised_row["values"]["descricao"],
            "Descrição corrigida",
        )
        revised_subcategory = revised_category["subcategories"][0]["name"]
        revised_row["values"]["categoria"] = revised_category["name"]
        revised_row["values"]["subcategoria"] = revised_subcategory
        revised_row["edited_fields"] = ["categoria", "subcategoria"]

        revised_result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [revised_row],
        )
        self.assertEqual(revised_result["imported"], 1, revised_result)
        with get_connection() as conn:
            saved = conn.execute(
                """
                SELECT transactions.description, categories.name AS category,
                    subcategories.name AS subcategory
                FROM transactions
                JOIN categories ON categories.id = transactions.category_id
                LEFT JOIN subcategories ON subcategories.id = transactions.subcategory_id
                WHERE transactions.description = 'Descrição corrigida'
                ORDER BY transactions.id DESC
                LIMIT 1
                """,
            ).fetchone()
        self.assertEqual(saved["category"], revised_category["name"])
        self.assertEqual(saved["subcategory"], revised_subcategory)

    def test_ignored_ofx_duplicate_learns_reviewed_category_without_changing_transaction(self) -> None:
        category = next(
            item for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]["name"]
        existing = create_transaction(self.user["id"], {
            "account_id": self.account["id"], "type": "expense", "date": "2026-06-08",
            "description": "Compra já lançada", "amount": "10,00",
            "category": category["name"], "subcategory": subcategory,
        })
        ofx_content = b'''<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260608000000<TRNAMT>-10.00<NAME>OFX Loja 88</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>'''
        first_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], ofx_content, "extrato.ofx",
        )
        row = first_preview["preview"][0]
        self.assertEqual(row["duplicate_matches"], [])
        row["values"]["categoria"] = category["name"]
        row["values"]["subcategoria"] = subcategory
        row["values"]["descricao"] = "Compra de mercado"
        row["edited_fields"] = ["categoria", "subcategoria", "descricao"]
        row["duplicate_action"] = "ignore"
        checked = imports_module.check_import_duplicates(
            self.user["id"], "account", self.account["id"], [row], is_legacy=True,
        )
        self.assertEqual([item["id"] for item in checked[0]["matches"]], [existing["id"]])

        result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [row],
        )
        self.assertEqual((result["imported"], result["skipped"]), (0, 1))
        next_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], ofx_content, "extrato.ofx",
        )
        learned = next_preview["preview"][0]
        self.assertTrue(learned["learned_adjustment"])
        self.assertEqual(learned["values"]["categoria"], category["name"])
        self.assertEqual(learned["values"]["subcategoria"], subcategory)
        self.assertEqual(learned["values"]["descricao"], "Compra de mercado")
        self.assertEqual([item["id"] for item in learned["duplicate_matches"]], [existing["id"]])
        with get_connection() as conn:
            saved = conn.execute(
                "SELECT description FROM transactions WHERE id=?", (existing["id"],),
            ).fetchone()
        self.assertEqual(saved["description"], "Compra já lançada")

    def test_ignored_duplicate_is_not_learned_if_candidate_disappears_before_confirmation(self) -> None:
        category = next(
            item for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        existing = create_transaction(self.user["id"], {
            "account_id": self.account["id"], "type": "expense", "date": "2026-06-09",
            "description": "Compra removida", "amount": "11,00",
            "category": category["name"], "subcategory": subcategory["name"],
        })
        source = (
            "data;tipo;descricao;valor;categoria;subcategoria\n"
            "2026-06-09;expense;OFX Removido 89;11,00;Outras Despesas;"
        ).encode("utf-8")
        row = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )["preview"][0]
        row["values"]["categoria"] = category["name"]
        row["values"]["subcategoria"] = subcategory["name"]
        row["edited_fields"] = ["categoria", "subcategoria"]
        row["duplicate_action"] = "ignore"
        self.assertEqual(
            [item["id"] for item in imports_module.check_import_duplicates(
                self.user["id"], "account", self.account["id"], [row],
            )[0]["matches"]],
            [existing["id"]],
        )
        with database.get_connection() as conn:
            conn.execute("UPDATE transactions SET archived_at=CURRENT_TIMESTAMP WHERE id=?", (existing["id"],))

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 0)
        self.assertIn("duplicidade não está mais presente", result["errors"][0]["reason"])
        with get_connection() as conn:
            learned_count = conn.execute("SELECT COUNT(*) FROM import_adjustments").fetchone()[0]
        self.assertEqual(learned_count, 0)

    def test_duplicate_import_can_replace_one_matching_account_transaction_or_ignore(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        existing = create_transaction(self.user["id"], {
            "account_id": self.account["id"],
            "type": "expense",
            "date": "2026-06-02",
            "description": "Já existente",
            "amount": "10,00",
            "category": category["name"],
            "subcategory": subcategory["name"],
            "tags": ["Anterior"],
        })
        source = (
            "data;tipo;descricao;valor;categoria;subcategoria;tags;observacoes\n"
            f"2026-06-02;expense;Descrição do arquivo;10,00;{category['name']};"
            f"{subcategory['name']};Importado;Nota nova"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        self.assertEqual([item["id"] for item in row["duplicate_matches"]], [existing["id"]])
        checked = imports_module.check_import_duplicates(
            self.user["id"],
            "account",
            self.account["id"],
            [row],
        )
        self.assertEqual([item["id"] for item in checked[0]["matches"]], [existing["id"]])
        row["values"]["descricao"] = "Descrição substituída"
        row["edited_fields"] = ["descricao"]
        row["duplicate_action"] = "replace"
        row["duplicate_target_id"] = str(existing["id"])

        replaced = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(replaced["imported"], 1, replaced)
        self.assertTrue(replaced["rows"][0]["replaced"])
        with get_connection() as conn:
            saved = conn.execute(
                """
                SELECT transactions.description, transactions.notes, COUNT(transaction_tags.tag_id) AS tag_count
                FROM transactions
                LEFT JOIN transaction_tags ON transaction_tags.transaction_id = transactions.id
                WHERE transactions.id = ?
                GROUP BY transactions.id
                """,
                (existing["id"],),
            ).fetchone()
            total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        self.assertEqual(total, 1)
        self.assertEqual(saved["description"], "Descrição substituída")
        self.assertEqual(saved["notes"], "Nota nova")
        self.assertEqual(saved["tag_count"], 1)

        ignored_preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        ignored_row = ignored_preview["preview"][0]
        ignored_row["duplicate_action"] = "ignore"
        ignored_row["duplicate_target_id"] = str(existing["id"])
        ignored = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [ignored_row],
        )
        self.assertEqual(ignored["imported"], 0)
        self.assertEqual(ignored["skipped"], 1)
        self.assertEqual(
            ignored["errors"][0]["reason"],
            "Linha ignorada conforme sua escolha.",
        )
        with get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            description = conn.execute(
                "SELECT description FROM transactions WHERE id = ?",
                (existing["id"],),
            ).fetchone()["description"]
        self.assertEqual(total, 1)
        self.assertEqual(description, "Descrição substituída")

    def test_ignored_duplicate_learns_user_corrected_classification_for_next_preview(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        existing = create_transaction(self.user["id"], {
            "account_id": self.account["id"], "type": "expense", "date": "2026-06-08",
            "description": "Compra já lançada", "amount": "10,00",
            "category": category["name"], "subcategory": subcategory["name"],
        })
        source = (
            "data;tipo;descricao;valor;categoria;subcategoria\n"
            "2026-06-08;expense;OFX Loja 88;10,00;Outras Despesas;"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        self.assertEqual(row["duplicate_matches"], [])

        row["values"]["descricao"] = "Compra mercado"
        row["values"]["categoria"] = category["name"]
        row["values"]["subcategoria"] = subcategory["name"]
        row["edited_fields"] = ["descricao", "categoria", "subcategoria"]
        row["duplicate_action"] = "ignore"
        checked = imports_module.check_import_duplicates(
            self.user["id"], "account", self.account["id"], [row],
        )
        self.assertEqual([item["id"] for item in checked[0]["matches"]], [existing["id"]])

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"][0]["reason"], "Linha ignorada conforme sua escolha.")

        next_preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        learned = next_preview["preview"][0]
        self.assertTrue(learned["learned_adjustment"])
        self.assertEqual(learned["values"]["descricao"], "Compra mercado")
        self.assertEqual(learned["values"]["categoria"], category["name"])
        self.assertEqual(learned["values"]["subcategoria"], subcategory["name"])
        self.assertEqual([item["id"] for item in learned["duplicate_matches"]], [existing["id"]])
        with get_connection() as conn:
            existing_description = conn.execute(
                "SELECT description FROM transactions WHERE id=?", (existing["id"],),
            ).fetchone()["description"]
        self.assertEqual(existing_description, "Compra já lançada")

    def test_import_result_returns_all_skipped_rows_above_previous_limit(self) -> None:
        preview = imports_module.preview_system_template(
            self.user["id"],
            "account",
            self.account["id"],
            b"data;tipo;descricao;valor;categoria\n2026-06-02;expense;Ignorada;10,00;Outras Despesas",
            "modelo.csv",
        )
        for index in range(51):
            create_transaction(self.user["id"], {
                "account_id": self.account["id"], "type": "expense", "date": "2026-06-02",
                "description": f"Duplicata {index}", "amount": "10,00",
                "category": "Outras Despesas", "subcategory": "",
            })
        selected_rows = [
            {
                **preview["preview"][0],
                "row": row_number,
                "duplicate_action": "ignore",
            }
            for row_number in range(1, 52)
        ]

        result = import_system_template(
            self.user["id"],
            "account",
            self.account["id"],
            b"",
            "preview.csv",
            selected_rows,
        )

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 51)
        self.assertEqual(len(result["errors"]), 51)
        self.assertEqual(
            [item["row"] for item in result["errors"]],
            list(range(1, 52)),
        )

    def test_duplicate_import_requires_candidate_selection_when_multiple_match(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        for description in ("Compra A", "Compra B"):
            create_transaction(self.user["id"], {
                "account_id": self.account["id"],
                "type": "expense",
                "date": "2026-06-03",
                "description": description,
                "amount": "12,00",
                "category": category["name"],
                "subcategory": subcategory["name"],
                "tags": ["Anterior"],
            })
        source = (
            "data;tipo;descricao;valor;categoria;subcategoria;tags\n"
            f"2026-06-03;expense;Compra do arquivo;12,00;{category['name']};"
            f"{subcategory['name']};Importado"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "account", self.account["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        self.assertEqual(len(row["duplicate_matches"]), 2)
        row["duplicate_action"] = "replace"
        row["duplicate_target_id"] = ""

        result = import_system_template(
            self.user["id"], "account", self.account["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertIn("selecione", result["errors"][0]["reason"].lower())

    def test_duplicate_card_import_can_replace_existing_transaction(self) -> None:
        category = next(
            item
            for item in imports_module.list_categories(self.user["id"])
            if item["group_type"] == "expense" and item["subcategories"]
        )
        subcategory = category["subcategories"][0]
        existing = create_credit_card_transaction(self.user["id"], {
            "credit_card_id": self.card["id"],
            "type": "expense",
            "date": "2026-06-04",
            "invoice_month": "2026-06",
            "description": "Compra existente",
            "amount": "15,00",
            "category": category["name"],
            "subcategory": subcategory["name"],
            "tags": ["Anterior"],
        })
        source = (
            "data;competencia_fatura;tipo;descricao;valor;categoria;subcategoria;tags\n"
            f"2026-06-04;2026-06;expense;Compra do arquivo;15,00;{category['name']};"
            f"{subcategory['name']};Nova"
        ).encode("utf-8")
        preview = imports_module.preview_system_template(
            self.user["id"], "card", self.card["id"], source, "modelo.csv",
        )
        row = preview["preview"][0]
        self.assertEqual([item["id"] for item in row["duplicate_matches"]], [existing["id"]])
        row["duplicate_action"] = "replace"
        row["duplicate_target_id"] = str(existing["id"])

        result = import_system_template(
            self.user["id"], "card", self.card["id"], b"", "preview.csv", [row],
        )

        self.assertEqual(result["imported"], 1, result)
        self.assertTrue(result["rows"][0]["replaced"])
        with get_connection() as conn:
            saved = conn.execute(
                """
                SELECT description, category_id, subcategory_id
                FROM credit_card_transactions
                WHERE id = ?
                """,
                (existing["id"],),
            ).fetchone()
        self.assertEqual(saved["description"], "Compra do arquivo")
        self.assertEqual(saved["category_id"], category["id"])
        self.assertEqual(saved["subcategory_id"], subcategory["id"])

    def test_ofx_adjustment_is_not_learned_when_import_fails(self) -> None:
        ofx_content = b'''<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><DTPOSTED>20260502000000<TRNAMT>-20.00<NAME>Loja Sem Importar</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>'''
        preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], ofx_content, "extrato.ofx",
        )
        row = preview["preview"][0]
        row["values"]["descricao"] = "Descrição editada"
        row["values"]["data"] = "data invalida"
        row["edited_fields"] = ["descricao"]

        result = import_legacy_transactions(
            self.user["id"], self.account["id"], b"", "preview.ofx", [row],
        )
        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        next_preview = preview_legacy_transactions(
            self.user["id"], self.account["id"], ofx_content, "extrato.ofx",
        )
        self.assertFalse(next_preview["preview"][0]["learned_adjustment"])
        self.assertEqual(next_preview["preview"][0]["values"]["descricao"], "Loja Sem Importar")

    def test_import_template_adjustment_is_scoped_to_credit_card(self) -> None:
        rows = [
            "data;tipo;descricao;valor;categoria;tags",
            "2026-06-01;expense;Loja Cartao;25,00;Outras Despesas;Importado",
        ]
        preview = imports_module.preview_system_template(
            self.user["id"],
            "card",
            self.card["id"],
            "\n".join(rows).encode("utf-8"),
            "modelo.csv",
        )
        row = preview["preview"][0]
        row["values"]["descricao"] = "Farmácia do bairro"
        row["values"]["categoria"] = "Saúde"
        row["edited_fields"] = ["descricao", "categoria"]
        result = import_system_template(
            self.user["id"],
            "card",
            self.card["id"],
            b"",
            "preview.csv",
            [row],
        )
        self.assertEqual(result["imported"], 1, result)

        next_preview = imports_module.preview_system_template(
            self.user["id"],
            "card",
            self.card["id"],
            "\n".join(rows).encode("utf-8"),
            "modelo.csv",
        )
        self.assertTrue(next_preview["preview"][0]["learned_adjustment"])
        self.assertEqual(next_preview["preview"][0]["values"]["descricao"], "Farmácia do bairro")
        self.assertEqual(next_preview["preview"][0]["values"]["categoria"], "Saúde")

    def test_import_transfer_ignores_repetition(self) -> None:
        destination = create_checking_account(self.user["id"], {
            "name": "Poupança",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        result = self.import_csv([
            "data;tipo;descricao;valor;conta_destino_id;repeticao;parcelas",
            "2026-06-01;transfer;Transferência parcelada;500,00;%d;parcelado;3" % destination["id"],
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 1)
        with get_connection() as conn:
            rows = conn.execute("SELECT series_id, installment_index FROM transactions").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["series_id"])
        self.assertIsNone(rows[0]["installment_index"])

    def test_import_card_installment_creates_series(self) -> None:
        result = self.import_csv([
            "data;competencia_fatura;tipo;descricao;valor;categoria;repeticao;parcelas",
            "2026-06-01;2026-06;expense;Compra parcelada cartao;300,00;Alimentação;parcelado;3",
        ], "card", self.card["id"])

        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["skipped"], 0)
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT series_id, installment_index, installment_count FROM credit_card_transactions ORDER BY id",
            ).fetchall()
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["installment_index"] for row in rows}, {1, 2, 3})
        self.assertTrue(all(row["series_id"] == rows[0]["series_id"] for row in rows))

    def test_import_card_rejects_invalid_date_with_reason(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria",
            "31.02.2026;expense;Data invalida;10,00;Alimentação",
        ], "card", self.card["id"])

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"][0]["reason"], "Data invalida.")

    def test_system_template_includes_repetition_columns(self) -> None:
        template_bytes = system_import_template(self.user["id"], "account")
        rows = parse_xlsx_rows(template_bytes, "Lançamentos")
        headers = [imports_module.normalize_template_header(value) for value in rows[0]]
        self.assertIn("repeticao", headers)
        self.assertIn("parcelas", headers)
        self.assertIn("recorrencia", headers)
        self.assertIn("media", headers)
        example_parcelado = rows[1]
        self.assertEqual(
            example_parcelado[headers.index("repeticao")],
            "parcelado",
            "a primeira linha de exemplo deve usar data DD.MM.YYYY e repeticao parcelado",
        )
        self.assertEqual(example_parcelado[headers.index("parcelas")], "3")
        self.assertEqual(example_parcelado[headers.index("data")], "15.06.2026")

    def test_xlsx_rejects_high_compression_ratio_before_xml_parse(self) -> None:
        output = BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"A" * (2 * 1024 * 1024))

        with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
            import_system_template(
                self.user["id"], "account", self.account["id"], output.getvalue(), "modelo.xlsx",
            )
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)

    def test_xlsx_rejects_member_count_and_duplicate_names(self) -> None:
        output = BytesIO()
        with mock.patch.object(xlsx_security, "MAX_XLSX_ARCHIVE_MEMBERS", 2):
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                for index in range(3):
                    archive.writestr(f"safe/member{index}.xml", "<root/>")
            with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                parse_xlsx_rows(output.getvalue(), "Lançamentos")

        output = BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("xl/workbook.xml", "<workbook/>")
                archive.writestr("xl/workbook.xml", "<workbook/>")
        with self.assertRaisesRegex(imports_module.ImportError, "membro duplicado"):
            parse_xlsx_rows(output.getvalue(), "Lançamentos")

    def test_xlsx_rejects_unsafe_sheet_target(self) -> None:
        workbook = imports_module.create_xlsx_workbook([("Lançamentos", [["data"]])])
        source = zipfile.ZipFile(BytesIO(workbook))
        output = BytesIO()
        with source, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for member in source.infolist():
                content = source.read(member.filename)
                if member.filename == "xl/_rels/workbook.xml.rels":
                    content = content.replace(b'Target="worksheets/sheet1.xml"', b'Target="../worksheets/sheet1.xml"')
                target.writestr(member.filename, content)

        with self.assertRaisesRegex(imports_module.ImportError, "caminho interno inseguro"):
            parse_xlsx_rows(output.getvalue(), "Lançamentos")

    def test_xlsx_accepts_absolute_internal_worksheet_target(self) -> None:
        workbook = imports_module.create_xlsx_workbook([("Lançamentos", [["data"], ["15.06.2026"]])])
        source = zipfile.ZipFile(BytesIO(workbook))
        output = BytesIO()
        with source, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target:
            for member in source.infolist():
                content = source.read(member.filename)
                if member.filename == "xl/_rels/workbook.xml.rels":
                    content = content.replace(
                        b'Target="worksheets/sheet1.xml"',
                        b'Target="/xl/worksheets/sheet1.xml"',
                    )
                target.writestr(member.filename, content)

        self.assertEqual(parse_xlsx_rows(output.getvalue(), "Lançamentos")[1][0], "15.06.2026")

    def test_xlsx_rejects_rows_cells_and_distant_columns(self) -> None:
        rows_workbook = imports_module.create_xlsx_workbook([("Lançamentos", [["data"], ["1"], ["2"]])])
        with mock.patch.object(import_parsers_module, "MAX_XLSX_ROWS", 2):
            with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                parse_xlsx_rows(rows_workbook, "Lançamentos")

        cells_workbook = imports_module.create_xlsx_workbook([("Lançamentos", [["a", "b", "c", "d"]])])
        with mock.patch.object(import_parsers_module, "MAX_XLSX_CELLS", 3):
            with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                parse_xlsx_rows(cells_workbook, "Lançamentos")

        columns_workbook = imports_module.create_xlsx_workbook([("Lançamentos", [[None] * 256 + ["fora"]])])
        with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
            parse_xlsx_rows(columns_workbook, "Lançamentos")

    def test_xlsx_rejects_excess_shared_strings(self) -> None:
        output = BytesIO()
        shared_strings = """<?xml version="1.0" encoding="UTF-8"?>
        <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
          <si><t>um</t></si><si><t>dois</t></si>
        </sst>"""
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/sharedStrings.xml", shared_strings)
        with zipfile.ZipFile(BytesIO(output.getvalue())) as archive:
            xlsx_security.validate_xlsx_archive(archive)
            with mock.patch.object(import_parsers_module, "MAX_XLSX_SHARED_STRINGS", 1):
                with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                    import_parsers_module.xlsx_shared_strings(archive)


if __name__ == "__main__":
    unittest.main()
