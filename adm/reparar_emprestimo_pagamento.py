#!/usr/bin/env python3
"""Corrige a revisão manual de um contrato de Empréstimos com pagamento conciliado não refletido.

Uso:
  python3 adm/reparar_emprestimo_pagamento.py --user-id 4 --loan-id 1 --transaction-id 90 \
      --remaining 31 --commitment-cents 8702319 --next-due 2026-11-07

Sem --apply apenas mostra o estado atual e as alterações previstas (dry-run).
Com --apply: pare o servidor antes, cria uma cópia do banco e grava em uma única transação
as parcelas restantes, o compromisso, o próximo vencimento e remove a revisão pendente, além
de registrar a operação no log de auditoria. Os valores informados devem vir do demonstrativo do credor.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from financeiro.operation_logs import create_operation_log_with_conn  # noqa: E402

DEFAULT_DB = ROOT / "data" / "finance.db"
PID_FILE = ROOT / "data" / "server.pid"


def server_is_running() -> bool:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def load_state(conn: sqlite3.Connection, user_id: int, loan_id: int, transaction_id: int) -> tuple[dict, dict, dict]:
    loan = conn.execute("SELECT * FROM loans WHERE id=? AND user_id=?", (loan_id, user_id)).fetchone()
    link = conn.execute(
        "SELECT * FROM loan_payment_links WHERE user_id=? AND loan_id=? AND transaction_id=?",
        (user_id, loan_id, transaction_id),
    ).fetchone()
    tx = conn.execute(
        "SELECT id, description, amount_cents, date, reconciled_at FROM transactions WHERE id=? AND user_id=?",
        (transaction_id, user_id),
    ).fetchone()
    if not loan:
        raise SystemExit("Contrato não encontrado para este usuário.")
    if not link or not tx:
        raise SystemExit("Vínculo entre contrato e lançamento não encontrado.")
    return dict(loan), dict(link), dict(tx)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--loan-id", type=int, required=True)
    parser.add_argument("--transaction-id", type=int, required=True)
    parser.add_argument("--remaining", type=int, required=True, help="Parcelas restantes conforme o demonstrativo.")
    parser.add_argument("--commitment-cents", type=int, required=True, help="Compromisso restante em centavos.")
    parser.add_argument("--next-due", required=True, help="Próximo vencimento (AAAA-MM-DD).")
    parser.add_argument("--apply", action="store_true", help="Grava as alterações. Sem esta opção, apenas simula.")
    args = parser.parse_args()

    next_due = date.fromisoformat(args.next_due).isoformat()
    if args.remaining < 0 or args.commitment_cents < 0:
        raise SystemExit("Parcelas e compromisso não podem ser negativos.")
    if not args.db.exists():
        raise SystemExit(f"Banco não encontrado: {args.db}")

    conn = sqlite3.connect(args.db, timeout=10)
    conn.row_factory = sqlite3.Row
    loan, link, tx = load_state(conn, args.user_id, args.loan_id, args.transaction_id)

    print(f"Contrato: {loan['name']} ({loan['currency']})")
    print(f"  atual:  parcelas={loan['remaining_installments']} compromisso={loan['remaining_commitment_cents']} "
          f"vencimento={loan['next_due_date']} revisão={loan['review_required']}")
    print(f"  novo:   parcelas={args.remaining} compromisso={args.commitment_cents} "
          f"vencimento={next_due} revisão=0")
    print(f"Lançamento {tx['id']}: {tx['description']} · {tx['amount_cents']} centavos · {tx['date']} · "
          f"conciliado em {tx['reconciled_at']}")
    print(f"Vínculo: valid={link['valid']} recognized={link['recognized']}")

    if not link["valid"] or not link["recognized"] or not tx["reconciled_at"]:
        raise SystemExit("O vínculo precisa estar válido, reconhecido e com lançamento conciliado para este reparo.")
    if not args.apply:
        print("\nDry-run: nada foi gravado. Confira os valores com o demonstrativo e repita com --apply.")
        return 0
    if server_is_running():
        raise SystemExit("O servidor está em execução. Pare-o antes de aplicar o reparo.")

    backup = args.db.with_name(f"{args.db.name}.antes-reparo-{datetime.now():%Y%m%d-%H%M%S}.bak")
    backup_conn = sqlite3.connect(backup)
    conn.backup(backup_conn)
    backup_conn.close()
    print(f"Cópia criada em: {backup}")

    conn.isolation_level = None
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            """UPDATE loans SET remaining_installments=?, remaining_commitment_cents=?, next_due_date=?,
                      review_required=0, updated_at=CURRENT_TIMESTAMP
               WHERE id=? AND user_id=?""",
            (args.remaining, args.commitment_cents, next_due, args.loan_id, args.user_id),
        )
        create_operation_log_with_conn(
            conn, args.user_id,
            module="loans", operation_type="update", entity_type="loan",
            entity_id=args.loan_id,
            description="Revisão manual do contrato após pagamento conciliado.",
            metadata={
                "transaction_id": args.transaction_id,
                "remaining_installments": args.remaining,
                "remaining_commitment_cents": args.commitment_cents,
                "next_due_date": next_due,
            },
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    print("Reparo aplicado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
