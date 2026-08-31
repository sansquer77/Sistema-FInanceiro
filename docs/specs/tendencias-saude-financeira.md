---
tipo: spec
area: tendencias-saude-financeira
status: implementado
versao: 2.23
atualizado: 2026-08-31
relacionados:
  - "[[score-saude-financeira]]"
  - "[[relatorios]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[seguranca-autenticacao]]"
  - "[[../adr/0003-sqlite-fonte-de-verdade|ADR-0003]]"
  - "[[../adr/0005-smtp-criptografado-local|ADR-0005]]"
  - "[[../adr/0006-classificacao-assistida-local|ADR-0006]]"
tags: [spec, "area/tendencias-saude-financeira", "status/implementado"]
aliases: ["Tendências de Saúde Financeira", "Achados Financeiros", "Insights Financeiros"]
---

# Tendências e Achados de Saúde Financeira

> [!info] Status
> **implementado** · área: `tendencias-saude-financeira` · atualizado em 2026-08-31 · relacionados: [[score-saude-financeira]], [[relatorios]], [[lancamentos]], [[cartoes]]

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
| `antecipacao_parcelas` | lista | Lançamentos antecipados para a fatura do mês, por histórico operacional ou por parcelas futuras concentradas na competência, com valor em centavos e descrição da compra quando identificável. |
| `resumo_local` | texto | Texto determinístico gerado por templates locais. |
| `resumo_ia` | texto opcional | Texto reescrito por IA, quando ativado explicitamente e disponível. |
| `ia_ativa` | booleano | Indica se a preferência do usuário permite uso de IA para esta função. |
| `ia_fornecedor` | texto opcional | Fornecedor configurado: `openai`, `anthropic`, `google`, `custom` ou `local`. |

## Regras

- A análise de tendências não pontua no Score principal e não altera nenhum pilar de [[score-saude-financeira]].
- A análise de tendências deve aparecer em uma aba própria do Cockpit, separada de **Situação do mês** e **Saúde Financeira**, para evitar rolagem excessiva e preservar foco de leitura.
- As abas analíticas do Cockpit devem aparecer na ordem **Situação**, **Tendências** e **Saúde Financeira**, mantendo a leitura do mês primeiro, os achados comparativos em seguida e o Score ao final.
- A aba deve priorizar uma leitura visual mês a mês, com gráfico misto de barras agrupadas para receitas/despesas e linha de saldo líquido, respeitando as cores semânticas do design system.
- O gráfico mês a mês deve caber na área disponível sem aumentar a altura padrão do Cockpit; rótulos monetários devem se ajustar ou reduzir discretamente quando necessário, como nos demais gráficos do app.
- O eixo Y do gráfico deve preservar sinal negativo em valores abaixo de zero, exibindo `-R$ ...` quando aplicável.
- O gráfico não deve forçar escala simétrica se apenas o saldo líquido ficar negativo; despesas e receitas devem ser tratadas como valores positivos em barras, e o campo negativo deve refletir apenas a menor perda/saldo negativo relevante.
- O eixo Y do gráfico deve usar escala visual confortável, evitando rótulos colados próximos ao zero e usando rótulos compactos quando valores altos prejudicarem a leitura.
- O gráfico deve evitar espaço morto por meses zerados no início da série; o filtro padrão deve exibir **Apenas meses com movimento**, mantendo atalhos para **3 meses**, **6 meses** e **12 meses**.
- A consulta base da série mensal deve filtrar lançamentos de conta por intervalo de datas (`date >= início` e `date <= fim`) para preservar o uso de índices; a extração `AAAA-MM` pode ficar apenas no agrupamento.
- O saldo líquido deve ser destacado como linha com pontos sobre as barras, e receitas/despesas devem ser barras lado a lado para reduzir cruzamento visual de linhas.
- O fundo de cada mês pode usar shading discreto para superávit/déficit: verde translúcido quando receitas superam despesas e vermelho translúcido quando despesas superam receitas.
- Cada mês do gráfico deve oferecer tooltip/descrição no hover com mês, receitas, despesas, saldo líquido e percentual de saldo sobre receita quando houver receita positiva.
- Abaixo do gráfico deve haver uma microfrase automática, calculada localmente sobre a série exibida, resumindo o principal achado do período, como melhor saldo, perda de força ou déficit no mês mais recente.
- A seção **Tendências e achados** deve evitar duplicidade entre resumo textual e cards. Achados de variação de receitas, variação de despesas e assinaturas/serviços recorrentes devem aparecer apenas no texto narrativo. Cards devem ficar reservados para limites, eventos pontuais, antecipações e outros itens que precisem de detalhe operacional.
- Quando a reescrita por IA estiver ativa, a IA deve atuar como síntese executiva integrada do resumo local, com 2 a 4 frases curtas, e não deve repetir em lista textual os limites estourados/próximos, eventos pontuais ou antecipações de parcelas que já serão exibidos como cards.
- A IA pode receber contexto operacional agregado sobre quantidade de cards de limites, eventos pontuais e antecipações, mas não deve receber os detalhes desses cards, para permitir leitura de causa provável sem duplicar a interface.
- A tabela **Budget x Realizado** deve reaproveitar os limites de gastos vigentes do mês consultado, sem criar um novo cadastro de orçamento paralelo.
- A tabela **Budget x Realizado** deve mostrar, no mínimo, categoria/subcategoria, limite mensal vigente, valor realizado, diferença, percentual usado e estado textual como `Dentro do limite`, `Atenção` ou `Acima do limite`.
- A coluna de estado da tabela **Budget x Realizado** deve manter alinhamento e largura consistentes entre `Dentro do limite`, `Atenção` e `Acima do limite`, sem molduras, fundos, bordas ou quebras visuais diferentes por tamanho do texto; a atenção deve ser comunicada apenas por cor/texto.
- As colunas numéricas da tabela **Budget x Realizado** devem ficar alinhadas à direita e com largura previsível, deixando a categoria ocupar o espaço flexível principal.
- Quando houver histórico suficiente, a tabela pode exibir colunas mês a mês para comparação visual do realizado por limite, preservando densidade e leitura em telas menores.
- Quando não houver limites cadastrados, a aba deve exibir estado vazio explicativo e orientar o usuário a cadastrar limites, sem impedir o uso do gráfico e dos achados.
- O MVP deve funcionar sem IA externa, internet, chave de API, modelo local ou dependência adicional.
- Os cálculos e achados estruturados devem ser feitos localmente no núcleo Python, usando centavos inteiros.
- A IA, quando ativada, pode apenas transformar achados estruturados em texto mais natural; ela não deve calcular valores financeiros, escolher categorias novas nem inferir dados ausentes.
- O botão de ligar/desligar IA deve ficar em **Preferências** e vir desligado por padrão.
- A configuração de IA deve oferecer um combo de provedor com as opções principais `OpenAI / ChatGPT`, `Anthropic / Claude`, `Google / Gemini` e `Custom / Local`.
- Quando o usuário selecionar um provedor principal, a interface deve exibir apenas os campos necessários para aquele fornecedor conhecido, preservando simplicidade.
- Para provedores externos conhecidos que exigem chave (`OpenAI / ChatGPT`, `Anthropic / Claude` e `Google / Gemini`), a interface deve exibir os campos `Modelo` e `API key`, sem expor `base_url` e `auth_type` ao usuário.
- `Google / Gemini` deve usar o contrato nativo do Gemini (`models/{model}:generateContent`) e extrair texto de `candidates[0].content.parts`, sem exigir compatibilidade OpenAI Chat Completions.
- O modelo do Google/Gemini pode ser informado com ou sem o prefixo `models/`, mas deve corresponder a um modelo válido da API Gemini; caso contrário, o app deve cair em fallback local sem consumo no provedor.
- `Anthropic / Claude` deve usar o contrato nativo Messages API (`/v1/messages`) e extrair texto de `content[]` com `type=text`, sem exigir compatibilidade OpenAI Chat Completions.
- Quando o usuário selecionar `Custom / Local`, a interface deve abrir campos adicionais para configurar endpoint/base URL, modelo, formato de autenticação e contrato de payload compatível.
- Na primeira versão, `Custom / Local` deve exigir compatibilidade com o contrato **OpenAI Chat Completions** (`/v1/chat/completions`), por ser o formato mais comum entre servidores locais e gateways compatíveis, como Ollama, LM Studio, LocalAI, LiteLLM e proxies equivalentes.
- A configuração mínima de `Custom / Local` deve conter `base_url`, `model`, `auth_type` (`none` ou `bearer`), `api_key` opcional, `timeout_seconds` curto, `temperature` baixa e `max_tokens` limitado.
- A primeira versão de `Custom / Local` não deve usar streaming nem aceitar contratos arbitrários de payload; suporte a Responses API customizada, contrato próprio do app ou outros formatos fica para evolução futura.
- Chaves de API devem ser armazenadas criptografadas localmente por usuário em arquivo dentro da pasta runtime `data/`, seguindo o mesmo princípio de [[../adr/0005-smtp-criptografado-local|ADR-0005]], nunca em texto puro no banco, frontend, logs ou pacote distribuível.
- A análise local deve usar timeout curto e fallback imediato quando a IA estiver indisponível.
- Nenhuma chamada de IA pode manter conexão SQLite aberta durante a requisição externa.
- O usuário deve conseguir desligar a IA sem perder a análise local.
- Quando a IA estiver ligada e corretamente configurada, a reescrita do resumo deve ser acionada automaticamente ao carregar o bloco **Tendências e achados**, sem exigir um botão adicional.
- A reescrita automática por IA deve preservar o fallback local: se a chamada falhar, expirar ou retornar conteúdo inválido, o usuário visualiza o resumo local determinístico.
- Textos enviados à IA devem ser minimizados: somente achados estruturados necessários, sem enviar histórico completo, senhas, tokens, caminhos locais ou dados de outros usuários.
- Chamadas externas de IA devem validar TLS; quando o Python local não tiver CA padrão funcional, o app pode usar um bundle de CA local disponível no ambiente, sem desativar verificação SSL.
- A interface deve informar claramente quando o texto foi gerado ou reescrito por IA.
- Quando o texto do bloco **Tendências e achados** for reescrito por IA, o título do bloco deve exibir um marcador discreto com ícone indicando o uso de IA.
- Com histórico inferior a 3 meses, a confiança da tendência deve ser `baixa` ou `intermediaria`, e o resumo deve evitar afirmar tendência permanente.
- O aviso de confiança por histórico curto, como **Histórico curto**, deve ser exibido como texto de seção fora da lista de cards de achados, para preservar hierarquia visual semelhante a **Tendências e achados** e **Budget x Realizado**.
- A área analítica da aba deve usar fluxo vertical em largura total, na ordem **Tendências e achados**, **Budget x Realizado** e, ao final, os cards/avisos de confiança como **Histórico curto**, evitando colunas lado a lado em telas menores como MacBook Air.
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
- O sistema deve identificar antecipações de parcelas em cartão quando houver lançamentos movidos para uma fatura anterior, incluindo o padrão de histórico operacional `Lancamento movido para fatura yyyy-mm`.
- Quando não houver histórico operacional disponível, o sistema também deve identificar antecipação por evidência estrutural: parcelas de compra parcelada com `invoice_month` igual ao mês consultado e data da parcela posterior ao último dia desse mês.
- Movimentos de lançamento para fatura posterior são postergação/remanejamento (`direction = next`) e não devem entrar no card **Antecipação de parcelas**.
- Antecipações de parcelas devem ser descritas como aumento pontual de despesa no mês atual que pode reduzir impacto de faturas futuras, sem classificar automaticamente como problema de consumo.
- O card de antecipação de parcelas deve exibir o total antecipado em centavos formatado pela interface e a quantidade de lançamentos antecipados para a fatura.
- Quando as compras antecipadas forem identificáveis, o texto explicativo deve citar até 5 descrições; acima disso, deve agrupar o restante para preservar densidade e evitar transformar o resumo em extrato.
- Pagamentos de fatura em conta-corrente continuam excluídos das despesas analíticas para evitar duplicidade, conforme [[relatorios]].
- Lançamentos de cartão devem entrar pela competência da fatura (`invoice_month`) nas análises mensais, conforme [[relatorios]].
- O card de **Despesas** no topo da aba deve oferecer indicação discreta de fonte, explicando que o valor soma despesas de contas pela data e lançamentos de cartão pela competência da fatura, com pagamentos de fatura excluídos para evitar duplicidade.
- Quando o saldo previsto no fim do mês em contas de liquidez ou carteira, considerando lançamentos futuros e faturas abertas dos cartões vinculados, ficar igual ou acima de 2x as despesas planejadas do mês, a aba deve exibir um aviso explicativo de oportunidade para revisar o caixa. O texto deve usar tom informativo, sem recomendar investimento específico, e pode indicar reserva ou objetivo financeiro como possibilidades.
- Sugestões devem ser explicativas e não prescritivas, evitando tom de aconselhamento financeiro personalizado.
- Em moeda estrangeira ou cenário multi-moeda, a primeira versão deve evitar misturar moedas sem explicação; quando necessário, gerar achados por moeda ou usar os valores normalizados já definidos pelo Score.
- O aviso de cenário multi-moeda deve aparecer apenas no bloco **Tendências e achados**, preferencialmente como último ponto do resumo textual, evitando repetição na linha de metadados da aba.
- O sistema deve identificar despesas recorrentes mensais na categoria `Assinaturas e Serviços` e suas subcategorias, agregando o custo mensal por subcategoria para sinalizar o peso relativo no orçamento.
- O achado de assinaturas e serviços deve ser explicativo e não prescritivo, apontando o valor mensal por subcategoria e sugerindo que o usuário avalie o uso, sem recomendar cancelamento ou classificar a despesa como problema.
- Lançamentos de cartão de crédito recorrentes mensais na categoria `Assinaturas e Serviços` também devem entrar na agregação, pela competência da fatura (`invoice_month`).

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
- Dado um usuário que acessa o Cockpit, quando visualiza as abas principais, então a ordem exibida é **Situação**, **Tendências** e **Saúde Financeira**.
- Dado um usuário com lançamentos em mais de um mês, quando consulta a aba **Tendências**, então visualiza um gráfico misto mês a mês com barras agrupadas de receitas/despesas e linha de saldo líquido.
- Dado uma série com saldo negativo, quando o eixo Y exibe valores abaixo de zero, então os rótulos aparecem com sinal negativo e moeda, como `-R$ 38.128,12`.
- Dado uma série com meses iniciais zerados, quando o filtro padrão do gráfico está ativo, então apenas meses com movimento aparecem para evitar compressão dos dados reais.
- Dado o usuário usando o gráfico de tendências, quando escolhe os atalhos de período, então pode alternar entre **Com movimento**, **3 meses**, **6 meses** e **12 meses** sem nova chamada à API.
- Dado um mês com receita maior que despesa, quando o gráfico é exibido, então o fundo daquele mês usa shading verde discreto; quando despesa supera receita, usa shading vermelho discreto.
- Dado o usuário passando o mouse sobre um mês do gráfico, quando o tooltip nativo aparece, então ele informa mês, receitas, despesas, saldo líquido e percentual do saldo sobre receita quando aplicável.
- Dado o gráfico com valores elevados e saldo negativo pequeno, quando o eixo Y é exibido, então os rótulos ficam compactos e não se sobrepõem próximos ao zero.
- Dado o usuário visualizando o gráfico de Tendências, quando a série filtrada é exibida, então uma microfrase abaixo do gráfico resume automaticamente o melhor saldo, pior saldo ou déficit mais recente.
- Dado a seção **Tendências e achados**, quando o resumo textual já citar receitas, despesas ou assinaturas recorrentes, então esses achados não aparecem novamente como cards.
- Dado existam limites próximos/estourados, eventos pontuais ou antecipações de parcelas, quando a seção é renderizada, então esses itens aparecem como cards por conterem detalhe operacional complementar ao resumo, sem serem repetidos em lista no texto narrativo.
- Dado um usuário com limites cadastrados, quando consulta a aba **Tendências**, então visualiza uma tabela **Budget x Realizado** reaproveitando os limites vigentes e o consumo real por categoria/subcategoria.
- Dado uma linha acima do limite na tabela **Budget x Realizado**, quando o estado exibido for `Acima do limite`, então o texto fica alinhado com os demais estados e não cria moldura, fundo ou borda visual diferente.
- Dado um usuário sem limites cadastrados, quando consulta a aba **Tendências**, então visualiza estado vazio explicativo para Budget x Realizado sem bloquear o gráfico e os achados.
- Dado um usuário com apenas dois meses de histórico, quando consulta tendências, então a análise informa confiança baixa ou intermediária e evita afirmar uma tendência permanente.
- Dado um usuário com despesas do mês acima do mês anterior, quando existem categorias responsáveis pela maior variação, então o sistema lista as principais categorias/subcategorias com valores em centavos formatados pela interface.
- Dado um usuário com receitas pontuais identificáveis como PLR, bônus, férias, 13º ou restituição, quando a receita do mês aumenta, então o resumo informa que parte do aumento pode ser pontual.
- Dado um usuário com receita não recorrente em `Freelance e Autônomo` ou `Outras Receitas`, quando a análise de tendências é calculada, então essa receita é candidata a evento pontual e pode ser citada como fator de distorção do mês.
- Dado um usuário com despesa em `Viagens, Passagens e Hospedagens (Férias)`, quando a análise de tendências é calculada, então essa despesa é candidata a evento pontual de férias/viagem.
- Dado um usuário com despesa em `Imprevistos e Emergências Domésticas` ou `Habitação › Manutenção, Reparos e Reformas`, quando a análise de tendências é calculada, então essa despesa é candidata a evento pontual de manutenção, reparo ou emergência doméstica.
- Dado um usuário com receitas recorrentes mensais, quando a análise compara receitas, então a leitura diferencia receitas recorrentes de receitas pontuais.
- Dado um usuário com antecipações de parcelas em cartão registradas no histórico como movimento para fatura anterior, quando o mês consultado concentra esses lançamentos, então o card **Antecipação de parcelas** informa que o aumento de despesa pode estar ligado a antecipação e pode reduzir faturas futuras.
- Dado um usuário com lançamentos movidos para fatura posterior, quando consulta o mês de destino, então esses lançamentos não aparecem como antecipação de parcelas.
- Dado um usuário com parcelas futuras concentradas em uma fatura sem histórico operacional disponível, quando consulta o mês dessa fatura, então o card **Antecipação de parcelas** aparece obrigatoriamente.
- Dado um usuário com antecipações de parcelas no mês, quando visualiza o card **Antecipação de parcelas**, então o card mostra o total antecipado e a quantidade de lançamentos antecipados.
- Dado um usuário com compras parceladas antecipadas identificáveis, quando visualiza o card **Antecipação de parcelas**, então o texto explicativo cita as compras antecipadas de forma resumida, limitando a lista para preservar a leitura.
- Dado um usuário com pagamentos de fatura em conta-corrente, quando as despesas do mês são agregadas, então esses pagamentos não são somados como despesa analítica.
- Dado um usuário com lançamentos de cartão, quando a tendência mensal é calculada, então os valores entram pela competência da fatura (`invoice_month`).
- Dado um usuário visualizando o card **Despesas** no topo da aba Tendências, quando consulta a indicação de fonte, então entende que o valor vem das despesas analíticas do mês em BRL, somando contas por data e cartões por competência da fatura, com pagamentos de fatura excluídos.
- Dado um usuário em cenário multi-moeda, quando houver dados em mais de uma moeda, então o sistema não mistura moedas sem indicar a base usada.
- Dado um usuário em cenário multi-moeda, quando visualiza a aba **Tendências**, então o aviso de moeda aparece uma única vez no bloco **Tendências e achados**.
- Dado um usuário com despesas recorrentes mensais na categoria `Assinaturas e Serviços`, quando consulta a aba **Tendências**, então o sistema exibe o custo mensal agregado por subcategoria como achado estruturado em centavos, sem recomendar cancelamento.
- Dado um usuário que acessa Preferências de IA, quando abre o campo de provedor, então visualiza as opções principais `OpenAI / ChatGPT`, `Anthropic / Claude`, `Google / Gemini` e `Custom / Local`.
- Dado um usuário que seleciona `OpenAI / ChatGPT`, `Anthropic / Claude` ou `Google / Gemini`, quando a tela de configuração é exibida, então visualiza os campos `Modelo` e `API key`, sem precisar configurar endpoint ou tipo de autenticação.
- Dado um usuário que seleciona `Custom / Local` como provedor de IA, quando a tela de configuração é exibida, então campos adicionais de endpoint/base URL, modelo, autenticação e contrato de payload ficam disponíveis.
- Dado um usuário que seleciona `Custom / Local`, quando configura a integração, então o endpoint deve ser tratado como compatível com OpenAI Chat Completions em `{base_url}/chat/completions`.
- Dado um usuário que seleciona `Google / Gemini`, quando a reescrita por IA é executada, então o sistema envia payload para `models/{model}:generateContent` e lê apenas o texto retornado em `candidates[0].content.parts`.
- Dado um usuário que seleciona `Google / Gemini` e informa modelo com prefixo `models/`, quando a reescrita por IA é executada, então o sistema não duplica o prefixo na URL final.
- Dado um usuário que seleciona `Anthropic / Claude`, quando a reescrita por IA é executada, então o sistema envia payload para `/v1/messages` e lê apenas textos retornados em `content[]`.
- Dado um usuário que seleciona `Custom / Local`, quando a reescrita por IA é executada, então o sistema envia payload não-streaming com `model`, `messages`, `temperature` e `max_tokens`, e lê apenas `choices[0].message.content`.
- Dado um usuário que ativa IA nas Preferências com chave válida, quando solicita resumo por IA, então a IA recebe apenas achados estruturados minimizados e retorna texto sem alterar os valores calculados localmente.
- Dado um usuário com IA ativa e configurada, quando abre a aba **Tendências**, então a reescrita por IA do bloco **Tendências e achados** é acionada automaticamente após o resumo local estar disponível.
- Dado um usuário que desativa IA nas Preferências, quando consulta a aba **Tendências** novamente, então nenhuma chamada externa é realizada e o resumo local permanece disponível.
- Dado uma falha de rede, timeout ou erro do fornecedor de IA, quando o usuário consulta tendências, então a tela exibe o resumo local e uma indicação discreta de que a IA não foi usada.
- Dado um usuário autenticado A, quando consulta tendências, então somente dados associados ao `user_id` de A são considerados.
- Dado uma requisição sem sessão válida, quando tenta consultar tendências ou preferências de IA, então o sistema retorna erro de autenticação sem expor dados.
- Dado uma tentativa de salvar chave de API, quando a configuração é persistida, então o segredo é armazenado criptografado e nunca retornado pela API.
- Dado o modo local/offline do app, quando nenhuma IA está configurada, então o sistema continua totalmente utilizável.
- Dado um usuário com IA ativa e resumo reescrito com sucesso, quando visualiza o bloco **Tendências e achados**, então o título do bloco exibe um marcador discreto com ícone indicando IA.
- Dado um usuário com histórico curto, quando visualiza **Tendências e achados**, então o aviso **Histórico curto** aparece fora dos cards de achados, como texto de seção.
- Dado um usuário em tela estreita ou intermediária, quando visualiza a aba **Tendências**, então **Tendências e achados**, **Budget x Realizado** e os cards de confiança aparecem em fluxo vertical usando a largura disponível.
- Dado um usuário com saldo previsto no fim do mês em contas de liquidez/carteira igual ou acima de 2x as despesas planejadas, quando consulta a aba **Tendências**, então o resumo exibe um aviso explicativo de oportunidade de revisar o caixa usando o saldo previsto que considera lançamentos futuros e faturas abertas dos cartões vinculados.

- Dado o gráfico de Tendências em tema claro ou escuro, quando o tooltip é exibido ou o tema muda, então texto, cabeçalho e indicadores dos eixos mantêm cores de texto e superfície do tema ativo, sem alterar as cores das séries. Contrato CSS automatizado; aparência no Safari requer validação manual.

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

- [x] Ajustar contraste do tooltip e dos indicadores dos eixos com tokens reativos ao tema; testar os seletores e preservar séries. Fecha: critério adicional de contraste. Teste estrutural aprovado; aparência no Safari pendente de validação manual.
- [x] Passo 1 — Atualizar specs afetadas e resolver pendências obrigatórias antes de codificar. Fecha: critérios 1 a 28.
- [x] Passo 2 — Criar armazenamento local criptografado de configuração de IA por usuário, seguindo o padrão de segurança aplicável. Fecha: critérios 17, 18, 19, 21, 23, 27 e 28.
- [x] Passo 3 — Implementar núcleo local de cálculo de tendências em Python, com série mensal, Budget x Realizado, achados estruturados em centavos inteiros, eventos pontuais, assinaturas e serviços recorrentes, oportunidade de caixa e confiança. Fecha: critérios 1, 3, 4, 5, 6, 7, 8, 9, 13, 22, 25, 26, 27, 28, 29 e 54.
- [x] Passo 4 — Criar rotas autenticadas e validadas para tendências e preferências de IA. Fecha: critérios 1, 12, 13, 14, 15, 16, 17, 18 e 19.
- [x] Passo 5 — Adicionar UI em Preferências para ligar/desligar IA, escolher provedor em combo e salvar configuração sem expor segredos. Fecha: critérios 10, 11, 12, 13, 15, 16 e 20.
- [x] Passo 6 — Adicionar aba **Tendências** no Cockpit, com gráfico mês a mês, tabela Budget x Realizado e bloco **Tendências e achados**, preservando identidade visual e leitura local sem IA. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 10, 20, 21, 25, 26, 27 e 28.
- [x] Passo 7 — Implementar reescrita automática opcional por IA com payload minimizado, timeout curto e fallback local. Fecha: critérios 12, 13, 14, 16 e 17.
- [x] Passo 8 — Criar testes automatizados para núcleo local, segurança de preferências, fallback de IA e isolamento por usuário. Fecha: critérios 1 a 28.

## Changelog

- `2.23` — 2026-08-31 — Corrigido o contraste do tooltip de Tendências com tokens dos temas claro e escuro, incluindo cabeçalho e indicadores dos eixos; contrato CSS coberto por teste automatizado.
- `2.22` — 2026-08-11 — Versionamento da app registrado: PATCH `1.4.0` → `1.4.1` aplicado em `financeiro/app_metadata.py` junto com a melhoria desta spec (v2.21), documentado no changelog do MoC.
- `2.21` — 2026-08-11 — Tendências passa a sinalizar oportunidade de revisar caixa quando o saldo previsto no fim do mês em contas de liquidez/carteira fica igual ou acima de 2x as despesas planejadas.
- `2.20` — 2026-08-10 — Card **Despesas** da aba Tendências ganha indicador discreto de fonte, explicando contas por data, cartões por competência e exclusão de pagamentos de fatura.
- `2.19` — 2026-08-09 — Prompt da IA de Tendências refinado para síntese executiva integrada em 2 a 4 frases e payload enriquecido apenas com contexto operacional agregado, sem detalhes de cards.
- `2.18` — 2026-08-09 — Ajustada a fronteira entre resumo e cards: IA e resumo local passam a evitar repetição de limites, eventos pontuais e antecipações já detalhados nos cards.
- `2.17` — 2026-08-09 — Consulta base da série mensal passa a filtrar lançamentos por intervalo de datas em vez de `substr(date, 1, 7)` no `WHERE`, preservando uso de índice em bases maiores.
- `2.16` — 2026-08-02 — Antecipação de parcelas passa a ser detectada também por evidência estrutural de parcelas futuras concentradas na fatura do mês, cobrindo bases sem histórico operacional.
- `2.15` — 2026-08-02 — Antecipação de parcelas passa a considerar apenas movimentos para fatura anterior, ignorando postergações/remanejamentos para faturas futuras.
- `2.14` — 2026-08-02 — Card e resumo de antecipação de parcelas passam a exibir total antecipado e compras parceladas identificadas.
- `2.13` — 2026-08-02 — Tendências e achados passam a evitar duplicidade: receitas, despesas e assinaturas ficam só no texto; cards ficam para limites, eventos e antecipações.
- `2.12` — 2026-08-02 — Escala do gráfico de Tendências refinada com rótulos compactos e microfrase automática abaixo do gráfico.
- `2.11` — 2026-08-02 — Gráfico de Evolução mensal evoluído para barras agrupadas de receitas/despesas com linha de saldo, filtro padrão de meses com movimento, eixo Y com negativos sinalizados e tooltip mensal.
- `2.10` — 2026-08-02 — Definida a ordem das abas do Cockpit como Situação, Tendências e Saúde Financeira.
- `2.9` — 2026-08-02 — Removida colisão com classe global `danger` no Budget x Realizado e refinada a distribuição/alinhamento das colunas numéricas e de estado.
- `2.8` — 2026-08-02 — Padronizado o alinhamento e a largura da coluna Estado no Budget x Realizado para evitar quebra/moldura visual em `Acima do limite`.
- `2.7` — 2026-08-02 — Layout da área analítica de Tendências reorganizado em fluxo vertical full-width: Tendências e achados, Budget x Realizado e cards de confiança ao final.
- `2.6` — 2026-08-02 — Especificado que chaves de IA ficam criptografadas em arquivo dentro de `data/` e que avisos de confiança por histórico curto aparecem fora dos cards de achados.
- `2.5` — 2026-08-02 — Chamadas externas de IA passam a usar contexto TLS com bundle de CA local disponível, preservando validação SSL em ambientes Python sem CA padrão funcional.
- `2.4` — 2026-08-02 — Corrigido o contrato de reescrita por IA para Anthropic/Claude via Messages API e aceito modelo Gemini com ou sem prefixo `models/`.
- `2.3` — 2026-08-02 — Corrigido o contrato de reescrita por IA para Google/Gemini, usando `generateContent` nativo e extração por `candidates[0].content.parts`.
- `2.2` — 2026-08-02 — Adicionado marcador discreto com ícone no título de **Tendências e achados** quando o resumo exibido foi reescrito por IA.
- `2.1` — 2026-08-02 — Aviso multi-moeda deixa de aparecer duplicado na linha de metadados e o layout prioriza Tendências e achados na coluna principal.
- `2.0` — 2026-08-02 — Preferências de IA passam a exibir `Modelo` e `API key` também para OpenAI, Anthropic e Google, mantendo endpoint e autenticação avançados restritos a Custom/Local.
- `1.9` — 2026-08-02 — Aviso multi-moeda passa a indicar que a base BRL usa valores normalizados por cotação manual ou pela última PTAX de venda disponível.
- `1.8` — 2026-08-02 — Aviso multi-moeda ajustado para aparecer sempre como último ponto do resumo e explicitar que a análise usa valores em BRL já normalizados nos lançamentos.
- `1.7` — 2026-08-02 — Melhorada a leitura da aba Tendências: achados de eventos pontuais e antecipações passam a ser agrupados para evitar cards repetidos, e o resumo textual é exibido como introdução e lista de pontos.
- `1.6` — 2026-08-02 — Versão do app ajustada para incremento MINOR e tratamento de erro da configuração de IA endurecido para não exibir mensagem genérica quando a resposta não vier em JSON; rota `PUT /api/ai-settings` coberta pelo fluxo real com origem válida.
- `1.5` — 2026-08-02 — Ajustada a rota de tendências para refletir `ia_ativa` quando a IA está ligada e configurada, permitindo a reescrita automática no Cockpit; adicionada cobertura automatizada para evitar regressão.
- `1.4` — 2026-08-02 — Passos 7 e 8 finalizados: reescrita opcional por IA validada com payload minimizado, fallback local e cobertura automatizada de núcleo local, preferências seguras, IA e isolamento por usuário.
- `1.2` — 2026-08-02 — Passo 6 concluído: aba **Tendências** no Cockpit com gráfico mês a mês, tabela Budget x Realizado e bloco Tendências e achados, leitura local sem IA.
- `1.1` — 2026-08-02 — Passo 5 concluído: UI em Preferências para ligar/desligar IA, escolher provedor em combo e salvar configuração sem expor segredos.
- `1.0` — 2026-08-02 — Passo 4 concluído: rotas autenticadas `/api/financial-health-trends`, `/api/ai-settings`, `/api/financial-health-trends/ai-summary` e módulo de reescrita por IA com fallback local.
- `0.9` — 2026-08-02 — Adicionado ao núcleo de tendências o achado de Assinaturas e Serviços recorrentes, agregando custo mensal por subcategoria de forma explicativa e não prescritiva.
- `0.8` — 2026-08-02 — Passo 3 concluído: núcleo local de tendências (`financeiro/trends.py`) calcula série mensal, Budget x Realizado, achados estruturados, eventos pontuais e confiança; antecipação de parcelas passa a ser registrada no histórico operacional ao mover fatura de cartão.
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
