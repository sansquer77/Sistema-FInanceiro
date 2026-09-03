from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse
from urllib.request import HTTPHandler, HTTPSHandler, OpenerDirector


class AIEndpointSecurityError(Exception):
    """URL base de IA rejeitada por violar as regras anti-SSRF."""


DEFAULT_ERROR_MESSAGE = "URL base de IA invalida ou nao permitida."


def allow_private_endpoints() -> bool:
    """Retorna True quando o operador habilitou explicitamente endpoints locais/privados."""
    return str(os.environ.get("AI_ALLOW_PRIVATE_ENDPOINTS") or "").lower() in (
        "1",
        "true",
        "yes",
    )


def allowed_local_hosts() -> set[str]:
    """Hostnames adicionais permitidos pelo operador para endpoints locais."""
    raw = str(os.environ.get("AI_ALLOWED_LOCAL_HOSTS") or "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def validate_ai_base_url(url: str, allow_private: bool | None = None) -> str:
    """
    Valida uma URL base de IA contra regras anti-SSRF.

    Levanta AIEndpointSecurityError se a URL for inválida ou não permitida.
    Retorna a URL normalizada sem barra final.
    """
    if allow_private is None:
        allow_private = allow_private_endpoints()

    parsed = urlparse(str(url or "").strip())

    scheme = (parsed.scheme or "").lower()
    if scheme not in {"http", "https"}:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    if parsed.username is not None or parsed.password is not None:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    try:
        port = parsed.port
    except ValueError:
        port = -1
    if port is not None and (port < 1 or port > 65535):
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    path = parsed.path or "/"
    if ".." in path or "//" in path:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    if parsed.query or parsed.fragment:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    local_hosts = allowed_local_hosts()
    is_explicitly_allowed_host = hostname in local_hosts

    # Hostnames listados explicitamente pelo operador são aceitos sem checagem
    # de resolução, desde que endpoints privados estejam habilitados.
    if is_explicitly_allowed_host and allow_private:
        return _build_normalized_url(scheme, hostname, port, path)

    resolved_ips = _resolve_hostname(hostname)
    if not resolved_ips:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    any_private = any(is_private_ip(ip) for ip in resolved_ips)

    if any_private and not allow_private:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    if scheme == "http" and not any_private:
        # http so e aceito para destinos privados, para evitar envio de
        # credenciais em texto pela internet publica.
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    return _build_normalized_url(scheme, hostname, port, path)


def _build_normalized_url(scheme: str, hostname: str, port: int | None, path: str) -> str:
    if port is None:
        netloc = hostname
    else:
        default_port = 443 if scheme == "https" else 80
        netloc = hostname if port == default_port else f"{hostname}:{port}"
    clean_path = (path or "/").rstrip("/")
    return f"{scheme}://{netloc}{clean_path}"


def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve um hostname para uma lista de endereços IP."""
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        return []
    ips = []
    for info in infos:
        family, _, _, _, sockaddr = info
        if family in (socket.AF_INET, socket.AF_INET6):
            ips.append(sockaddr[0])
    return ips


def is_private_ip(ip_str: str) -> bool:
    """Verifica se um endereço IP e privado, loopback, link-local, multicast, reservado ou nao especificado."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def create_ai_opener() -> OpenerDirector:
    """Cria um opener que NAO segue redirecionamentos HTTP."""
    opener = OpenerDirector()
    opener.add_handler(HTTPHandler())
    opener.add_handler(HTTPSHandler())
    return opener


def ai_urlopen(request, **kwargs):
    """Abre uma requisicao de IA usando o opener que bloqueia redirecionamentos."""
    return create_ai_opener().open(request, **kwargs)
