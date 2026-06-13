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
- `app.js`: estado da interface, chamadas `fetch` e renderizacao.

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

- `GET /api/me`
- `POST /api/register`
- `POST /api/login`
- `POST /api/logout`
- `POST /api/password-reset/request`
- `POST /api/password-reset/confirm`
- `POST /api/me/email`
- `POST /api/me/password`
- `DELETE /api/me`
- `GET /api/checking-accounts`
- `GET /api/checking-accounts?status=archived`
- `POST /api/checking-accounts`
- `PUT /api/checking-accounts/{id}`
- `DELETE /api/checking-accounts/{id}`
- `POST /api/checking-accounts/{id}/restore`
- `GET /api/transactions`
- `POST /api/transactions`
- `DELETE /api/transactions/{id}`
- `POST /api/import/organizze-transactions`
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

### Nucleo da aplicacao

Pacote `financeiro/`.

- `database.py`: conexao SQLite, schema e migracoes idempotentes simples.
- `auth.py`: usuarios, hashes de senha, sessoes e recuperacao de senha.
- `accounts.py`: contas-correntes, saldos e arquivamento.
- `transactions.py`: lancamentos, transferencias, tags e impacto em saldo.
- `categories.py`: categorias, subcategorias, tags e bloqueios de exclusao.
- `imports.py`: leitura de exportacoes Organizze `.xls` e `.csv`.
- `emailer.py`: envio SMTP do codigo de recuperacao.
- `secure_config.py`: armazenamento criptografado da configuracao SMTP.

## Persistencia

O banco local fica em `data/finance.db` e e criado automaticamente na inicializacao. Arquivos de `data/` sao runtime local e nao devem ser versionados.

Tabelas atuais:

- `users`
- `sessions`
- `password_resets`
- `checking_accounts`
- `categories`
- `subcategories`
- `tags`
- `transactions`
- `transaction_tags`

Indices principais:

- `idx_transactions_user_date`
- `idx_transactions_account`
- `idx_subcategories_category`
- `idx_transaction_tags_tag`
- `idx_password_resets_token`

## Fluxos principais

### Autenticacao

1. O usuario registra ou autentica pela interface.
2. `app.py` chama `financeiro.auth`.
3. A senha e validada contra hash PBKDF2.
4. Uma sessao e criada em `sessions`.
5. A API grava cookie `session` com `HttpOnly` e `SameSite=Lax`.

### Operacao financeira

1. A interface chama uma rota `/api/*`.
2. `app.py` identifica o usuario pelo cookie.
3. O modulo de dominio valida os dados e a propriedade dos registros.
4. O SQLite e alterado dentro de uma conexao local.
5. A API retorna JSON para a interface renderizar.

### Lancamentos e saldos

1. `transactions.py` valida tipo, data, valor, conta, categoria e tags.
2. Para receita/despesa, o saldo da conta de origem e ajustado.
3. Para transferencia, origem e destino sao ajustados em sentidos opostos.
4. Ao excluir lancamento, o impacto financeiro e revertido.

### Importacao Organizze

1. A rota recebe arquivo multipart de ate 5 MB.
2. `imports.py` identifica `.xls` OLE/BIFF ou `.csv`.
3. Linhas sao normalizadas para o modelo de lancamentos.
4. Categorias, subcategorias e tags inexistentes sao criadas.
5. O retorno informa total lido, importado, ignorado e erros amostrados.

## Convencoes

- Valores monetarios sao persistidos em centavos.
- Datas de lancamento usam ISO `YYYY-MM-DD`.
- Registros historicos devem preferir arquivamento quando houver impacto financeiro.
- Erros de dominio expõem mensagem amigavel e status HTTP.
- Novas tabelas e colunas devem ser criadas de forma idempotente.
- Novas funcionalidades devem nascer em `docs/specs/` antes da implementacao.

## Decisoes atuais

- Sem framework web para manter o app simples e portavel.
- Sem dependencias de frontend ou etapa de build.
- SQLite como fonte de verdade local.
- Configuracao SMTP criptografada no proprio ambiente local.
- Importador `.xls` implementado sem pacote externo para reduzir requisitos de instalacao.
