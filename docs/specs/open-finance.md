---
tipo: spec
area: open-finance
status: rascunho
versao: 0.4
atualizado: 2026-08-23
relacionados:
  - "[[contas-correntes]]"
  - "[[importacao-dados]]"
  - "[[classificacao-assistida]]"
  - "[[seguranca-autenticacao]]"
  - "[[privacidade-valores]]"
  - "[[adr/0005-smtp-criptografado-local]]"
  - "[[requisitos]]"
  - "[[arquitetura]]"
tags: [spec, "area/open-finance", "status/rascunho"]
aliases: ["Open Finance", "Conector 200", "Meu Pluggy", "Pluggy"]
---

# Open Finance

> [!info] Status
> **rascunho** · área: `open-finance` · atualizado em 2026-08-23 · relacionados: [[contas-correntes]], [[importacao-dados]], [[classificacao-assistida]], [[privacidade-valores]], [[adr/0005-smtp-criptografado-local]]

## Problema

O usuário precisa conectar suas próprias contas bancárias via Open Finance, usando o Conector 200 da Pluggy (Meu Pluggy, uso pessoal gratuito), para que saldos e transações sejam sincronizados automaticamente, reduzindo o lançamento manual e a dependência de importação de extratos.

## Usuário

Usuário autenticado localmente que já possui uma conta pessoal no Meu Pluggy com um ou mais bancos conectados e deseja refletir esses dados no sistema, sem uso comercial.

## Jornada

1. O usuário acessa a área de Open Finance nas Preferências, um recurso opcional que ele decide ativar — assim como outros recursos opt-in do sistema.
2. Configura suas próprias credenciais de aplicação da Pluggy (`CLIENT_ID` e `CLIENT_SECRET`) obtidas no Dashboard pessoal dele.
3. Inicia uma nova conexão a partir das Preferências, ou a partir da criação de uma conta corrente marcando a opção "Conectar via Open Finance"; o sistema abre o widget do Pluggy Connect autenticado com um connect token gerado pelo backend.
4. O usuário seleciona o conector "MeuPluggy" e autoriza o acesso às contas já vinculadas no Meu Pluggy.
5. Ao concluir, o usuário associa manualmente cada conta retornada a uma conta corrente já existente no sistema (ou à conta recém-criada, se veio do fluxo de criação com a opção marcada). Não há vínculo ou criação automática de conta.
6. No cabeçalho superior, ao lado do botão de ocultar/mostrar valores (ver [[privacidade-valores]]), o usuário encontra um botão de sincronização do Open Finance. Ao acioná-lo, dispara manualmente a busca de saldo e transações novas para todas as suas conexões ativas — não há sincronização automática nem agendada.
7. As transações novas trazidas pela sincronização não são lançadas diretamente: ficam em uma tela de revisão, cada uma com uma categoria/subcategoria sugerida automaticamente (mesma lógica local de sugestão usada em [[classificacao-assistida]]). O usuário confirma ou ajusta a categoria de cada transação e aprova — individualmente ou em lote — antes que qualquer uma delas vire lançamento no sistema. Esse é o mesmo papel que a planilha modelo cumpre na importação de dados (ver [[importacao-dados]]): como a Pluggy não devolve o plano de contas do usuário, a categorização acontece nesta tela em vez de já vir pronta num arquivo.
8. Transações pendentes de revisão não aparecem no extrato da conta nem entram em relatórios ou no Score de Saúde Financeira até serem aprovadas. O usuário pode rejeitar uma transação pendente; ela não gera lançamento e não volta a aparecer em sincronizações futuras.
9. O usuário pode revisar as conexões ativas nas Preferências e desconectar uma conta quando quiser.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `client_id` | texto | Obrigatório para iniciar qualquer conexão. Credencial da aplicação Pluggy. |
| `client_secret` | texto | Obrigatório. Armazenado apenas de forma criptografada, nunca em texto puro. |
| `connection_id` | texto (UUID interno) | Identificador da conexão no sistema. |
| `item_id` | texto | Identificador do item retornado pela Pluggy ao concluir a conexão no widget. |
| `connector_nome` | texto | Nome da instituição/conector retornado pela Pluggy (ex.: `MeuPluggy`). |
| `checking_account_id` | inteiro (FK) | Conta corrente do sistema vinculada a esta conexão. |
| `status_conexao` | enum | `ativa`, `erro`, `desconectada`. |
| `ultima_sincronizacao` | data/hora ISO | Preenchida a cada sincronização bem-sucedida. |
| `moeda_origem` | enum | Moeda retornada pela Pluggy para a conta; deve corresponder ao enum de moeda já usado em [[contas-correntes]]. |
| `transacao_external_id` | texto | Identificador da transação na Pluggy, usado para deduplicação. |
| `vincular_open_finance` | booleano | Opcional, informado na criação de uma conta corrente. Não cria a conexão por si só — apenas leva o usuário ao fluxo de conexão logo após salvar a conta, com essa conta já pré-selecionada como destino. |
| `status_revisao` | enum | `pendente`, `aprovada`, `rejeitada`. Toda transação trazida pela sincronização nasce `pendente` e só existe como lançamento em `transactions` ao ser aprovada. |
| `categoria_sugerida_id` / `subcategoria_sugerida_id` | inteiro (FK, opcional) | Sugestão automática de categoria/subcategoria para a transação pendente, calculada com a mesma lógica local de [[classificacao-assistida]]. O usuário pode aceitar ou substituir antes de aprovar. |

## Regras

- O Open Finance é um recurso opcional por usuário: cada usuário decide se ativa o recurso e configura suas próprias credenciais da Pluggy (`client_id`/`client_secret`). Não existem credenciais globais da instalação.
- Uma conexão de Open Finance sempre pertence a um único usuário autenticado do sistema e a uma única conta corrente vinculada.
- O `client_secret` nunca é exposto ao frontend; apenas o connect token de curta duração (30 minutos) é enviado ao widget.
- O connect token é gerado sob demanda no backend e não é reutilizado entre conexões.
- A sincronização é sempre manual, acionada pelo botão dedicado no cabeçalho superior (ver Jornada). O sistema não faz sincronização agendada nem expõe endpoint para receber webhooks da Pluggy.
- Uma sincronização atualiza diretamente o saldo da conta corrente vinculada com o saldo retornado pela Pluggy. Transações novas **não** são gravadas diretamente em `transactions`: entram em staging com `status_revisao = pendente`, em centavos, seguindo a mesma convenção monetária do restante do sistema.
- Toda transação em staging recebe uma sugestão automática de categoria/subcategoria (mesma lógica local usada nas outras importações, ver [[classificacao-assistida]]). A sugestão é apenas um ponto de partida — o usuário pode aceitá-la ou trocá-la livremente antes de aprovar.
- Uma transação em staging só passa a existir como lançamento em `transactions` quando o usuário a aprova explicitamente, individualmente ou em lote. Aprovação em lote grava cada transação selecionada com a categoria confirmada para ela naquele momento (aceita ou ajustada), nunca com uma categoria genérica aplicada a todas.
- Rejeitar uma transação em staging não gera lançamento e marca `status_revisao = rejeitada`; ela não volta a ser reapresentada em sincronizações futuras.
- Transações já trazidas anteriormente para staging (mesmo `transacao_external_id`) não geram nova entrada em staging numa sincronização seguinte, independentemente do `status_revisao` atual (pendente, aprovada ou rejeitada).
- Uma conexão com erro de autenticação ou de comunicação com a API da Pluggy não deve travar a sincronização de outras conexões do mesmo usuário quando o botão de sincronização cobre várias conexões de uma vez.
- Desconectar uma conexão interrompe futuras sincronizações manuais dela, sem apagar o histórico de transações já importado.
- A reconexão de uma conta bancária já vinculada anteriormente deve atualizar a conexão existente em vez de criar uma conexão duplicada para a mesma conta corrente.
- A vinculação entre uma conta retornada pelo widget e uma conta corrente do sistema é sempre manual — nunca criada ou associada automaticamente pelo sistema.
- Ao criar uma conta corrente, o usuário pode marcar `vincular_open_finance`; isso apenas encaminha para o fluxo de conexão com a conta recém-criada pré-selecionada, sem pular a etapa de autorização no widget.

## Regras de segurança

- A rota de configuração de credenciais e todas as rotas de Open Finance exigem sessão autenticada.
- `client_id` e `client_secret` são armazenados criptografados por usuário em `secure_configs`, reaproveitando `financeiro/secure_config.py` e o mesmo padrão de credenciais sensíveis descrito em [[adr/0005-smtp-criptografado-local]]. Não é necessário novo ADR dedicado.
- A conta corrente vinculada a uma conexão precisa pertencer ao usuário autenticado.
- Uma conexão não pode ser sincronizada, editada ou desconectada por um usuário diferente do dono.
- Erros retornados pela API da Pluggy são traduzidos em mensagem amigável ao usuário, sem vazar payload, stack trace ou detalhes internos da chamada.
- Nenhuma credencial (`client_secret`, API key, connect token) é registrada em log.
- O diretório onde as credenciais criptografadas são persistidas segue a mesma regra de `data/` do restante do sistema: runtime local, não versionado, excluído de pacotes de distribuição.

## API e dados

| Método | Rota |
|---|---|
| `POST` | `/api/open-finance/credentials` — salva `client_id`/`client_secret` criptografados. |
| `POST` | `/api/open-finance/connect-token` — gera connect token de curta duração para o widget. |
| `GET` | `/api/open-finance/connections` — lista conexões do usuário autenticado. |
| `POST` | `/api/open-finance/connections` — registra uma conexão concluída no widget (`item_id`) e vincula manualmente a uma conta corrente existente. |
| `POST` | `/api/open-finance/sync` — botão do cabeçalho: dispara sincronização manual de saldo e transações de todas as conexões ativas do usuário autenticado; transações novas entram em staging como `pendente`. |
| `DELETE` | `/api/open-finance/connections/{id}` — desconecta e interrompe sincronizações futuras.
| `GET` | `/api/open-finance/staging` — lista as transações pendentes de revisão do usuário autenticado, já com categoria/subcategoria sugerida. |
| `POST` | `/api/open-finance/staging/{id}/aprovar` — grava a transação em `transactions` com a categoria confirmada (aceita ou ajustada) e marca `status_revisao = aprovada`. |
| `POST` | `/api/open-finance/staging/aprovar-lote` — aprova várias transações de staging de uma vez, cada uma com sua própria categoria confirmada. |
| `POST` | `/api/open-finance/staging/{id}/rejeitar` — marca `status_revisao = rejeitada`, sem gerar lançamento. |
| `POST` | `/api/checking-accounts` — ganha parâmetro opcional `vincular_open_finance` (booleano); quando `true`, a resposta sinaliza ao frontend para encaminhar ao fluxo de conexão com a conta recém-criada pré-selecionada.

Tabelas novas (a criar de forma idempotente em `financeiro/database.py`): `open_finance_connections`, `open_finance_sync_log`, `open_finance_staged_transactions`.
Tabela afetada: `checking_accounts` (vínculo por `checking_account_id`; saldo atualizado direto pela sincronização), `transactions` (lançamentos criados somente após aprovação em staging).

## Critérios de aceite

- Dado credenciais válidas de `client_id`/`client_secret` configuradas, quando o usuário inicia uma conexão, então o backend gera um connect token válido sem expor o `client_secret` ao frontend.
- Dado um connect token expirado, quando o widget tenta usá-lo, então a conexão falha e o sistema orienta o usuário a solicitar um novo token.
- Dado uma conta conectada com sucesso pelo Conector 200 e vinculada a uma conta corrente, quando a sincronização roda, então o saldo dessa conta é atualizado e as transações novas aparecem em staging com `status_revisao = pendente`, sem gerar lançamento em `transactions`.
- Dado uma transação em staging, quando ela é exibida na tela de revisão, então o sistema apresenta uma categoria/subcategoria sugerida automaticamente, calculada pela mesma lógica local usada nas outras importações.
- Dado uma transação pendente, quando o usuário aprova mantendo ou ajustando a categoria sugerida, então um lançamento é criado em `transactions` com a categoria confirmada e `status_revisao` passa a `aprovada`.
- Dado múltiplas transações pendentes, quando o usuário aprova em lote, então todas as selecionadas são lançadas de uma vez, cada uma com a categoria confirmada individualmente para ela.
- Dado uma transação pendente, quando o usuário rejeita, então nenhum lançamento é criado, `status_revisao` passa a `rejeitada`, e essa transação não volta a aparecer em staging em sincronizações futuras.
- Dado uma transação já trazida anteriormente para staging (mesmo `transacao_external_id`), quando a sincronização roda novamente, então essa transação não gera nova entrada em staging, independentemente do `status_revisao` atual.
- Dado uma conexão pertencente a outro usuário, quando o usuário autenticado tenta sincronizá-la ou desconectá-la, então a operação é bloqueada.
- Dado uma falha de comunicação com a API da Pluggy durante a sincronização, quando ela ocorre, então o erro é registrado sem detalhes internos e o usuário recebe mensagem amigável, sem afetar outras conexões.
- Dado uma conexão desconectada pelo usuário, quando consultada, então ela não aparece mais entre as conexões ativas e não sofre novas sincronizações automáticas.
- Dado o usuário sem `client_id`/`client_secret` configurados, quando tenta iniciar uma conexão, então o sistema orienta a configuração das credenciais antes de prosseguir.
- Dado o botão de sincronização no cabeçalho, quando acionado, então dispara a sincronização de todas as conexões ativas do usuário sem exigir seleção individual, e sem que ocorra qualquer sincronização automática fora desse acionamento.
- Dado uma conta corrente criada com `vincular_open_finance` marcado, quando a criação é concluída, então o sistema encaminha o usuário ao fluxo de conexão com essa conta já pré-selecionada como destino, sem pular a etapa de autorização no widget.
- Dado duas contas retornadas pelo widget na mesma sessão de conexão, quando o usuário vincula cada uma manualmente a uma conta corrente diferente, então nenhuma vinculação é criada automaticamente para a conta que ainda não foi associada.

## Pendências

> [!question] Pendências

- [ ] Este documento contraria o item "Open Finance, sincronização em nuvem ou integrações bancárias automáticas diretas" listado em "Fora do escopo atual" em [[requisitos]]. Antes de qualquer implementação, `docs/requisitos.md` precisa ser atualizado para refletir a mudança de escopo (passo 2 do fluxo SDD em `AGENTS.md`).
- [ ] Definir regra de deduplicação entre transações sincronizadas via Open Finance e transações já lançadas manualmente ou importadas de arquivos externos no mesmo período. Ver [[importacao-dados]].
- [ ] Definir tratamento quando a moeda retornada pela Pluggy não corresponder a um dos valores do enum atual de moeda (`BRL`, `USD`, `EUR`, `GBP`) em [[contas-correntes]].
- [ ] Confirmar limites reais do Conector 200 (número de contas, requisições, throttling) e o comportamento esperado quando excedidos.
- [ ] O saldo da conta corrente é atualizado direto pela Pluggy a cada sincronização, mas os lançamentos só existem em `transactions` após aprovação em staging — definir como o sistema comunica ao usuário essa divergência temporária entre o saldo exibido e a soma dos lançamentos aprovados (ex.: aviso na tela da conta enquanto houver transações pendentes de revisão para ela).

## Fora de escopo

- Uso comercial da API da Pluggy (exige plano pago; este documento cobre apenas o Conector 200 de uso pessoal gratuito).
- Iniciação de pagamentos (Pix Automático, portabilidade de crédito) via Open Finance.
- Conexão de contas de terceiros — apenas contas nominais do próprio usuário, conforme regra do Conector 200.
- Enriquecimento de dados pago ou categorização automática via IA externa da Pluggy.
- Lançamento automático de transações sincronizadas sem revisão do usuário: toda transação trazida pela sincronização exige aprovação explícita antes de virar lançamento, mesmo quando a categoria sugerida está correta.

## Plano de implementação

- [ ] Passo 1 — Resolver as Pendências de escopo e arquitetura acima, incluindo atualização de `docs/requisitos.md`. Armazenamento de `client_id`/`client_secret` confirmado como extensão do ADR-0005 via `financeiro/secure_config.py`. Fecha: critérios 1, 12.
- [ ] Passo 2 — Migração idempotente em `financeiro/database.py` criando `open_finance_connections`, `open_finance_sync_log` e `open_finance_staged_transactions` (com `status_revisao`, categoria/subcategoria sugerida e `transacao_external_id` único por usuário/conexão). Fecha: critérios 3, 4, 5, 6, 7, 8, 9, 11.
- [ ] Passo 3 — Novo módulo `financeiro/open_finance.py` com autenticação na API da Pluggy, geração de connect token, sincronização de saldo e gravação de transações novas em staging (sem tocar em `transactions`) e desconexão. Fecha: critérios 1, 2, 3, 8, 10.
- [ ] Passo 4 — Sugestão automática de categoria/subcategoria para cada transação em staging, reaproveitando a mesma lógica local já usada em [[classificacao-assistida]]/importação. Fecha: critério 4.
- [ ] Passo 5 — Aprovação (individual e em lote) e rejeição de transações em staging, criando o lançamento em `transactions` somente na aprovação, com a categoria confirmada naquele momento. Fecha: critérios 5, 6, 7.
- [ ] Passo 6 — Rotas em `app.py` expondo os endpoints da tabela acima (conexão, sincronização, staging, aprovação, rejeição), validando sessão e propriedade da conexão/transação, incluindo o parâmetro `vincular_open_finance` em `POST /api/checking-accounts`. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 9, 11, 12, 13, 14.
- [ ] Passo 7 — View no frontend (`web/modules/`) para configurar credenciais por usuário, iniciar o widget, listar conexões, desconectar, o botão de sincronização manual no cabeçalho (ao lado do controle de [[privacidade-valores]]), a opção `vincular_open_finance` no formulário de criação de conta, e a tela de revisão/categorização/aprovação de transações pendentes. Fecha: critérios 1, 3, 4, 5, 6, 7, 11, 12, 13, 14.
- [ ] Passo 8 — Testes automatizados cobrindo os critérios acima, com mocks da API da Pluggy (sem chamadas reais em teste), incluindo sugestão de categoria, aprovação em lote e rejeição.

## Changelog

- `0.4` — 2026-08-23 — Pendência de armazenamento criptografado de `client_id`/`client_secret` resolvida: estende `financeiro/secure_config.py` e o ADR-0005, sem novo ADR dedicado.
- `0.3` — 2026-08-23 — Credenciais confirmadas como opt-in por usuário (mesmo padrão de IA/Mais Retorno). Introduzida a tela de revisão: transações novas da sincronização passam a entrar em staging (`status_revisao`) com categoria/subcategoria sugerida automaticamente (mesma lógica de [[classificacao-assistida]]), e só viram lançamento em `transactions` após aprovação explícita (individual ou em lote); rejeição não gera lançamento e não reaparece em sincronizações futuras. Saldo da conta segue atualizado direto pela sincronização, independente da aprovação das transações. Pendência de categorização resolvida e removida; nova pendência aberta sobre a divergência entre saldo sincronizado e soma dos lançamentos aprovados.
- `0.2` — 2026-08-06 — Credenciais definidas como opt-in por usuário; sincronização definida como manual via botão no cabeçalho (sem agendamento/webhook); vínculo de conta definido como sempre manual, com opção `vincular_open_finance` na criação de conta corrente. Pendências correspondentes resolvidas e removidas.
- `0.1` — 2026-08-06 — Rascunho inicial da spec de Open Finance via Conector 200 (Meu Pluggy).

## Relacionados

- [[contas-correntes]]
- [[importacao-dados]]
- [[classificacao-assistida]]
- [[seguranca-autenticacao]]
- [[adr/0005-smtp-criptografado-local]]
- [[requisitos]]
- [[arquitetura]]
