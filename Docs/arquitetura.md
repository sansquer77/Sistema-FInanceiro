# Arquitetura

## Visão geral

O Sistema Financeiro é um app local com servidor HTTP em Python, banco SQLite e interface web estática.

```text
web/                 Interface do usuário
app.py               Servidor HTTP, rotas e arquivos estáticos
financeiro/          Regras de negócio e persistência
data/finance.db      Banco SQLite criado em runtime
Docs/                Especificações e arquitetura
```

## Camadas

### Interface

Arquivos em `web/`.

- `index.html`: estrutura das telas.
- `styles.css`: aparência e responsividade.
- `app.js`: estado de tela, chamadas de API e renderização.

A interface deve conter apenas lógica de apresentação e orquestração simples. Regras financeiras devem ficar no núcleo Python.

### API local

Arquivo principal: `app.py`.

Responsabilidades:

- Servir arquivos do front-end.
- Expor endpoints JSON.
- Controlar sessão por cookie.
- Traduzir erros de domínio para respostas HTTP.

### Núcleo

Pacote `financeiro/`.

- `auth.py`: usuários, senhas e sessões.
- `accounts.py`: regras de contas-correntes.
- `database.py`: conexão SQLite e schema.

Novos módulos devem seguir o mesmo padrão: um arquivo de domínio para regras e funções pequenas chamadas pela API.

## Fluxo de dados atual

1. Usuário acessa a interface local.
2. `web/app.js` chama a API com `fetch`.
3. `app.py` valida sessão e encaminha para o módulo de domínio.
4. O módulo consulta ou altera o SQLite.
5. A API retorna JSON.
6. A interface renderiza o estado atualizado.

## Convenções

- Valores monetários são persistidos em centavos.
- Valores exibidos usam formatação `pt-BR`.
- Registros arquivados usam `archived_at` em vez de exclusão física.
- O banco local fica em `data/finance.db`.
- A interface não deve duplicar o mesmo saldo em mais de uma área da mesma tela.

## Evolução sugerida

Cada novo módulo deve nascer com:

- Uma especificação em `Docs/specs/`.
- Endpoints definidos antes da implementação.
- Modelo de dados descrito antes da migração.
- Critérios de aceite verificáveis manualmente ou por teste.
