# Arquitetura

## Visao geral

O Sistema Financeiro e um app local composto por servidor HTTP em Python, banco SQLite e interface web estatica.

```text
app.py             Servidor HTTP, roteamento da API e arquivos estaticos
financeiro/        Regras de dominio, persistencia e integracoes locais
web/               Interface do usuario em HTML, CSS e JavaScript
data/              Arquivos de runtime criados localmente
docs/              Requisitos, arquitetura, specs e referencias
```

## Camadas

### Interface web

Arquivos em `web/`.

- `index.html`: estrutura das telas.
- `styles.css`: aparencia e responsividade.
- `app.js`: ponto de entrada da interface, estado geral e orquestracao dos modulos de tela.
- `web/modules/`: modulos ES nativos sem etapa de build para API, utilitarios, formatacao, componentes pequenos e futuras views funcionais.

A interface deve orquestrar formularios, listas e navegacao. Regras financeiras, validacoes de propriedade e calculo de saldo ficam no nucleo Python.

### API local

Arquivo principal: `app.py`.

Responsabilidades:

- Servir o frontend estatico.
- Expor endpoints JSON.
- Ler corpo JSON e uploads multipart.
- Controlar sessao por cookie.
- Exigir usuario autenticado nas rotas financeiras.
- Converter erros de dominio em respostas HTTP.

Rotas atuais:

- **Autenticação e Perfil**:
  - `GET /api/me`
  - `POST /api/register`
  - `POST /api/login`
  - `POST /api/logout`
  - `POST /api/password-reset/request`
  - `POST /api/password-reset/confirm`
  - `POST /api/me/email`
  - `POST /api/me/password`
  - `POST /api/me/clear-launches`
  - `DELETE /api/me`
- **Contas-correntes**:
  - `GET /api/checking-accounts`
  - `GET /api/checking-accounts?status=archived`
  - `POST /api/checking-accounts`
  - `PUT /api/checking-accounts/{id}`
  - `DELETE /api/checking-accounts/{id}`
  - `POST /api/checking-accounts/{id}/restore`
- **Lançamentos / Transações**:
  - `GET /api/transactions`
  - `POST /api/transactions`
  - `PUT /api/transactions/{id}`
  - `DELETE /api/transactions/{id}`
  - `PUT /api/transactions/{id}/reconciliation`
  - `GET /api/exchange-rate`
- **Cartões de Crédito**:
  - `GET /api/credit-cards`
  - `GET /api/credit-cards?status=archived`
  - `POST /api/credit-cards`
  - `PUT /api/credit-cards/{id}`
  - `DELETE /api/credit-cards/{id}`
  - `POST /api/credit-cards/{id}/restore`
  - `GET /api/credit-card-invoice`
  - `GET /api/credit-card-transactions`
  - `POST /api/credit-card-transactions`
  - `PUT /api/credit-card-transactions/{id}`
  - `DELETE /api/credit-card-transactions/{id}`
  - `PUT /api/credit-card-transactions/{id}/invoice`
  - `PUT /api/credit-card-transactions/{id}/reconciliation`
  - `GET /api/credit-card-payments`
  - `POST /api/credit-card-invoice/pay`
- **Categorias e Tags**:
  - `GET /api/categories`
  - `POST /api/categories`
  - `PUT /api/categories/{id}`
  - `DELETE /api/categories/{id}`
  - `POST /api/subcategories`
  - `PUT /api/subcategories/{id}`
  - `DELETE /api/subcategories/{id}`
  - `GET /api/tags`
  - `POST /api/tags`
  - `PUT /api/tags/{id}`
  - `DELETE /api/tags/{id}`
- **Limites de Gastos**:
  - `GET /api/spending-limits`
  - `POST /api/spending-limits`
  - `PUT /api/spending-limits/{id}`
  - `DELETE /api/spending-limits/{id}`
- **Investimentos e Portfólio**:
  - `GET /api/portfolio`
  - `POST /api/portfolio/positions`
  - `PUT /api/portfolio/positions/{id}`
  - `DELETE /api/portfolio/positions/{id}`
  - `POST /api/portfolio/redeem`
  - `POST /api/portfolio/close`
  - `POST /api/portfolio/value`
- **Importação**:
  - `POST /api/import/organizze-transactions`
  - `POST /api/import/system-template`
  - `GET /api/import/template`

### Núcleo da aplicação

Pacote `financeiro/`.

- `database.py`: conexão SQLite, schema e migrações idempotentes simples.
- `auth.py`: usuários, hashes de senha, sessões e recuperação de senha.
- `accounts.py`: contas-correntes (suporte a moedas múltiplas e naturezas), saldos e arquivamento.
- `transactions.py`: lançamentos, transferências, tags, taxas de câmbio, séries recorrentes/parcelamentos e conciliação.
- `categories.py`: categorias, subcategorias, tags e bloqueios de exclusão.
- `credit_cards.py`: controle de cartões de crédito, faturas mensais, transações em faturas e fluxos de pagamentos.
- `spending_limits.py`: gestão de metas e orçamentos mensais por categoria/subcategoria.
- `portfolio.py`: consolidação de investimentos (ações, criptos, fundos, renda fixa, poupança), precificação integrada com Yahoo/CoinGecko, rendimento de renda fixa e poupança via SGS do Banco Central e aplicação de impostos regressivos (IOF/IR) quando aplicável.
- `imports.py`: leitura de exportações Organizze e planilhas modelo do próprio sistema.
- `emailer.py`: envio SMTP do código de recuperação de senha.
- `secure_config.py`: armazenamento criptografado da configuração SMTP local.

## Persistência

O banco local fica em `data/finance.db` e é criado automaticamente na inicialização. Arquivos de `data/` são runtime local e não devem ser versionados.

Tabelas atuais:

- `users`: cadastro de usuários locais.
- `sessions`: tokens de login ativos.
- `password_resets`: tokens para recuperação de senha.
- `checking_accounts`: contas-correntes manuais com moeda, saldo e natureza.
- `credit_cards`: cartões de crédito ativos ou arquivados e seus limites.
- `credit_card_transactions`: despesas e receitas feitas em faturas de cartões.
- `credit_card_payments`: histórico de pagamentos de faturas de cartão de crédito.
- `categories`: categorias financeiras (receita, despesa, investimento).
- `subcategories`: subcategorias dependentes de categorias principais.
- `tags`: marcadores transversais de lançamentos.
- `transactions`: lançamentos normais e de investimento, incluindo recorrências e parcelas.
- `investment_opening_positions`: posições históricas iniciais de investimentos cadastrados.
- `investment_operations`: operações de compras/vendas de investimentos detalhadas.
- `investment_redemptions`: resgates associados a posições/operações de investimento.
- `investment_closed_positions`: histórico de posições encerradas.
- `investment_value_overrides`: ajustes manuais de valor atual para posições sem cotação/indexador confiável.
- `quote_cache`: cache persistente de cotações e indicadores externos.
- `transaction_tags`: relação N:M entre transações e tags.
- `credit_card_transaction_tags`: relação N:M entre transações de cartão e tags.
- `spending_limits`: limites e metas de gastos definidos por mês/categoria/subcategoria.

Índices principais:

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

## Fluxos principais

### Autenticação

1. O usuário registra ou autentica pela interface.
2. `app.py` chama `financeiro.auth`.
3. A senha é validada contra hash PBKDF2.
4. Uma sessão é criada em `sessions`.
5. A API grava cookie `session` com `HttpOnly` e `SameSite=Lax`.

### Operação financeira

1. A interface chama uma rota `/api/*`.
2. `app.py` identifica o usuário pelo cookie.
3. O módulo de domínio valida os dados e a propriedade dos registros.
4. O SQLite é alterado dentro de uma conexão local.
5. A API retorna JSON para a interface renderizar.

### Lançamentos e saldos

1. `transactions.py` valida tipo, data, valor, conta, categoria e tags.
2. Para receita/despesa, o saldo da conta de origem é ajustado.
3. Para transferência, origem e destino são ajustados em sentidos opostos.
4. Ao excluir lançamento, o impacto financeiro é revertido.

### Cartões de Crédito e Fatura

1. Lançamentos em cartões são associados a um cartão específico e a uma fatura mensal (`AAAA-MM`).
2. A fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão. Compras após o fechamento entram na fatura posterior.
3. Faturas acumulam despesas e receitas, exibem total atual, total conciliado e contador de lançamentos não conciliados.
4. Lançamentos de fatura podem ser movidos para fatura anterior/posterior se a fatura de destino estiver aberta.
5. O pagamento de fatura deduz o saldo da conta-corrente do usuário, respeita moeda e conta preferencial de pagamento, e marca a fatura no banco de dados.

### Portfólio de Investimentos

1. A carteira é consolidada unindo posições iniciais e operações em contas de investimento.
2. Cotações para Renda Variável e Cripto ativos são buscadas de APIs externas (Yahoo Finance / CoinGecko) e cacheadas em memória e em `quote_cache`.
3. Rendimentos de Renda Fixa pós-fixados ou híbridos são indexados via APIs do Banco Central (SGS), com fallback local.
4. O valor líquido é projetado aplicando a tributação regressiva de IOF e IR baseada no tempo decorrido desde a aquisição quando aplicável.
5. Poupança é tratada como ativo próprio com aniversários; Previdência Privada é tratada como `private_pension`.
6. Resgates usam FIFO em múltiplas origens e encerramentos movem posições para histórico.
7. Valores de ativos em moeda estrangeira são mantidos e exibidos na moeda da carteira; conversão ocorre via lançamentos de câmbio.

### Cockpit e Relatórios

1. `GET /api/cockpit` consolida lançamentos de conta pelo mês e lançamentos de cartão pela fatura (`invoice_month`).
2. Planejamento do mês considera receitas recorrentes, investimentos planejados e despesas recorrentes, incluindo recorrências de cartão.
3. Relatórios no frontend agrupam por categoria, subcategoria, conta, tag e fluxo diário.
4. Lançamentos de cartão entram em relatórios e limites pela competência da fatura.

### Importação de Arquivos

1. Suporta o parser clássico do Organizze (.xls/.csv) em `imports.py`.
2. Suporta importação em massa estruturada via modelos em planilha do próprio sistema (.xlsx) para facilitar migrações.

## Convenções

- Valores monetários são persistidos em centavos.
- Datas de lançamento usam ISO `YYYY-MM-DD`.
- Registros históricos devem preferir arquivamento quando houver impacto financeiro.
- Erros de domínio expõem mensagem amigável e status HTTP.
- Novas tabelas e colunas devem ser criadas de forma idempotente.
- Novas funcionalidades devem nascer em `docs/specs/` antes da implementação.

## Decisões atuais

- Sem framework web para manter o app simples e portável.
- Sem dependências de frontend ou etapa de build.
- SQLite como fonte de verdade local.
- Configuração SMTP criptografada no próprio ambiente local.
- Importador `.xls` implementado sem pacote externo para reduzir requisitos de instalação.
- Integração de mercado leve em Python via chamadas de rede diretas a APIs públicas (Yahoo, CoinGecko, BCB).
