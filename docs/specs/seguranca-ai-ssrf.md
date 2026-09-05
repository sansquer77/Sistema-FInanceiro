---
tipo: spec
area: seguranca
status: implementado
versao: 1.1
atualizado: 2026-09-03
relacionados:
  - "[[seguranca-transporte-externo]]"
  - "[[tendencias-saude-financeira]]"
  - "[[consultor]]"
  - "[[preferencias-abas]]"
  - "[[arquitetura]]"
tags: [spec, "area/seguranca", "status/implementado"]
aliases: ["Segurança de endpoints de IA", "SSRF em endpoints de IA"]
---

# Segurança de endpoints de IA contra SSRF

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-09-03 · relacionados: [[seguranca-transporte-externo]], [[tendencias-saude-financeira]], [[consultor]], [[preferencias-abas]], [[arquitetura]]

## Problema

A integração de IA permite que o usuário configure uma URL base arbitrária para provedores customizados ou locais. Sem validação, um endpoint malicioso ou uma configuração enganosa pode transformar o servidor em um cliente de ataques SSRF, direcionando requisições para serviços internos da máquina ou da rede local.

## Usuário

Todo usuário que configura um provedor de IA customizado/local em **Preferências > APIs**, e o operador da instalação que decide se endpoints privados são aceitos.

## Jornada

1. O usuário escolhe o provedor "Custom / Local" (ou outro com URL base editável) em Preferências.
2. Informa a URL base, modelo e, quando necessário, chave de API.
3. Ao salvar, o app valida a URL contra regras de esquema, hostname e IP resolvido.
4. Ao usar o Consultor ou a reescrita de Tendências, a requisição é novamente validada e redirecionamentos são bloqueados.
5. Se o operador tiver habilitado endpoints privados, URLs locais são aceitas; caso contrário, recebem erro claro.

## Dados

| Campo | Tipo | Descrição |
|---|---|---|
| `base_url` | URL | URL base do endpoint de IA, configurável pelo usuário. |
| `AI_ALLOW_PRIVATE_ENDPOINTS` | env boolean | Quando `true`, permite que a URL resolva para IPs privados, loopback ou link-local. |
| `AI_ALLOWED_LOCAL_HOSTS` | env CSV | Lista opcional de hostnames permitidos além da validação de IP (ex.: `ollama.local,lmstudio.local`). |
| `AI_ALLOWED_LOCAL_ENDPOINTS` | env CSV | Allowlist estrita de endpoints locais no formato `host:port` ou `ip:port`, preferencialmente com porta. Exige `AI_ALLOW_PRIVATE_ENDPOINTS=true`. |

## Regras

- Apenas os esquemas `http` e `https` são aceitos.
- Por padrão, a URL deve usar `https`.
- `http` só é permitido quando o hostname resolvido for local e `AI_ALLOW_PRIVATE_ENDPOINTS=true`.
- A URL não pode conter credenciais de usuário (`user:pass@`), porta fora do intervalo 1–65535, caminho, query ou fragmento.
- O hostname deve ser resolvível; endereços literais (IPv4/IPv6) são aceitos desde que não sejam privados/reservados, salvo quando permitido pelo operador.
- Endereços privados/reservados incluem, no mínimo: loopback (`127.0.0.0/8`, `::1/128`), RFC 1918 (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`, `fe80::/10`), multicast, broadcast e redes reservadas/documentação.
- Redirecionamentos HTTP são bloqueados: respostas 3xx resultam em falha segura.
- A validação ocorre no salvamento da configuração e no momento da requisição.
- Erros de validação expõem apenas mensagem amigável, sem detalhes de rede interna.
- Quando `AI_ALLOW_PRIVATE_ENDPOINTS=true`, endereços privados só são aceitos se houver uma allowlist explícita (`AI_ALLOWED_LOCAL_ENDPOINTS` ou `AI_ALLOWED_LOCAL_HOSTS`).
- `AI_ALLOWED_LOCAL_ENDPOINTS` usa o formato `host:port` ou `ip:port`; quando a porta é informada, apenas essa porta é permitida para o host/IP.
- O transporte de IA resolve o hostname uma única vez e conecta diretamente ao IP validado (DNS pinning), preservando o hostname original no cabeçalho `Host`, no SNI e na validação do certificado TLS.
- A URL final montada (`/chat/completions`, `/messages`, `/models/...:generateContent`) é validada antes da requisição, além da `base_url`.
- `AI_ALLOWED_LOCAL_HOSTS` pode ampliar a allowlist por hostname sem resolução, mas ainda respeita a exigência de allowlist explícita.

## API e dados

- Rotas afetadas:
  - `PUT /api/ai-settings` — valida `base_url` antes de persistir.
  - `POST /api/financial-health-trends/ai-summary` — valida a URL configurada antes de chamar a IA.
  - `POST /api/consultor/analyze` — valida a URL configurada antes de chamar a IA.
- Nenhuma tabela nova. A validação é comportamental, não de schema.

## Critérios de aceite

- Dado uma URL base `https://api.openai.com/v1`, quando validada, então é aceita.
- Dado uma URL base `http://api.openai.com/v1`, quando `AI_ALLOW_PRIVATE_ENDPOINTS` não está ativada, então é rejeitada.
- Dado uma URL base `http://127.0.0.1:11434`, quando `AI_ALLOW_PRIVATE_ENDPOINTS=true`, então é aceita.
- Dado uma URL base `http://localhost:11434`, quando `AI_ALLOW_PRIVATE_ENDPOINTS=true` e localhost resolve para 127.0.0.1, então é aceita.
- Dado uma URL base `http://192.168.1.10:11434`, quando `AI_ALLOW_PRIVATE_ENDPOINTS` não está ativada, então é rejeitada.
- Dado uma URL base `ftp://exemplo.com/v1`, quando validada, então é rejeitada por esquema inválido.
- Dado uma URL base `https://user:pass@exemplo.com/v1`, quando validada, então é rejeitada por conter credenciais.
- Dado uma URL base `https://exemplo.com:99999/v1`, quando validada, então é rejeitada por porta inválida.
- Dado uma URL base `https://exemplo.com/v1?x=1`, quando validada, então é rejeitada por conter query.
- Dado uma URL base `https://10.0.0.1/v1`, quando `AI_ALLOW_PRIVATE_ENDPOINTS` não está ativada, então é rejeitada antes da requisição.
- Dado uma URL base `https://exemplo.com/v1` que responde com redirecionamento 302, quando a requisição de IA é feita, então o redirecionamento é bloqueado e o fluxo falha de forma segura.
- Dado `AI_ALLOWED_LOCAL_HOSTS=ollama.local`, quando a URL base é `http://ollama.local:11434`, então é aceita mesmo sem resolução de IP permitido, desde que `AI_ALLOW_PRIVATE_ENDPOINTS=true`.
- Dado uma URL base com hostname que resolve para IP privado, quando `AI_ALLOW_PRIVATE_ENDPOINTS` não está ativada, então é rejeitada.
- Dado uma URL base inválida no formulário de Preferências, quando o usuário salva, então recebe mensagem amigável e a configuração não é persistida.
- Dado uma configuração já persistida com URL válida que posteriormente passa a resolver para IP privado, quando usada sem permissão de privado, então a requisição falha de forma segura.
- Dado `AI_ALLOWED_LOCAL_ENDPOINTS=127.0.0.1:11434`, quando a URL base é `http://127.0.0.1:11434`, então é aceita; quando é `http://127.0.0.1:11435`, então é rejeitada.
- Dado `AI_ALLOW_PRIVATE_ENDPOINTS=true` sem allowlist configurada, quando a URL base resolve para IP privado, então é rejeitada.
- Dado uma requisição de IA para `https://api.example.com/v1/chat/completions`, quando o transporte é iniciado, então o socket conecta ao IP validado, o cabeçalho `Host` e o SNI usam `api.example.com`.
- Dado uma requisição de IA cujo hostname resolve para IP público na validação e para IP privado na conexão, quando o transporte é iniciado, então a conexão usa o IP da validação e não sofre DNS rebinding.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Validação de endpoints de cotações, PTAX, Mais Retorno ou verificação de versão (já possuem domínios fixos).
- Proxy reverso ou VPN para endpoints locais.
- Validação de certificados além do TLS padrão.
- Rate-limit por endpoint.

## Plano de implementação

- [x] Passo 1 — Criar `financeiro/ai_endpoint_security.py` com parser de URL, resolução DNS, checagem de IP privado e função de validação exposta. Fecha: critérios 1 a 13.
- [x] Passo 2 — Integrar validação em `financeiro/secure_config.py` no salvamento de `base_url`. Fecha: critérios 1, 2, 12.
- [x] Passo 3 — Integrar validação e bloqueio de redirecionamentos em `financeiro/ai_summary.py` e `financeiro/consultor_provider.py`. Fecha: critérios 10, 13.
- [x] Passo 4 — Adicionar `tests/test_ai_endpoint_security.py` com casos de esquema, hostname, IP, redirecionamento e env. Fecha: todos os critérios.
- [x] Passo 5 — Implementar DNS pinning no transporte (`ai_urlopen`) conectando ao IP validado e preservando Host/SNI. Fecha: critérios de transporte.
- [x] Passo 6 — Adicionar allowlist estrita por host:port (`AI_ALLOWED_LOCAL_ENDPOINTS`) e exigi-la quando privados estiverem habilitados. Fecha: critérios de allowlist.
- [x] Passo 7 — Validar a URL final da requisição em `ai_urlopen`, além da `base_url`. Fecha: defesa em profundidade.
- [x] Passo 8 — Atualizar `docs/arquitetura.md`, `docs/requisitos.md` e README do vault com a nova fronteira de segurança. Fecha: documentação.

## Changelog

- `1.1` — 2026-09-03 — DNS pinning no transporte de IA, allowlist estrita por host:port (`AI_ALLOWED_LOCAL_ENDPOINTS`) e validação da URL final da requisição.

- `1.0` — 2026-09-03 — Implementada proteção SSRF para endpoints configuráveis de IA: validação de esquema, hostname, IP resolvido, bloqueio de redirecionamentos e opt-in controlado por operador para endpoints privados (`AI_ALLOW_PRIVATE_ENDPOINTS` / `AI_ALLOWED_LOCAL_HOSTS`).

## Relacionados

- [[seguranca-transporte-externo]]
- [[tendencias-saude-financeira]]
- [[consultor]]
- [[preferencias-abas]]
- [[arquitetura]]
