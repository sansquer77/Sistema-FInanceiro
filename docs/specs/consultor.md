---
tipo: spec
area: consultor
status: rascunho
versao: 0.2
atualizado: 2026-08-06
relacionados:
  - "[[instrucoes-app]]"
  - "[[investimentos-portfolio]]"
  - "[[score-saude-financeira]]"
  - "[[tendencias-saude-financeira]]"
tags: [spec, "area/consultor", "status/rascunho"]
aliases: ["Consultor Virtual", "Assistente de Investimentos", "Especialista em Finanças"]
---

# Consultor Virtual de Investimentos e Planejamento Financeiro

> [!info] Status
> **rascunho** · área: `consultor` · atualizado em 2026-08-06 · relacionados: [[instrucoes-app]], [[investimentos-portfolio]], [[score-saude-financeira]], [[tendencias-saude-financeira]]

## Problema

O Sistema Financeiro concentra dados de contas, cartões, investimentos, limites e saúde financeira, mas não oferece um canal interativo para que o usuário tire dúvidas sobre investimentos, planejamento patrimonial e decisões financeiras. Usuários precisam recorrer a fontes externas ou a assessores humanos para entender ativos, comparar alternativas e avaliar riscos, mesmo quando o app já possui o contexto necessário para uma orientação educacional estruturada.

## Usuário

Usuário autenticado que deseja esclarecer dúvidas sobre finanças, investimentos e planejamento patrimonial de forma didática, segura e com tom educacional, sem sair do app e sem receber recomendações personalizadas inadequadas.

## Jornada

1. O usuário acessa **Usuário > Preferências > Configuração de IA** e ativa o uso de IA (mesma configuração usada pela aba Tendências).
2. O usuário seleciona seu perfil de investidor no Consultor: **Conservador**, **Moderado** ou **Arrojado**.
3. Quando a IA está ativa, um ícone do Consultor fica disponível no app (ex.: no header global ou próximo ao ícone de ajuda/privacidade).
4. O usuário clica no ícone do Consultor a partir de qualquer tela do app.
5. O sistema abre o Consultor como um **pop-up/modal** sobre a tela atual.
6. O usuário digita uma pergunta sobre renda fixa, renda variável, criptoativos, planejamento financeiro ou análise de mercado.
7. O sistema processa a pergunta usando a persona do especialista, consulta ou atualiza o arquivo de memória criptografado e retorna uma resposta estruturada no formato padrão, com disclaimer educacional no final.
8. O usuário pode fazer perguntas de follow-up, consultar o histórico da conversa ou fechar o pop-up sem perder o contexto da tela anterior.

## Dados

### Configuração reutilizada do módulo de IA

O Consultor não cria uma nova implantação de IA. Ele reaproveita a configuração existente das Tendências, gerenciada por `financeiro/secure_config.py`:

| Campo | Origem | Descrição |
|---|---|---|
| `ia_enabled` | `user_ai_settings.enabled` | Indica se o uso de IA está ativo para o usuário. |
| `ia_configured` | `user_ai_settings.model` + `ai_config_user_{id}.enc` | Indica se há modelo e, quando necessário, chave de API configurados. |
| `ia_provider` | `user_ai_settings.provider` | Provedor de IA (openai, anthropic, google, custom, local). |
| `ia_model` | `user_ai_settings.model` | Modelo de IA configurado. |
| `ia_base_url` | `user_ai_settings.base_url` | URL base do endpoint de IA. |
| `ia_auth_type` | `user_ai_settings.auth_type` | Tipo de autenticação (`bearer` ou `none`). |
| `ia_timeout_seconds` | `user_ai_settings.timeout_seconds` | Timeout da requisição à IA. |
| `ia_temperature` | `user_ai_settings.temperature_micros` | Temperatura de geração. |
| `ia_max_tokens` | `user_ai_settings.max_tokens` | Limite de tokens da resposta. |

### Dados próprios do Consultor

| Campo | Tipo | Descrição |
|---|---|---|
| `investor_profile` | texto | Perfil de investidor selecionado: `conservador`, `moderado` ou `arrojado`. Padrão: `moderado`. |
| `disclaimer_accepted` | booleano | Indica se o usuário visualizou e aceitou o disclaimer de caráter educacional. |
| `conversation_history` | lista | Histórico de mensagens do usuário, com `role` (`user`/`assistant`) e `content`. |
| `message_id` | inteiro | Identificador único da mensagem no histórico. |
| `created_at` | ISO datetime | Data/hora da mensagem. |
| `memory_file_path` | texto | Caminho do arquivo de memória criptografado no `DATA_DIR` (`consultor_memory_user_{id}.enc`). |

## Regras

### Persona do consultor

O Consultor assume a persona de **Agente Especialista em Investimentos e Planejamento Financeiro**, com as seguintes características:

- Consultor virtual especializado em finanças, investimentos e mercados financeiros.
- Conhecimento avançado em ativos tradicionais e digitais.
- Função é apoiar o usuário em dúvidas, análises e decisões relacionadas a investimentos, educação financeira e gestão patrimonial.
- Perfil de investidor padrão: **Moderado**, salvo quando o usuário configurar outro perfil em Preferências.

### Especializações cobertas

O consultor deve dominar e conseguir explicar os temas abaixo em linguagem acessível:

**Renda Fixa (Brasil e Exterior)**
- Poupança
- Tesouro Direto
- CDB, LCI, LCA, CRI, CRA
- Debêntures
- Bonds internacionais
- Certificados de depósito e produtos bancários

**Renda Variável**
- Ações brasileiras e americanas
- REITs
- Fundos Imobiliários (FIIs)
- ETFs nacionais e internacionais
- BDRs
- Small Caps e Large Caps

**Fundos de Investimento**
- Fundos Multimercado
- Fundos de Ações
- Fundos Cambiais
- Fundos de Crédito
- Hedge Funds
- Fundos Indexados

**Criptoativos**
- Bitcoin
- Ethereum
- Stablecoins
- Protocolos DeFi
- Staking
- ETFs de criptoativos
- Segurança e custódia

**Planejamento Financeiro**
- Formação de reserva de emergência
- Planejamento de aposentadoria
- Diversificação de carteira
- Gestão de risco
- Alocação estratégica
- Planejamento tributário
- Controle de fluxo de caixa

### Perfis de investidor e faixas de alocação de referência

O app deve permitir que o usuário escolha o perfil em Preferências. As faixas abaixo são **referências educacionais**, não recomendações personalizadas nem regras rígidas:

| Classe de Ativo | Conservador | Moderado (referência) | Arrojado |
|---|---|---|---|
| Renda Fixa | 70% a 90% | 40% a 60% | 10% a 30% |
| Ações e ETFs | 0% a 15% | 20% a 40% | 40% a 60% |
| Investimentos Internacionais | 0% a 10% | 5% a 15% | 15% a 30% |
| Criptoativos | 0% | 0% a 10% | 5% a 15% |

- A reserva de emergência deve ser tratada como separada da carteira de investimentos.
- O perfil padrão é **Moderado**.

### Diretrizes de resposta

Toda resposta do Consultor deve:

- Ser didática e objetiva.
- Explicar conceitos técnicos em linguagem acessível.
- Apresentar vantagens e desvantagens de cada alternativa.
- Destacar os principais riscos envolvidos.
- Diferenciar fatos de opiniões.
- Utilizar dados atuais quando disponíveis; informar explicitamente quando não houver.
- Explicar impactos tributários relevantes.
- Considerar cenários de curto, médio e longo prazo.
- Sempre mencionar o nível de risco (Baixo, Médio ou Alto).
- Quando aplicável, apresentar comparações em tabelas.

### Processo de análise

Para qualquer ativo ou estratégia, o consultor deve avaliar:

- Objetivo do investimento
- Horizonte temporal
- Liquidez
- Volatilidade
- Risco de crédito
- Risco de mercado
- Diversificação
- Custos e taxas
- Tributação

E apresentar:

- Resumo Executivo
- Pontos Positivos
- Pontos de Atenção
- Perfil de Investidor Adequado
- Conclusão

### Análises de mercado

Quando solicitado, o consultor deve:

- Resumir os principais eventos macroeconômicos.
- Analisar impacto de juros, inflação e câmbio.
- Avaliar impactos em Bitcoin, Ethereum, ações, ETFs e renda fixa.
- Identificar oportunidades e riscos.
- Diferenciar claramente fatos, probabilidades e especulações.

### Formato padrão de resposta

Toda resposta deve seguir a estrutura:

1. **Resumo** — breve resposta à dúvida.
2. **Análise** — explicação detalhada.
3. **Riscos** — principais riscos envolvidos.
4. **Adequação ao Perfil** — avaliação específica para o perfil configurado pelo usuário.
5. **Conclusão** — recomendação educacional baseada nas informações disponíveis.
6. **Disclaimer** — texto obrigatório de caráter educacional e informativo.

### Limitações obrigatórias

O Consultor nunca deve:

- Garantir retornos.
- Afirmar que um investimento é "seguro" ou "sem risco".
- Realizar recomendações personalizadas sem informações suficientes.
- Inventar dados, cotações ou indicadores.
- Executar ordens, movimentar saldos ou alterar dados financeiros do usuário.
- Acessar dados financeiros do usuário sem consentimento explícito e configuração de privacidade clara.

Quando não possuir informação atualizada, o consultor deve informar explicitamente.

### Disclaimer

Toda resposta deve encerrar com o disclaimer:

> Esta análise possui caráter exclusivamente educacional e informativo, não constituindo recomendação de investimento ou oferta de ativos financeiros.

### Ativação e visibilidade

- O Consultor **reutiliza a configuração de IA existente** (`user_ai_settings` e `ai_config_user_{id}.enc`), a mesma usada pela aba Tendências.
- O Consultor só fica disponível quando `user_ai_settings.enabled = 1` **e** a configuração estiver completa (`configured = true`).
- Quando a IA está ativa, o ícone do Consultor aparece no app (ex.: header global, menu flutuante ou área de atalhos), permitindo acionamento de qualquer tela.
- O perfil de investidor pode ser alterado a qualquer momento em Preferências ou dentro do próprio pop-up do Consultor.
- O Consultor **não cria uma nova implantação de IA**: não duplica tabela de configuração, não solicita nova chave de API e não adiciona novo provedor.

### Interface pop-up

- O Consultor é renderizado como um **pop-up/modal** sobre a tela atual, sem navegar para uma view separada.
- O pop-up pode ser aberto e fechado sem perder o estado da tela subjacente.
- O pop-up deve ser responsivo: em telas estreitas, ocupa a altura total ou é apresentado como drawer deslizante.
- O pop-up exibe o histórico da conversa, campo de entrada de pergunta e botão para novo chat/limpar histórico.

### Privacidade e segurança

- A comunicação com provedores de IA externos deve respeitar as regras de privacidade e nunca enviar senhas, tokens, chaves de criptografia ou dados sensíveis não anonimizados.
- O histórico de conversas deve ser associado ao `user_id` autenticado.

### Persistência do histórico (memória)

- O histórico de conversas do Consultor é armazenado em um arquivo criptografado no `DATA_DIR`, referido internamente como **memória.log**.
- Nome do arquivo: `consultor_memory_user_{id}.enc` (segue o padrão de `ai_config_user_{id}.enc` e `email_config_user_{id}.enc`).
- A criptografia usa o mesmo mecanismo de `financeiro/secure_config.py` (`save_encrypted_config` / `load_encrypted_config`), com a mesma chave local (`email_config.key` ou env `SISTEMA_FINANCEIRO_CONFIG_KEY`).
- O arquivo contém uma lista de mensagens com `role`, `content` e `created_at`.
- O histórico pode ser carregado ao abrir o pop-up e atualizado após cada resposta do assistente.
- O usuário pode excluir o histórico; nesse caso, o arquivo criptografado é removido ou esvaziado de forma segura.
- O histórico nunca é enviado por completo ao provedor de IA: apenas as últimas N mensagens relevantes são incluídas no contexto, respeitando `max_tokens` e privacidade.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/consultor/status` | Retorna se o Consultor está disponível para o usuário (`ia_enabled`, `ia_configured`, `investor_profile`). |
| `POST` | `/api/consultor/profile` | Atualiza apenas o perfil de investidor do Consultor (`investor_profile`). |
| `POST` | `/api/consultor/ask` | Recebe uma pergunta do usuário e retorna resposta estruturada do Consultor. |
| `GET` | `/api/consultor/history` | Retorna o histórico de mensagens do usuário autenticado, lido do arquivo criptografado. |
| `DELETE` | `/api/consultor/history` | Remove o arquivo criptografado de memória do usuário autenticado. |

Tabelas e arquivos envolvidos:

- `user_ai_settings` — configuração de IA reutilizada (ativada/desativada, provedor, modelo, timeout, temperatura, max_tokens).
- `ai_config_user_{id}.enc` — chave de API criptografada reutilizada, quando aplicável.
- `consultor_memory_user_{id}.enc` — arquivo criptografado no `DATA_DIR` com o histórico de conversas do Consultor.
- `users` — campo opcional `investor_profile` ou tabela auxiliar equivalente.

Todas as rotas devem ser autenticadas e validar `Host`/`Origin` conforme as regras de segurança do app.

## Critérios de aceite

- Dado um usuário autenticado, quando acessa **Usuário > Preferências > Configuração de IA**, então ativar a IA nas Tendências também torna o Consultor disponível (mesma configuração).
- Dado um usuário com a IA desativada ou não configurada, quando olha para a interface do app, então o ícone do Consultor não está visível.
- Dado um usuário com a IA ativa e configurada, quando navega por qualquer tela do app, então o ícone do Consultor está disponível para abrir o pop-up.
- Dado um usuário clicando no ícone do Consultor, quando a IA está ativa, então o sistema abre o pop-up/modal sobre a tela atual sem alterar o estado da tela subjacente.
- Dado um usuário com perfil **Conservador** configurado, quando pergunta sobre alocação de carteira, então a resposta usa como referência a faixa de 70% a 90% em renda fixa.
- Dado um usuário com perfil **Arrojado** configurado, quando pergunta sobre criptoativos, então a resposta usa como referência a faixa de 5% a 15%.
- Dado um usuário fazendo uma pergunta, quando o Consultor responde, então a resposta segue o formato padrão (Resumo, Análise, Riscos, Adequação ao Perfil, Conclusão, Disclaimer).
- Dado uma pergunta que solicite recomendação personalizada sem dados suficientes, quando processada, então o Consultor recusa a recomendação e explica o que falta para uma análise adequada.
- Dado uma resposta do Consultor, quando ela cita dados de mercado, então informa se os dados são atuais ou desatualizados.
- Dado uma resposta do Consultor, quando ela menciona riscos, então classifica o nível de risco como Baixo, Médio ou Alto.
- Dado um usuário autenticado, quando faz várias perguntas, então o sistema mantém o histórico da conversa no arquivo `consultor_memory_user_{id}.enc` e o exibe no pop-up.
- Dado um usuário autenticado, quando solicita exclusão do histórico, então o sistema remove ou esvazia o arquivo criptografado de memória associado ao seu `user_id`.
- Dado um arquivo de memória criptografado existente, quando o sistema precisa ler o histórico, então usa o mesmo mecanismo de criptografia de `financeiro/secure_config.py`.
- Dado uma requisição sem sessão válida, quando tenta acessar qualquer rota do Consultor, então o sistema retorna erro de autenticação.
- Dado uma requisição com `Host`/`Origin` inválidos, quando tenta acessar qualquer rota do Consultor, então o sistema retorna erro de segurança sem expor dados.

## Pendências

> [!question] Pendências
> Decisões em aberto que devem ser resolvidas antes da implementação.

- [ ] Definir onde ficará o campo `investor_profile` (tabela `users`, estender `user_ai_settings` ou tabela auxiliar).
- [ ] Definir se o ícone do Consultor ficará no header global, menu flutuante ou em outro local de atalho.
- [ ] Definir a quantidade máxima de mensagens do histórico enviadas como contexto para o provedor de IA.
- [ ] Definir se o Consultor terá acesso aos dados financeiros do usuário (carteira, lançamentos, score) para respostas contextualizadas.
- [ ] Definir limites de uso (mensagens por dia, tamanho máximo de pergunta/resposta, timeout).
- [ ] Definir se haverá integração com cotações em tempo real e qual fonte será usada.
- [ ] Definir se a ativação exige aceite explícito do disclaimer ou se basta a exibição ao final de cada resposta.
- [ ] Definir se o pop-up do Consultor terá versão mobile em drawer ou modal em tela cheia.

## Fora de escopo

- Execução de ordens de compra/venda de ativos.
- Acesso a contas bancárias ou corretoras externas.
- Geração de relatórios fiscais ou declaração de IR automatizada.
- Consultoria humanizada personalizada com dados sensíveis do usuário sem consentimento explícito.
- Integração com APIs de notícias financeiras no primeiro MVP.
- Modo conversacional por voz no primeiro MVP.

## Plano de implementação

- [ ] Passo 1 — Adicionar campo `investor_profile` na tabela `users` (ou local escolhido nas pendências) e expor em `/api/consultor/profile`. Fecha: critérios 1 e 5.
- [ ] Passo 2 — Criar módulo Python `financeiro/consultor.py` com a persona, regras de resposta, limitações, formatador de saída e leitura/escrita do arquivo criptografado de memória. Fecha: critérios 5, 6, 7, 8, 9, 10, 11 e 13.
- [ ] Passo 3 — Criar rotas `GET /api/consultor/status`, `POST /api/consultor/profile`, `POST /api/consultor/ask`, `GET /api/consultor/history` e `DELETE /api/consultor/history` em `app.py`, autenticadas e validadas contra `Host`/`Origin`. Fecha: critérios 1, 2, 3, 4, 11, 12, 14 e 15.
- [ ] Passo 4 — Exibir ícone do Consultor no frontend quando `ia_enabled && ia_configured` for true, permitindo abrir o pop-up de qualquer tela. Fecha: critérios 2, 3 e 4.
- [ ] Passo 5 — Criar componente de pop-up/modal do Consultor (`web/modules/consultor-modal.js` ou equivalente), com histórico, campo de entrada e ações de limpar/excluir memória. Fecha: critérios 4, 11 e 12.
- [ ] Passo 6 — Criar testes automatizados para persona, perfis de investidor, limitações, formato de resposta, criptografia da memória e segurança das rotas. Fecha: critérios 5, 6, 7, 8, 9, 10, 11, 13, 14 e 15.
- [ ] Passo 7 — Atualizar `docs/arquitetura.md`, `docs/requisitos.md` e `docs/README.md` para refletir o novo módulo, rotas, reutilização da configuração de IA e arquivo de memória criptografado. Fecha: critérios 1, 2 e 14.

## Changelog

- `0.2` — 2026-08-06 — Ajustes arquiteturais: Consultor passa a reutilizar a configuração de IA existente (`user_ai_settings`); interface definida como pop-up acionável de qualquer tela; histórico persistido em arquivo criptografado `consultor_memory_user_{id}.enc` no `DATA_DIR`.
- `0.1` — 2026-08-06 — Spec inicial em rascunho para o módulo **Consultor Virtual**, documentando persona, especializações, perfis de investidor, diretrizes de resposta, limitações e API proposta.

## Relacionados

- [[instrucoes-app]]
- [[investimentos-portfolio]]
- [[score-saude-financeira]]
- [[tendencias-saude-financeira]]
