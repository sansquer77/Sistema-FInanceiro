---
tipo: adr
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-08-31
relacionados:
  - "[[../specs/seguranca-ai-ssrf]]"
  - "[[../specs/seguranca-transporte-externo]]"
  - "[[../specs/preferencias-abas]]"
  - "[[../specs/tendencias-saude-financeira]]"
  - "[[../specs/consultor]]"
tags: [adr, "area/seguranca", "status/implementado"]
aliases: ["ADR-0015", "SSRF em endpoints de IA"]
---

# ADR-0015 — Validação de endpoints configuráveis de IA contra SSRF

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-08-31 · relacionados: [[../specs/seguranca-ai-ssrf]], [[../specs/seguranca-transporte-externo]], [[../specs/preferencias-abas]]

## Problema

As integrações de IA (Tendências e Consultor) permitem que o usuário configure uma URL base arbitrária para provedores customizados ou locais. Isso introduz risco de SSRF: o servidor pode ser induzido a fazer requisições para serviços internos da máquina ou da rede local, dependendo do que o usuário ou um atacante consegue colocar no campo `base_url`.

## Usuário

Usuários que configuram IA customizada/local e operadores que decidem se a instalação aceita endpoints privados.

## Jornada

1. Usuário configura URL base de IA em Preferências.
2. O app valida a URL antes de persistir.
3. Em cada uso, a URL é revalidada e redirecionamentos são bloqueados.
4. Se o operador habilitou endpoints privados, URLs locais são aceitas; senão, falham com mensagem amigável.

## Regras

### Decisão recomendada

Adotar uma **fronteira de validação SSRF dedicada** em `financeiro/ai_endpoint_security.py`:

- Validar esquema, hostname, porta, ausência de credenciais/path/query/fragment e resolução DNS.
- Rejeitar IPs privados/reservados por padrão.
- Permitir IPs privados apenas quando o operador definir `AI_ALLOW_PRIVATE_ENDPOINTS=true`.
- Permitir hostnames locais adicionais via `AI_ALLOWED_LOCAL_HOSTS` (CSV), desde que a flag de privados esteja habilitada.
- Bloquear redirecionamentos HTTP nas requisições de IA.
- Aplicar a validação tanto no salvamento da configuração quanto no momento da requisição.

### Motivos

- A URL de IA é a única configuração editável pelo usuário que resulta em requisições de saída do servidor para um destino arbitrário.
- Provedores locais legítimos (Ollama, LM Studio, etc.) rodam em `localhost` ou IPs privados; não podemos rejeitá-los incondicionalmente sem quebrar casos de uso reais.
- Deixar a decisão de permitir privados com o operador (via env) mantém o padrão seguro por omissão e permite homologação/desenvolvimento local.
- Bloquear redirecionamentos evita bypass de validação por DNS rebinding ou resolução diferente no destino.
- Manter a validação no núcleo Python segue a regra de fronteira: a interface apenas orquestra, as regras de segurança ficam no backend.

### Privacidade e segurança

- Mensagens de erro não expõem detalhes de resolução DNS ou topologia interna.
- A validação no salvamento impede persistência de configurações maliciosas; a validação no uso protege contra alterações de DNS ou configurações legadas.
- Nenhum segredo de IA é logado ou exposto.

## API e dados

- Nenhuma rota ou tabela nova.
- Rotas afetadas: `PUT /api/ai-settings`, `POST /api/financial-health-trends/ai-summary`, `POST /api/consultor/analyze`.
- Variáveis de ambiente: `AI_ALLOW_PRIVATE_ENDPOINTS`, `AI_ALLOWED_LOCAL_HOSTS`.

## Critérios de aceite

- Dado um endpoint `https` público válido, quando validado, então é aceito.
- Dado um endpoint `http` local sem permissão explícita, quando validado, então é rejeitado.
- Dado um endpoint que resolva para IP privado com `AI_ALLOW_PRIVATE_ENDPOINTS=true`, quando validado, então é aceito.
- Dado um redirecionamento 3xx em uma requisição de IA, quando ocorrido, então é bloqueado.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Não permitir nenhum endpoint editável | Rejeitada: quebra o suporte a provedores locais e customizados já existente. |
| Permitir tudo e confiar no usuário | Rejeitada: expõe o servidor a SSRF. |
| Validar apenas no frontend | Rejeitada: bypass trivial; regras de segurança devem ficar no backend. |
| Usar lista fixa de provedores permitidos | Rejeitada: impede inovação e uso de provedores locais/open-source. |
| Validar apenas no salvamento | Rejeitada: não protege contra mudanças de DNS ou configurações legadas. |
| Seguir redirecionamentos e revalidar cada destino | Rejeitada: complexidade maior; para IA, bloquear redirecionamentos é aceitável e mais seguro. |

## Fora de escopo

- Endpoints de cotações, PTAX, Mais Retorno e verificação de versão (usam domínios fixos).
- Proxy reverso, VPN ou tunelamento para IA.
- Validação de certificado fora do TLS padrão.

## Changelog

- `1.0` — 2026-08-31 — Decisão adotada e implementada: validação SSRF centralizada em `financeiro/ai_endpoint_security.py`, integrada ao salvamento de configuração e às requisições de IA, com opt-in por env para provedores locais.

## Relacionados

- [[../specs/seguranca-ai-ssrf]]
- [[../specs/seguranca-transporte-externo]]
- [[../specs/preferencias-abas]]
- [[../specs/tendencias-saude-financeira]]
- [[../specs/consultor]]
