---
tipo: arquitetura
area: meta
status: implementado
versao: 1.1
atualizado: 2026-06-29
relacionados:
  - "[[requisitos]]"
  - "[[sdd]]"
  - "[[glossario]]"
  - "[[adr/0001-stack-local-sem-framework]]"
  - "[[adr/0002-modularizacao-frontend]]"
tags: [arquitetura, meta]
---

# Arquitetura

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-06-29 · relacionados: [[requisitos]], [[adr/0001-stack-local-sem-framework]], [[adr/0002-modularizacao-frontend]]

## Visão geral

O Sistema Financeiro é um app local composto por servidor HTTP em Python, banco SQLite e interface web estática. Roda em macOS sem dependências externas para operação financeira básica.

```text
app.py              Servidor HTTP, roteamento da API e arquivos estáticos
financeiro/         Regras de domínio, persistência e integrações locais
web/                Interface do usuário em HTML, CSS e JavaScript
data/               Arquivos de runtime criados localmente (não versionados)
docs/               Requisitos, arquitetura, specs e referências
```

---

## Camadas

### Interface web (`web/`)

| Arquivo | Responsabilidade |
|---|---|
| `index.html` | Estrutura das telas. |
| `styles.css` | Aparência e responsividade conforme [[design/design-system]]. |
| `app.js` | Ponto de entrada, estado geral e orquestração dos módulos de tela. |
| `web/modules/` | Módulos ES nativos sem etapa de build. |

**Módulos utilitários já extraídos:**

| Módulo | Responsabilidade |
|---|---|
| `api.js` | Chamadas HTTP JSON e upload. |
| `date-utils.js` | Datas locais, meses e exibição de datas. |
| `money-utils.js` | Formatação e parsing numérico/monetário. |
| `dom-utils.js` | Helpers de formulário, mensagens, empty state e escaping. |
| `transaction-kind.js` | Predicados de tipo de lançamento. |
| `labels.js` | Labels de domínio usados pela interface. |
| `month-picker.js` | Popover reutilizável de seleção de mês. |

**Views funcionais já extraídas:**

| Módulo | Responsabilidade |
|---|---|
| `auth-view.js` | Login, cadastro, logout e recuperação de senha. |
| `user-admin-view.js` | Troca de email/senha, config. SMTP, limpeza e exclusão. |
| `classifications-view.js` | Categorias, subcategorias e tags. |
| `limits-view.js` | Limites de gastos e índice de consumo. |
| `reports-view.js` | Filtros, abas, agrupamentos e tabelas. |
| `imports-view.js` | Upload, download de modelo e resultado da importação. |
| `cockpit-view.js` | Resumo, saldos, planejamento, dívidas, portfólio e alertas. |
| `accounts-view.js` | Contas: cadastro, edição, arquivamento, restauração. |
| `cards-view.js` | Cartões: cadastro, faturas, pagamento, conciliação. |
| `portfolio-view.js` | Ativos: posições, histórico, resgate, encerramento. |
| `transactions-view.js` | Lançamentos: formulário, recorrência, parcelas, câmbio. |

> [!tip] Regra de fronteira
> A interface orquestra formulários, listas e navegação. **Regras financeiras, validações de propriedade e cálculo de saldo ficam no núcleo Python.** Ver [[adr/0002-modularizacao-frontend]].

### API local (`app.py`)

Responsabilidades:
- Servir o frontend estático.
- Expor endpoints JSON.
- Ler corpo JSON e uploads multipart.
- Controlar sessão por cookie.
- Exigir usuário autenticado nas rotas financeiras.
- Converter erros de domínio em respostas HTTP.

#### Rotas — Autenticação e Perfil

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/me` | Dados do usuário autenticado. |
| `POST` | `/api/register` | Cadastro de novo usuário. |
| `POST` | `/api/login` | Login com e-mail e senha. |
| `POST` | `/api/logout` | Encerra a sessão. |
| `POST` | `/api/password-reset/request` | Solicita código de recuperação. |
| `POST` | `/api/password-reset/confirm` | Confirma código e redefine senha. |
| `POST` | `/api/me/email` | Altera e-mail do usuário. |
| `POST` | `/api/me/password` | Altera senha do usuário. |
| `POST` | `/api/me/clear-launches` | Apaga todos os lançamentos do usuário. |
| `DELETE` | `/api/me` | Exclui conta do usuário autenticado. |
| `GET` | `/api/email-config` | Retorna status e remetente da configuração SMTP. |
| `POST` | `/api/email-config` | Salva configuração SMTP criptografada. |

#### Rotas — Contas-correntes → [[contas-correntes]]

| Método | Rota |
|---|---|
| `GET` | `/api/checking-accounts` |
| `GET` | `/api/checking-accounts?status=archived` |
| `POST` | `/api/checking-accounts` |
| `PUT` | `/api/checking-accounts/{id}` |
| `DELETE` | `/api/checking-accounts/{id}` |
| `POST` | `/api/checking-accounts/{id}/restore` |

#### Rotas — Lançamentos → [[lancamentos]]

| Método | Rota |
|---|---|
| `GET` | `/api/transactions` |
| `POST` | `/api/transactions` |
| `PUT` | `/api/transactions/{id}` |
| `DELETE` | `/api/transactions/{id}` |
| `PUT` | `/api/transactions/{id}/reconciliation` |
| `GET` | `/api/exchange-rate` |

#### Rotas — Cartões de Crédito → [[cartoes]]

| Método | Rota |
|---|---|
| `GET` | `/api/credit-cards` |
| `GET` | `/api/credit-cards?status=archived` |
| `POST` | `/api/credit-cards` |
| `PUT` | `/api/credit-cards/{id}` |
| `DELETE` | `/api/credit-cards/{id}` |
| `POST` | `/api/credit-cards/{id}/restore` |
| `GET` | `/api/credit-card-invoice` |
| `GET` | `/api/credit-card-transactions` |
| `POST` | `/api/credit-card-transactions` |
| `PUT` | `/api/credit-card-transactions/{id}` |
| `DELETE` | `/api/credit-card-transactions/{id}` |
| `PUT` | `/api/credit-card-transactions/{id}/invoice` |
| `PUT` | `/api/credit-card-transactions/{id}/reconciliation` |
| `GET` | `/api/credit-card-payments` |
| `POST` | `/api/credit-card-invoice/pay` |

#### Rotas — Categorias e Tags → [[categorias-tags-gestao]]

| Método | Rota |
|---|---|
| `GET/POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |
| `POST` | `/api/subcategories` |
| `PUT/DELETE` | `/api/subcategories/{id}` |
| `GET/POST` | `/api/tags` |
| `PUT/DELETE` | `/api/tags/{id}` |

#### Rotas — Limites de Gastos → [[limites-gastos]]

| Método | Rota |
|---|---|
| `GET` | `/api/spending-limits` |
| `POST` | `/api/spending-limits` |
| `PUT` | `/api/spending-limits/{id}` |
| `DELETE` | `/api/spending-limits/{id}` |

#### Rotas — Investimentos e Portfólio → [[investimentos-portfolio]]

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio` |
| `POST` | `/api/portfolio/positions` |
| `PUT` | `/api/portfolio/positions/{id}` |
| `DELETE` | `/api/portfolio/positions/{id}` |
| `POST` | `/api/portfolio/redeem` |
| `POST` | `/api/portfolio/close` |
| `POST` | `/api/portfolio/value` |

#### Rotas — Importação → [[importacao-organizze]]

| Método | Rota |
|---|---|
| `POST` | `/api/import/organizze-transactions` |
| `POST` | `/api/import/system-template` |
| `GET` | `/api/import/template` |

---

### Núcleo da aplicação (`financeiro/`)

| Módulo | Responsabilidade |
|---|---|
| `database.py` | Conexão SQLite, schema e migrações idempotentes. |
| `auth.py` | Usuários, hashes, sessões, recuperação de senha. Ver [[seguranca-autenticacao]], [[recuperacao-senha]]. |
| `accounts.py` | Contas-correntes, saldos e arquivamento. Ver [[contas-correntes]]. |
| `transactions.py` | Lançamentos, transferências, tags, câmbio, recorrência/parcelamento e conciliação. Ver [[lancamentos]]. |
| `categories.py` | Categorias, subcategorias, tags e bloqueios de exclusão. Ver [[categorias-tags-gestao]]. |
| `credit_cards.py` | Cartões, faturas mensais, transações e pagamentos. Ver [[cartoes]]. |
| `spending_limits.py` | Metas e orçamentos mensais. Ver [[limites-gastos]]. |
| `portfolio.py` | Consolidação de investimentos, precificação e impostos. Ver [[investimentos-portfolio]]. |
| `imports.py` | Leitura de exportações Organizze e planilhas modelo. Ver [[importacao-organizze]]. |
| `emailer.py` | Envio SMTP do código de recuperação de senha. Ver [[recuperacao-senha]]. |
| `secure_config.py` | Armazenamento criptografado da configuração SMTP local. Ver [[recuperacao-senha]]. |

---

## Persistência

Banco local em `data/finance.db`, criado automaticamente na inicialização. Arquivos de `data/` são runtime local e **não devem ser versionados**.

### Tabelas

| Tabela | Módulo responsável |
|---|---|
| `users` | `auth.py` |
| `sessions` | `auth.py` |
| `password_resets` | `auth.py` |
| `auth_attempts` | `auth.py` — Ver [[seguranca-autenticacao]]. |
| `checking_accounts` | `accounts.py` — Ver [[contas-correntes]]. |
| `credit_cards` | `credit_cards.py` — Ver [[cartoes]]. |
| `credit_card_transactions` | `credit_cards.py` — Ver [[cartoes]]. |
| `credit_card_payments` | `credit_cards.py` — Ver [[cartoes]]. |
| `categories` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `subcategories` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `tags` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `transactions` | `transactions.py` — Ver [[lancamentos]]. |
| `transaction_tags` | `transactions.py` — Ver [[lancamentos]]. |
| `credit_card_transaction_tags` | `credit_cards.py` — Ver [[cartoes]]. |
| `spending_limits` | `spending_limits.py` — Ver [[limites-gastos]]. |
| `investment_opening_positions` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_operations` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_redemptions` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_closed_positions` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_value_overrides` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `quote_cache` | `portfolio.py` — Ver [[investimentos-portfolio]]. |

### Índices principais

- `idx_transactions_user_date`
- `idx_transactions_account`
- `idx_subcategories_category`
- `idx_transaction_tags_tag`
- `idx_password_resets_token`
- `idx_spending_limits_category`
- `idx_spending_limits_subcategory`
- `idx_investment_operations_user`
- `idx_investment_opening_positions_user`
- `idx_credit_card_transactions_card_month`

---

## Fluxos principais

### Autenticação

1. Usuário registra ou autentica pela interface.
2. `app.py` chama `financeiro.auth`.
3. Senha validada contra hash PBKDF2.
4. Sessão criada em `sessions`.
5. API grava cookie `session` com `HttpOnly` e `SameSite=Lax`.

Ver [[seguranca-autenticacao]], [[recuperacao-senha]].

### Operação financeira (fluxo comum)

1. Interface chama uma rota `/api/*`.
2. `app.py` identifica o usuário pelo cookie.
3. Módulo de domínio valida os dados e a propriedade dos registros.
4. SQLite alterado dentro de uma conexão local.
5. API retorna JSON para a interface renderizar.

### Lançamentos e saldos

1. `transactions.py` valida tipo, data, valor, conta, categoria e tags.
2. Receita/despesa: saldo da conta de origem ajustado.
3. Transferência: origem e destino ajustados em sentidos opostos.
4. Exclusão: impacto financeiro revertido.

Ver [[lancamentos]].

### Cartões de Crédito e Fatura

1. Lançamentos em cartões são associados a um cartão e a uma fatura mensal (`AAAA-MM`).
2. A fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão.
3. Faturas acumulam despesas/receitas e exibem total atual, total conciliado e contador de não conciliados.
4. Lançamentos de fatura podem ser movidos para fatura anterior/posterior se a fatura destino estiver aberta.
5. Pagamento de fatura deduz saldo da conta-corrente, respeita moeda e conta preferencial.

Ver [[cartoes]].

### Portfólio de Investimentos

1. Carteira consolidada unindo posições iniciais e operações em contas de investimento.
2. Cotações de Renda Variável e Cripto buscadas de APIs externas (Yahoo Finance / CoinGecko) e cacheadas em `quote_cache`.
3. Rendimentos de Renda Fixa pós-fixados/híbridos indexados via SGS/BCB, com fallback local.
4. Valor líquido projetado aplicando tributação regressiva de IOF e IR baseada no tempo de aquisição.
5. Poupança tratada como ativo próprio com aniversários; Previdência Privada como `private_pension`.
6. Resgates usam FIFO; encerramentos movem posições para histórico.
7. Ativos em moeda estrangeira exibidos na moeda da carteira; conversão via lançamentos de câmbio.

Ver [[investimentos-portfolio]].

### Cockpit e Relatórios

1. `GET /api/cockpit` consolida lançamentos de conta pelo mês e lançamentos de cartão pela fatura (`invoice_month`).
2. Planejamento do mês considera receitas/despesas/investimentos recorrentes, incluindo recorrências de cartão.
3. Relatórios no frontend agrupam por categoria, subcategoria, conta, tag e fluxo diário.
4. Lançamentos de cartão entram em relatórios e limites pela competência da fatura.

Ver [[relatorios]], [[limites-gastos]].

### Importação de Arquivos

1. Parser Organizze (`.xls`/`.csv`) em `imports.py`.
2. Importação estruturada via modelos `.xlsx` do próprio sistema.

Ver [[importacao-organizze]].

### Configuração de E-mail

1. Usuário autenticado abre Preferências > Recuperação por e-mail.
2. `GET /api/email-config` retorna status e remetente configurado, sem expor senha de app.
3. `POST /api/email-config` salva a configuração criptografada em `data/email_config.enc`.
4. Presets: Gmail (`smtp.gmail.com:587`) e Outlook/Microsoft (`smtp.office365.com:587`), ambos com STARTTLS.
5. Configuração manual permite servidor SMTP, porta e uso de STARTTLS.

Ver [[recuperacao-senha]].

---

## Convenções

- Valores monetários persistidos em centavos.
- Datas de lançamento em ISO `YYYY-MM-DD`.
- Registros históricos preferem arquivamento quando houver impacto financeiro.
- Erros de domínio expõem mensagem amigável e status HTTP; sem detalhes internos.
- Novas tabelas e colunas devem ser criadas de forma idempotente.
- **Novas funcionalidades devem nascer em `docs/specs/` antes da implementação.** Ver [[sdd]].

---

## Decisões técnicas

Decisões não triviais estão documentadas como ADRs para preservar o raciocínio:

- [[adr/0001-stack-local-sem-framework]] — Sem framework web: servidor HTTP puro em Python para manter o app simples e portável.
- [[adr/0002-modularizacao-frontend]] — ES Modules nativos sem build step; fronteiras de responsabilidade entre views, utilitários e domínio Python.
- [[adr/0003-sqlite-fonte-de-verdade]] — SQLite local como fonte de verdade: offline-first, sem servidor de banco externo.
- [[adr/0004-importador-xls-sem-dependencia]] — Parser `.xls` implementado sem pacote externo para reduzir requisitos de instalação.
- [[adr/0005-smtp-criptografado-local]] — Configuração SMTP criptografada no próprio ambiente; pacotes distribuíveis nunca incluem credenciais.

## Changelog

- `1.1` — 2026-06-29 — Frontmatter, tabelas de rotas e módulos por área, wikilinks e referência para ADRs.
- `1.0` — versão original.

## Relacionados

- [[requisitos]]
- [[sdd]]
- [[glossario]]
- [[adr/0001-stack-local-sem-framework]]
- [[adr/0002-modularizacao-frontend]]
