---
tipo: adr
area: investimentos
status: implementado
versao: 1.1
atualizado: 2026-08-08
relacionados:
  - "[[../specs/preferencias-abas]]"
  - "[[../specs/investimentos-portfolio]]"
  - "[[0005-smtp-criptografado-local]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
tags: [adr, "area/investimentos", "status/implementado"]
aliases: ["ADR-0009", "Cotações de Fundos Mais Retorno"]
---

# ADR-0009 — Cotas de fundos via API Mais Retorno (opt-in)

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-08-08 · relacionados: [[../specs/preferencias-abas]], [[../specs/investimentos-portfolio]], [[0005-smtp-criptografado-local]]

## Problema

Posições de fundos de investimento (`fund`) no Portfólio não têm fonte automática de cota: Yahoo Finance não indexa fundos brasileiros por CNPJ e a regra atual marca a posição como `Cotacao manual pendente`. O usuário precisa decidir se vale integrar uma fonte externa de cotas e, em caso positivo, como armazenar a credencial de forma segura sem violar as regras do projeto (sem framework, sem banco externo, créditos criptografados em `secure_config.py`).

## Usuário

Usuários do Portfólio com fundos de investimento brasileiros que queiram valor atual automático sem cadastrar valor manual sempre que consultam.

## Jornada

1. O usuário ativa a integração na aba **APIs** de Preferências informando a chave da API Mais Retorno (plano com cota mensal e identificador por CNPJ).
2. Posições de fundo com CNPJ e carteira em BRL passam a usar a última cota da API para o valor atual.
3. Falhas ou desativação mantêm o valor de custo com status amigável — nunca bloqueiam o Portfólio.

## Regras

### Decisão recomendada

Adotar a **API Mais Retorno (mr-data v4)** como fonte **opcional** de cotas para posições `fund`:

- Identificador `{cnpj}:fi`, endpoint de cotações (`GET /quotes/{identifier}`), última cota do retorno como preço e a anterior como variação do dia.
- Chave por usuário em `data/mais_retorno_config_user_{id}.enc`, criptografada pela mesma infraestrutura do SMTP/IA (`secure_config.py`), **nunca** devolvida por rota nem logada.
- Integração desligada por padrão; chamadas externas apenas quando ativada, com cache até o fim do dia corrente em `quote_cache` (reusando `cached_json_url`) e nunca com transação de escrita aberta.
- Erros (401/403/429/indisponibilidade) viram status amigável na posição e o valor de custo é mantido.

### Motivos

- Fundos brasileiros se identificam por CNPJ e a Mais Retorno é a fonte especializada em fundos do Brasil com API documentada, payload compacto (última cota) e chave gerada no portal do usuário.
- Segue os padrões já adotados para SMTP e IA: opt-in, chave criptografada por usuário, nunca vazar segredos, cache com TTL e resiliência sem bloqueio.
- A variante de preço `c` do endpoint de cotações responde em `Decimal` — converte para centavos inteiros respeitando a regra de valores monetários.
- Não contraria a restrição de stack: apenas requisição HTTP da biblioteca padrão (`urllib`), como Yahoo/CoinGecko/BCB já existentes.

### Resiliência

- Limite mensal de requisições do plano retorna `429`; o cache de 90 min evita consumir a cota a cada abertura do Portfólio.
- Chave inválida, plano sem acesso ao recurso (`403`) ou indisponibilidade tratam como "cotação indisponível" — o resto do portfólio continua funcionando.

### Privacidade e segurança

- Credenciais nunca em texto puro, nunca versionadas, nunca em pacote distribuível (regra de `secure_config.py`).
- A chave da API é env apenas ao servidor da Mais Retorno via `X-Api-Key`, nunca ao frontend.

## API e dados

- Rotas: `GET /api/mais-retorno-config` e `PUT /api/mais-retorno-config` (documentadas em [[../arquitetura]]).
- Arquivo: `data/mais_retorno_config_user_{id}.enc` (payload `{"enabled": bool, "api_key": str}`).
- Nenhuma tabela nova: configuração segue o padrão SMTP.

## Critérios de aceite

- Com a integração ativada, posição de fundo com CNPJ em BRL usa a última cota da API para o valor atual.
- Sem ativação/sem CNPJ/não-BRL, a posição mantém valor de custo com status `Cotacao manual pendente` e nenhuma chamada à API.
- A chave nunca aparece nas respostas nem em texto puro no disco.
- Falha da API nunca bloqueia a abertura do Portfólio.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Manter valor manual sempre | Zero custo e privacidade total, mas não atende a necessidade de valor atual automático. |
| Yahoo Finance par posição de fundo com ticker | Não cobre fundos brasileiros por CNPJ; apenas ações/ETFs; rejeitada para fundos. |
| Dados de Mercado (DDM) | Possível alternativa; avaliação futura se a Mais não atender (mesmo desenho de chave e cache se aplica). |
| Importar cotas manualmente | Continua disponível, mas não resolve a automatização. |

## Fora de escopo

- Cotar outras classes via Mais Retorno (ETFs/ações continuam Yahoo; FIIs listados como `stock` seguem Yahoo).
- Uso da carteira detalhada, estatísticas ou histórico longo da API (somente última cota agora).
- Suporte a subclasses de fundos (`{cnpj}-{subclasse}:fi`).

## Changelog

- `1.1` — 2026-08-08 — Cache passa de 90 minutos para até o fim do dia corrente; CNPJ só dígitos + `:fi` e `start_date`/`end_date` iguais à data atual na chamada à API.
- `1.0` — 2026-08-08 — Decisão adotada: Mais Retorno opt-in com chave criptografada por usuário, cache de 90 min e fallback de custo sem bloqueio.

## Relacionados

- [[../specs/preferencias-abas]]
- [[../specs/investimentos-portfolio]]
- [[0005-smtp-criptografado-local]]
- [[0003-sqlite-fonte-de-verdade]]