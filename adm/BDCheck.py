#!/usr/bin/env python3

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("/opt/sistema-financeiro/data/finance.db")
LOG_DIR = Path("/mnt/endor/Data_backup/Logs")
CHECK = "integrity_check" if "--completo" in sys.argv else "quick_check"
LOG_PREFIX = "log_full" if CHECK == "integrity_check" else "log"
LOG_PATH = LOG_DIR / datetime.now().strftime(f"{LOG_PREFIX}_%Y_%m_%d_%H_%M")


def write_message(message: str, *, error: bool = False) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message, file=sys.stderr if error else sys.stdout)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        print(formatted_message, file=log_file)


try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError as error:
    print(f"ERRO: não foi possível criar o diretório de logs {LOG_DIR}: {error}", file=sys.stderr)
    raise SystemExit(1)

write_message(f"Iniciando {CHECK} no banco {DB_PATH}.")

if not DB_PATH.is_file():
    write_message(f"ERRO: banco não encontrado: {DB_PATH}", error=True)
    raise SystemExit(2)

try:
    connection = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
        timeout=30,
    )

    with connection:
        connection.execute("PRAGMA query_only = ON")

        integrity_errors = [
            row[0]
            for row in connection.execute(f"PRAGMA {CHECK}")
            if row[0] != "ok"
        ]

        foreign_key_errors = list(
            connection.execute("PRAGMA foreign_key_check")
        )

    if integrity_errors or foreign_key_errors:
        write_message(f"ERRO: {CHECK} encontrou inconsistências:", error=True)

        for error in integrity_errors:
            write_message(f"  integridade: {error}", error=True)

        for table, rowid, parent, constraint in foreign_key_errors:
            write_message(
                f"  chave estrangeira: tabela={table}, rowid={rowid}, "
                f"tabela_pai={parent}, restrição={constraint}",
                error=True,
            )

        raise SystemExit(1)

    write_message(f"OK: {CHECK} e foreign_key_check concluídos sem inconsistências.")

except sqlite3.Error as error:
    write_message(f"ERRO SQLite: {error}", error=True)
    raise SystemExit(1)
finally:
    if "connection" in locals():
        connection.close()
