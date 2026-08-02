---
tipo: spec
area: tendencias-saude-financeira
status: em-implementacao
versao: 0.7
atualizado: 2026-08-02
relacionados:
  - "[[score-saude-financeira]]"
  - "[[relatorios]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[seguranca-autenticacao]]"
  - "[[../adr/0003-sqlite-fonte-de-verdade|ADR-0003]]"
  - "[[../adr/0005-smtp-criptografado-local|ADR-0005]]"
  - "[[../adr/0006-classificacao-assistida-local|ADR-0006]]"
tags: [spec, "area/tendencias-saude-financeira", "status/em-implementacao"]
aliases: ["Tendências de Saúde Financeira", "Achados Financeiros", "Insights Financeiros"]
---

# Tendências e Achados de Saúde Financeira

> [!info] Status
> **em-implementacao** · área: `tendencias-saude-financeira` · atualizado em 2026-08-02 · relacionados: [[score-saude-financeira]], [[relatorios]], [[lancamentos]], [[cartoes]]

## Problema

O Cockpit mostra a situação do mês e o Score de Saúde Financeira, mas o usuário ainda precisa interpretar manualmente quais receitas, despesas, categorias, limites e eventos pontuais explicam a mudança do período. Com poucos meses de histórico, como ocorre no início de uso do sistema, essa leitura precisa ser cuidadosa para não confundir tendência real com evento isolado.

## Usuário

Usuário autenticado que consulta o Cockpit e deseja entender, em linguagem simples, o que mudou nas receitas, despesas e orçamento realizado ao longo dos meses, com sugestões explicativas e não prescritivas.

## Jornada

1. O usuário acessa **Cockpit > Tendências**, em uma aba separada de **Situação do mês** e **Saúde Financeira**.
2. O sistema calcula sinais locais de tendência usando os lançamentos, cartões, limites, recorrências, categorias e histórico disponível.
3. O usuário visualiza um gráfico mês a mês comparando receitas, despesas e saldo do período.
4. Abaixo do gráfico, o usuário visualiza uma tabela **Budget x Realizado** baseada nos limites cadastrados, com leitura por categoria/subcategoria.
5. O usuário visualiza um bloco **Tendências e achados** com resumo textual curto e lista de pontos de atenção.
6. Quando o histórico for curto, o sistema informa a confiança reduzida da análise.
7. Quando houver eventos pontuais conhecidos, como férias, PLR, bônus ou antecipação de parcelas, o sistema explica que o mês pode estar distorcido por fatores não recorrentes.
8. Se o usuário tiver ativado IA nas Preferências, o sistema pode usar a IA apenas para redigir melhor o resumo, mantendo os cálculos e achados estruturados sob controle local.
9. Se a IA estiver desligada, indisponível ou sem chave válida, o sistema continua exibindo a análise local determinística.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Mês consultado pelo usuário. |
| `currency` | texto | Moeda analisada, respeitando a separação/normalização definida em [[relatorios]] e [[score-saude-financeira]]. |
| `historico_meses_disponiveis` | inteiro | Quantidade de meses com dados relevantes usados na comparação. |
| `confianca` | texto | `alta`, `intermediaria` ou `baixa`, conforme volume e qualidade do histórico. |
| `receitas_mes_cents` | inteiro | Total de receitas do mês em centavos. |
| `despesas_mes_cents` | inteiro | Total de despesas analíticas do mês em centavos, sem pagamentos de fatura duplicados. |
| `receitas_base_comparacao_cents` | inteiro | Média ou mês anterior usado para comparação. |
| `despesas_base_comparacao_cents` | inteiro | Média ou mês anterior usado para comparação. |
| `serie_mensal` | lista | Série de meses exibida no gráfico, com receitas, despesas e saldo em centavos por mês. |
| `orcamento_realizado` | lista | Linhas da tabela Budget x Realizado, reaproveitando limites vigentes e consumo real por categoria/subcategoria. |
| `achados` | lista | Sinais estruturados com tipo, severidade, título, descrição, valores em centavos e referência de comparação. |
| `eventos_pontuais` | lista | Eventos detectados que podem distorcer o mês, como PLR, bônus, férias e antecipação de parcelas. |
| `resumo_local` | texto | Texto determinístico gerado por templates locais. |
| `resumo_ia` | texto opcional | Texto reescrito por IA, quando ativado explicitamente e disponível. |
| `ia_ativa` | booleano | Indica se a preferência do usuário permite uso de IA para esta função. |
| `ia_fornecedor` | texto opcional | Fornecedor configurado: `openai`, `anthropic`, `google`, `custom` ou `local`. |

## Regras

- A análise de tendências não pontua no Score principal e não altera nenhum pilar de [[score-saude-financeira]].
- A análise de tendências deve aparecer em uma aba própria do Cockpit, separada de **Situação do mês** e **Saúde Financeira**, para evitar rolagem excessiva e preservar foco de leitura.
- A aba deve priorizar uma leitura visual mês a mês, com gráfico simples de receitas x despesas e indicação de saldo, respeitando as cores semânticas do design system.
- O gráfico mês a mês deve caber na área disponível sem aumentar a altura padrão do Cockpit; rótulos monetários devem se ajustar ou reduzir discretamente quando necessário, como nos demais gráficos do app.
- A tabela **Budget x Realizado** deve reaproveitar os limites de gastos vigentes do mês consultado, sem criar um novo cadastro de orçamento paralelo.
- A tabela **Budget x Realizado** deve mostrar, no mínimo, categoria/subcategoria, limite mensal vigente, valor realizado, diferença, percentual usado e estado textual como `Dentro do limite`, `Atenção` ou `Acima do limite`.
- Quando houver histórico suficiente, a tabela pode exibir colunas mês a mês para comparação visual do realizado por limite, preservando densidade e leitura em telas menores.
- Quando não houver limites cadastrados, a aba deve exibir estado vazio explicativo e orientar o usuário a cadastrar limites, sem impedir o uso do gráfico e dos achados.
- O MVP deve funcionar sem IA externa, internet, chave de API, modelo local ou dependência adicional.
- Os cálculos e achados estruturados devem ser feitos localmente no núcleo Python, usando centavos inteiros.
- A IA, quando ativada, pode apenas transformar achados estruturados em texto mais natural; ela não deve calcular valores financeiros, escolher categorias novas nem inferir dados ausentes.
- O botão de ligar/desligar IA deve ficar em **Preferências** e vir desligado por padrão.
- A configuração de IA deve oferecer um combo de provedor com as opções principais `OpenAI / ChatGPT`, `Anthropic / Claude`, `Google / Gemini` e `Custom / Local`.
- Quando o usuário selecionar um provedor principal, a interface deve exibir apenas os campos necessários para aquele fornecedor conhecido, preservando simplicidade.
- Quando o usuário selecionar `Custom / Local`, a interface deve abrir campos adicionais para configurar endpoint/base URL, modelo, formato de autenticação e contrato de payload compatível.
- Na primeira versão, `Custom / Local` deve exigir compatibilidade com o contrato **OpenAI Chat Completions** (`/v1/chat/completions`), por ser o formato mais comum entre servidores locais e gateways compatíveis, como Ollama, LM Studio, LocalAI, LiteLLM e proxies equivalentes.
- A configuração mínima de `Custom / Local` deve conter `base_url`, `model`, `auth_type` (`none` ou `bearer`), `api_key` opcional, `timeout_seconds` curto, `temperature` baixa e `max_tokens` limitado.
- A primeira versão de `Custom / Local` não deve usar streaming nem aceitar contratos arbitrários de payload; suporte a Responses API customizada, contrato próprio do app ou outros formatos fica para evolução futura.
- Chaves de API devem ser armazenadas criptografadas localmente por usuário, seguindo o mesmo princípio de [[../adr/0005-smtp-criptografado-local|ADR-0005]], nunca em texto puro no banco, frontend, logs ou pacote distribuível.
- A análise local deve usar timeout curto e fallback imediato quando a IA estiver indisponível.
- Nenhuma chamada de IA pode manter conexão SQLite aberta durante a requisição externa.
- O usuário deve conseguir desligar a IA sem perder a análise local.
- Quando a IA estiver ligada e corretamente configurada, a reescrita do resumo deve ser acionada automaticamente ao carregar o bloco **Tendências e achados**, sem exigir um botão adicional.
- A reescrita automática por IA deve preservar o fallback local: se a chamada falhar, expirar ou retornar conteúdo inválido, o usuário visualiza o resumo local determinístico.
- Textos enviados à IA devem ser minimizados: somente achados estruturados necessários, sem enviar histórico completo, senhas, tokens, caminhos locais ou dados de outros usuários.
- A interface deve informar claramente quando o texto foi gerado ou reescrito por IA.
- Com histórico inferior a 3 meses, a confiança da tendência deve ser `baixa` ou `intermediaria`, e o resumo deve evitar afirmar tendência permanente.
- Com histórico de 3 a 5 meses, a comparação pode usar média disponível recente, mas deve informar confiança intermediária.
- Com 6 meses ou mais, a comparação pode usar média móvel de 3 meses, 6 meses ou 12 meses, conforme o contexto do achado.
- O sistema deve identificar receitas pontuais conhecidas por descrição, categoria, tag ou recorrência ausente, incluindo férias, PLR, bônus, 13º salário, restituição e eventos similares.
- A primeira versão deve priorizar categorias e subcategorias existentes como sinal de evento pontual, usando palavras-chave de descrição ou tags apenas como reforço.
- Receitas classificadas em subcategorias como `Freelance e Autônomo` e `Outras Receitas` devem ser tratadas como candidatas a receita pontual quando não forem recorrentes.
- Despesas classificadas em `Viagens, Passagens e Hospedagens (Férias)` devem ser tratadas como candidatas a evento pontual de férias/viagem.
- Despesas classificadas em `Imprevistos e Emergências Domésticas` ou `Habitação › Manutenção, Reparos e Reformas` devem ser tratadas como candidatas a evento pontual de manutenção, reparo ou emergência doméstica.
- Descrições ou tags contendo termos como `PLR`, `bônus`, `bonus`, `férias`, `ferias`, `13º`, `décimo terceiro`, `decimo terceiro` e `restituição` podem reforçar a identificação do evento pontual, mas não devem ser a única base obrigatória.
- A primeira versão não deve exigir marcação manual de “evento pontual” pelo usuário, evitando complexidade no cadastro e preservando a experiência simples.
- Receitas recorrentes mensais devem ter peso maior para leitura de tendência do que receitas pontuais.
- O sistema deve identificar antecipações de parcelas em cartão quando houver lançamentos movidos para uma fatura específica, incluindo o padrão de histórico operacional `Lancamento movido para fatura yyyy-mm`.
- Antecipações de parcelas devem ser descritas como aumento pontual de despesa no mês atual que pode reduzir impacto de faturas futuras, sem classificar automaticamente como problema de consumo.
- Pagamentos de fatura em conta-corrente continuam excluídos das despesas analíticas para evitar duplicidade, conforme [[relatorios]].
- Lançamentos de cartão devem entrar pela competência da fatura (`invoice_month`) nas análises mensais, conforme [[relatorios]].
- Sugestões devem ser explicativas e não prescritivas, evitando tom de aconselhamento financeiro personalizado.
- Em moeda estrangeira ou cenário multi-moeda, a primeira versão deve evitar misturar moedas sem explicação; quando necessário, gerar achados por moeda ou usar os valores normalizados já definidos pelo Score.

## API e dados

Proposta para implementação futura:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/financial-health-trends?month=AAAA-MM` | Retorna série mensal, Budget x Realizado, achados estruturados, confiança, eventos pontuais e resumo local determinístico. |
| `GET` | `/api/ai-settings` | Retorna o estado configurado da integração de IA sem expor segredos. |
| `PUT` | `/api/ai-settings` | Atualiza fornecedor, endpoint, modelo, estado ligado/desligado e chave criptografada. |
| `POST` | `/api/financial-health-trends/ai-summary` | Reescreve achados estruturados com IA quando a configuração estiver ativa. |

Tabelas:

- `user_ai_settings`: configuração por usuário para provedor de IA, endpoint/base URL, modelo, estado ligado/desligado e metadados não secretos.
- `data/ai_config_user_{id}.enc`: arquivo local criptografado por usuário para armazenar o segredo de API, seguindo o padrão de chave local de [[../adr/0005-smtp-criptografado-local|ADR-0005]].
- Reuso das tabelas `transactions`, `credit_card_transactions`, `credit_card_payments`, `categories`, `subcategories`, `tags`, `operation_logs`, `checking_accounts` e `credit_cards`.

A tabela `user_ai_settings` é criada de forma idempotente no passo 2 para preparar as Preferências de IA. As rotas e a UI de configuração continuam previstas para os passos 4 e 5.

Decisão para a primeira implementação: usar rota separada (`GET /api/financial-health-trends?month=AAAA-MM`) para facilitar manutenção, isolamento de responsabilidades e evolução independente do Score. A visualização deve ser uma aba própria do Cockpit, chamada **Tendências**, e não um bloco interno da aba **Saúde Financeira**.

Contrato mínimo para `Custom / Local`:

```http
POST {base_url}/chat/completions
Authorization: Bearer {api_key}
Content-Type: application/json
```

Payload esperado:

```json
{
  "model": "modelo-configurado",
  "messages": [
    { "role": "system", "content": "instruções fixas do sistema" },
    { "role": "user", "content": "achados estruturados em JSON minimizado" }
  ],
  "temperature": 0.2,
  "max_tokens": 700
}
```

Resposta esperada:

```json
{
  "choices": [
    {
      "message": {
        "content": "resumo textual"
      }
    }
  ]
}
```

O app deve consumir somente `choices[0].message.content` e descartar qualquer tentativa da IA de alterar valores calculados localmente.

## Critérios de aceite

- Dado um usuário com IA desligada nas Preferências, quando consulta a aba **Tendências** no Cockpit, então o bloco **Tendências e achados** é gerado localmente e exibido sem chamada externa.
- Dado um usuário que acessa o Cockpit, quando visualiza as abas principais, então **Tendências** aparece como aba própria separada de **Situação do mês** e **Saúde Financeira**.
- Dado um usuário com lançamentos em mais de um mês, quando consulta a aba **Tendências**, então visualiza um gráfico mês a mês de receitas, despesas e saldo do período.
- Dado um usuário com limites cadastrados, quando consulta a aba **Tendências**, então visualiza uma tabela **Budget x Realizado** reaproveitando os limites vigentes e o consumo real por categoria/subcategoria.
- Dado um usuário sem limites cadastrados, quando consulta a aba **Tendências**, então visualiza estado vazio explicativo para Budget x Realizado sem bloquear o gráfico e os achados.
- Dado um usuário com apenas dois meses de histórico, quando consulta tendências, então a análise informa confiança baixa ou intermediária e evita afirmar uma tendência permanente.
- Dado um usuário com despesas do mês acima do mês anterior, quando existem categorias responsáveis pela maior variação, então o sistema lista as principais categorias/subcategorias com valores em centavos formatados pela interface.
- Dado um usuário com receitas pontuais identificáveis como PLR, bônus, férias, 13º ou restituição, quando a receita do mês aumenta, então o resumo informa que parte do aumento pode ser pontual.
- Dado um usuário com receita não recorrente em `Freelance e Autônomo` ou `Outras Receitas`, quando a análise de tendências é calculada, então essa receita é candidata a evento pontual e pode ser citada como fator de distorção do mês.
- Dado um usuário com despesa em `Viagens, Passagens e Hospedagens (Férias)`, quando a análise de tendências é calculada, então essa despesa é candidata a evento pontual de férias/viagem.
- Dado um usuário com despesa em `Imprevistos e Emergências Domésticas` ou `Habitação › Manutenção, Reparos e Reformas`, quando a análise de tendências é calculada, então essa despesa é candidata a evento pontual de manutenção, reparo ou emergência doméstica.
- Dado um usuário com receitas recorrentes mensais, quando a análise compara receitas, então a leitura diferencia receitas recorrentes de receitas pontuais.
- Dado um usuário com antecipações de parcelas em cartão registradas no histórico como `Lancamento movido para fatura yyyy-mm`, quando o mês consultado concentra esses lançamentos, então o resumo informa que o aumento de despesa pode estar ligado a antecipação e pode reduzir faturas futuras.
- Dado um usuário com pagamentos de fatura em conta-corrente, quando as despesas do mês são agregadas, então esses pagamentos não são somados como despesa analítica.
- Dado um usuário com lançamentos de cartão, quando a tendência mensal é calculada, então os valores entram pela competência da fatura (`invoice_month`).
- Dado um usuário em cenário multi-moeda, quando houver dados em mais de uma moeda, então o sistema não mistura moedas sem indicar a base usada.
- Dado um usuário que acessa Preferências de IA, quando abre o campo de provedor, então visualiza as opções principais `OpenAI / ChatGPT`, `Anthropic / Claude`, `Google / Gemini` e `Custom / Local`.
- Dado um usuário que seleciona `Custom / Local` como provedor de IA, quando a tela de configuração é exibida, então campos adicionais de endpoint/base URL, modelo, autenticação e contrato de payload ficam disponíveis.
- Dado um usuário que seleciona `Custom / Local`, quando configura a integração, então o endpoint deve ser tratado como compatível com OpenAI Chat Completions em `{base_url}/chat/completions`.
- Dado um usuário que seleciona `Custom / Local`, quando a reescrita por IA é executada, então o sistema envia payload não-streaming com `model`, `messages`, `temperature` e `max_tokens`, e lê apenas `choices[0].message.content`.
- Dado um usuário que ativa IA nas Preferências com chave válida, quando solicita resumo por IA, então a IA recebe apenas achados estruturados minimizados e retorna texto sem alterar os valores calculados localmente.
- Dado um usuário com IA ativa e configurada, quando abre a aba **Tendências**, então a reescrita por IA do bloco **Tendências e achados** é acionada automaticamente após o resumo local estar disponível.
- Dado um usuário que desativa IA nas Preferências, quando consulta a aba **Tendências** novamente, então nenhuma chamada externa é realizada e o resumo local permanece disponível.
- Dado uma falha de rede, timeout ou erro do fornecedor de IA, quando o usuário consulta tendências, então a tela exibe o resumo local e uma indicação discreta de que a IA não foi usada.
- Dado um usuário autenticado A, quando consulta tendências, então somente dados associados ao `user_id` de A são considerados.
- Dado uma requisição sem sessão válida, quando tenta consultar tendências ou preferências de IA, então o sistema retorna erro de autenticação sem expor dados.
- Dado uma tentativa de salvar chave de API, quando a configuração é persistida, então o segredo é armazenado criptografado e nunca retornado pela API.
- Dado o modo local/offline do app, quando nenhuma IA está configurada, então o sistema continua totalmente utilizável.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Alterar a fórmula do Score de Saúde Financeira.
- Substituir os pilares ou a seção Paz Financeira.
- Criar um novo cadastro de orçamento separado de Limites.
- Enviar histórico financeiro completo para fornecedores externos.
- Exigir marcação manual de “evento pontual” nos lançamentos.
- Criar categorias, subcategorias ou tags automaticamente com IA.
- Classificar lançamentos antigos em lote.
- Treinar, empacotar ou distribuir modelo local de machine learning.
- Dar recomendação personalizada de investimento, crédito ou planejamento tributário.

## Plano de implementação

- [x] Passo 1 — Atualizar specs afetadas e resolver pendências obrigatórias antes de codificar. Fecha: critérios 1 a 28.
- [x] Passo 2 — Criar armazenamento local criptografado de configuração de IA por usuário, seguindo o padrão de segurança aplicável. Fecha: critérios 17, 18, 19, 21, 23, 27 e 28.
- [ ] Passo 3 — Implementar núcleo local de cálculo de tendências em Python, com série mensal, Budget x Realizado, achados estruturados em centavos inteiros, eventos pontuais e confiança. Fecha: critérios 1, 3, 4, 5, 6, 7, 8, 9, 13, 22, 25, 26, 27 e 28.
- [ ] Passo 4 — Criar rotas autenticadas e validadas para tendências e preferências de IA. Fecha: critérios 1, 12, 13, 14, 15, 16, 17, 18 e 19.
- [ ] Passo 5 — Adicionar UI em Preferências para ligar/desligar IA, escolher provedor em combo e salvar configuração sem expor segredos. Fecha: critérios 10, 11, 12, 13, 15, 16 e 20.
- [ ] Passo 6 — Adicionar aba **Tendências** no Cockpit, com gráfico mês a mês, tabela Budget x Realizado e bloco **Tendências e achados**, preservando identidade visual e leitura local sem IA. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 10, 20, 21, 25, 26, 27 e 28.
- [ ] Passo 7 — Implementar reescrita automática opcional por IA com payload minimizado, timeout curto e fallback local. Fecha: critérios 12, 13, 14, 16 e 17.
- [ ] Passo 8 — Criar testes automatizados para núcleo local, segurança de preferências, fallback de IA e isolamento por usuário. Fecha: critérios 1 a 28.

## Changelog

- `0.7` — 2026-08-02 — Iniciada implementação dos passos 1 e 2: documentação alinhada e armazenamento local criptografado de configuração de IA por usuário definido como fundação para Preferências e tendências futuras.
- `0.6` — 2026-08-02 — Registrada decisão de tratar Tendências como aba própria do Cockpit, com gráfico mês a mês de receitas x despesas x saldo e tabela Budget x Realizado baseada nos Limites existentes.
- `0.5` — 2026-07-31 — Definidos sinais iniciais de eventos pontuais por categorias/subcategorias existentes, com palavras-chave e tags apenas como reforço, removendo a última pendência conhecida.
- `0.4` — 2026-07-31 — Definida reescrita automática por IA quando configurada e descartada marcação manual de evento pontual para preservar simplicidade do cadastro.
- `0.3` — 2026-07-31 — Definida rota separada `GET /api/financial-health-trends` para tendências e contrato `Custom / Local` compatível com OpenAI Chat Completions na primeira versão.
- `0.2` — 2026-07-31 — Definida primeira versão das Preferências de IA com combo para OpenAI/ChatGPT, Anthropic/Claude, Google/Gemini e Custom/Local, abrindo campos específicos quando Custom/Local for selecionado.
- `0.1` — 2026-07-31 — Spec inicial em rascunho para seção de tendências e achados na Saúde Financeira, com MVP local determinístico, configuração opcional de IA nas Preferências, identificação de eventos pontuais e plano de implementação.

## Relacionados

- [[score-saude-financeira]]
- [[relatorios]]
- [[lancamentos]]
- [[cartoes]]
- [[seguranca-autenticacao]]
- [[../adr/0003-sqlite-fonte-de-verdade|ADR-0003]]
- [[../adr/0005-smtp-criptografado-local|ADR-0005]]
- [[../adr/0006-classificacao-assistida-local|ADR-0006]]
