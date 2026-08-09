---
tipo: spec
area: usuario
status: implementado
versao: 0.8
atualizado: 2026-08-09
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[tendencias-saude-financeira]]"
  - "[[recuperacao-senha]]"
  - "[[seguranca-autenticacao]]"
  - "[[arquitetura]]"
  - "[[../adr/0010-segredos-criptografados-sqlite]]"
tags: [spec, "area/usuario", "status/implementado"]
aliases: ["Preferências", "Abas de Preferências", "Mais Retorno"]
---

# Preferências — abas Geral, APIs e Perigo

> [!info] Status
> **implementado** · área: `usuario` · atualizado em 2026-08-09 · relacionados: [[investimentos-portfolio]], [[tendencias-saude-financeira]], [[recuperacao-senha]]

## Problema

A tela **Usuário > Preferências** é um rolo único de painéis. Conforme novas integrações opcionais surgem (IA, Mais Retorno, Open Finance), a tela fica longa e o usuário precisa rolar muito para achar a seção que procura. Ações destrutivas (apagar lançamentos, apagar conta) ficam misturadas a configurações rotineiras, aumentando o risco de clique acidental.

## Usuário

Qualquer usuário autenticado que precise configurar perfil, integrações opcionais ou executar ações destrutivas da própria conta.

## Jornada

1. O usuário abre **Usuário > Preferências** e encontra três abas: **Geral**, **APIs** e **Perigo**.
2. Na aba **Geral**, ajusta aparência, email, senha e recuperação por email (configurações rotineiras).
3. Na aba **APIs**, liga/desliga e configura integrações opcionais: a **Configuração de IA** (reescrita de resumo de Tendências e Consultor) e a **Mais Retorno** (cotas de fundos do Portfólio).
4. Na aba **Perigo**, encontra as ações destrutivas **Apagar lançamentos** e **Apagar conta**, que continuam exigindo confirmação explícita e senha atual.
5. No Portfólio, com a integração Mais Retorno ativada, posições de fundos com CNPJ passam a exibir o valor atual pela última cota disponível.

## Regras

**Abas:**
- Preferências tem exatamente três abas: `Geral`, `APIs` e `Perigo`. A troca de aba mostra/oculta os painéis sem recarregar a página e sem estado persistente entre sessões (a primeira aba aberta é sempre `Geral`).
- A aba **Geral** contém: Aparência (tema), Alterar email, Alterar senha e Recuperação por email.
- A aba **APIs** contém: Configuração de IA (provedor, modelo, chave, ativação — reutilizada por Tendências e Consultor) e Configuração Mais Retorno.
- A aba **Perigo** contém apenas as ações destrutivas: Apagar lançamentos e Apagar conta, com os mesmos formulários, confirmações e rotas atuais — nada é removido nem enfraquecido.

**Mais Retorno (configuração):**
- A integração é **opt-in**: desligada por padrão, sem chave armazenada até o usuário salvar.
- A chave de API é criptografada por usuário em `secure_configs.payload_enc` no SQLite, usando a mesma infraestrutura de `secure_config.py` (mesma chave mestra do SMTP/IA). A chave **nunca** é devolvida por nenhuma rota nem logada.
- Instalações existentes com `data/email_config_user_{id}.enc`, `data/ai_config_user_{id}.enc`, `data/mais_retorno_config_user_{id}.enc` ou `data/email_config.key` continuam compatíveis: no primeiro uso, o envelope criptografado é copiado para `secure_configs` e a chave mestra legada é copiada para `secure/config.key`, sem apagar os arquivos antigos automaticamente.
- Novas gravações salvam SMTP, IA e Mais Retorno como blobs criptografados por usuário no SQLite; a chave mestra padrão fica fora de `data/`, em `secure/config.key`, ou no caminho definido por `SISTEMA_FINANCEIRO_CONFIG_KEY_PATH`.
- Salvar com `enabled` ligado sem chave armazenada (ou sem chave nova informada) retorna erro amigável e não altera o estado anterior.
- Desligar mantém a chave criptografada em disco (sem expô-la) para facilitar reativação; informar chave nova substitui a anterior.

**Mais Retorno (cotas de fundos):**
- Apenas posições com `asset_type = fund` são afetadas; ações/ETFs/FIIs listados como `stock` continuam usando Yahoo Finance.
- A cota é buscada apenas quando a integração está ativada, a posição tem **CNPJ** preenchido e a carteira é em **BRL**. Fora disso, a posição mantém o comportamento atual (`Cotacao manual pendente`).
- O identificador usado na API é `{cnpj}:fi`, com o CNPJ **somente dígitos** (sem pontos e sem barra — ex.: `46.422.299/0001-73` vira `46422299000173:fi`), consultando o endpoint de cotações sempre com `start_date`/`end_date` = **data atual**; a variação do dia usa a cota anterior do mesmo retorno.
- Respostas da API são cacheadas em `quote_cache` (TTL até o **fim do dia corrente**, reutilizando `cached_json_url`) — o cache evita re-consumo da API ao entrar na tela várias vezes no mesmo dia, e chamadas externas nunca acontecem com transação de escrita aberta.
- O preço da cota chega como numeral JSON com separador decimal `.` (ex.: `1.601637`) e é convertido para centavos inteiros no núcleo.
- Em dias sem cota publicada (fim de semana/feriado), a data atual retorna lista vazia e a consulta é refeita automaticamente com janela retroativa de 7 dias, usando a última cota publicada.
- Falha da API (indisponível, chave inválida, cota do plano esgotada) exibe o status de cotação com mensagem amigável e mantém o valor de custo da posição — nunca bloqueia a abertura do Portfólio.

## API e dados

- `GET /api/mais-retorno-config` — status da configuração (`configured`, `enabled`, `has_api_key`), sem segredos.
- `PUT /api/mais-retorno-config` — salva `enabled` e `api_key`; valida origem (Host/Origin) como toda mutação.
- Tabela `secure_configs`: guarda envelopes criptografados por usuário (`config_type = email | ai | mais_retorno`) em `payload_enc`; `source_path` registra a origem quando o payload veio de arquivo legado.
- Arquivos legados compatíveis: `data/email_config_user_{id}.enc`, `data/ai_config_user_{id}.enc`, `data/mais_retorno_config_user_{id}.enc` e `data/email_config.key`.
- Arquivo novo de chave mestra padrão: `secure/config.key`, fora de `data/`; servidores podem sobrepor com `SISTEMA_FINANCEIRO_CONFIG_KEY_PATH`.

## Critérios de aceite

1. Dado um usuário autenticado, quando abre **Usuário > Preferências**, então visualiza as abas **Geral**, **APIs** e **Perigo**, com a aba **Geral** ativa por padrão e seus painéis visíveis.
2. Dado o usuário na aba **Geral**, quando clica em **APIs** ou **Perigo**, então apenas o painel correspondente fica visível e a aba ativa muda de destaque, sem recarregar a página.
3. Dado o usuário na aba **Geral**, quando abre Preferências, então encontra Aparência, Alterar email, Alterar senha e Recuperação por email.
4. Dado o usuário na aba **APIs**, quando abre Preferências, então encontra a Configuração de IA e a Configuração Mais Retorno.
5. Dado o usuário na aba **Perigo**, quando abre Preferências, então encontra apenas **Apagar lançamentos** e **Apagar conta**, com confirmação e senha atual obrigatórias.
6. Dado um usuário sem integração configurada, quando consulta `GET /api/mais-retorno-config`, então recebe `configured = false`, `enabled = false` e `has_api_key = false`.
7. Dado um usuário salvando a integração com `enabled = true` e sem chave (nova ou armazenada), então recebe erro amigável e o estado anterior permanece inalterado.
8. Dado um usuário salvando a integração com chave nova, quando consulta o status, então a chave nunca aparece na resposta e o conteúdo de `secure_configs.payload_enc` não contém a chave em texto puro.
9. Dado um usuário com a integração ativada e uma posição de fundo com CNPJ em BRL, quando o Portfólio é carregado, então a posição exibe valor atual calculado pela última cota da API, com fonte e data da cota.
10. Dado um usuário com a integração desativada (ou posição de fundo sem CNPJ), quando o Portfólio é carregado, então a posição de fundo mantém valor de custo com status `Cotacao manual pendente`, sem nenhuma chamada à API Mais Retorno.
11. Dado um usuário com a integração ativada e a API indisponível, quando o Portfólio é carregado, então a posição de fundo mantém valor de custo com status amigável de falha e o restante do portfólio continua funcionando.
12. Dado um usuário com a integração ativada, quando uma posição de fundo é em carteira não-BRL ou é de outro tipo de ativo, então a integração não é usada e o comportamento anterior é preservado.
13. Dado um usuário desabilitando a integração que já tinha chave salva, quando salva, então `enabled = false` mas a chave permanece armazenada criptografada (reativação não exige nova chave).
14. Dado uma instalação anterior com arquivos `.enc` e `data/email_config.key`, quando o usuário consulta ou salva SMTP, IA ou Mais Retorno após atualizar o app, então a configuração continua legível, o payload é copiado para `secure_configs` e a chave mestra é copiada para `secure/config.key`.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Plano de implementação

- [x] Passo 1 — Criar esta spec e atualizar [[investimentos-portfolio]] com a regra de cotas de fundos. Fecha: critérios 1 a 13 (ancoragem).
- [x] Passo 2 — Registar ADR-0009 (integração opt-in com API paga). Fecha: ancoragem de decisão técnica.
- [x] Passo 3 — `financeiro/secure_config.py`: status/save/load criptografado da Mais Retorno. Fecha: critérios 6, 7, 8 e 13.
- [x] Passo 4 — `financeiro/portfolio.py`: `apply_fund_quote`, `fetch_mais_retorno_quote`, headers em `cached_json_url`/`read_json_url`, threading de `user_id` em `quote_positions`. Fecha: critérios 9, 10, 11 e 12.
- [x] Passo 5 — `app.py`: rotas `GET/PUT /api/mais-retorno-config` com handlers espelhando ai-settings. Fecha: critérios 6, 7 e 8.
- [x] Passo 6 — `web/index.html` + `web/styles.css`: abas Geral/APIs/Perigo e painel de configuração Mais Retorno. Fecha: critérios 1, 2, 3, 4 e 5.
- [x] Passo 7 — `web/app.js` + `web/modules/user-admin-view.js`: troca de abas e formulário Mais Retorno. Fecha: critérios 2, 4 e 6 a 8 (lado cliente).
- [x] Passo 8 — Testes automatizados: `tests/test_security.py` (config criptografada e rotas, critérios 6, 7, 8 e 13) e `tests/test_portfolio_fund_quotes.py` (cotação de fundos e fallbacks, critérios 9 a 12). Fecha: critérios 6 a 13. Critérios 1 a 5 verificáveis manualmente.
- [x] Passo 9 — Documentação: [[arquitetura]], [[requisitos]], MoC, [[instrucoes-app]] e atualização de status/versão/changelog das specs. Fecha: consistência documental.
- [x] Passo 10 — Migrar segredos de SMTP/IA/Mais Retorno para `secure_configs`, mantendo compatibilidade com arquivos `.enc` legados e chave mestra copiada para `secure/config.key`. Fecha: critérios 8, 13 e 14.

## Changelog

- `0.8` — 2026-08-09 — Segredos de SMTP, IA e Mais Retorno passam a ser persistidos como envelopes criptografados em `secure_configs`; arquivos `.enc` e `data/email_config.key` continuam compatíveis e são copiados/migrados no primeiro uso.
- `0.7` — 2026-08-09 — Tag de status sincronizada com o frontmatter, callout e MoC.
- `0.6` — 2026-08-08 — Cotas de fundos resilientes a fins de semana/feriados: data atual vazia dispara consulta retroativa de 7 dias usando a última cota publicada.
- `0.5` — 2026-08-08 — Ajustes na integração Mais Retorno: CNPJ enviado somente com dígitos + `:fi`, requisição sempre com `start_date`/`end_date` = data atual, cache diário (até o fim do dia) no lugar do TTL de 90 minutos e conversão do separador decimal `.` para centavos.

- `0.4` — 2026-08-08 — Passos 4, 8 parte 2 e 9 concluídos: testes de cotas de fundos validando os critérios 9 a 12 (headers `X-Api-Key`, cota mais recente, cache de 90 min, fallbacks de custo) e consolidação documental; spec promovida a **implementado**.
- `0.3` — 2026-08-08 — Implementados os Passos 3, 5, 6 e 7: rotas `GET/PUT /api/mais-retorno-config`, arquivo `.enc` por usuário e abas Geral/APIs/Perigo no frontend com formulário de configuração; testes de `tests/test_security.py` (critérios 6, 7, 8 e 13).
- `0.2` — 2026-08-08 — Adicionadas regras e critérios das cotas de fundos via Mais Retorno (posições `fund` com CNPJ em BRL, cache de 90 min, fallback de custo sem bloquear o Portfólio) e do armazenamento criptografado da chave por usuário.
- `0.1` — 2026-08-08 — Spec inicial: reorganização de Preferências em abas **Geral**, **APIs** e **Perigo**, movendo IA para a aba APIs e ações destrutivas para a aba Perigo.

## Relacionados

- [[investimentos-portfolio]]
- [[tendencias-saude-financeira]]
- [[recuperacao-senha]]
- [[seguranca-autenticacao]]
- [[arquitetura]]
- [[../adr/0010-segredos-criptografados-sqlite]]
