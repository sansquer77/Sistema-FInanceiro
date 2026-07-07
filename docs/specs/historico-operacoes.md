---
tipo: spec
area: historico-operacoes
status: rascunho
versao: 0.1
atualizado: 2026-07-07
relacionados:
  - "[[sdd]]"
  - "[[templates/spec-template|Template de spec]]"
  - "[[arquitetura]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[importacao-organizze]]"
tags: [spec, "area/historico-operacoes", auditoria]
aliases: ["Histórico de Operações", "Historico de Operacoes", "Auditoria de Operações"]
---

# Histórico de Operações

> [!info] Status
> **rascunho** · área: `historico-operacoes` · atualizado em 2026-07-07 · relacionados: [[sdd]], [[templates/spec-template|Template de spec]], [[arquitetura]], [[lancamentos]], [[cartoes]], [[investimentos-portfolio]], [[importacao-organizze]]

## Problema

Com o aumento do volume de dados, o usuário precisa entender quais operações foram realizadas no sistema, quando ocorreram e quais entidades financeiras foram afetadas, sem depender apenas da memória ou da tela final de lançamentos, cartões e portfólio.

## Usuário

Usuário autenticado que administra seus dados financeiros e precisa auditar ações recentes ou antigas, localizar alterações, conferir importações, rastrear lançamentos parcelados/recorrentes e investigar inconsistências percebidas no saldo, fatura ou portfólio.

## Jornada

1. O usuário acessa o módulo **Histórico de Operações**.
2. O sistema mostra as operações mais recentes agrupadas por data.
3. O usuário filtra por módulo, tipo de operação, conta, cartão, período ou texto livre.
4. O usuário identifica uma operação individual ou um lote de operações relacionadas por `operation_batch_id`.
5. O usuário usa as telas existentes de contas, cartões, lançamentos ou portfólio para corrigir dados quando necessário.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `operation_logs.id` | inteiro | Identificador único do registro de operação. |
| `operation_logs.user_id` | inteiro | Usuário proprietário da operação. Obrigatório e usado em todos os filtros. |
| `operation_logs.operation_batch_id` | texto nullable | Identificador comum para operações em lote, como importações, recorrências e parcelamentos. |
| `operation_logs.module` | enum/texto | Módulo funcional: `accounts`, `transactions`, `cards`, `portfolio`, `imports`, `classifications`, `limits`, `user_admin`. |
| `operation_logs.operation_type` | enum/texto | Tipo de operação: `create`, `update`, `delete`, `archive`, `restore`, `reconcile`, `unreconcile`, `move`, `pay`, `import`, `redeem`, `close`, `value_update`, `clear`. |
| `operation_logs.entity_type` | enum/texto | Tipo da entidade afetada: `account`, `transaction`, `credit_card`, `credit_card_transaction`, `credit_card_payment`, `portfolio_position`, `portfolio_redemption`, `category`, `subcategory`, `tag`, `spending_limit`, `user`. |
| `operation_logs.entity_id` | texto nullable | Identificador da entidade principal afetada. Pode ficar nulo quando a ação for global ou em lote. |
| `operation_logs.account_id` | inteiro nullable | Conta relacionada, quando aplicável. |
| `operation_logs.credit_card_id` | inteiro nullable | Cartão relacionado, quando aplicável. |
| `operation_logs.description` | texto | Descrição curta, legível ao usuário. |
| `operation_logs.metadata_json` | JSON texto | Dados complementares mínimos para contexto e filtros. Não deve armazenar segredos. |
| `operation_logs.created_at` | timestamp | Data/hora da operação. |

## Regras

- O histórico é somente leitura para o usuário.
- O módulo não deve oferecer desfazer operação.
- Cada operação financeira relevante deve gerar pelo menos um registro em `operation_logs`.
- Operações em lote devem compartilhar o mesmo `operation_batch_id`.
- Importações devem registrar um lote único e permitir identificar os itens criados por aquela importação.
- Parcelamentos devem registrar um lote único para as parcelas criadas.
- Recorrências devem registrar um lote único para as ocorrências futuras criadas ou atualizadas em conjunto.
- Pagamento de fatura deve registrar a operação composta, relacionando cartão, fatura, conta de pagamento e transação criada.
- Operações de portfólio devem registrar cadastro, edição, resgate, encerramento e atualização de valor.
- O histórico deve respeitar isolamento por `user_id`; nenhum usuário pode listar operações de outro.
- O histórico não deve armazenar senha, token de sessão, token de recuperação, chave SMTP, conteúdo bruto de arquivo importado ou qualquer segredo.
- `metadata_json` deve conter apenas dados necessários para auditoria e exibição, como mês da fatura, descrição do lançamento, valor formatável, moeda, nome de conta/cartão no momento da operação e identificadores relacionados.
- A busca textual deve considerar `description`, `module`, `operation_type`, `entity_type` e campos relevantes de `metadata_json`.
- Filtros obrigatórios na interface: período, módulo, tipo, conta, cartão e texto livre.
- Agrupamentos obrigatórios na interface: data, módulo, tipo, conta e cartão.
- A listagem inicial deve trazer as operações mais recentes, com paginação ou limite incremental para evitar carregar todo o histórico.
- O registro de log não deve impedir a operação principal se falhar por erro recuperável? Não. Para operações financeiras, falha ao registrar auditoria deve abortar a transação para evitar alteração sem rastro.
- Operações destrutivas administrativas, como limpeza de lançamentos e exclusão de usuário, devem registrar operação antes da efetivação quando possível e dentro da mesma transação quando tecnicamente viável.

## API e dados

### Rotas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/operation-logs` | Lista operações com filtros e paginação. |
| `GET` | `/api/operation-logs/{id}` | Detalha uma operação específica do usuário autenticado. |

Parâmetros previstos para `GET /api/operation-logs`:

| Parâmetro | Regra |
|---|---|
| `date_from` | Data inicial opcional no formato `AAAA-MM-DD`. |
| `date_to` | Data final opcional no formato `AAAA-MM-DD`. |
| `module` | Módulo opcional. |
| `operation_type` | Tipo de operação opcional. |
| `account_id` | Conta opcional. |
| `credit_card_id` | Cartão opcional. |
| `q` | Busca textual opcional. |
| `group_by` | `date`, `module`, `type`, `account`, `card` ou vazio para lista simples. |
| `limit` | Limite por página, com teto definido pelo backend. |
| `offset` | Deslocamento para paginação. |

### Tabela

Tabela nova:

```sql
CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_batch_id TEXT,
    module TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    account_id INTEGER REFERENCES checking_accounts(id) ON DELETE SET NULL,
    credit_card_id INTEGER REFERENCES credit_cards(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Índices recomendados:

```sql
CREATE INDEX IF NOT EXISTS idx_operation_logs_user_created
ON operation_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_module_created
ON operation_logs (user_id, module, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_type_created
ON operation_logs (user_id, operation_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_account_created
ON operation_logs (user_id, account_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_card_created
ON operation_logs (user_id, credit_card_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_batch
ON operation_logs (user_id, operation_batch_id);
```

### Frontend

Módulo sugerido:

| Arquivo | Responsabilidade |
|---|---|
| `web/modules/operation-history-view.js` | Filtros, busca, agrupamentos, paginação e renderização do histórico. |

O menu lateral deve incluir **Histórico** ou **Operações** com ícone compatível com auditoria, como `History` quando disponível no conjunto de ícones usado pelo app.

## Critérios de aceite

- Dado um lançamento de conta criado, quando o usuário abre o Histórico de Operações, então existe uma operação `transactions/create` relacionada à conta.
- Dado um lançamento de cartão criado, quando o usuário filtra pelo cartão, então a operação aparece vinculada ao `credit_card_id`.
- Dado uma compra parcelada, quando as parcelas são criadas, então as operações relacionadas compartilham o mesmo `operation_batch_id`.
- Dado uma recorrência criada ou atualizada em lote, quando o usuário busca pelo lote, então todas as ocorrências relacionadas podem ser identificadas.
- Dado uma importação de planilha, quando o usuário filtra por tipo `import`, então a operação mostra o lote e a quantidade de itens afetados.
- Dado um pagamento de fatura, quando o usuário abre o detalhe da operação, então vê cartão, mês da fatura, conta de pagamento e transação relacionada.
- Dado uma operação de portfólio, quando o usuário filtra pelo módulo `portfolio`, então cadastro, edição, resgate, encerramento e atualização de valor aparecem no histórico.
- Dado um usuário autenticado, quando chama `/api/operation-logs`, então recebe apenas operações do próprio `user_id`.
- Dado uma busca textual, quando o texto aparece na descrição, módulo, tipo, entidade ou metadados relevantes, então a operação é retornada.
- Dado um volume alto de histórico, quando a listagem inicial é aberta, então apenas a primeira página/limite é carregada.
- Dado uma operação financeira que falha ao registrar auditoria, quando executada, então a operação principal não é persistida sem log.

## Fora de escopo

- Desfazer operações.
- Editar ou excluir registros de histórico pela interface.
- Exportação do histórico.
- Logs técnicos de servidor, stack traces ou métricas de performance.
- Auditoria de leitura simples, como abrir uma tela ou consultar relatório.
- Armazenar payload completo de arquivos importados.

## Changelog

- `0.1` — 2026-07-07 — Spec inicial do Histórico de Operações, sem desfazer, com `operation_batch_id`, filtros, busca e agrupamentos.

## Relacionados

- [[sdd]]
- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[importacao-organizze]]
