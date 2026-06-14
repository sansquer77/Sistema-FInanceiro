# Sistema Financeiro Local

App financeiro local em Python, SQLite e interface web estática.

## O que este módulo entrega

- Cadastro, login, logout e sessão por cookie.
- Alteração de email, alteração de senha e exclusão da conta local.
- Recuperação de senha por email via SMTP configurado localmente.
- Cadastro, edição, listagem, arquivamento e restauração de contas-correntes.
- Categorias, subcategorias e tags.
- Lançamentos de receita, despesa e transferência com atualização de saldos.
- Importação de lançamentos do Organizze em `.xls` ou `.csv`.
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
http://sistema-financeiro.localhost:8010
```

Se o macOS bloquear a primeira abertura, use botão direito no app > `Abrir`.

Como plano B, também existe o lançador `Abrir Sistema Financeiro Executavel.command` nesta pasta.

### Abrindo pelo terminal

```bash
python3 app.py
```

Depois acesse:

```text
http://sistema-financeiro.localhost:8010
```

Se quiser usar outra porta temporariamente:

```bash
APP_PORT=8020 APP_URL=http://sistema-financeiro.localhost:8020 python3 app.py
```

Para reiniciar os testes do zero, pare o servidor e apague `data/finance.db`.

## Documentação

A documentação oficial fica em `docs/`:

- `docs/requisitos.md`: escopo funcional e regras.
- `docs/arquitetura.md`: camadas, rotas, dados e fluxos.
- `docs/specs/`: especificações por módulo.

## Configuração segura de email

As credenciais SMTP não ficam no código fonte. O app lê a configuração criptografada em:

```text
data/email_config.enc
```

A chave local usada para descriptografar fica em:

```text
data/email_config.key
```

Ambos são arquivos locais de runtime e estão ignorados pelo Git. Para trocar a conta ou senha de aplicativo, gere novamente a configuração chamando `financeiro.secure_config.save_encrypted_config(...)` em um ambiente local seguro.

## Estrutura

```text
app.py                  Servidor HTTP e rotas da API
financeiro/             Núcleo da aplicação
  auth.py               Senhas, sessões e autenticação
  database.py           Conexão, schema e migrações simples
  accounts.py           Regras de contas-correntes
  categories.py         Categorias, subcategorias e tags
  transactions.py       Lançamentos e saldos
  imports.py            Importação Organizze
web/                    Interface local
  index.html
  styles.css
  app.js
data/                   Arquivos locais criados em runtime
docs/                   Requisitos, arquitetura e specs
```
