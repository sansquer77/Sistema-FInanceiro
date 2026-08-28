---
tipo: produto
area: meta
status: implementado
versao: 11.56
atualizado: 2026-08-28
tags: [meta, moc]
aliases: ["Home", "Índice", "Map of Content"]
---

# Sistema Financeiro — Documentação

> [!info] Como usar este vault
> Abra esta pasta no **Obsidian** para navegação por wikilinks, grafo de dependências e painel de tags. Funciona igualmente como markdown puro em qualquer IDE ou agente de IA. O processo de desenvolvimento está em [[sdd]].

Este é o **Map of Content (MoC)** do vault. Cada link leva ao documento canônico da área. Antes de alterar qualquer parte do app, localize a spec correspondente aqui e siga o fluxo descrito em [[sdd]].

---

## Documentos estruturais

| Documento | Descrição |
|---|---|
| [[sdd]] | Metodologia SDD: como criar e manter specs, ciclo de vida, convenções do vault. |
| [[requisitos]] | Escopo funcional completo, regras de negócio e requisitos não funcionais. |
| [[arquitetura]] | Camadas, rotas da API, tabelas, módulos Python e fluxos principais. |
| [[visao-produto]] | Direção de produto, princípios de experiência e estado atual dos módulos. |
| [[roadmap]] | Sequência de evolução, status por módulo e próximas prioridades. |
| [[glossario]] | Vocabulário de domínio com links para as specs onde cada conceito é definido. |
| [[distribuição]] | Regras de geração, limpeza, instalação e validação dos pacotes macOS e Windows. |
| [[templates/spec-template]] | Template obrigatório para criar novos documentos. |

---

## Specs por módulo

| Spec | Status | Área |
|---|---|---|
| [[specs/contas-correntes]] | ✅ implementado | Contas |
| [[specs/lancamentos]] | ✅ implementado | Lançamentos |
| [[specs/categorias-tags-gestao]] | ✅ implementado | Classificação |
| [[specs/cartoes]] | ✅ implementado | Cartões |
| [[specs/limites-gastos]] | ✅ implementado | Limites |
| [[specs/classificacao-assistida]] | ✅ implementado | Classificação |
| [[specs/investimentos-portfolio]] | ✅ implementado | Investimentos |
| [[specs/relatorios]] | ✅ implementado | Relatórios |
| [[specs/importacao-dados]] | ✅ implementado | Importação |
| [[specs/historico-operacoes]] | ✅ implementado | Auditoria |
| [[specs/recuperacao-senha]] | ✅ implementado | Segurança |
| [[specs/seguranca-autenticacao]] | ✅ implementado | Segurança |
| [[specs/sobre-app]] | ✅ implementado | Usuário |
| [[specs/instrucoes-app]] | ✅ implementado | Usuário |
| [[specs/preferencias-abas]] | ✅ implementado | Usuário |
| [[specs/frontend-modularizacao]] | ✅ implementado | Frontend |
| [[specs/tendencias-saude-financeira]] | ✅ implementado | Diagnóstico |
| [[specs/score-saude-financeira]] | ✅ implementado | Diagnóstico |
| [[specs/consultor]] | ✅ implementado | Consultor |
| [[specs/privacidade-valores]] | ✅ implementado | Privacidade |
| [[specs/alerta-nova-versao]] | ✅ implementado | Atualização |
| [[specs/rentabilidade-portfolio]] | ✅ implementado | Investimentos |
| [[specs/efeito-borboleta]] | ✅ implementado | Simulações |
| [[specs/cockpit-calendario]] | ✅ implementado | Cockpit |
| [[specs/Update Server]] | ✅ implementado | Distribuição |
| [[distribuição]] | ✅ implementado | Distribuição |
| [[specs/landing-page]] | ✅ implementado | Institucional |

---

## Specs em outros status

> Specs `rascunho`, `em-implementacao` ou `depreciado` ficam na mesma pasta `specs/` das demais — o status é sempre o campo `status` do frontmatter (e a tag `status/<valor>`), nunca a localização do arquivo. Use o painel de tags do Obsidian para filtrar por status sem depender desta tabela.

| Spec | Status | Área |
|---|---|---|
| [[specs/open-finance]] | 📝 rascunho | Open Finance |
| [[specs/consolidacao-familiar]] | 📝 rascunho | Consolidação Familiar |
| [[specs/imposto-renda]] | ❌ depreciado — custo de manter regras fiscais atualizadas não compensa para uso familiar | Investimentos |
| [[specs/exportacao-dados]] | ❌ depreciado — arquivo SQLite já acessível por leitor genérico ou agente de IA | Exportação |

---

## ADRs — Decisões técnicas

| ADR | Decisão |
|---|---|
| [[adr/0001-stack-local-sem-framework]] | Servidor HTTP puro em Python, sem framework web. |
| [[adr/0002-modularizacao-frontend]] | ES Modules nativos sem build step. |
| [[adr/0003-sqlite-fonte-de-verdade]] | SQLite local como única fonte de verdade. |
| [[adr/0004-importador-xls-sem-dependencia]] | Parser `.xls` implementado sem biblioteca externa. |
| [[adr/0005-smtp-criptografado-local]] | Configuração SMTP criptografada em arquivo local. |
| [[adr/0006-classificacao-assistida-local]] | Proposta de classificação assistida por hábitos locais, com IA externa apenas como fallback opcional. |
| [[adr/0007-landing-page-institucional-isolada]] | Landing Page institucional em repositório separado, deployável pela Vercel fora da distribuição do app. |
| [[adr/0008-licenca-apache-2-0]] | App principal disponibilizado gratuitamente como projeto open source sob Apache License 2.0. |
| [[adr/0009-mais-retorno-cotas-opt-in]] | Cotas de fundos via API Mais Retorno em integração opt-in. |
| [[adr/0010-segredos-criptografados-sqlite]] | Segredos de SMTP, IA e integrações em SQLite criptografado, com chave fora de `data/`. |
| [[adr/0011-criptografia-snapshots-familiares]] | Rascunho da criptografia transportável dos snapshots familiares com `cryptography`, `scrypt` e `AES-256-GCM`. |

---

## Design

| Documento | Descrição |
|---|---|
| [[design/design-system]] | Tokens visuais, paleta, tipografia, espaçamento, bordas e componentes. |

---

## Regra prática para qualquer mudança

```
1. Localize ou crie a spec/documento usando [[templates/spec-template]]
2. Atualize requisitos se o escopo geral mudar  →  [[requisitos]]
3. Atualize arquitetura se houver nova rota, tabela ou fluxo  →  [[arquitetura]]
4. Se houver decisão técnica não trivial, registre um ADR em adr/
5. Implemente a menor mudança que cumpre a spec
6. Atualize status, versao, atualizado e Changelog da spec
7. Mantenha o código simples e passivel de manutenção e entendimento humano
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Servidor | Python 3 (biblioteca padrão, sem framework) |
| Banco | SQLite em `data/finance.db` |
| Frontend | HTML + CSS + JavaScript (ES Modules nativos, sem build) |
| Distribuição | Pacotes macOS e Windows offline-first, com modo local padrão e modo LAN explícito |

## Licença

O Sistema Financeiro é disponibilizado gratuitamente como projeto open source sob a **Apache License 2.0** (`Apache-2.0`). Consulte o arquivo [`LICENSE`](../LICENSE) na raiz do repositório.

## Changelog

- `11.56` — 2026-08-28 — Auditoria código/documentação: rotas `GET` exatas, testes de contratos do frontend, timestamps UTC sem API depreciada, inventários arquiteturais e referências código↔spec sincronizados; entradas históricas duplicadas deste changelog foram consolidadas sem perda de conteúdo.
- `11.55` — 2026-08-28 — [[adr/0011-criptografia-snapshots-familiares]] v0.4 fixa `scrypt n=2^17, r=8, p=1` para o envelope v1 e registra os alvos iniciais de validação macOS Apple Silicon e Windows x86-64 com 8 GB/i5 ou equivalente.
- `11.54` — 2026-08-28 — [[specs/consolidacao-familiar]] v0.6 fecha o MVP funcional (`.sffamily` até 1 MB, Portfólio por classe, Score parcial com cobertura, limites recorrentes/aliases, snapshots arquiváveis e mensagens educativas); [[adr/0011-criptografia-snapshots-familiares]] v0.3 concentra as validações técnicas restantes.
- `11.53` — 2026-08-28 — [[specs/consolidacao-familiar]] v0.5: consolidador inclui ou atualiza seus próprios dados sob demanda usando o snapshot analítico canônico, com persistência direta no SQLite, confirmação de substituição e sem arquivo ou senha.
- `11.52` — 2026-08-28 — [[specs/consolidacao-familiar]] v0.4 e [[adr/0011-criptografia-snapshots-familiares]] v0.2 definem senha por arquivo com 8 a 128 caracteres, ao menos uma maiúscula e um número, confirmação obrigatória, troca livre para arquivos futuros e ausência de revogação sobre cópias já distribuídas.
- `11.51` — 2026-08-28 — [[specs/consolidacao-familiar]] v0.3 define `cryptography`, `scrypt`, `AES-256-GCM` e senha somente em memória; criado o rascunho [[adr/0011-criptografia-snapshots-familiares]] v0.1 com gates de PyInstaller e interoperabilidade macOS/Windows/Linux.
- `11.50` — 2026-08-28 — [[specs/consolidacao-familiar]] v0.2: snapshots importados serão persistidos em colunas analíticas normais no SQLite; a senha familiar protege o transporte e a validação ocorre em memória antes da escrita.
- `11.49` — 2026-08-28 — Criado o rascunho [[specs/consolidacao-familiar]] v0.1: snapshots mensais criptografados entre instalações, persistência isolada, cobertura por integrante, evolução histórica e Score Familiar recalculado pelos cinco pilares.
- `11.48` — 2026-08-28 — [[specs/relatorios]] v2.16: agrupamento e evolução de subcategorias corrigidos; linhas sem subcategoria preservam filtro nulo, faturas usam a competência e a série combina valores normalizados em BRL. A spec temporária da investigação foi consolidada na spec canônica.
- `11.47` — 2026-08-23 — [[specs/relatorios]] v2.13: relatório de Tags reformulado com nova rota `GET /api/reports/tags` e tabela por tag mostrando Receitas, Despesas, Saldo e Investimentos; backend centralizado em `financeiro/reports.py`. [[arquitetura]] v3.39 sincronizada.
- `11.46` — 2026-08-23 — [[specs/efeito-borboleta]] v1.3: módulo Efeito Borboleta ganha tabela de projeção semanal abaixo do gráfico, com saldo atual + 8 semanas e linhas Previsto, Simulado e Diferença; [[arquitetura]] v3.38 sincronizada.
- `11.45` — 2026-08-22 — Documentação de produto e ajuda sincronizada ao novo fluxo do Consultor: [[requisitos]] v2.5 e [[specs/instrucoes-app]] v1.9 registram seletor fechado de análises e botão **Gerar**.
- `11.44` — 2026-08-22 — [[specs/consultor]] v1.6: grade de cards substituída por seletor fechado de análises e botão único **Gerar**; período condicional de ralos fica ao lado e resposta passa a usar largura integral abaixo dos controles. [[arquitetura]] v3.36 sincronizada.
- `11.43` — 2026-08-22 — [[specs/rentabilidade-portfolio]] v1.7 e [[specs/investimentos-portfolio]] v2.31: flyover de rentabilidade ampliado para aproximadamente metade da viewport em desktop e gráfico SVG refinado, sem dependências externas.
- `11.42` — 2026-08-20 — [[specs/lancamentos]] v3.24 e [[specs/cartoes]] v2.15: modal de escopo de série recorrente com média ativa passa a explicar que editar somente a ocorrência atual não recalcula os próximos, enquanto aplicar aos próximos recalcula pela média.
- `11.41` — 2026-08-20 — Auditoria documental: [[arquitetura]] v3.35 passa a registrar a rota e o módulo do [[specs/efeito-borboleta]]; callouts de status sincronizados em [[specs/investimentos-portfolio]] v2.30, [[specs/relatorios]] v2.11 e [[specs/sobre-app]] v1.9.
- `11.40` — 2026-08-17 — [[specs/lancamentos]] v3.23 e [[specs/cartoes]] v2.14: modal de escopo de edição restaurado em séries recorrentes — o modal `Apenas este lançamento` / `Este e os próximos` volta a aparecer quando a flag de média **não** é alterada (ativa ou inativa); apenas a mudança da flag (marcar em série sem marcação ou desmarcar em série marcada) continua pulando o modal e aplicando a cascata automaticamente.
- `11.39` — 2026-08-17 — [[specs/cartoes]] v2.13: linha de referência da média no gráfico de evolução de faturas passa a usar o token `--chart-average-line` (cinza no tema claro, branca no escuro) e exibe o valor da média formatado na moeda do cartão em texto compacto ao final (lado direito) da linha. [[design/design-system]] ganha a regra do token para linhas de referência neutras.
- `11.38` — 2026-08-17 — [[specs/cartoes]] v2.12: gráfico de evolução de faturas ganha linha horizontal de referência com a média aritmética dos valores absolutos das 5 faturas em tela (2 anteriores, atual e 2 futuras), no mesmo estilo das linhas atuais (contínua, branca) e na mesma escala vertical.
- `11.37` — 2026-08-17 — [[specs/lancamentos]] v3.22 e [[specs/cartoes]] v2.11: ao editar um lançamento recorrente, o checkbox de cálculo dos próximos pela média fica habilitado — ativando a flag, a edição aplica em cascata às ocorrências futuras não conciliadas (sem modal) persistindo a marcação e recalculando valores pela média; desmarcando em série que tinha a flag, a cascata segue sem recálculo e a marcação é removida no escopo.
- `11.36` — 2026-08-16 — [[specs/consultor]] v1.5: prompt do card **Análise da Carteira** orienta completude dentro do teto de 900 tokens de saída (encerrar todas as seções, encurtando justificativas se preciso), corrigindo truncamento que bloqueava a análise com "indisponível"; [[arquitetura]] v3.34 sincronizada.
- `11.35` — 2026-08-15 — [[specs/consultor]] v1.4: correções no pós-processamento de cabeçalhos e recomendações; [[specs/frontend-modularizacao]] v2.8: modo ícones da sidebar compactado para manter todos os itens visíveis sem rolagem.
- `11.34` — 2026-08-15 — Versão do app elevada para `1.5.0` (MINOR), com perfil aplicado a todos os cards do Consultor; [[specs/frontend-modularizacao]] v2.7: grupos colapsáveis e **Cockpit** como item de primeiro nível.
- `11.33` — 2026-08-13 — Versão do app elevada para `1.4.2` (PATCH): [[specs/cartoes]] v2.9 pagamento parcial de fatura (registrada também na spec como v2.10).
- `11.32` — 2026-08-13 — [[specs/cartoes]] v2.9: pagamento parcial de fatura — botões **Pagar fatura integral** / **Pagar parte da fatura** (modal com valor); no parcial, a fatura fecha como hoje e o saldo restante é lançado na próxima fatura aberta como despesa na categoria **Empréstimos**, com descrição `Saldo da fatura MM/AAAA`. [[arquitetura]] atualizada para v3.29.
- `11.31` — 2026-08-11 — Versão do app elevada para `1.4.1` (PATCH): [[specs/tendencias-saude-financeira]] v2.21 passa a sinalizar oportunidade de revisar caixa quando o saldo previsto no fim do mês em contas de liquidez/carteira fica igual ou acima de 2x as despesas planejadas.
- `11.30` — 2026-08-11 — [[specs/lancamentos]] v3.21 e [[specs/investimentos-portfolio]] v2.29: cotações de moeda estrangeira corrigidas — formulário de Lançamentos pré-preenche a PTAX (campo manual visível se indisponível); posição inicial do Portfólio consulta PTAX; sem mais taxa `1,0` silenciosa.
- `11.29` — 2026-08-11 — [[specs/investimentos-portfolio]] v2.28: coluna **Tipo** da aba Posição mostra ícone de escudo para posições de reserva de emergência.
- `11.28` — 2026-08-11 — [[specs/lancamentos]] v3.20 e [[specs/cartoes]] v2.8: escala vertical dos gráficos de histórico de saldos (Extrato) e de evolução de faturas ampliada para a faixa 10–88 do plot (antes 24–48 e 28–74), sem aumentar a área do gráfico.
- `11.27` — 2026-08-11 — [[specs/lancamentos]] v3.19 e [[specs/investimentos-portfolio]] v2.27: helper (?) de modalidade alinhado inline ao rótulo nos dois formulários (correção de layout).
- `11.26` — 2026-08-11 — [[specs/investimentos-portfolio]] atualizada para v2.26: formulário do Portfólio equalizado com Lançamentos — modalidade em combo com helper (?); controles segmentados/chips/presets removidos do app.
- `11.25` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.18: modalidade de renda fixa (Pós/Pré/Híbrida) volta a ser combo ao lado do Indexador com helper (?); CSS de presets/chips removido (sem usos restantes).
- `11.24` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.17: checkboxes de média histórica sem moldura pill (checkbox simples); layout pill de checkboxes descontinuado no app (CSS removido).
- `11.23` — 2026-08-15 — [[specs/consultor]] v1.3 aplica perfil a todos os cards; [[specs/lancamentos]] v3.16 e [[specs/investimentos-portfolio]] v2.25 removem presets de renda fixa e refinam os controles visuais.
- `11.22` — 2026-08-15 — [[specs/consultor]] v1.2 aprofunda a Análise da Carteira; [[specs/lancamentos]] v3.15 e [[specs/investimentos-portfolio]] v2.24 simplificam o bloco visual de renda fixa.
- `11.21` — 2026-08-15 — [[specs/consultor]] v1.1 adiciona Análise da Carteira e amplia o catálogo; [[specs/lancamentos]] v3.14 remove o bloco escurecido de Fundo ou previdência.
- `11.20` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.13: **Valor investido** ocupa a mesma posição do Valor (abaixo da Descrição) no tipo Investimento — mesmo altura do valor em todos os tipos de lançamento.
- `11.19` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.12: campo Valor abaixo da Descrição em posição estável para todos os tipos; blocos escurecidos removidos também de Câmbio, Transferência e do agrupamento geral de Investimento (permanecem apenas Fundos/previdência e Renda fixa).
- `11.18` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.11: formulário de Lançamentos mais largo (até 460px) com espaçamento lateral equilibrado — 16px entre menu e formulário, iguais aos 16px entre formulário e extrato.
- `11.17` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.10: linhas simples do formulário (Valor, Repetição, Recorrência e Média) deixam de usar o bloco contextual escurecido com título em caixa alta — formulário mais denso; blocos permanecem apenas para grupos de múltiplos campos.
- `11.16` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.9: layout de Lançamentos ganha formulário compacto, blocos condicionais por tipo/categoria e lista diária mais limpa.
- `11.15` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.8: gráfico de saldos passa a usar a mesma linguagem visual refinada do gráfico de faturas.
- `11.14` — 2026-08-11 — [[specs/cartoes]] atualizada para v2.7: gráfico de evolução de faturas refinado visualmente com cards compactos e curva SVG nativa.
- `11.13` — 2026-08-11 — [[specs/lancamentos]] atualizada para v3.7: edição de lançamento avulso permite alterar a repetição para parcelado ou recorrente.
- `11.12` — 2026-08-11 — [[specs/tendencias-saude-financeira]] atualizada para v2.21: Tendências passa a sinalizar oportunidade de revisar caixa quando o saldo previsto de fim do mês em contas de liquidez/carteira fica igual ou acima de 2x as despesas planejadas.
- `11.11` — 2026-08-11 — [[specs/alerta-nova-versao]] atualizada para v1.2: validação operacional do alerta de nova versão e fallback TLS com `certifi` para ambientes Python sem bundle de certificados.
- `11.10` — 2026-08-10 — [[specs/sobre-app]] atualizada para v1.8: tela Sobre passa a exibir **Sansquer** como desenvolvedor e `darksansquer@gmail.com` como contato.
- `11.9` — 2026-08-10 — [[specs/investimentos-portfolio]] atualizada para v2.23: formulário de posição inicial do Portfólio exibe o campo CNPJ opcional também para Previdência Privada, alinhado aos Fundos (mesma integração Mais Retorno).
- `11.8` — 2026-08-10 — [[specs/investimentos-portfolio]] atualizada para v2.22: renda fixa e Poupança passam a exibir variação do dia no Portfólio (diferença do valor na curva entre hoje e o dia anterior); [[arquitetura]] v3.28 documenta o cálculo via `day_variation_cents`.
- `11.7` — 2026-08-10 — [[specs/consultor]] atualizada para v1.0 e movida para implementado; Passos 19 e 20 concluídos com homologação registrada e versão do app elevada para `1.4.0`.
- `11.6` — 2026-08-10 — [[specs/consultor]] atualizada para v0.50 com Passo 18 concluído: documentação pós-implementação sincronizada em [[arquitetura]], [[requisitos]], [[instrucoes-app]] e no MoC do vault.
- `11.5` — 2026-08-10 — [[specs/consultor]] atualizada para v0.49 com Passo 17 concluído: mocks e testes automatizados do executor de IA do Consultor.
- `11.4` — 2026-08-10 — [[specs/consultor]] atualizada para v0.48 com Passo 16 concluído: testes automatizados de API do Consultor.
- `11.3` — 2026-08-10 — [[specs/consultor]] atualizada para v0.47 com Passo 15 concluído: testes automatizados de domínio e persistência do Consultor.
- `11.2` — 2026-08-10 — [[specs/consultor]] atualizada para v0.46: desativação do Consultor confirma perda de histórico e sincroniza imediatamente a aba Consultor.
- `11.1` — 2026-08-10 — [[specs/consultor]] atualizada para v0.45: subtab Análises usa catálogo compacto à esquerda, resposta à direita e tipografia mais enxuta em telas largas.
- `11.0` — 2026-08-10 — [[specs/consultor]] atualizada para v0.44: timeout mínimo operacional de 20s no executor para reduzir indisponibilidade prematura em cards mais lentos.
- `10.9` — 2026-08-10 — [[specs/consultor]] atualizada para v0.43: removida a inserção automática de risco normalizado e endurecido o prompt para a IA classificar risco explicitamente.
- `10.8` — 2026-08-10 — [[specs/consultor]] atualizada para v0.42: payload de Portfólio do Consultor explicita centavos e inclui valores em reais formatados para reduzir erro de interpretação pela IA.
- `10.7` — 2026-08-10 — [[specs/consultor]] atualizada para v0.41: histórico de análises em subtab própria do Consultor, com filtro textual.
- `10.6` — 2026-08-10 — [[specs/consultor]] atualizada para v0.40 removendo o card "Teste de Estresse da Reserva de Emergência", já coberto pela aba Saúde Financeira.
- `10.5` — 2026-08-10 — [[specs/consultor]] atualizada para v0.39: prompt mais conciso e pós-processamento completa o disclaimer obrigatório quando só a seção final vier ausente/alterada.
- `10.4` — 2026-08-10 — [[specs/consultor]] atualizada para v0.38: pós-processamento aceita títulos com bullets e normaliza nível de risco descrito em linguagem natural.
- `10.3` — 2026-08-10 — [[specs/consultor]] atualizada para v0.37 corrigindo também a compatibilidade do card de Ralos Financeiros com o formato atual de `antecipacao_parcelas` em Tendências.
- `10.2` — 2026-08-10 — [[specs/consultor]] atualizada para v0.36 corrigindo a compatibilidade do card de Assinaturas e Recorrências com o formato atual de `assinaturas_e_servicos` em Tendências.
- `10.1` — 2026-08-10 — [[specs/consultor]] atualizada para v0.35 com ajuste fino de UX na aba Consultor: espaçamento entre calendário/status/catálogo e botões de cards em escala compacta.
- `10.0` — 2026-08-10 — [[specs/consultor]] atualizada para v0.34: Preferências deixa claro que a IA habilita o Consultor e bloqueia os controles do Consultor quando a IA geral está desligada.
- `9.9` — 2026-08-10 — [[specs/consultor]] atualizada para v0.33 com Passo 14 concluído; [[arquitetura]] v3.26 documenta a UI da aba Consultor no Cockpit.
- `9.8` — 2026-08-10 — [[specs/consultor]] atualizada para v0.32 com Passo 13 concluído; [[arquitetura]] v3.25 documenta Preferências do Consultor.
- `9.7` — 2026-08-10 — [[specs/consultor]] atualizada para v0.31 com Passo 12 concluído; [[arquitetura]] v3.24 documenta as rotas autenticadas do Consultor.
- `9.6` — 2026-08-10 — [[specs/consultor]] atualizada para v0.30 com Passo 11 concluído; [[arquitetura]] v3.23 documenta quota diária, cooldown e persistência apenas de execuções bem-sucedidas.
- `9.5` — 2026-08-10 — [[specs/consultor]] atualizada para v0.29 com Passo 10 concluído; [[arquitetura]] v3.22 documenta o pós-processamento de respostas do Consultor.
- `9.4` — 2026-08-10 — [[specs/consultor]] atualizada para v0.28 com Passo 9 concluído; [[arquitetura]] v3.21 documenta o executor de IA reutilizando `user_ai_settings`.
- `9.3` — 2026-08-10 — [[specs/consultor]] atualizada para v0.27 com Passo 8 concluído; [[arquitetura]] v3.20 documenta metadados de cotações herdados do Portfólio.
- `9.2` — 2026-08-10 — [[specs/consultor]] atualizada para v0.26 com Passo 7 concluído; [[arquitetura]] v3.19 documenta contexto minimizado por card.
- `9.1` — 2026-08-10 — [[specs/consultor]] atualizada para v0.25 com Passo 6 concluído; [[arquitetura]] v3.18 documenta Perfil Complementar criptografado por usuário.
- `9.0` — 2026-08-10 — [[specs/consultor]] atualizada para v0.24 com Passo 5 concluído; [[arquitetura]] v3.17 documenta configuração por usuário e expurgo de histórico no domínio do Consultor.
- `8.9` — 2026-08-10 — [[specs/consultor]] atualizada para v0.23 com Passo 4 concluído; [[arquitetura]] v3.16 documenta `financeiro/consultor.py`.
- `8.8` — 2026-08-10 — [[specs/consultor]] atualizada para v0.22 com Passo 3 concluído: helpers reutilizáveis de envelope JSON criptografado em memória para o Perfil Complementar.
- `8.7` — 2026-08-10 — [[specs/consultor]] atualizada para v0.21 com Passo 2 concluído; [[arquitetura]] v3.15 documenta as tabelas futuras do Consultor.
- `8.6` — 2026-08-10 — [[specs/consultor]] atualizada para v0.20 com Passo 1 concluído; [[requisitos]] v2.3 alinha regras de segurança ao [[adr/0010-segredos-criptografados-sqlite]].
- `8.5` — 2026-08-10 — [[specs/consultor]] atualizada para v0.19, ainda em rascunho, com plano de implementação transformado em passos executáveis antes do início do código.
- `8.4` — 2026-08-10 — [[specs/tendencias-saude-financeira]] v2.20 documenta indicador de fonte no card **Despesas** da aba Tendências.
- `8.3` — 2026-08-10 — [[specs/investimentos-portfolio]] v2.21 documenta resgates de Poupança consumindo aniversários por FIFO e resgate total removendo a posição aberta.
- `8.2` — 2026-08-10 — [[specs/lancamentos]] v3.6 e [[specs/investimentos-portfolio]] v2.20 ampliam o uso de CNPJ/Mais Retorno para Previdência Privada.
- `8.1` — 2026-08-10 — [[specs/lancamentos]] v3.5, [[specs/investimentos-portfolio]] v2.19 e [[arquitetura]] v3.14 documentam busca assistida de cota de fundos por CNPJ via Mais Retorno no formulário de Lançamentos.
- `8.0` — 2026-08-10 — [[specs/instrucoes-app]] atualizada para v1.7: instruções de Investimento/Aporte e Portfólio passam a detalhar fundos, cotas, preço unitário/preço médio, CNPJ e Mais Retorno.
- `7.9` — 2026-08-09 — [[specs/tendencias-saude-financeira]] atualizada para v2.19: IA passa a gerar síntese executiva integrada em 2 a 4 frases com contexto operacional agregado.
- `7.8` — 2026-08-09 — [[specs/tendencias-saude-financeira]] atualizada para v2.18: resumo local/IA deixa de repetir limites, eventos pontuais e antecipações que já aparecem como cards.
- `7.7` — 2026-08-09 — [[specs/landing-page]] atualizada para v2.1 com destaque público do Portfólio conectado a Yahoo Finance, CoinGecko, BACEN/SGS e Mais Retorno opcional.
- `7.6` — 2026-08-09 — [[specs/landing-page]] atualizada para v2.0 com nova vitrine de screenshots demonstrativos: APIs, Consultor, Tendências, Análise do Portfólio e Demonstrativos.
- `7.5` — 2026-08-09 — Fechamento dos ajustes leves de performance: removido log de debug no Portfólio, Tendências filtra por intervalo indexável, histórico do Portfólio ganha índice compatível, BMC carrega assíncrono, dashboard não anima grid estrutural e Modo Privacidade troca blur massivo por máscara textual leve.
- `7.4` — 2026-08-09 — Performance média do Portfólio/HTTP: abas do Portfólio e rentabilidade sob demanda, agrupamento renderiza só posições, cache de cotações/câmbio limitado, `ETag`/`Last-Modified` para estáticos e gzip para JSON grande.
- `7.3` — 2026-08-09 — Ajustes de performance documentados: Cockpit reaproveita snapshot em memória, histórico do Score reutiliza uma fotografia do Portfólio e cotações do Portfólio passam a paralelizar posições independentes.
- `7.2` — 2026-08-09 — Adicionado [[adr/0010-segredos-criptografados-sqlite]] e atualizada [[specs/preferencias-abas]] para v0.8 com segredos criptografados em `secure_configs` e migração compatível de arquivos legados.
- `7.1` — 2026-08-09 — [[specs/consultor]] atualizada para v0.18, ainda em rascunho, com ajustes pré-implementação sobre disponibilidade IA/Consultor/consentimento, 4 categorias e Perfil Complementar criptografado em SQLite por usuário.
- `7.0` — 2026-08-09 — [[specs/rentabilidade-portfolio]] atualizada para v1.5 com refinamento visual do gráfico de rentabilidade: linhas mais finas e pontos discretos.
- `6.9` — 2026-08-09 — [[specs/cockpit-calendario]] promovida para specs implementadas no MoC, alinhada à spec v0.8.
- `6.8` — 2026-08-09 — [[specs/efeito-borboleta]] promovida para specs implementadas no MoC, alinhada à spec v1.2.
- `6.7` — 2026-08-09 — MoC sincronizado com os arquivos de specs atuais: adicionadas as specs implementadas de Histórico de Operações, Preferências, Alerta de Nova Versão, Rentabilidade do Portfólio e Update Server; adicionada [[specs/efeito-borboleta]] em rascunho; [[specs/open-finance]] alinhada ao diretório `docs/specs/`.
- `6.6` — 2026-08-07 — [[specs/score-saude-financeira]] atualizada (v3.5): lançamentos de cartão passam a entrar no Score via `amount_brl_cents` (BRL normalizado) em todas as somas (resumo mensal, contexto de dívida e aderência a limites), alinhando com [[specs/tendencias-saude-financeira]] e a regra de normalização de moedas para cartões estrangeiros; teste de regressão adicionado.
- `6.5` — 2026-08-07 — Aba **Saúde Financeira** do Cockpit extraída para módulo próprio `web/modules/financial-health-view.js` (fábrica `registerFinancialHealthView`), seguindo o padrão de `trends-view.js`/`consultor-view.js`; estado de tela local migra para o módulo e `invalidateFinancialHealth` é delegado pelo `cockpit-view.js`. [[specs/score-saude-financeira]] em v3.4, [[specs/frontend-modularizacao]] em v2.3 e [[arquitetura]] atualizada.
- `6.4` — 2026-08-07 — [[specs/consultor]] atualizada (v0.12): adicionada a **blindagem de prompt injection** — `system_prompt` imutável com prioridade absoluta, esteira de neutralização lexical (`financeiro/consultor_injection.py`) tratando o input como dados, sinalização `injection_triggered` e pós-processamento que bloqueia recomendações de compra/venda na saída. Permanece em rascunho.
- `6.3` — 2026-08-07 — [[specs/consultor]] atualizada (v0.11): adicionada a camada **DLP (prevenção de vazamento de dados no prompt)** — esteira local de sanitização em `financeiro/consultor_dlp.py` com RegEx, dígitos verificadores de CPF, Luhn para cartões (evita falsos positivos), padrões de conta bancária e NER de nomes; ofuscação do payload com tags, retorno `dlp_triggered`, banner de alerta e reflexo no histórico (dado original nunca enviado, renderizado nem persistido). Permanece em rascunho.
- `6.2` — 2026-08-07 — [[specs/consultor]] atualizada (v0.10): adicionada a seção **Indisponibilidade e resiliência** — falhas da API externa exibem a mensagem padronizada "O Consultor está indisponível no momento", sem vazar detalhes; a pergunta que falhou não é persistida nem desconta da quota diária de 20 mensagens; cooldown de reenvio de 30s, com histórico preservado e auto-recuperação sem reenvio retroativo. Permanece em rascunho.
- `6.1` — 2026-08-07 — [[specs/consultor]] atualizada (v0.9): adicionada regra de **expurgo automático do histórico** — desabilitar a IA nas Preferências (revogação do consentimento) purga automaticamente todo o histórico de conversas (`consultor_messages`); ao reabilitar, o Consultor reinicia com histórico vazio. Permanece em rascunho.
- `6.0` — 2026-08-07 — [[specs/consultor]] atualizada (v0.8): pendência de versionamento do Perfil Complementar resolvida — `renda_mensal_aproximada` e `tolerancia_perdas` entram na v1; versionamento aditivo (append) e respostas sempre consideram o cenário atual cadastrado (histórico não é revisado com o cenário antigo). **Pendências todas resolvidas.** Permanece em rascunho.
- `5.9` — 2026-08-07 — [[specs/consultor]] atualizada (v0.7): pendência de limites de uso resolvida — pergunta máx. 600 caracteres, resposta limitada ao `max_tokens` das Preferências ou 900, contexto de histórico restrito às últimas 6 mensagens, contexto de dados minimizado e quota diária de 20 mensagens/usuário/dia (reset por data). Permanece em rascunho.
- `5.8` — 2026-08-07 — [[specs/consultor]] atualizada (v0.6): pendência do disclaimer resolvida — a exibição do disclaimer educacional ao final de cada resposta é suficiente, sem aceite explícito na ativação; o aceite do uso dos dados (`data_access_consent`) permanece obrigatório; removido o campo `disclaimer_accepted`. Permanece em rascunho.
- `5.7` — 2026-08-07 — [[specs/consultor]] atualizada (v0.5): resolvidas as pendências de provedor (reuso da config de IA das Preferências), histórico (persistido em SQLite, uma linha por mensagem em `consultor_messages`), acesso a dados (mediante pop-up de consentimento `data_access_consent`; recusa desabilita), cotações (mesmas fontes do Portfólio: Yahoo Finance, CoinGecko, PTAX, via `quote_cache`) e criptografia do Perfil Complementar (reaproveita `secure_config.py`); exemplos de uso substituídos pelas 3 sugestões transversais. Permanece em rascunho.
- `5.6` — 2026-08-07 — [[specs/cockpit-calendario]] atualizada (v0.6): novo subtítulo "Apoio no acompanhamento das suas contas" e, com `ia_ativa` verdadeiro, indicador de IA idêntico ao da aba **Tendências**; explicitado que o clique em item navega ao lançamento sem abrir o formulário de edição.
- `5.5` — 2026-08-07 — [[specs/consultor]] atualizada (v0.2): a aba **Consultor** do Cockpit passa a ser o único ponto de entrada — removido o ícone de cartola flutuante/pop-up acionável de qualquer tela — e, com a IA habilitada, a aba centraliza o campo de prompt. Permanece em rascunho.
- `5.4` — 2026-08-06 — Adicionada [[specs/open-finance]] em rascunho para conexão de contas via Conector 200/Meu Pluggy (Pluggy), com credenciais opt-in por usuário, sincronização manual e vínculo sempre manual a contas correntes; spec ainda contraria o escopo atual de [[requisitos]] e depende de resolução das pendências antes de implementação.
- `5.3` — 2026-08-06 — [[specs/consultor]] atualizada (v0.2): reutiliza configuração de IA existente (`user_ai_settings`), interface definida como pop-up acionável de qualquer tela e histórico persistido em arquivo criptografado no `DATA_DIR`.
- `5.2` — 2026-08-06 — Adicionada [[specs/consultor]] em rascunho para o módulo **Consultor Virtual** de investimentos e planejamento financeiro.
- `5.1` — 2026-08-06 — Reorganização do Map of Content: [[specs/instrucoes-app]], [[specs/landing-page]] e [[specs/score-saude-financeira]] movidas para a seção de specs implementadas; [[specs/cockpit-calendario]] permanece em `em-implementacao` na seção de specs em outros status.
- `5.0` — 2026-08-04 — Adicionada [[specs/cockpit-calendario]] em rascunho para a nova aba **Calendário** do Cockpit; especificação não implementa código, apenas documenta a aba, regras, API e plano de implementação.
- `4.9` — 2026-08-04 — [[specs/instrucoes-app]] atualizada com decisões sobre links internos, botões contextuais `?` e cobertura de todos os módulos operacionais.
- `4.8` — 2026-08-04 — Adicionada [[specs/instrucoes-app]] em rascunho para orientar o futuro módulo **Instruções** no menu Usuário.
- `4.7` — 2026-08-04 — [[specs/landing-page]] atualizada com orientação didática da seção “Como começar”, especialmente para o fluxo de Portfólio e ativos.
- `4.6` — 2026-08-04 — [[specs/landing-page]] atualizada para remover o link textual separado de notas da versão na seção de downloads.
- `4.5` — 2026-08-04 — [[specs/landing-page]] atualizada para incluir Linux e símbolos de sistema operacional nos botões de download.
- `4.4` — 2026-08-04 — [[specs/landing-page]] atualizada com downloads oficiais via última GitHub Release, cache server-side de 1h e botões Windows/macOS.
- `4.3` — 2026-08-04 — [[specs/landing-page]] atualizada para exibir Apache 2.0 na landing e contribuição voluntária via Buy Me a Coffee sem condicionar o uso gratuito.
- `4.2` — 2026-08-04 — [[specs/landing-page]] atualizada para remover PIX/cobrança e documentar download gratuito via GitHub Releases com contato apenas para sugestões/relatos.
- `4.1` — 2026-08-04 — Adicionado [[adr/0008-licenca-apache-2-0]] para registrar a adoção da Apache License 2.0 e distribuição gratuita sem suporte formal.
- `4.0` — 2026-08-03 — [[specs/landing-page]] avançou para v1.0 com regra de animação/alinhamento da árvore visual no repositório separado da landing.
- `3.9` — 2026-08-03 — [[specs/landing-page]] atualizada com seção pública de uso em família/rede local confiável.
- `3.8` — 2026-08-03 — [[specs/landing-page]] atualizada para preservar a árvore visual como metáfora de evolução financeira e evitar linguagem interna de homologação/massa fictícia na copy pública.
- `3.7` — 2026-08-03 — Registrada a remoção do diretório legado `landing-page/` do repositório principal e atualizada a regra de distribuição para a Landing Page em repositório separado.
- `3.6` — 2026-08-03 — [[adr/0007-landing-page-institucional-isolada]] e [[specs/landing-page]] atualizadas para registrar que a landing page passa a viver no repositório próprio `sistemafinanceiropage`.
- `3.5` — 2026-08-03 — [[specs/landing-page]] avançou para `em-implementacao` com adaptação inicial do template v0.app, screenshots demonstrativos e CTA manual por PIX/e-mail.
- `3.4` — 2026-08-02 — Adicionado [[adr/0007-landing-page-institucional-isolada]] para registrar a Landing Page como subprojeto independente com stack própria em `landing-page/`.
- `3.3` — 2026-08-02 — Adicionada [[specs/privacidade-valores]] como spec implementada do Modo Privacidade.
- `3.2` — 2026-08-02 — [[specs/tendencias-saude-financeira]] marcada como implementada após conclusão da reescrita opcional por IA, fallback local e testes automatizados.
- `3.1` — 2026-08-02 — [[specs/tendencias-saude-financeira]] avançou para `em-implementacao` com passo 3 concluído: núcleo local de tendências.
- `3.0` — 2026-07-31 — Adicionada [[specs/tendencias-saude-financeira]] em status `rascunho` para discutir tendências, achados e uso opcional de IA na Saúde Financeira.
- `2.9` — 2026-07-27 — Adicionada [[specs/score-saude-financeira]] em status `em-implementacao`.
- `2.8` — 2026-07-27 — Adicionada [[specs/exportacao-dados]] (depreciada) à seção "Specs em outros status".
- `2.7` — 2026-07-27 — Adicionada seção "Specs em outros status" para dar visibilidade a specs fora de `implementado` (ex.: `depreciado`) sem criar pasta separada por status — reforça que o status vive no frontmatter/tag, não na localização do arquivo.
- `2.6` — 2026-07-24 — Incluída a spec da tela Sobre no grupo Usuário.
- `2.5` — 2026-07-23 — MVP de classificação assistida concluído e documentação marcada como implementada.
- `2.4` — 2026-07-23 — MVP de classificação assistida aprovado e movido para implementação; ADR-0006 adotado.
- `2.3` — 2026-07-23 — Incluídos a spec e o ADR em rascunho para classificação assistida por hábitos locais.
- `2.2` — 2026-07-04 — Índice inclui a spec de distribuição, stack reflete macOS/Windows e reforça que novos documentos também partem do template de spec.
- `2.1` — 2026-06-30 — Regra prática ajustada para explicitar que novas specs devem usar `docs/templates/spec-template.md` como base.
- `2.0` — 2026-06-29 — Reestruturação completa do vault: frontmatter padronizado em todas as notas, glossário, ADRs, design system, template de spec, MoC como ponto de entrada único, wikilinks cruzados entre todos os documentos.
- `1.0` — versão original com documentos soltos sem estrutura de navegação.
