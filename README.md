# Sistema Financeiro Local

Protótipo inicial para validar a arquitetura local do sistema financeiro.

## O que este módulo entrega

- Login local com sessão por cookie.
- Cadastro do primeiro usuário.
- Cadastro, edição, listagem e arquivamento de contas-correntes.
- Banco SQLite local em `data/finance.db`.
- Interface web local sem dependências externas.

## Como rodar

### Abrindo pelo ícone

Dê dois cliques em:

```text
/Users/sansquer/Applications/Sistema Financeiro.app
```

O app inicia o servidor local em segundo plano e abre o sistema no navegador em:

```text
http://localhost:8000
```

Se o macOS bloquear a primeira abertura, use botão direito no app > `Abrir`.

Como plano B, também existe o lançador `Abrir Sistema Financeiro Executavel.command` nesta pasta.

### Abrindo pelo terminal

```bash
python3 app.py
```

Depois acesse:

```text
http://localhost:8000
```

Para reiniciar os testes do zero, pare o servidor e apague `data/finance.db`.

## Estrutura

```text
app.py                  Servidor HTTP e rotas da API
financeiro/             Núcleo da aplicação
  auth.py               Senhas, sessões e autenticação
  database.py           Conexão, schema e migrações simples
  accounts.py           Regras de contas-correntes
web/                    Interface local
  index.html
  styles.css
  app.js
data/                   Banco local criado em runtime
```
