---
tipo: spec
area: consultor
status: rascunho
versao: 0.1
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

1. O usuário acessa **Usuário > Preferências** e ativa a função de IA que irá usar o módulo **Consultor**.
2. O usuário seleciona seu perfil de investidor: **Conservador**, **Moderado** ou **Arrojado** no menu de Preferências. 
3. O usuário abre um campo de prompt do módulo **Consultor** no ícone de uma cartola que fica ao lado do ícone ocultar/mostrar valores.
4. O usuário digita uma pergunta sobre renda fixa, renda variável, criptoativos, planejamento financeiro ou análise de mercado.
5. O sistema processa a pergunta usando a persona do especialista e os dados do usuário a partir da base de dados e retorna uma resposta estruturada no formato padrão, com disclaimer educacional no final.
6. O usuário pode fazer perguntas de follow-up ou consultar o histórico da conversa.

## Dados

| Campo | Tipo | Descrição |
|---|---|---|
| `investor_profile` | texto | Perfil de investidor selecionado: `conservador`, `moderado` ou `arrojado`. Padrão: `moderado`. |
| `disclaimer_accepted` | booleano | Indica se o usuário visualizou e aceitou o disclaimer de caráter educacional. |
| `conversation_history` | lista | Histórico de mensagens da sessão ou do usuário, com `role` (`user`/`assistant`) e `content`. |
| `message_id` | inteiro | Identificador único da mensagem no histórico. |
| `created_at` | ISO datetime | Data/hora da mensagem. |

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

### Ativação e privacidade

- O Consultor só fica disponível quando explicitamente ativado em Preferências.
- O perfil de investidor pode ser alterado a qualquer momento em Preferências.
- A comunicação com provedores de IA externos, se houver, deve respeitar as regras de privacidade e nunca enviar senhas, tokens, chaves de criptografia ou dados sensíveis não anonimizados.
- O histórico de conversas deve ser associado ao `user_id` autenticado.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/consultor/config` | Retorna a configuração atual do Consultor para o usuário autenticado. |
| `POST` | `/api/consultor/config` | Atualiza configuração (`consultor_enabled`, `investor_profile`). |
| `POST` | `/api/consultor/ask` | Recebe uma pergunta do usuário e retorna resposta estruturada do Consultor. |
| `GET` | `/api/consultor/history` | Retorna o histórico de mensagens do usuário autenticado. |
| `DELETE` | `/api/consultor/history` | Remove o histórico de conversas do usuário autenticado. |

Tabelas potencialmente envolvidas:

- `users` — configurações do Consultor e perfil de investidor.
- `consultor_messages` — histórico de mensagens (`user_id`, `role`, `content`, `created_at`).

Todas as rotas devem ser autenticadas e validar `Host`/`Origin` conforme as regras de segurança do app.

## Critérios de aceite

- Dado um usuário autenticado, quando acessa **Usuário > Preferências**, então encontra a opção de ativar/desativar o Consultor e selecionar o perfil de investidor.
- Dado um usuário com o Consultor desativado, quando tenta acessar o módulo Consultor, então o sistema informa que a função precisa ser ativada nas Preferências.
- Dado um usuário com perfil **Conservador** configurado, quando pergunta sobre alocação de carteira, então a resposta usa como referência a faixa de 70% a 90% em renda fixa.
- Dado um usuário com perfil **Arrojado** configurado, quando pergunta sobre criptoativos, então a resposta usa como referência a faixa de 5% a 15%.
- Dado um usuário fazendo uma pergunta, quando o Consultor responde, então a resposta segue o formato padrão (Resumo, Análise, Riscos, Adequação ao Perfil, Conclusão, Disclaimer).
- Dado uma pergunta que solicite recomendação personalizada sem dados suficientes, quando processada, então o Consultor recusa a recomendação e explica o que falta para uma análise adequada.
- Dado uma resposta do Consultor, quando ela cita dados de mercado, então informa se os dados são atuais ou desatualizados.
- Dado uma resposta do Consultor, quando ela menciona riscos, então classifica o nível de risco como Baixo, Médio ou Alto.
- Dado um usuário autenticado, quando faz várias perguntas, então o sistema mantém o histórico da conversa acessível pelo mesmo módulo.
- Dado um usuário autenticado, quando solicita exclusão do histórico, então o sistema remove as mensagens associadas ao seu `user_id`.
- Dado uma requisição sem sessão válida, quando tenta acessar qualquer rota do Consultor, então o sistema retorna erro de autenticação.
- Dado uma requisição com `Host`/`Origin` inválidos, quando tenta acessar qualquer rota do Consultor, então o sistema retorna erro de segurança sem expor dados.

## Pendências

> [!question] Pendências
> Decisões em aberto que devem ser resolvidas antes da implementação.

- [ ] Definir qual provedor de IA será utilizado (OpenAI, Groq, modelo local ou outro) e se haverá fallback offline.
- [ ] Definir se o histórico de conversas será persistido no SQLite ou mantido apenas em memória/sessão.
- [ ] Definir se o Consultor terá acesso aos dados financeiros do usuário (carteira, lançamentos, score) para respostas contextualizadas.
- [ ] Definir limites de uso (mensagens por dia, tamanho máximo de pergunta/resposta, timeout).
- [ ] Definir se haverá integração com cotações em tempo real e qual fonte será usada.
- [ ] Definir se a ativação exige aceite explícito do disclaimer ou se basta a exibição ao final de cada resposta.
- [ ] Definir se o Consultor será uma view independente ou integrado a outro módulo existente (ex.: dentro de Instruções ou Cockpit).

## Fora de escopo

- Execução de ordens de compra/venda de ativos.
- Acesso a contas bancárias ou corretoras externas.
- Geração de relatórios fiscais ou declaração de IR automatizada.
- Consultoria humanizada personalizada com dados sensíveis do usuário sem consentimento explícito.
- Integração com APIs de notícias financeiras no primeiro MVP.
- Modo conversacional por voz no primeiro MVP.

## Plano de implementação

- [ ] Passo 1 — Adicionar configurações do Consultor em Preferências (`investor_profile`, `consultor_enabled`). Fecha: critérios 1 e 2.
- [ ] Passo 2 — Criar módulo Python `financeiro/consultor.py` com a persona, regras de resposta, limitações e formatador de saída. Fecha: critérios 3, 4, 5, 6, 7 e 8.
- [ ] Passo 3 — Criar rotas `GET/POST /api/consultor/config`, `POST /api/consultor/ask`, `GET/DELETE /api/consultor/history` em `app.py`, autenticadas e validadas contra `Host`/`Origin`. Fecha: critérios 1, 2, 9, 10, 11 e 12.
- [ ] Passo 4 — Criar tabela(s) SQLite de forma idempotente em `financeiro/database.py` para configuração e histórico do Consultor. Fecha: critérios 9 e 10.
- [ ] Passo 5 — Criar view do Consultor em `web/modules/` seguindo o contrato de fábrica e integrar navegação em `web/app.js`. Fecha: critérios 1, 2 e 9.
- [ ] Passo 6 — Criar testes automatizados para persona, perfis de investidor, limitações, formato de resposta e segurança das rotas. Fecha: critérios 3, 4, 5, 6, 7, 8, 11 e 12.
- [ ] Passo 7 — Atualizar `docs/arquitetura.md`, `docs/requisitos.md` e `docs/README.md` para refletir o novo módulo, rotas e tabelas. Fecha: critérios 1 e 11.

## Changelog

- `0.1` — 2026-08-06 — Spec inicial em rascunho para o módulo **Consultor Virtual**, documentando persona, especializações, perfis de investidor, diretrizes de resposta, limitações e API proposta.

## Relacionados

- [[instrucoes-app]]
- [[investimentos-portfolio]]
- [[score-saude-financeira]]
- [[tendencias-saude-financeira]]
