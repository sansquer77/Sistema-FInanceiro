from __future__ import annotations

import smtplib
from email.message import EmailMessage
from http import HTTPStatus

from financeiro.secure_config import SecureConfigError, load_encrypted_config


class EmailError(Exception):
    def __init__(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def send_password_reset_email(recipient: str, token: str, expires_in_minutes: int) -> None:
    subject = "Codigo de recuperacao do Sistema Financeiro"
    body = (
        "Ola,\n\n"
        "Recebemos uma solicitacao para redefinir sua senha no Sistema Financeiro.\n\n"
        f"Codigo de recuperacao: {token}\n"
        f"Validade: {expires_in_minutes} minutos.\n\n"
        "Se voce nao solicitou esta recuperacao, ignore este email."
    )
    send_email(recipient, subject, body)


def send_email(recipient: str, subject: str, body: str) -> None:
    try:
        config = load_encrypted_config()
    except SecureConfigError as exc:
        raise EmailError(exc.args[0] or "Configuracao de email indisponivel.") from exc

    smtp_server = str(config.get("smtp_server") or "").strip()
    smtp_port = int(config.get("smtp_port") or 587)
    sender = str(config.get("sender") or "").strip()
    password = str(config.get("password") or "")
    use_tls = bool(config.get("use_tls", True))

    if not smtp_server or not sender or not password:
        raise EmailError("Configuracao de email incompleta.")

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            server.login(sender, password)
            server.send_message(message)
    except Exception as exc:
        raise EmailError("Nao foi possivel enviar o email de recuperacao.", HTTPStatus.BAD_GATEWAY) from exc
