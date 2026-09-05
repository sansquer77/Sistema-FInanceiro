---
tipo: spec
area: open-finance
status: rascunho
versao: 0.8
atualizado: 2026-09-05
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
> **rascunho** · área: `open-finance` · atualizado em 2026-09-05 · relacionados: [[contas-correntes]], [[importacao-dados]], [[classificacao-assistida]], [[privacidade-valores]], [[adr/0005-smtp-criptografado-local]]

## Problema

O usuário precisa conectar suas próprias contas bancárias via Open Finance para reduzir o lançamento manual sem perder a qualidade da classificação. O problema não é apenas transportar transações: descrições bancárias são inconsistentes, pouco informativas e variam entre instituições. Uma descrição como `Zig*anh Eventos Praca` não deve ser importada diretamente como se fosse uma informação compreensível nem gerar uma categoria automática sem revisão.

Atualmente não há uma API de Open Finance gratuita, simples de configurar e adequada para um usuário comum. O Conector 200 da Pluggy pode atender ao uso pessoal, mas exige configuração de credenciais e widget que aumentam a complexidade de onboarding. A escolha do provedor permanece em aberto; esta spec define o contrato de revisão e normalização independentemente do provedor.

O saldo da conta corrente continua soberano no app: o provedor não atualiza o saldo diretamente — apenas traz eventos que entram como lançamentos após revisão explícita.

## Usuário

Usuário autenticado localmente que deseja importar movimentos de suas próprias contas bancárias, revisar descrições e classificação e transformar os dados em lançamentos confiáveis, sem uso comercial.

## Jornada

1. O usuário acessa a área de Open Finance nas Preferências, um recurso opcional que ele decide ativar — assim como outros recursos opt-in do sistema.
2. Configura o provedor disponível, quando necessário. No cenário Pluggy/Conector 200, informa suas próprias credenciais (`CLIENT_ID` e `CLIENT_SECRET`) obtidas no dashboard pessoal.
3. Inicia uma nova conexão a partir das Preferências, ou a partir da criação de uma conta corrente marcando a opção "Conectar via Open Finance"; o sistema abre o widget do Pluggy Connect autenticado com um connect token gerado pelo backend.
4. O usuário seleciona o conector "MeuPluggy" e autoriza o acesso às contas já vinculadas no Meu Pluggy.
5. Ao concluir, o usuário associa manualmente cada conta retornada a uma conta corrente já existente no sistema (ou à conta recém-criada, se veio do fluxo de criação com a opção marcada). Não há vínculo ou criação automática de conta.
6. O processo de importação via Open Finance vive como uma **aba dentro do menu Gestão > Importações**, ao lado das outras formas de importação do sistema (ver [[importacao-dados]]).
7. Dentro dessa aba, o usuário seleciona a conta Pluggy de origem, a conta de destino no sistema e a data de início, depois aciona a busca manual — não há sincronização automática nem agendada.
8. O sistema busca os lançamentos a partir da data definida e grava os dados brutos e normalizados em uma tela de importação (staging/revisão), exibindo apenas itens ainda não analisados.
9. Para cada lançamento, o sistema preserva a descrição original do banco, apresenta uma descrição normalizada e sugere descrição do usuário, categoria/subcategoria e tags com a memória local de classificações. O usuário pode corrigir qualquer campo antes de confirmar.
10. O usuário analisa e marca **OK** (importar) ou **NOK** (não importar). O `transacao_external_id` e o status OK/NOK são persistidos para que o item não seja reapresentado em buscas futuras.
11. O botão **Importar** só é habilitado após todos os lançamentos exibidos terem sido marcados como OK ou NOK. Ao confirmar, os lançamentos OK são inseridos em `transactions` como lançamentos conciliados (`reconciled_at` preenchido) na conta de destino selecionada. Itens NOK não geram lançamento.
12. O saldo da conta corrente não é substituído pelo saldo do provedor; ele continua sendo calculado pelos lançamentos do app.
13. O usuário pode revisar as conexões ativas nas Preferências e desconectar uma conta quando quiser.

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
| `ultima_busca` | data/hora ISO | Preenchida a cada busca bem-sucedida de transações na Pluggy. |
| `moeda_origem` | enum | Moeda retornada pela Pluggy para a conta; deve corresponder ao enum de moeda já usado em [[contas-correntes]]. |
| `data_inicio` | data ISO | Data inicial definida pelo usuário para buscar lançamentos na Pluggy. |
| `conta_pluggy_id` | texto | Identificador da conta bancária na Pluggy escolhida como origem. |
| `conta_destino_id` | inteiro (FK) | Conta corrente do sistema selecionada como destino dos lançamentos importados. |
| `transacao_external_id` | texto | Identificador da transação na Pluggy, usado para deduplicação e para não reapresentar itens já analisados. |
| `raw_description` | texto | Descrição original recebida do banco/provedor, imutável para auditoria e nunca substituída pela descrição editada. |
| `normalized_description` | texto | Assinatura local preparada para comparação, removendo ruídos variáveis sem descartar a descrição original. |
| `user_description` | texto | Descrição clara escolhida pelo usuário, usada no lançamento definitivo quando preenchida. |
| `classification_source` | enum | `none`, `exact_local`, `suggested_local`, `manual`; indica como a classificação foi obtida. |
| `classification_confidence` | decimal | Confiança da sugestão local; não autoriza importação silenciosa quando estiver abaixo do limite definido. |
| `classification_confirmations` | inteiro | Número de confirmações do usuário que sustentam a regra de memória local. |
| `tag_ids` | relação | Uma ou mais tags de projeto/contexto confirmadas para o lançamento, como `Airbnb`, `Reforma 2026` ou `Imóvel Centro`. |
| `status_revisao` | enum | `pendente`, `ok`, `nok`. Todo lançamento trazido pela API nasce `pendente` e só é importado para `transactions` quando marcado `ok`. Itens `nok` são descartados, mas mantidos registrados para não reaparecerem. |
| `category_id` / `subcategory_id` | inteiro (FK, opcional) | Categoria/subcategoria sugerida automaticamente pela mesma lógica local de [[classificacao-assistida]]; o usuário pode ajustar antes de marcar OK/NOK. |
| `vincular_open_finance` | booleano | Opcional, informado na criação de uma conta corrente. Não cria a conexão por si só — apenas leva o usuário ao fluxo de conexão logo após salvar a conta, com essa conta já pré-selecionada como destino. |
| `reconciled_at` | timestamp | Preenchido automaticamente ao importar os lançamentos OK para `transactions`; o lançamento entra como conciliado. |

## Regras

- O Open Finance é um recurso opcional por usuário: cada usuário decide se ativa o recurso e configura suas próprias credenciais da Pluggy (`client_id`/`client_secret`). Não existem credenciais globais da instalação.
- Uma conexão de Open Finance sempre pertence a um único usuário autenticado do sistema e a uma única conta corrente vinculada.
- O `client_secret` nunca é exposto ao frontend; apenas o connect token de curta duração (30 minutos) é enviado ao widget.
- O connect token é gerado sob demanda no backend e não é reutilizado entre conexões.
- A importação é sempre manual, acionada dentro da aba Open Finance em **Gestão > Importações** (ver Jornada). O sistema não faz sincronização agendada nem expõe endpoint para receber webhooks da Pluggy.
- A importação **não** atualiza o saldo da conta corrente diretamente pela Pluggy. O saldo do app continua sendo calculado a partir dos lançamentos existentes, mantendo o app como fonte de verdade soberana.
- O usuário define a data de início e seleciona a conta Pluggy de origem e a conta de destino no sistema antes de buscar os lançamentos.
- Transações retornadas pela Pluggy são inseridas em uma tabela de staging (`open_finance_staged_transactions`), em centavos, seguindo a mesma convenção monetária do restante do sistema. Cada item nasce com `status_revisao = pendente`.
- Toda transação em staging recebe uma sugestão automática de categoria/subcategoria (mesma lógica local usada nas outras importações, ver [[classificacao-assistida]]). O usuário pode ajustar a classificação antes de marcar OK ou NOK.
- O staging preserva `raw_description` sem alteração e separa essa informação de `normalized_description` e `user_description`.
- A normalização remove apenas tokens variáveis conhecidos ou identificados por regra segura; ela nunca substitui nem descarta a descrição original.
- A memória de classificação é por usuário e pode considerar instituição, conta, tipo de evento e assinatura normalizada. Uma classificação confirmada em uma conta não deve ser aplicada cegamente em outra conta sem confiança suficiente.
- A memória local pode sugerir descrição, categoria, subcategoria e uma ou mais tags. A aplicação automática só é permitida após confirmações suficientes e correspondência inequívoca; casos ambíguos permanecem para revisão.
- Tags representam contexto, projeto ou finalidade transversal às categorias. O lançamento já suporta múltiplas tags; na entrada textual, elas podem ser separadas por `;`, `|`, vírgula ou quebra de linha e são persistidas na relação própria de tags do lançamento.
- Corrigir um item não altera silenciosamente lançamentos históricos já importados; o usuário deve escolher entre corrigir apenas o item ou atualizar a regra futura.
- O usuário marca cada lançamento em staging como `ok` (importar) ou `nok` (não importar). O botão **Importar** só é habilitado quando não houver mais itens `pendente` na tela.
- Ao confirmar a importação, todos os itens `ok` são inseridos em `transactions` na conta de destino selecionada, com `reconciled_at` preenchido. Itens `nok` não geram lançamento, mas permanecem registrados com seu `transacao_external_id` e status para não serem reapresentados.
- Transações já buscadas anteriormente (mesmo `transacao_external_id`) não reaparecem na tela de importação, independentemente de terem sido marcadas `ok` ou `nok`.
- Uma conexão com erro de autenticação ou de comunicação com a API da Pluggy não deve travar a busca/importação de outras contas Pluggy do mesmo usuário.
- Desconectar uma conexão interrompe futuras buscas manuais dela, sem apagar o histórico de transações já importado.
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
- A descrição bruta e os identificadores externos são dados financeiros importados; seu armazenamento deve respeitar o mesmo isolamento por usuário e a política de retenção do staging.
- O diretório onde as credenciais criptografadas são persistidas segue a mesma regra de `data/` do restante do sistema: runtime local, não versionado, excluído de pacotes de distribuição.

## API e dados

| Método | Rota |
|---|---|
| `POST` | `/api/open-finance/credentials` — salva `client_id`/`client_secret` criptografados. |
| `POST` | `/api/open-finance/connect-token` — gera connect token de curta duração para o widget. |
| `GET` | `/api/open-finance/connections` — lista conexões do usuário autenticado. |
| `POST` | `/api/open-finance/connections` — registra uma conexão concluída no widget (`item_id`) e vincula manualmente a uma conta corrente existente. |
| `POST` | `/api/open-finance/fetch` — busca transações na Pluggy a partir da data de início informada e insere os itens novos em `open_finance_staged_transactions` com `status_revisao = pendente`. |
| `GET` | `/api/open-finance/staging` — lista os lançamentos pendentes de revisão do usuário autenticado para a conta Pluggy/conta de destino selecionadas. |
| `POST` | `/api/open-finance/staging/{id}/ok` — marca o lançamento como `ok` (importar). |
| `POST` | `/api/open-finance/staging/{id}/nok` — marca o lançamento como `nok` (não importar). |
| `POST` | `/api/open-finance/import` — executa a importação: insere em `transactions` todos os itens `ok` da tela atual, com `reconciled_at` preenchido, e remove (ou marca como importados) os itens processados. |
| `DELETE` | `/api/open-finance/connections/{id}` — desconecta e interrompe buscas futuras.
| `POST` | `/api/checking-accounts` — ganha parâmetro opcional `vincular_open_finance` (booleano); quando `true`, a resposta sinaliza ao frontend para encaminhar ao fluxo de conexão com a conta recém-criada pré-selecionada.

Tabelas novas (a criar de forma idempotente em `financeiro/database.py`): `open_finance_connections`, `open_finance_sync_log`, `open_finance_staged_transactions`.
Tabela afetada: `checking_accounts` (vínculo por `checking_account_id`), `transactions` (lançamentos criados ao confirmar a importação, com `reconciled_at` preenchido).

## Critérios de aceite

- Dado credenciais válidas de `client_id`/`client_secret` configuradas, quando o usuário inicia uma conexão, então o backend gera um connect token válido sem expor o `client_secret` ao frontend.
- Dado um connect token expirado, quando o widget tenta usá-lo, então a conexão falha e o sistema orienta o usuário a solicitar um novo token.
- Dado uma conta conectada com sucesso pelo Conector 200, quando o usuário aciona a busca na aba Open Finance informando data de início, conta Pluggy e conta de destino, então as transações novas são inseridas em `open_finance_staged_transactions` com `status_revisao = pendente`, sem alterar o saldo soberano da conta.
- Dado uma transação em staging, quando exibida na tela de importação, então o sistema apresenta categoria/subcategoria sugerida automaticamente, calculada pela mesma lógica local usada nas outras importações.
- Dado um lançamento importado com descrição bancária inconsistente, quando ele entra no staging, então `raw_description` permanece preservada e a interface apresenta uma representação normalizada separada.
- Dado um lançamento que o usuário corrige manualmente, quando a correção é confirmada, então descrição, categoria, subcategoria e tags escolhidas ficam disponíveis para a revisão desse item sem alterar lançamentos históricos.
- Dado um padrão normalizado previamente confirmado pelo usuário, quando outro lançamento compatível é recebido, então o sistema apresenta a classificação como sugestão local com origem e confiança identificáveis.
- Dado um padrão ambíguo ou com confiança abaixo do limite, quando outro lançamento compatível é recebido, então o sistema não aplica a classificação silenciosamente e mantém o item em revisão.
- Dado um lançamento associado ao projeto Airbnb, quando o usuário confirma a importação, então a tag `Airbnb` é preservada independentemente da categoria ou subcategoria escolhida.
- Dado uma transação pendente, quando o usuário marca como OK, então seu `status_revisao` passa a `ok` e ela fica elegível para importação.
- Dado uma transação pendente, quando o usuário marca como NOK, então seu `status_revisao` passa a `nok` e ela não será importada, mas também não reaparecerá em buscas futuras.
- Dado uma tela de importação com ao menos um lançamento pendente, quando o usuário tenta acionar o botão Importar, então o botão permanece desabilitado até que todos os itens estejam marcados como OK ou NOK.
- Dado que todos os lançamentos exibidos foram marcados como OK ou NOK, quando o usuário confirma a importação, então os itens OK são inseridos em `transactions` como conciliados (`reconciled_at` preenchido) na conta de destino selecionada, e os itens NOK não geram lançamento.
- Dado uma transação já buscada anteriormente (mesmo `transacao_external_id`), quando uma nova busca é acionada, então ela não reaparece na tela de importação, independentemente de ter sido marcada OK ou NOK anteriormente.
- Dado uma conexão pertencente a outro usuário, quando o usuário autenticado tenta buscar transações ou desconectá-la, então a operação é bloqueada.
- Dado uma falha de comunicação com a API da Pluggy durante a busca, quando ela ocorre, então o erro é registrado sem detalhes internos e o usuário recebe mensagem amigável, sem afetar outras contas Pluggy do mesmo usuário.
- Dado uma conexão desconectada pelo usuário, quando consultada, então ela não aparece mais entre as conexões ativas e não sofre novas buscas automáticas.
- Dado o usuário sem `client_id`/`client_secret` configurados, quando tenta iniciar uma conexão, então o sistema orienta a configuração das credenciais antes de prosseguir.
- Dado o usuário na aba Open Finance em **Gestão > Importações**, quando seleciona conta Pluggy, conta de destino e data de início e aciona a busca, então o sistema traz os lançamentos a partir da data definida, sem ocorrer qualquer sincronização automática fora desse acionamento.
- Dado uma conta corrente criada com `vincular_open_finance` marcado, quando a criação é concluída, então o sistema encaminha o usuário ao fluxo de conexão com essa conta já pré-selecionada como destino, sem pular a etapa de autorização no widget.
- Dado duas contas retornadas pelo widget na mesma sessão de conexão, quando o usuário vincula cada uma manualmente a uma conta corrente diferente, então nenhuma vinculação é criada automaticamente para a conta que ainda não foi associada.

## Pendências

> [!question] Pendências

- [ ] Este documento contraria o item "Open Finance, sincronização em nuvem ou integrações bancárias automáticas diretas" listado em "Fora do escopo atual" em [[requisitos]]. Antes de qualquer implementação, `docs/requisitos.md` precisa ser atualizado para refletir a mudança de escopo (passo 2 do fluxo SDD em `AGENTS.md`).
- [ ] Definir regra de deduplicação entre transações sincronizadas via Open Finance e transações já lançadas manualmente ou importadas de arquivos externos no mesmo período. Ver [[importacao-dados]].
- [ ] Definir tratamento quando a moeda retornada pela Pluggy não corresponder a um dos valores do enum atual de moeda (`BRL`, `USD`, `EUR`, `GBP`) em [[contas-correntes]].
- [ ] Confirmar limites reais do Conector 200 (número de contas, requisições, throttling) e o comportamento esperado quando excedidos.
- [ ] Escolher o provedor inicial de Open Finance e validar se a complexidade de credenciais/widget é aceitável para um usuário padrão; Pluggy/Conector 200 permanece apenas como candidato.
- [ ] Definir o limite de confiança e o número de confirmações necessários para aplicação automática da memória de classificação.
- [ ] Definir como a tela de revisão do staging apresentará e editará múltiplas tags já suportadas pelo modelo atual, sem serializar tags em uma coluna textual.
- [ ] Definir a política de retenção e expurgo da descrição bruta e do payload do provedor após a importação ou rejeição.

## Fora de escopo

- Uso comercial da API da Pluggy (exige plano pago; este documento cobre apenas o Conector 200 de uso pessoal gratuito).
- Dependência obrigatória de um provedor pago ou de uma API que exija configuração incompatível com o usuário padrão; a implementação só avança após um caminho de onboarding simples ser confirmado.
- Iniciação de pagamentos (Pix Automático, portabilidade de crédito) via Open Finance.
- Conexão de contas de terceiros — apenas contas nominais do próprio usuário, conforme regra do Conector 200.
- Enriquecimento de dados pago ou categorização automática via IA externa da Pluggy.
- Lançamento automático sem rastreabilidade: toda transação importada via Open Finance deve carregar `transacao_external_id` para deduplicação e aparecer como conciliada no extrato.

## Plano de implementação

- [ ] Passo 1 — Resolver as Pendências de escopo e arquitetura acima, incluindo atualização de `docs/requisitos.md`. Armazenamento de `client_id`/`client_secret` confirmado como extensão do ADR-0005 via `financeiro/secure_config.py`. Fecha: critérios 1, 13.
- [ ] Passo 2 — Migração idempotente em `financeiro/database.py` criando `open_finance_connections`, `open_finance_sync_log` e `open_finance_staged_transactions` (com `status_revisao`, `transacao_external_id` único por usuário/conexão, sugestão de categoria/subcategoria e referência à conta de destino). Fecha: critérios 3, 4, 5, 6, 7, 8, 9.
- [ ] Passo 3 — Novo módulo `financeiro/open_finance.py` com autenticação na API da Pluggy, geração de connect token, busca de transações novas (`/api/open-finance/fetch`) e desconexão. Fecha: critérios 1, 2, 3, 11.
- [ ] Passo 4 — Sugestão automática de categoria/subcategoria para cada transação em staging, reaproveitando a mesma lógica local já usada em [[classificacao-assistida]]/importação. Fecha: critério 4.
- [ ] Passo 4A — Definir o contrato de staging para descrição bruta, descrição normalizada, descrição do usuário, origem/confiança da classificação e memória local por usuário. Fecha: critérios 4, 17, 18 e 19.
- [ ] Passo 4B — Reutilizar a relação existente de múltiplas tags na tela de staging e definir as regras de confirmação da memória local, incluindo ambiguidade, correção pontual e atualização futura. Fecha: critérios 18, 19 e 20.
- [ ] Passo 5 — Deduplicação por `transacao_external_id`, garantindo que transações já buscadas (OK ou NOK) não reapareçam em novas buscas. Fecha: critérios 6, 9.
- [ ] Passo 6 — Rotas em `app.py` expondo os endpoints da tabela acima (credenciais, connect token, conexões, fetch, staging OK/NOK, importar), validando sessão e propriedade da conexão, incluindo o parâmetro `vincular_open_finance` em `POST /api/checking-accounts`. Fecha: critérios 1, 2, 3, 5, 6, 7, 8, 10, 12, 15, 16.
- [ ] Passo 7 — View no frontend (`web/modules/`) para configurar credenciais por usuário, iniciar o widget, listar conexões, desconectar, a aba Open Finance dentro de **Gestão > Importações** (seleção de conta Pluggy, conta de destino, data de início, busca manual, tela de staging/revisão OK/NOK e botão Importar), e a opção `vincular_open_finance` no formulário de criação de conta. Fecha: critérios 3, 4, 5, 6, 7, 8, 14, 15.
- [ ] Passo 8 — Testes automatizados cobrindo os critérios acima, com mocks da API da Pluggy (sem chamadas reais em teste), incluindo sugestão de categoria, marcação OK/NOK, habilitação do botão Importar e deduplicação.

## Changelog

- `0.8` — 2026-09-05 — Corrigida a spec para registrar que lançamentos já suportam múltiplas tags por relação própria, com entrada textual separada por `;`, `|`, vírgula ou quebra de linha; a decisão pendente passa a ser apenas a apresentação no staging.
- `0.7` — 2026-09-05 — Spec permanece em rascunho e passa a definir o staging como camada de preservação da descrição bancária, normalização, memória local de classificação e tags de projeto; registra a ausência atual de uma API gratuita e simples de Open Finance e mantém Pluggy como candidato não decidido.
- `0.6` — 2026-08-23 — Processo de importação Open Finance movido para uma aba dentro de **Gestão > Importações**; removida a ideia de botão no cabeçalho superior.
- `0.5` — 2026-08-23 — Modelo de sincronização ajustado: o saldo do app permanece soberano (não é atualizado direto pela Pluggy); transações importadas via Open Finance passam por uma tela de staging/revisão onde o usuário marca cada item como OK (importar) ou NOK (não importar) antes de inserir os OK em `transactions` como conciliados.
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
