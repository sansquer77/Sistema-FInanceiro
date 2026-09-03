---
tipo: spec
area: cockpit
status: em-implementacao
versao: 0.3
atualizado: 2026-09-03
relacionados:
  - "[[cockpit-calendario]]"
  - "[[limites-gastos]]"
  - "[[cartoes]]"
  - "[[lancamentos]]"
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
  - "[[requisitos]]"
tags: [spec, "area/cockpit", "status/em-implementacao"]
aliases: ["Alertas e Notificações do Cockpit", "Alertas Cockpit", "Central de Notificações do Cockpit"]
---

# Alertas e Notificações do Cockpit

> [!info] Status
> **em implementação** · versão: `0.3` · área: `cockpit` · atualizado em 2026-09-03 · relacionados: [[cockpit-calendario]], [[limites-gastos]], [[cartoes]], [[lancamentos]], [[investimentos-portfolio]], [[arquitetura]], [[requisitos]]

### Problema

Atualmente, o Cockpit exibe alertas empilhando múltiplas faixas e cards horizontais (como alertas de nova versão, limites excedidos e vencimentos de renda fixa) diretamente no topo do painel executivo. Esse empilhamento vertical consome espaço nobre da tela, aumenta a rolagem desnecessariamente e sobrecarrega a visualização do usuário, além de misturar avisos acionáveis urgentes com lembretes e informativos temporais. O usuário precisa de uma visão limpa do painel principal, com acesso rápido, contextualizado e não intrusivo a alertas críticos e informativos periódicos.

### Usuário

Usuário autenticado localmente que consulta o Cockpit para acompanhar o panorama mensal das suas finanças e deseja identificar imediatamente pendências críticas que exigem ação corretiva (ex.: estouro de limites, saldo negativo projetado, contas/faturas vencidas) ou novidades informativas da semana (ex.: dividendos creditados/previstos, vencimentos próximos) sem poluição visual.

### Jornada

1. O usuário acessa o **Cockpit** do sistema.
2. Na barra de ferramentas do Cockpit, ao lado das abas de navegação (**Situação**, **Consultor**, **Tendências**, **Saúde**), ele observa dois indicadores distintos com ícone, contador e cor semântica:
   - **Alertas Críticos** (ícone em tom vermelho quando houver itens pendentes);
   - **Informativos** (ícone em tom amarelo quando houver eventos ou novidades da semana).
   *(Em telas estreitas/mobile, os dois indicadores se consolidam em um único botão de notificações com seções internas separadas).*
3. Se não houver itens em uma categoria, o indicador correspondente exibe contador zero ou estado recolhido neutro sem destaque colorido.
4. Ao clicar em um dos indicadores, o sistema abre um painel flutuante (**flyout global**) renderizado no nível superior de sobreposições da aplicação, sem sofrer cortes de contêiner ou conflitos de empilhamento de camadas.
5. O usuário visualiza os itens agrupados por tipo, contendo título curto, explicação clara, competência/data de referência e uma ação contextual direta (ex.: “Ver limites”, “Abrir calendário”, “Ver eventos”, “Ver faturas”).
6. Para **Alertas Críticos**, o usuário clica na ação para ser direcionado à tela correspondente e corrigir o problema. O alerta permanece ativo no flyout até que a condição de negócio seja sanada (ex.: conciliação de conta, ajuste orçamentário).
7. Para **Informativos**, o usuário pode ler o evento da semana ou clicar em **"Marcar como vistos"** para remover o destaque do indicador, mantendo os eventos acessíveis na lista durante o período de vigência.
8. Ao clicar fora, no botão de fechar ou pressionar `Escape`, o flyout fecha suavemente, restaurando o foco acessível.
9. O banner de nova versão do aplicativo (`cockpitVersionAlert`) permanece visível de forma independente logo acima dos cards de resumo executivo com seu botão de dispensar, sem ser misturado à lista do flyout de notificações financeiras.

### Dados

#### Contrato da API (`GET /api/cockpit/notifications`)

```json
{
  "critical": [
    {
      "id": "limit_exceeded:12:2026-09",
      "type": "limit_exceeded",
      "category": "limits",
      "title": "Limite de Alimentação excedido",
      "description": "Gastos atingiram R$ 1.350,00 de R$ 1.200,00 planejados (112%).",
      "date_or_period": "2026-09",
      "action": {
        "label": "Ver limites",
        "route": "limits",
        "params": { "month": "2026-09" }
      }
    }
  ],
  "informational": [
    {
      "id": "dividend_week:ITUB4:2026-09-05",
      "type": "dividend_incoming",
      "category": "portfolio",
      "title": "Provento ITUB4 previsto",
      "description": "Pagamento de provento informado para 05/09/2026.",
      "date_or_period": "2026-09-05",
      "seen": false,
      "action": {
        "label": "Ver eventos",
        "route": "calendar",
        "params": {}
      }
    }
  ],
  "critical_count": 1,
  "informational_count": 1,
  "generated_at": "2026-09-03T12:00:00Z"
}
```

#### Estrutura de Notificação (`NotificationItem`)

| Campo | Tipo | Obrigatoriedade | Descrição |
|---|---|---|---|
| `id` | texto | Obrigatório | Identificador único estável do item (ex.: `type:entity_id:period`). |
| `type` | texto | Obrigatório | Código funcional do alerta (ex.: `limit_exceeded`, `projected_negative_balance`, `overdue_payable`, `overdue_invoice`, `dividend_incoming`, `maturity_upcoming`). |
| `category` | texto | Obrigatório | Grupo de agregação visual (ex.: `limits`, `cashflow`, `invoices`, `portfolio`, `system`). |
| `title` | texto | Obrigatório | Título conciso (até 45 caracteres). |
| `description` | texto | Obrigatório | Mensagem explicativa contextual (1 a 2 frases objetivas). |
| `date_or_period` | texto | Obrigatório | Data no formato ISO `AAAA-MM-DD` ou competência `AAAA-MM`. |
| `action` | objeto | Obrigatório | Metadados de redirecionamento: `label` (texto do botão), `route` (módulo de destino) e `params` (parâmetros contextuais opcionais). |
| `seen` | booleano | Opcional | Presente em informativos para indicar se já foi lido/visualizado pelo usuário. |

#### Contrato de Marcação de Vistos (`POST /api/cockpit/notifications/mark-seen`)

- Payload de entrada:
```json
{
  "notification_ids": ["dividend_week:ITUB4:2026-09-05"]
}
```
- Resposta de sucesso: HTTP 200 `{ "status": "ok", "marked_count": 1 }`.

#### Tabela SQLite: `notification_reads`

Persiste a marcação de visualização dos informativos por usuário no banco local.

| Coluna | Tipo SQLite | Restrição | Descrição |
|---|---|---|---|
| `user_id` | `INTEGER` | `NOT NULL`, FK `users(id) ON DELETE CASCADE` | Identificador do usuário. |
| `notification_id` | `TEXT` | `NOT NULL` | Identificador único da notificação informativa vista. |
| `seen_at` | `TEXT` | `NOT NULL` | Data/hora ISO em que o usuário marcou o item como visto. |

Restrição de unicidade: `PRIMARY KEY (user_id, notification_id)`.

### Regras

#### 1. Separação Estrita de Severidades e Cores Semânticas
- **Alertas Críticos (Vermelho)**:
  - Destinados exclusivamente a condições com impacto financeiro ou operacional que exigem ação do usuário:
    1. **Limites de gastos excedidos**: despesas do mês corrente ou selecionado que ultrapassaram o teto cadastrado para a categoria/subcategoria (ver [[limites-gastos]]).
    2. **Saldo negativo previsto**: projeção diária de caixa que entra em terreno negativo dentro do horizonte de liquidez (ver [[tendencias-saude-financeira]]).
    3. **Faturas ou contas vencidas**: faturas de cartão com vencimento anterior à data atual sem registro de pagamento integral/parcial (ver [[cartoes]]), ou despesas em contas com data anterior a hoje não conciliadas (ver [[cockpit-calendario]]).
    4. **Problemas que exigem ação corretiva explícita**: ex.: inconsistências críticas de conciliação.
  - **Restrição de criticidade**: A cor vermelha **nunca** deve ser utilizada para indisponibilidade temporária de APIs externas (ex.: cotações Yahoo/CoinGecko/PTAX offline), falhas passageiras de rede ou avisos meramente informativos.
- **Informativos (Amarelo)**:
  - Destinados a acontecimentos, novidades e eventos com vigência semanal/temporal sem necessidade de correção imediata:
    1. **Dividendos e proventos**: proventos de ativos do portfólio anunciados ou com pagamento previsto na semana corrente.
    2. **Vencimentos futuros**: investimentos de renda fixa com data de vencimento nos próximos dias da semana ou quinzena.
    3. **Alterações relevantes sem ação urgente**: eventos cadastrados no calendário para os próximos 7 dias.
  - O amarelo significa atenção e consciência situacional, **não** falha nem erro.

#### 2. Acessibilidade e Identificação Não Exclusiva por Cor
- Cor **não pode ser o único indicador** visual:
  - Todo botão indicador deve possuir ícone próprio perceptível (ex.: triângulo com exclamação para crítico; sino/círculo informativo para informativos).
  - Deve conter contador numérico em badge explícito.
  - Deve conter rótulo acessível textual via atributos `aria-label`, `aria-haspopup="dialog"`, `aria-expanded="false|true"`.
  - Leitores de tela devem receber o status semântico através de textos descritivos como "1 alerta crítico pendente" ou "Nenhum alerta crítico".

#### 3. Ciclo de Vida e Persistência de Leitura
- **Alertas Críticos**:
  - **Não desaparecem** quando o usuário abre o flyout ou clica no item.
  - Permanecem no estado ativo enquanto a condição no banco de dados persistir.
  - Somem automaticamente apenas quando a causa for solucionada (ex.: conta conciliada/quitada, limite ajustado, aporte realizado).
- **Informativos**:
  - Podem perder o destaque visual (badge numérico atenuado/zerado e cor vibrante desativada) após o usuário visualizá-los ou acionar a opção "Marcar como vistos".
  - Permanecem listados e consultáveis dentro do flyout durante todo o período de vigência definido (semana corrente).
  - O estado de visualização (`seen`) é persistido no SQLite na tabela dedicada `notification_reads(user_id, notification_id, seen_at)`. Ao montar a lista, o backend cruza os IDs com essa tabela para preencher `seen: true/false`.

#### 4. Flyout Global e Resolução de Camadas (Overlays)
- O flyout deve ser instanciado ou acoplado na camada de sobreposição global (`<body>` ou contêiner de overlays no topo do DOM), com `position: fixed` ou elemento `<dialog>` nativo.
- Deve evitar qualquer confinamento dentro de contêineres pais com `overflow: hidden`, `overflow-x: auto` ou contextos de empilhamento com `z-index` intermediário, prevenindo problemas históricos de z-index e corte já ocorridos no Portfólio.
- O flyout deve suportar fechamento por clique fora (backdrop dismiss), clique no botão de fechar (`×`) e tecla `Escape`, com restauração do foco no botão acionador.

#### 5. Conteúdo Interno do Flyout
- Cabeçalho claro identificando a aba ativa (Alertas Críticos ou Informativos).
- Itens agrupados por tipo/categoria funcional.
- Cada item exibe:
  - Título curto;
  - Texto explicativo;
  - Competência ou data formatada;
  - Ação contextual direta com navegação limpa (sem recarga completa de página).
- **Estado vazio explícito**:
  - Quando não houver alertas críticos: exibe mensagem positiva neutra (ex.: "Nenhum alerta crítico pendente. Suas contas e limites estão em dia.").
  - Quando não houver informativos: exibe mensagem informativa neutra (ex.: "Nenhum novo evento ou provento registrado para esta semana.").

#### 6. Responsividade e Adaptação para Telas Estreitas
- **Desktop e telas médias**: Dois indicadores independentes posicionados na barra de ferramentas do Cockpit, adjacentes às abas.
- **Telas estreitas / Mobile**:
  - Os dois indicadores se fundem em um único botão condensado de **Notificações** na barra de ferramentas.
  - O botão unificado exibe badge somado ou dois pontos de status (vermelho e amarelo).
  - Ao abrir o flyout, a interface apresenta as duas seções ("Alertas Críticos" e "Informativos") organizadas internamente (seja por abas internas no flyout ou por blocos verticais colapsáveis).

#### 7. Centralização de Regras no Backend e Endpoint Exclusivo
- Todas as regras financeiras (limites excedidos, contas atrasadas, parcelas a vencer, saldos projetados, proventos na semana) são calculadas exclusivamente no Python (`financeiro/cockpit.py` ou módulo auxiliar de notificações).
- O endpoint `GET /api/cockpit/notifications` é **exclusivo e desacoplado** da rota `GET /api/cockpit?month=...`, permitindo que revalidações periódicas das notificações ocorram sem o custo de recalcular o snapshot mensal completo do Cockpit.
- O frontend em `web/` é estritamente de apresentação: consome o payload JSON de `GET /api/cockpit/notifications`, renderiza badges/flyouts e executa a navegação de rota solicitada.

#### 8. Independência do Banner de Nova Versão
- O banner de nova versão do aplicativo (`cockpitVersionAlert`) permanece como um componente visual direto e independente no painel executivo do Cockpit com seu próprio botão de dispensar (`cockpitVersionAlertDismiss`).
- O banner de versão **não** é incorporado ao flyout de notificações, assegurando que os indicadores do flyout fiquem estritamente restritos a regras e eventos do domínio financeiro do usuário.

### API e dados

- **Rotas afetadas ou criadas**:
  - `GET /api/cockpit/notifications`: endpoint exclusivo autenticado que retorna listas de alertas críticos e informativos com contadores e data de geração.
  - `POST /api/cockpit/notifications/mark-seen`: marca identificadores de informativos como visualizados para o usuário autenticado, inserindo registros em `notification_reads`.
- **Tabelas / Persistência**:
  - Tabela `notification_reads(user_id, notification_id, seen_at)` criada de forma idempotente em `financeiro/database.py`, com chave primária composta `(user_id, notification_id)` e integridade referencial com `users(id)`.

### Critérios de aceite

- Dado que o usuário possui uma categoria cujo consumo do mês ultrapassou o limite estabelecido, quando ele carrega o Cockpit, então o indicador de Alertas Críticos exibe a cor vermelha com o contador correspondente e rótulo acessível informando a pendência.
- Dado que existem contas a pagar com data anterior à atual não conciliadas e faturas de cartão em atraso, quando o usuário clica no indicador de Alertas Críticos, então o flyout global abre no topo da viewport listando esses itens com título, data e botões de ação ("Ver limites" / "Ver extrato" / "Ver cartões").
- Dado que o usuário abriu e fechou o flyout de Alertas Críticos sem alterar suas contas ou limites, quando o Cockpit for reconsultado, então o indicador vermelho e a contagem permanecem ativos inalterados até a efetiva resolução no sistema.
- Dado que uma falha transitória de rede ou indisponibilidade externa de cotações de mercado ocorre, quando o backend monta as notificações, então nenhum alerta crítico vermelho é emitido por essa indisponibilidade temporária.
- Dado que há proventos previstos para a semana corrente na carteira do usuário, quando ele consulta o Cockpit, então o indicador de Informativos exibe a cor amarela e contador correspondente.
- Dado que o usuário visualiza a lista de Informativos no flyout e aciona a opção de marcar como vistos, quando o flyout é fechado, então o badge amarelo perde o destaque de novidade, mas os itens continuam acessíveis para consulta na listagem durante a semana.
- Dado que o usuário acessa o sistema a partir de uma viewport estreita (mobile), quando o Cockpit é renderizado, então os indicadores ao lado das abas se condensam em um botão único de Notificações, cujo clique abre o flyout preservando internamente as seções separadas de Críticos e Informativos.
- Dado que o flyout está aberto sobre o Cockpit e o usuário pressiona a tecla `Escape` ou clica fora da área do diálogo, quando o evento é disparado, então o flyout fecha imediatamente e o foco retorna ao botão que o acionou.
- Dado que não há nenhum limite excedido nem faturas/contas vencidas, quando o usuário abre a visualização de Alertas Críticos, então a interface apresenta um estado vazio explícito informando que não existem pendências.
- Dado um usuário não autenticado, quando uma requisição for enviada para `GET /api/cockpit/notifications`, então o servidor retorna status HTTP 401 Unauthorized e nenhum dado é exposto.
- Dado que o usuário marcou informativos como vistos, quando uma nova requisição a `GET /api/cockpit/notifications` é realizada (inclusive após novo login ou recarga da página), então os itens correspondentes retornam com `seen: true` e não contabilizam no `informational_count` não lido.
- Dado que há uma nova versão do sistema disponível, quando o usuário acessa o Cockpit, então o banner de nova versão (`cockpitVersionAlert`) continua sendo renderizado no topo do painel executivo com seu botão de dispensar, sem ser incorporado ao flyout de notificações financeiras.

### Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

### Fora de escopo

- Notificações push nativas do sistema operacional ou envio de alertas por SMS/WhatsApp.
- Sistema distribuído de mensageria em tempo real via WebSocket (o app opera em HTTP puro local conforme [[adr/0001-stack-local-sem-framework]]).
- Configuração personalizada de thresholds de tolerância além dos já existentes em Limites de Gastos.

### Plano de implementação

- [x] Passo 1 — Schema: criar a tabela `notification_reads` de forma idempotente em `financeiro/database.py` com `PRIMARY KEY (user_id, notification_id)`. Fecha: critério 11.
- [ ] Passo 2 — Backend: criar o motor de agregação de notificações em `financeiro/cockpit_notifications.py` (ou dentro de `financeiro/cockpit.py`), compilando limites excedidos, saldo negativo projetado, contas vencidas e eventos da semana, cruzando com `notification_reads`. Fecha: critérios 1, 3, 4, 5, 6, 11.
- [ ] Passo 3 — Backend: expor o endpoint exclusivo autenticado `GET /api/cockpit/notifications` e a rota `POST /api/cockpit/notifications/mark-seen` em `financeiro/http_routes.py`. Fecha: critérios 6, 10, 11.
- [ ] Passo 4 — Frontend: criar o componente de flyout global acessível e desacoplado de empilhamentos em `web/modules/notification-flyout.js` (ou utilitário de overlay), respeitando ARIA e tecla Escape. Fecha: critérios 2, 8, 9.
- [ ] Passo 5 — Frontend: integrar os botões de Alertas Críticos e Informativos na barra de abas do Cockpit (`web/modules/cockpit-view.js` e `web/index.html`), mantendo o banner de nova versão independente e suportando modo condensado responsivo. Fecha: critérios 1, 2, 5, 7, 12.
- [ ] Passo 6 — Frontend: implementar a navegação contextual das ações de cada card de notificação e o fluxo de marcar informativos como lidos. Fecha: critérios 2, 6.
- [ ] Passo 7 — Testes automatizados: criar testes unitários e de integração em `tests/test_cockpit_notifications.py` cobrindo cálculo de alertas, persistência na `notification_reads`, tolerância a falhas de cotação e controle de autenticação. Fecha: critérios 1, 3, 4, 10, 11, 12.

### Changelog

- `0.3` — 2026-09-03 — Passo 1 concluído: criada a tabela `notification_reads` de forma idempotente em `financeiro/database.py` com chave primária composta `(user_id, notification_id)`, cascata por usuário e testes unitários de integridade.
- `0.2` — 2026-09-03 — Resolvidas as pendências de arquitetura: persistência de leitura via tabela SQLite `notification_reads`, permanência do banner independente de nova versão no painel e rota exclusiva `GET /api/cockpit/notifications`.
- `0.1` — 2026-09-03 — Especificação inicial da reformulação dos alertas do Cockpit em dois indicadores (Alertas Críticos e Informativos) com flyout global desacoplado de empilhamentos, backend centralizado e suporte responsivo.

### Relacionados

- [[cockpit-calendario]]
- [[limites-gastos]]
- [[cartoes]]
- [[lancamentos]]
- [[investimentos-portfolio]]
- [[arquitetura]]
- [[requisitos]]
