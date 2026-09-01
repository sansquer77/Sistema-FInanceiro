from __future__ import annotations

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
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.credit_cards import create_credit_card
from financeiro.database import get_connection, initialize_database
from financeiro.imports import import_system_template, parse_xlsx_rows, system_import_template
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

        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["errors"][0]["reason"], "Data invalida.")

    def test_import_account_installment_creates_series(self) -> None:
        result = self.import_csv([
            "data;tipo;descricao;valor;categoria;repeticao;parcelas",
            "2026-06-01;expense;Compra parcelada;300,00;Mercado;parcelado;3",
        ], "account", self.account["id"])

        self.assertEqual(result["imported"], 1)
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
        with mock.patch.object(imports_module, "MAX_XLSX_ROWS", 2):
            with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                parse_xlsx_rows(rows_workbook, "Lançamentos")

        cells_workbook = imports_module.create_xlsx_workbook([("Lançamentos", [["a", "b", "c", "d"]])])
        with mock.patch.object(imports_module, "MAX_XLSX_CELLS", 3):
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
            with mock.patch.object(imports_module, "MAX_XLSX_SHARED_STRINGS", 1):
                with self.assertRaisesRegex(imports_module.ImportError, "limites seguros"):
                    imports_module.xlsx_shared_strings(archive)


if __name__ == "__main__":
    unittest.main()
