# Referência: Segurança da Aplicação

Este documento define controles obrigatórios para o Sistema Financeiro. Como o app lida com dados financeiros, toda funcionalidade deve ser desenhada com segurança desde a spec.

## Objetivos

- Proteger dados financeiros de cada usuário.
- Evitar acesso indevido entre contas.
- Reduzir riscos de injeção, sessão roubada e autorização fraca.
- Garantir que cada rota valide autenticação, autorização e entrada.
- Manter uma base local segura mesmo em evolução rápida.

## Modelo de ameaça

Riscos principais:

- Usuário autenticado tentando acessar dados de outro usuário.
- Manipulação de IDs em URLs ou payloads.
- SQL Injection por filtros, buscas e ordenações.
- Sessão roubada ou reutilizada.
- Senhas fracas ou mal armazenadas.
- Falta de validação no servidor.
- Exposição de dados sensíveis em logs, erros ou arquivos.
- Ações destrutivas sem confirmação ou arquivamento.

## Regras obrigatórias

### Autenticação

- Senhas nunca devem ser armazenadas em texto puro.
- Usar hash de senha com algoritmo próprio para senha, como Argon2, bcrypt ou PBKDF2 com sal.
- Login deve retornar sessão opaca, não dados sensíveis.
- Cookie de sessão deve usar `HttpOnly`, `SameSite=Lax` ou mais restritivo.
- Em ambiente HTTPS, cookie deve usar `Secure`.
- Logout deve invalidar a sessão no servidor.
- Mensagens de erro de login não devem revelar se email existe.
- Login, pedido de recuperacao e confirmacao de token devem ter limite de tentativas persistente.

### Autorização

- Toda rota autenticada deve obter o usuário da sessão.
- Toda consulta por entidade deve filtrar por `user_id`.
- Operações de leitura, edição, arquivamento e exclusão devem validar posse do registro.
- IDs recebidos do cliente nunca provam autorização.
- Controle de autorização deve ficar no servidor, não no front-end.

### Proteção contra IDOR

IDOR ocorre quando o usuário altera um ID e acessa recurso de outra pessoa.

Padrão obrigatório:

```text
SELECT *
FROM resource
WHERE id = ? AND user_id = ? AND archived_at IS NULL
```

Nunca usar:

```text
SELECT *
FROM resource
WHERE id = ?
```

Critérios:

- Se o registro não pertence ao usuário, retornar 404 ou resposta equivalente.
- Não revelar que o ID existe para outro usuário.
- Testar tentativa de acesso cruzado em todo módulo novo.

### Proteção contra SQL Injection

- Todas as consultas devem ser parametrizadas.
- Nunca montar SQL com concatenação de valores do usuário.
- Ordenação dinâmica deve usar allowlist.
- Filtros dinâmicos devem ser compostos com parâmetros.
- Busca textual deve escapar caracteres conforme mecanismo usado.

Padrão seguro:

```python
conn.execute(
    "SELECT * FROM transactions WHERE user_id = ? AND description LIKE ?",
    (user_id, f"%{term}%"),
)
```

Ordenação segura:

```python
allowed_sorts = {"date": "date", "amount": "amount_cents"}
sort_column = allowed_sorts.get(requested_sort, "date")
```

### Validação de entrada

- Validar tipo, formato, tamanho e obrigatoriedade no servidor.
- Validar valores monetários com `Decimal`.
- Rejeitar moeda fora da allowlist.
- Rejeitar datas inválidas.
- Normalizar strings com `strip`.
- Limitar tamanho de textos livres.
- Não aceitar campos extras para alterar propriedades sensíveis.

### Sessões

- Token de sessão deve ser aleatório e de alta entropia.
- Sessão deve estar associada a um usuário existente.
- Sessões antigas devem poder ser invalidadas.
- Futuramente, considerar expiração por inatividade.
- Não registrar token de sessão em logs.

Decisao atual:

- A sessao usa token opaco armazenado no servidor em `sessions`; o cookie guarda apenas esse identificador.
- JWE nao e adotado nesta fase porque nao reduz IDOR, SQL Injection ou brute-force, e adicionaria gestao de chave/rotacao a um app local sem necessidade imediata.
- Caso o app deixe de ser local e passe a ser exposto em ambiente web multiusuario, reavaliar expiracao de sessao, rotacao de token, CSRF token e, se houver necessidade de claims cliente-side, tokens assinados ou JWE.

### CSRF

Mesmo em app local, cookies podem ser enviados automaticamente.

Controles recomendados:

- `SameSite=Lax` no cookie.
- Para ações sensíveis, usar token CSRF ou validar origem quando o app ganhar superfícies externas.
- Métodos `POST`, `PUT` e `DELETE` não devem aceitar execução por links simples.

### XSS

- Escapar toda saída dinâmica no front-end.
- Nunca inserir HTML vindo do usuário sem sanitização.
- Preferir `textContent` a `innerHTML`.
- Quando `innerHTML` for necessário, escapar campos interpolados.
- Observações, nomes, tags e categorias são dados não confiáveis.

### Dados sensíveis

- Não exibir senha, hash, token ou cookie.
- Não salvar credenciais de terceiros na documentação.
- Não registrar dados financeiros detalhados em logs de erro.
- Arquivos de banco local devem ficar em pasta controlada.
- Backups devem ser tratados como dados sensíveis.

## Segurança por módulo

### Contas

- Conta sempre pertence a um usuário.
- Atualização e arquivamento exigem `id` e `user_id`.
- Saldo não deve ser alterado diretamente quando houver lançamentos; deve vir de regras de domínio.

### Cartões

- Cartão sempre pertence a um usuário.
- Fatura pertence a cartão do usuário.
- Pagamento de fatura deve validar cartão, fatura e conta de pagamento do mesmo usuário.

### Categorias e Tags

- Categoria e tag pertencem a um usuário.
- Lançamento só pode usar categoria e tag do mesmo usuário.
- Categoria arquivada não deve ser usada em novo lançamento, salvo regra explícita.

### Lançamentos

- Conta, cartão, categoria e tags informados devem pertencer ao usuário.
- Transferência deve validar origem e destino do mesmo usuário.
- Parcelas e recorrências devem herdar o usuário do lançamento original.

### Relatórios

- Relatórios sempre filtram por `user_id`.
- Filtros por conta, cartão, categoria ou tag devem validar posse antes de consultar.
- Exportações devem respeitar os mesmos filtros de autorização.

## Checklist de rota segura

Para cada endpoint:

1. Exige sessão quando necessário.
2. Identifica `user_id` a partir da sessão.
3. Valida entrada.
4. Usa SQL parametrizado.
5. Filtra registros por `user_id`.
6. Não revela existência de registro de outro usuário.
7. Retorna erro seguro.
8. Não registra dados sensíveis.

## Checklist de revisão de segurança

- Existe risco de IDOR?
- Algum SQL foi montado com string do usuário?
- O front-end está confiando em regra que deveria estar no servidor?
- O usuário consegue alterar `user_id`, saldo, status ou dono pelo payload?
- Campos de texto são escapados antes de renderizar?
- O módulo novo tem teste de acesso cruzado?
- A ação destrutiva arquiva em vez de apagar quando existe histórico?

## Critério mínimo para produção local

Nenhum módulo deve ser considerado pronto se:

- Permite acessar registro de outro usuário.
- Usa SQL concatenado com entrada do usuário.
- Armazena senha sem hash forte.
- Confia apenas no front-end para bloquear ação.
- Exibe dados sensíveis em erro ou log.
