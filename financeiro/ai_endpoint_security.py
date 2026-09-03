from __future__ import annotations

import http.client
import ipaddress
import os
import socket
import ssl
from contextlib import contextmanager
from urllib.parse import urlparse
from urllib.request import HTTPHandler, HTTPSHandler, OpenerDirector, Request


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


def allowed_local_endpoints() -> set[tuple[str, int | None]]:
    """
    Endpoints locais permitidos pelo operador no formato host:port ou host.
    Preferencialmente com porta, para nao abrir toda a rede local.
    """
    raw = str(os.environ.get("AI_ALLOWED_LOCAL_ENDPOINTS") or "")
    result: set[tuple[str, int | None]] = set()
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        # IPv6 com porta usa notacao [addr]:port; aqui tratamos o caso geral
        # pelo ultimo ':' separador de porta, que funciona para IPv4 e hostnames.
        if ":" in entry:
            host_part, port_part = entry.rsplit(":", 1)
            host_part = host_part.strip()
            try:
                port = int(port_part)
                if port < 1 or port > 65535:
                    port = None
            except ValueError:
                host_part = entry
                port = None
        else:
            host_part = entry
            port = None
        if host_part:
            result.add((host_part.lower(), port))
    return result


def _default_port_for_scheme(scheme: str) -> int:
    return 443 if scheme == "https" else 80


def _parse_ai_url(url: str) -> tuple[str, str, int, str]:
    """
    Faz parsing e validacoes comuns a base_url e URL final de requisicao.

    Retorna (scheme, hostname, port, path). Levanta AIEndpointSecurityError em
    qualquer problema de formato, credenciais, porta, query, fragmento ou path
    malicioso.
    """
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
    if port is None:
        port = _default_port_for_scheme(scheme)

    path = parsed.path or ""
    if ".." in path or "//" in path:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    if parsed.query or parsed.fragment:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    return scheme, hostname, port, path


def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve um hostname para uma lista de enderecos IP."""
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
    """Verifica se um endereco IP e privado, loopback, link-local, multicast, reservado ou nao especificado."""
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


def _matches_local_allowlist(
    hostname: str, port: int, resolved_ips: list[str]
) -> bool:
    """Verifica se hostname/porta/IP resolvido consta de uma allowlist local explicita."""
    if hostname in allowed_local_hosts():
        return True

    endpoints = allowed_local_endpoints()
    if not endpoints:
        return False

    for host_entry, entry_port in endpoints:
        if entry_port is not None and entry_port != port:
            continue
        if host_entry == hostname:
            return True
        if host_entry in resolved_ips:
            return True
    return False


def _validate_ai_url(url: str) -> tuple[str, str, int, str, list[str], bool]:
    """
    Valida uma URL de IA (base ou final) contra regras anti-SSRF.

    Retorna (scheme, hostname, port, path, resolved_ips, any_private).
    Levanta AIEndpointSecurityError se a URL for invalida ou nao permitida.
    """
    scheme, hostname, port, path = _parse_ai_url(url)

    local_hosts = allowed_local_hosts()
    endpoints = allowed_local_endpoints()
    allow_private = allow_private_endpoints()
    is_explicitly_allowed_host = hostname in local_hosts

    # Hostnames listados explicitamente pelo operador sao aceitos sem checagem
    # de resolucao, desde que endpoints privados estejam habilitados.
    if is_explicitly_allowed_host and allow_private:
        # Ainda assim precisamos de um IP para conectar; resolvemos depois no
        # transporte, mas validamos aqui a allowlist de porta, se houver.
        if endpoints and not _matches_local_allowlist(hostname, port, []):
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)
        return scheme, hostname, port, path, [], True

    resolved_ips = _resolve_hostname(hostname)
    if not resolved_ips:
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    any_private = any(is_private_ip(ip) for ip in resolved_ips)

    if any_private:
        if not allow_private:
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)
        # Com endpoints privados habilitados, exigimos allowlist explicita.
        if not (local_hosts or endpoints):
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)
        if not _matches_local_allowlist(hostname, port, resolved_ips):
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    if scheme == "http" and not any_private:
        # http so e aceito para destinos privados, para evitar envio de
        # credenciais em texto pela internet publica.
        raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    return scheme, hostname, port, path, resolved_ips, any_private


def validate_ai_base_url(url: str, allow_private: bool | None = None) -> str:
    """
    Valida uma URL base de IA contra regras anti-SSRF.

    Levanta AIEndpointSecurityError se a URL for invalida ou nao permitida.
    Retorna a URL normalizada sem barra final.
    """
    # allow_private mantido por compatibilidade; a fonte de verdade continua
    # sendo as variaveis de ambiente, usadas internamente por _validate_ai_url.
    scheme, hostname, port, path, resolved_ips, _ = _validate_ai_url(url)
    _ = resolved_ips
    clean_path = path.rstrip("/")
    if port == _default_port_for_scheme(scheme):
        netloc = hostname
    else:
        netloc = f"{hostname}:{port}"
    return f"{scheme}://{netloc}{clean_path}"


def validate_ai_request_url(url: str) -> tuple[str, str, int, str, list[str]]:
    """
    Valida a URL final de uma requisicao de IA.

    Retorna (scheme, hostname, port, path, resolved_ips).
    Levanta AIEndpointSecurityError se a URL for invalida ou nao permitida.
    """
    scheme, hostname, port, path, resolved_ips, _ = _validate_ai_url(url)
    return scheme, hostname, port, path, resolved_ips


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Conexao HTTP que conecta a um IP fixo, preservando o hostname do Host."""

    def __init__(
        self,
        host: str,
        resolved_host: str,
        port: int | None = None,
        timeout: float | None = None,
        **kwargs,
    ):
        super().__init__(host, port=port, timeout=timeout, **kwargs)
        self._resolved_host = resolved_host

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._resolved_host, self.port),
            self.timeout,
            self.source_address,
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Conexao HTTPS que conecta a um IP fixo, preservando Host/SNI."""

    def __init__(
        self,
        host: str,
        resolved_host: str,
        port: int | None = None,
        timeout: float | None = None,
        context: ssl.SSLContext | None = None,
        **kwargs,
    ):
        super().__init__(host, port=port, timeout=timeout, context=context, **kwargs)
        self._resolved_host = resolved_host

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._resolved_host, self.port),
            self.timeout,
            self.source_address,
        )
        if self._tunnel_host:
            self._tunnel()
        else:
            # Python 3.13 nao expoe server_hostname; o SNI usa self.host.
            self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)


def _build_host_header(hostname: str, port: int) -> str:
    if port == 443 or port == 80:
        return hostname
    return f"{hostname}:{port}"


@contextmanager
def ai_urlopen(request, **kwargs):
    """
    Abre uma requisicao de IA com DNS pinning e sem seguir redirecionamentos.

    A URL final e validada anti-SSRF, o hostname e resolvido uma unica vez e a
    conexao TCP e feita diretamente ao IP validado, preservando o hostname
    original no cabecalho Host, no SNI e na validacao do certificado TLS.
    """
    if isinstance(request, str):
        request = Request(request)

    scheme, hostname, port, path, resolved_ips = validate_ai_request_url(
        request.full_url
    )

    # Hostnames explicitamente permitidos sem resolucao sao resolvidos agora,
    # no momento da conexao, e ainda assim passam pelas mesmas regras de IP.
    if not resolved_ips:
        resolved_ips = _resolve_hostname(hostname)
        if not resolved_ips:
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)
        any_private = any(is_private_ip(ip) for ip in resolved_ips)
        if any_private and not allow_private_endpoints():
            raise AIEndpointSecurityError(DEFAULT_ERROR_MESSAGE)

    selected_ip = resolved_ips[0]
    request_path = path or "/"
    timeout = kwargs.get("timeout")
    context = kwargs.get("context")

    if scheme == "https":
        conn: http.client.HTTPConnection = _PinnedHTTPSConnection(
            hostname,
            selected_ip,
            port=port,
            timeout=timeout,
            context=context,
        )
    else:
        conn = _PinnedHTTPConnection(
            hostname,
            selected_ip,
            port=port,
            timeout=timeout,
        )

    headers = dict(request.header_items())
    headers.setdefault("Host", _build_host_header(hostname, port))
    body = request.data
    if isinstance(body, str):
        body = body.encode("utf-8")

    try:
        conn.request(request.get_method() or "GET", request_path, body=body, headers=headers)
        yield conn.getresponse()
    finally:
        conn.close()


def create_ai_opener() -> OpenerDirector:
    """Cria um opener urllib que NAO segue redirecionamentos HTTP."""
    opener = OpenerDirector()
    opener.add_handler(HTTPHandler())
    opener.add_handler(HTTPSHandler())
    return opener
