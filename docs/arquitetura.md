---
tipo: arquitetura
area: meta
status: implementado
versao: 3.60
atualizado: 2026-08-31
relacionados:
  - "[[requisitos]]"
  - "[[sdd]]"
  - "[[glossario]]"
  - "[[qualidade-codigo]]"
  - "[[specs/bank-logos]]"
  - "[[adr/0001-stack-local-sem-framework]]"
  - "[[adr/0002-modularizacao-frontend]]"
tags: [arquitetura, meta]
---

# Arquitetura

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-08-31 · relacionados: [[requisitos]], [[qualidade-codigo]], [[specs/bank-logos]], [[adr/0001-stack-local-sem-framework]], [[adr/0002-modularizacao-frontend]]

## Visão geral

O Sistema Financeiro é um app local composto por servidor HTTP em Python, banco SQLite e interface web estática. Roda em macOS sem dependências externas para operação financeira básica.

```text
app.py              Adaptador HTTP, autenticação e arquivos estáticos
financeiro/         Regras de domínio, persistência e integrações locais
web/                Interface do usuário em HTML, CSS e JavaScript
data/               Arquivos de runtime criados localmente (não versionados)
secure/             Chave mestra local de segredos criptografados (não versionada)
docs/               Requisitos, arquitetura, specs e referências
```

O servidor HTTP revalida arquivos estáticos com `ETag` e `Last-Modified`; arquivos não versionados usam `Cache-Control: no-cache` para permitir `304 Not Modified` sem cache agressivo. Respostas JSON acima de 1 KB podem ser comprimidas com gzip quando o cliente envia `Accept-Encoding: gzip`.

As fronteiras de responsabilidade e os sinais de alerta para crescimento de módulos estão consolidados em [[qualidade-codigo]]. Além da revisão manual, `tests/test_code_quality.py` aplica um gate automatizado aos limites e às fronteiras arquiteturais verificáveis.

O fluxo do **Consultor** fica dividido entre **Usuário > Preferências** e **Cockpit > Consultor**. Em Preferências, o usuário configura a IA geral, ativa o Consultor, aceita o consentimento de acesso aos dados e pode preencher/remover o Perfil Complementar criptografado. No Cockpit, a aba Consultor exibe os indicadores de atrasos/vencimentos, a subaba **Análises** com catálogo fechado de 9 análises em seletor (incluindo o card `evolucao_score_tempo` com seletor de 6/12 meses), botão único **Gerar** e a subaba **Histórico** com filtro textual. O módulo não possui prompt livre: cada execução envia apenas o contexto minimizado da análise escolhida e persiste somente respostas bem-sucedidas.

---

## Camadas

### Interface web (`web/`)

| Arquivo | Responsabilidade |
|---|---|
| `index.html` | Estrutura das telas. |
| `styles.css` | Aparência e responsividade conforme [[design/design-system]]. |
| `app.js` | Composition root: seleciona DOM, registra views, injeta dependências e controla boot, sessão visual e navegação. |
| `web/modules/` | Módulos ES nativos sem etapa de build. |

**Módulos utilitários já extraídos:**

| Módulo | Responsabilidade |
|---|---|
| `api.js` | Chamadas HTTP JSON e upload. |
| `date-utils.js` | Datas locais, meses e exibição de datas. |
| `money-utils.js` | Formatação e parsing numérico/monetário. |
| `dom-utils.js` | Helpers de formulário, mensagens, empty state e escaping. |
| `chart-adapter.js` | Fronteira única para instâncias ApexCharts, tokens do tema, movimento reduzido, descarte e fallback. |
| `transaction-kind.js` | Predicados de tipo de lançamento. |
| `labels.js` | Labels de domínio usados pela interface. |
| `month-picker.js` | Popover reutilizável de seleção de mês. |
| `asset-autocomplete.js` | Catálogo local derivado das posições do usuário para sugerir e reutilizar ativos sem impedir digitação livre. |
| `decision-modal.js` | Modal reutilizável para decisões, confirmações explícitas e pequenos formulários. |
| `theme-utils.js` | Persistência local e aplicação do tema visual. |
| `privacy-utils.js` | Persistência local e aplicação do modo de ocultação de valores. |
| `instructions-content.js` | Conteúdo estático, offline e versionado da central de ajuda. Ver [[instrucoes-app]]. |
| `app-state.js` | Fábrica do estado inicial e reset puro dos dados de sessão, sem singleton, DOM ou API. |
| `app-data-loader.js` | Coordenação dos carregamentos compartilhados por dependências explícitas e acesso tardio às views, sem regras financeiras. |
| `bank-logos.js` | Catálogo e resolvedor compartilhado de logos de instituições e bandeiras, com normalização, aliases e fallback visual. Ver [[specs/bank-logos]]. |

Os assets normalizados do catálogo ficam em `web/assets/banks/` e `web/assets/bandeiras/`, com nomes ASCII minúsculos. Contas e Cartões reutilizam o mesmo resolvedor; Cartões também exibem a bandeira quando catalogada.

**Fundação da v2 em implementação:** os gráficos existentes já usam ApexCharts 4.7.0 vendorizado por meio de `chart-adapter.js`; [[specs/frontend-fundacao-v2]] mantém planejados o adaptador IMask, uma Command Palette em ES Modules com experiência equivalente ao padrão cmdk e um virtualizador compartilhado de listas de altura fixa. O pacote React `cmdk` não integra a arquitetura; o frontend continua sem framework, bundler ou download de CDN. Ver [[adr/0013-dependencias-frontend-v2]].

**Views funcionais já extraídas:**

| Módulo | Responsabilidade |
|---|---|
| `auth-view.js` | Login, cadastro, logout e recuperação de senha. |
| `user-admin-view.js` | Preferências de usuário, tema, SMTP, IA, Mais Retorno, ativação/perfil do Consultor, limpeza e exclusão. |
| `classifications-view.js` | Categorias, subcategorias e tags. |
| `limits-view.js` | Limites de gastos e índice de consumo. |
| `reports-view.js` | Filtros, abas, agrupamentos e tabelas. |
| `imports-view.js` | Upload, download de modelo e resultado da importação. |
| `cockpit-view.js` | Resumo, saldos, planejamento, dívidas, portfólio e alertas; registra sub-views de Calendário, Tendências e Saúde Financeira. |
| `financial-health-view.js` | Aba **Saúde Financeira** do Cockpit: score/gauge, pilares, Paz Financeira e consolidado do diagnóstico. |
| `trends-view.js` | Aba **Tendências** do Cockpit: gráfico mês a mês, Budget x Realizado e achados local. |
| `consultor-view.js` | Aba **Consultor** do Cockpit: seletor fechado de análises, execução sob demanda, período condicional para ralos, histórico, vencimentos e atrasos, com renderização de tabelas markdown nas respostas. |
| `accounts-view.js` | Contas: cadastro, edição, arquivamento, restauração. |
| `cards-view.js` | Cartões: cadastro, faturas, pagamento, conciliação. |
| `portfolio-view.js` | Ativos: posições, histórico, resgate e encerramento; libera gráficos, overlays e DOM dinâmico ao sair e remonta a apresentação do estado ao entrar. |
| `portfolio-lifecycle.js` | Política de reaproveitamento do snapshot e limpeza seletiva do DOM dinâmico do Portfólio. |
| `transactions-view.js` | Lançamentos: formulário, recorrência, parcelas, câmbio. |
| `operation-history-view.js` | Histórico de Operações: filtros, busca, agrupamentos e paginação. |
| `simulations-view.js` | Efeito Borboleta: formulário e renderização das projeções calculadas pelo backend. |
| `load-policy.js` | Política compartilhada de cache curto, invalidação, chave contextual e deduplicação de requisições em andamento. |
| `transaction-slice-loader.js` | Coordena lançamentos e projeção do Extrato por conta e mês, fora da view. |
| `instructions-view.js` | Central de ajuda: busca, grupos, tópicos expansíveis, links internos e botões contextuais `?` no header. Ver [[instrucoes-app]]. |

> [!tip] Regra de fronteira
> A interface orquestra formulários, listas e navegação. **Regras financeiras, validações de propriedade e cálculo de saldo ficam no núcleo Python.** Ver [[adr/0002-modularizacao-frontend]].

### API local (`app.py`)

Responsabilidades:
- Servir o frontend estático.
- Expor endpoints JSON.
- Ler corpo JSON e uploads multipart.
- Controlar sessão por cookie.
- Exigir usuário autenticado nas rotas financeiras.
- Converter erros de domínio em respostas HTTP.
- Exigir e validar `Host` e `Origin` em mutações contra `APP_URL`, hosts locais e listas CSV opcionais em `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS`.

#### Configuração de origem e rede

| Variável | Uso |
|---|---|
| `APP_HOST` | Interface de escuta do servidor. Padrão: `127.0.0.1`; modo LAN usa `0.0.0.0`. |
| `APP_PORT` | Porta HTTP local. Padrão: `8010`. |
| `APP_URL` | URL pública esperada do app; entra na lista de origens/hosts permitidos e define cookie `Secure` quando usa HTTPS. |
| `APP_ALLOWED_HOSTS` | CSV de hosts adicionais aceitos. Entradas sem porta também aceitam a porta padrão configurada. |
| `APP_ALLOWED_ORIGINS` | CSV de origens adicionais aceitas. Entradas sem esquema assumem `http://`; entradas sem porta assumem `APP_PORT`. |

O modo local mantém `APP_HOST=127.0.0.1` e permite HTTP. O modo rede/LAN dos pacotes usa `APP_HOST=0.0.0.0`, detecta o IP local e preenche `APP_URL`, `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`; esse modo é adequado apenas para redes confiáveis. Quando essa exposição usa HTTP, a inicialização emite um alerta não bloqueante. Acesso remoto deve ficar atrás de reverse-proxy com HTTPS.

#### Rotas — Autenticação e Perfil

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/app-info` | Metadados públicos do app, incluindo nome e versão atual. |
| `GET` | `/api/latest-version` | Versão local e versão mais recente publicada no site oficial, com indicação de atualização disponível. |
| `GET` | `/api/me` | Dados do usuário autenticado. |
| `POST` | `/api/register` | Cadastro de novo usuário. |
| `POST` | `/api/login` | Login com e-mail e senha. |
| `POST` | `/api/logout` | Encerra a sessão. |
| `POST` | `/api/password-reset/request` | Solicita código de recuperação. |
| `POST` | `/api/password-reset/confirm` | Confirma código e redefine senha. |
| `POST` | `/api/me/email` | Altera e-mail do usuário. |
| `POST` | `/api/me/password` | Altera senha do usuário. |
| `POST` | `/api/me/clear-launches` | Apaga todos os lançamentos do usuário. |
| `DELETE` | `/api/me` | Exclui conta do usuário autenticado. |
| `GET` | `/api/email-config` | Retorna status e remetente da configuração SMTP do usuário autenticado. |
| `POST` | `/api/email-config` | Salva configuração SMTP criptografada do usuário autenticado. |

#### Rotas — Contas-correntes → [[contas-correntes]]

| Método | Rota |
|---|---|
| `GET` | `/api/checking-accounts` |
| `GET` | `/api/checking-accounts?status=archived` |
| `POST` | `/api/checking-accounts` |
| `PUT` | `/api/checking-accounts/{id}` |
| `DELETE` | `/api/checking-accounts/{id}` |
| `POST` | `/api/checking-accounts/{id}/restore` |

#### Rotas — Lançamentos → [[lancamentos]]

| Método | Rota |
|---|---|
| `GET` | `/api/transactions` |
| `POST` | `/api/transactions` |
| `PUT` | `/api/transactions/{id}` |
| `DELETE` | `/api/transactions/{id}` |
| `PUT` | `/api/transactions/{id}/reconciliation` |
| `GET` | `/api/exchange-rate` |
| `GET` | `/api/classification-suggestion?description={texto}&group_type={grupo}` |

#### Rotas — Cartões de Crédito → [[cartoes]]

| Método | Rota |
|---|---|
| `GET` | `/api/credit-cards` |
| `GET` | `/api/credit-cards?status=archived` |
| `POST` | `/api/credit-cards` |
| `PUT` | `/api/credit-cards/{id}` |
| `DELETE` | `/api/credit-cards/{id}` |
| `POST` | `/api/credit-cards/{id}/restore` |
| `GET` | `/api/credit-card-invoice` |
| `GET` | `/api/credit-card-transactions` |
| `POST` | `/api/credit-card-transactions` |
| `PUT` | `/api/credit-card-transactions/{id}` |
| `DELETE` | `/api/credit-card-transactions/{id}` |
| `PUT` | `/api/credit-card-transactions/{id}/invoice` |
| `PUT` | `/api/credit-card-transactions/{id}/reconciliation` |
| `GET` | `/api/credit-card-payments` |
| `POST` | `/api/credit-card-invoice/pay` |

#### Rotas — Categorias e Tags → [[categorias-tags-gestao]]

| Método | Rota |
|---|---|
| `GET/POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |
| `POST` | `/api/subcategories` |
| `PUT/DELETE` | `/api/subcategories/{id}` |
| `GET/POST` | `/api/tags` |
| `PUT/DELETE` | `/api/tags/{id}` |

#### Rotas — Limites de Gastos → [[limites-gastos]]

| Método | Rota |
|---|---|
| `GET` | `/api/spending-limits` |
| `POST` | `/api/spending-limits` |
| `PUT` | `/api/spending-limits/{id}` |
| `DELETE` | `/api/spending-limits/{id}` |

#### Rotas — Simulações → [[efeito-borboleta]]

| Método | Rota |
|---|---|
| `POST` | `/api/simulations/butterfly-effect` |

#### Rotas — Investimentos e Portfólio → [[investimentos-portfolio]]

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio` |
| `GET` | `/api/portfolio/returns` |
| `GET` | `/api/portfolio/fund-quote?cnpj={cnpj}` |
| `POST` | `/api/portfolio/positions` |
| `PUT` | `/api/portfolio/positions/{id}` |
| `DELETE` | `/api/portfolio/positions/{id}` |
| `POST` | `/api/portfolio/redeem` |
| `POST` | `/api/portfolio/close` |
| `PUT` | `/api/portfolio/value` |
| `DELETE` | `/api/portfolio/value` |
| `PUT` | `/api/portfolio/allocation-goals` |

#### Rotas — Cockpit e Relatórios → [[relatorios]]

| Método | Rota |
|---|---|
| `GET` | `/api/cockpit?month=AAAA-MM` |
| `GET` | `/api/cockpit/calendar` |
| `GET` | `/api/reports/tags?month=AAAA-MM` |
| `GET` | `/api/reports/category-evolution?category_id={id}&subcategory_id={id}&period={periodo}` |

#### Rotas — Tendências e IA → [[tendencias-saude-financeira]]

| Método | Rota |
|---|---|
| `GET` | `/api/financial-health-trends?month=AAAA-MM` |
| `GET` | `/api/ai-settings` |
| `PUT` | `/api/ai-settings` |
| `POST` | `/api/financial-health-trends/ai-summary` |

#### Rotas — Consultor → [[specs/consultor]]

| Método | Rota |
|---|---|
| `GET` | `/api/consultor/config` |
| `POST` | `/api/consultor/config` |
| `GET` | `/api/consultor/perfil-complementar` |
| `POST` | `/api/consultor/perfil-complementar` |
| `DELETE` | `/api/consultor/perfil-complementar` |
| `POST` | `/api/consultor/analyze` |
| `GET` | `/api/consultor/history` |
| `DELETE` | `/api/consultor/history` |

#### Rotas — Preferências e integrações opt-in → [[preferencias-abas]]

| Método | Rota |
|---|---|
| `GET` | `/api/mais-retorno-config` |
| `PUT` | `/api/mais-retorno-config` |

#### Rotas — Score de Saúde Financeira → [[score-saude-financeira]]

| Método | Rota |
|---|---|
| `GET` | `/api/financial-health-score?month=AAAA-MM` |
| `GET` | `/api/financial-health-score/history?months={1-36}` |

#### Rotas — Histórico de Operações → [[historico-operacoes]]

| Método | Rota |
|---|---|
| `GET` | `/api/operation-logs` |
| `GET` | `/api/operation-logs/{id}` |

#### Rotas — Importação → [[importacao-dados]]

| Método | Rota |
|---|---|
| `POST` | `/api/import/legacy-transactions` |
| `POST` | `/api/import/system-template` |
| `GET` | `/api/import/template` |

---

### Núcleo da aplicação (`financeiro/`)

Utilitários puros compartilhados preservam as fronteiras funcionais: `money.py` trata centavos e arredondamento; `calendar_rules.py`, datas e meses; `identifiers.py`, IDs positivos; e `recurrence.py`, frequências e avanço de ocorrências. Eles não acessam SQLite nem conhecem erros dos módulos consumidores. Ver [[specs/utilitarios-dominio]].

| Módulo | Responsabilidade |
|---|---|
| `database.py` | Conexão SQLite, schema e migrações idempotentes. |
| `money.py` | Conversões monetárias puras, escala de centavos, arredondamento e divisão exata de parcelas. Ver [[specs/utilitarios-dominio]]. |
| `calendar_rules.py` | Normalização ISO e aritmética pura de datas, meses e fins de mês. Ver [[specs/utilitarios-dominio]]. |
| `identifiers.py` | Parsing puro de identificadores inteiros positivos obrigatórios e opcionais. Ver [[specs/utilitarios-dominio]]. |
| `recurrence.py` | Vocabulário compartilhado de séries/frequências e cálculo das ocorrências. Ver [[specs/utilitarios-dominio]]. |
| `auth.py` | Usuários, hashes, sessões, recuperação de senha. Ver [[seguranca-autenticacao]], [[recuperacao-senha]]. |
| `accounts.py` | Contas-correntes, saldos e arquivamento. Ver [[contas-correntes]]. |
| `transactions.py` | Lançamentos, transferências, tags, câmbio, recorrência/parcelamento e conciliação. Ver [[lancamentos]]. |
| `categories.py` | Categorias, subcategorias, tags e bloqueios de exclusão. Ver [[categorias-tags-gestao]]. |
| `classification_suggestions.py` | Normalização de descrições e sugestão local por histórico exato indexado. Ver [[classificacao-assistida]]. |
| `credit_cards.py` | Cartões, faturas mensais, transações e pagamentos. Ver [[cartoes]]. |
| `spending_limits.py` | Metas e orçamentos mensais. Ver [[limites-gastos]]. |
| `http_routes.py` | Tabela declarativa e resolução de rotas, independente do transporte HTTP. Ver [[specs/desconcentracao-arquitetura-v2]]. |
| `cockpit.py` | Agregações de domínio do resumo mensal do Cockpit, fora do adaptador HTTP. |
| `balance_projections.py` | Saldos conciliados/projetados, reservas de faturas e consolidação por moeda; autoridade backend consumida por Cockpit e Extrato. |
| `portfolio.py` | Fachada pública e orquestração compatível do Portfólio. Ver [[investimentos-portfolio]]. |
| `portfolio_positions.py` | Regras internas de identidade, lotes e persistência lógica das posições. |
| `portfolio_quotes.py` | Helpers de integrações externas e limites de cache de cotações. |
| `portfolio_calculations.py` | Agregações, normalizações e cálculos puros do Portfólio. |
| `financial_health.py` | Núcleo analítico do Score de Saúde Financeira: cálculo atômico dos pilares, lista `pilares`, Paz Financeira e função de histórico com validação de `months` (1-36). Ver [[score-saude-financeira]]. |
| `trends.py` | Núcleo local de Tendências e Achados: série mensal, Budget x Realizado, achados estruturados, eventos pontuais, assinaturas/serviços recorrentes, confiança e resumo determinístico. Ver [[tendencias-saude-financeira]]. |
| `ai_summary.py` | Reescrita opcional do resumo por IA com payload minimizado, timeout curto e fallback para resumo local. Ver [[tendencias-saude-financeira]]. |
| `consultor.py` | Domínio do Consultor: catálogo fechado de 9 análises, validações de enums, prompts estritos, persona, disclaimer, configuração por usuário, Perfil Complementar criptografado, contexto minimizado por card (incluindo série histórica dos 5 pilares do Score para o card `evolucao_score_tempo`), metadados de cotações herdados do Portfólio, executor de IA via `user_ai_settings`, pós-processamento de respostas, quota/cooldown de resiliência e expurgo de histórico por privacidade. Ver [[specs/consultor]]. |
| `imports.py` | Leitura de arquivos externos legados e planilhas modelo. Ver [[importacao-dados]]. |
| `operation_logs.py` | Auditoria funcional das operações do usuário. Ver [[historico-operacoes]]. |
| `emailer.py` | Envio SMTP do código de recuperação de senha. Ver [[recuperacao-senha]]. |
| `secure_config.py` | Armazenamento criptografado da configuração SMTP local, segredos de IA e chaves de integrações por usuário em `secure_configs`, com compatibilidade para arquivos `.enc` legados. Ver [[recuperacao-senha]], [[tendencias-saude-financeira]], [[specs/preferencias-abas]]. |
| `version_check.py` | Consulta a landing page oficial por nova versão, compara com a versão local e mantém cache de 1h. Ver [[alerta-nova-versao]]. |
| `calendar.py` | Cálculo da aba **Calendário** do Cockpit: contas a receber/pagar atrasadas e vencimentos de renda fixa em 30 e 60 dias. Ver [[specs/cockpit-calendario]]. |
| `simulations.py` | Validação e projeção comparativa, sem persistência, de cenários hipotéticos do Efeito Borboleta. Ver [[efeito-borboleta]]. |
| `reports.py` | Agregações de relatórios por tag e por evolução de categoria/subcategoria, normalizadas em BRL quando necessário. Ver [[relatorios]]. |

---

## Persistência

Banco local em `data/finance.db`, criado automaticamente na inicialização. Arquivos de `data/` são runtime local e **não devem ser versionados**.

O cache regenerável `quote_cache` recebe manutenção na inicialização: respostas expiradas há mais de 30 dias são removidas, com limites de 1.000 entradas por provedor e 1.500 no total. Se a limpeza liberar ao menos 1 MiB e 20% das páginas, o banco executa `VACUUM`; abaixo disso, o SQLite apenas reutiliza as páginas livres. Falhas nessa manutenção não bloqueiam a abertura e nenhuma tabela financeira é afetada. Ver [[specs/manutencao-cache-cotacoes]].

Conexões SQLite são abertas com `journal_mode=WAL`, `busy_timeout` curto e `foreign_keys=ON`. Escritas que dependem de leituras prévias de saldo/fatura usam transações imediatas para serializar a janela crítica; operações potencialmente demoradas, como envio SMTP, cotação externa, consolidação de portfólio e importações em lote, não devem manter uma conexão aberta além do trecho estritamente necessário de leitura ou gravação.

### Baseline e migração para a linha v2

O baseline inicial da v2 usa `PRAGMA user_version = 20000`. Banco ausente é criado e marcado diretamente; banco já marcado abre sem percorrer as compatibilizações da linha 1.x. Um `finance.db` com `user_version = 0` é tratado como legado: na abertura, o app normaliza uma cópia de trabalho, gera um candidato compacto por `VACUUM INTO`, valida integridade, chaves estrangeiras, versão e contagens por tabela e somente então promove os arquivos. O original passa a `data/finance-v1.bkp`, que nunca é sobrescrito, enquanto o candidato mantém o nome ativo `data/finance.db`. Falhas anteriores à promoção preservam o nome original; falha na segunda renomeação tenta restaurá-lo. Ver [[specs/migracao-banco-v2]] e [[adr/0012-fundacao-v2-contrato-e-migracao-de-dados]].

### Tabelas

| Tabela | Módulo responsável |
|---|---|
| `users` | `auth.py` |
| `sessions` | `auth.py` |
| `password_resets` | `auth.py` |
| `auth_attempts` | `auth.py` — Ver [[seguranca-autenticacao]]. |
| `checking_accounts` | `accounts.py` — Ver [[contas-correntes]]. |
| `credit_cards` | `credit_cards.py` — Ver [[cartoes]]. |
| `credit_card_transactions` | `credit_cards.py` — Ver [[cartoes]]. |
| `credit_card_payments` | `credit_cards.py` — Ver [[cartoes]]. |
| `categories` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `subcategories` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `tags` | `categories.py` — Ver [[categorias-tags-gestao]]. |
| `transactions` | `transactions.py` — Ver [[lancamentos]]. |
| `transaction_tags` | `transactions.py` — Ver [[lancamentos]]. |
| `credit_card_transaction_tags` | `credit_cards.py` — Ver [[cartoes]]. |
| `spending_limits` | `spending_limits.py` — Ver [[limites-gastos]]. |
| `investment_opening_positions` | `portfolio.py` — inclui `emergency_reserve_eligible` para reserva de emergência explícita. Ver [[investimentos-portfolio]]. |
| `investment_operations` | `transactions.py` grava aportes e `portfolio.py` consolida; inclui `emergency_reserve_eligible` para reserva de emergência explícita em aportes. Ver [[investimentos-portfolio]]. |
| `investment_redemptions` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_closed_positions` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `investment_value_overrides` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `quote_cache` | `portfolio.py` — Ver [[investimentos-portfolio]]. |
| `user_ai_settings` | `secure_config.py` — metadados não secretos de configuração opcional de IA por usuário; segredo fica em `secure_configs`. Ver [[tendencias-saude-financeira]]. |
| `secure_configs` | `secure_config.py` — envelopes criptografados por usuário para SMTP, IA e Mais Retorno; `source_path` indica arquivo legado migrado quando aplicável. Ver [[specs/preferencias-abas]], [[adr/0010-segredos-criptografados-sqlite]]. |
| `consultor_settings` | `database.py` — configuração do Consultor por usuário (`consultor_enabled`, `investor_profile`, `data_access_consent`). Ver [[specs/consultor]]. |
| `consultor_analyses` | `database.py` — histórico de execuções bem-sucedidas do Consultor, indexado por usuário, data e `analysis_id` para leitura e quota diária. Ver [[specs/consultor]]. |
| `consultor_perfil_complementar` | `database.py` — payload criptografado do Perfil Complementar por usuário (`payload_enc`, `schema_version`). Ver [[specs/consultor]]. |

`transactions` e `credit_card_transactions` persistem `normalized_description` para a classificação assistida. Ambas também mantêm valor normalizado em BRL (`amount_brl_cents`); em moedas estrangeiras sem cotação manual, a normalização usa a última PTAX de venda disponível até a data do lançamento. Bancos existentes são retroalimentados de forma idempotente durante a inicialização.

`user_ai_settings` armazena somente provedor, endpoint/base URL, modelo, estado ligado/desligado, autenticação e parâmetros operacionais. Chaves de API de IA, senha SMTP e chaves de integrações opcionais são salvas em `secure_configs.payload_enc` como envelopes criptografados por usuário; APIs nunca devem retornar o segredo. Instalações antigas com `data/*_config_user_{id}.enc` continuam legíveis: o payload criptografado é copiado para `secure_configs` no primeiro uso, sem exigir que o usuário recadastre a chave.

A chave mestra padrão de `secure_config.py` fica fora de `data/`, em `secure/config.key` ao lado da pasta de dados; `data/email_config.key` continua aceito e é copiado para o novo caminho no primeiro uso. Operações de servidor podem fixar o caminho com `SISTEMA_FINANCEIRO_CONFIG_KEY_PATH` ou fornecer o material diretamente por `SISTEMA_FINANCEIRO_CONFIG_KEY`.

### Índices principais

- `idx_transactions_user_date`
- `idx_transactions_account`
- `idx_transactions_user_account_date`
- `idx_transactions_user_destination_date`
- `idx_transactions_user_series_date`
- `idx_transactions_user_type_normalized_description`
- `idx_subcategories_category`
- `idx_transaction_tags_tag`
- `idx_password_resets_token`
- `idx_auth_attempts_locked_until`
- `idx_spending_limits_category`
- `idx_spending_limits_subcategory`
- `idx_investment_operations_user`
- `idx_investment_opening_positions_user`
- `idx_investment_redemptions_source`
- `idx_investment_value_overrides_user`
- `idx_investment_closed_positions_user`
- `idx_investment_closed_positions_user_closed`
- `idx_credit_card_transactions_card_month`
- `idx_credit_card_transactions_user_card_invoice_date`
- `idx_credit_card_transactions_user_invoice_date`
- `idx_credit_card_transactions_user_series_invoice_date`
- `idx_card_transactions_user_type_normalized_description`
- `idx_credit_card_payments_user_card_invoice`
- `idx_credit_card_payments_user_date`
- `idx_credit_card_transaction_tags_tag`
- `idx_quote_cache_expires_at`

---

## Fluxos principais

### Autenticação

1. Usuário registra ou autentica pela interface.
2. `app.py` chama `financeiro.auth`.
3. Senha validada contra hash PBKDF2.
4. Sessão criada em `sessions`, persistindo somente o hash SHA-256 do token.
5. API grava cookie `session` com `HttpOnly` e `SameSite=Lax`.
6. Troca ou recuperação de senha revoga todas as sessões do usuário.
7. A sessão expira definitivamente 30 dias após a criação, sem renovação por atividade.

Ver [[seguranca-autenticacao]], [[recuperacao-senha]].

### Detecção de nova versão

1. O frontend carrega metadados do app (`/api/app-info`) e, em seguida, consulta `/api/latest-version`.
2. `app.py` chama `financeiro.version_check.latest_version_info()`, que consulta o endpoint `/api/latest-version` da landing page oficial com timeout curto.
3. O resultado é cacheado por 1 hora para evitar requisições repetidas.
4. O frontend compara a versão local com a versão publicada e exibe um alerta no Cockpit quando a publicada for maior.
5. Se a landing page ou a rede estiver indisponível, o app omite o alerta silenciosamente.

Ver [[alerta-nova-versao]].

### Operação financeira (fluxo comum)

1. Interface chama uma rota `/api/*`.
2. `app.py` identifica o usuário pelo cookie.
3. Módulo de domínio valida os dados e a propriedade dos registros.
4. SQLite alterado dentro de uma conexão local.
5. API retorna JSON para a interface renderizar.

### Lançamentos e saldos

1. `transactions.py` valida tipo, data, valor, conta, categoria e tags.
2. Receita/despesa: saldo da conta de origem ajustado.
3. Transferência: origem e destino ajustados em sentidos opostos.
4. Exclusão: impacto financeiro revertido.

Ver [[lancamentos]].

### Classificação assistida

1. O frontend aguarda 300 ms após a digitação da descrição.
2. `GET /api/classification-suggestion` normaliza descrição e grupo.
3. SQLite busca correspondências exatas, isoladas por usuário, nos índices de lançamentos de conta e cartão.
4. O backend agrega suporte por categoria/subcategoria e só retorna resultado com pelo menos 2 ocorrências e 80% de dominância.
5. O frontend preenche campos ainda não alterados manualmente e ignora respostas obsoletas; falhas nunca bloqueiam o cadastro.

Ver [[classificacao-assistida]], [[adr/0006-classificacao-assistida-local]].

### Cartões de Crédito e Fatura

1. Lançamentos em cartões são associados a um cartão e a uma fatura mensal (`AAAA-MM`).
2. A fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão.
3. Faturas acumulam despesas/receitas e exibem total atual, total conciliado e contador de não conciliados.
4. Lançamentos de fatura podem ser movidos para fatura anterior/posterior se a fatura destino estiver aberta.
5. Pagamento de fatura deduz saldo da conta-corrente, respeita moeda e conta preferencial.
6. Pagamento pode ser **integral** (saldo em aberto) ou **parcial** (`amount` < saldo): no parcial, a fatura fecha como no integral e o saldo restante é gravado como novo lançamento de cartão na próxima fatura aberta, categoria **Empréstimos**, descrição `Saldo da fatura MM/AAAA`, junto da mesma transação atômica do pagamento.

Ver [[cartoes]].

### Portfólio de Investimentos

1. Carteira consolidada unindo posições iniciais e operações em contas de investimento.
2. Cotações de Renda Variável, Cripto e Stablecoin são buscadas de APIs externas (Yahoo Finance / CoinGecko) e cacheadas em `quote_cache`; Stablecoins constituem classe própria, mas usam o par definido pela moeda da conta e posições legadas conhecidas são reclassificadas em leitura. Tickers internacionais que exigem código de bolsa usam aliases explícitos e testados, como `VWRA`/USD → `VWRA.L`.
3. Rendimentos de Renda Fixa pós-fixados/híbridos indexados via SGS/BCB, com fallback local.
4. Valor líquido projetado aplicando tributação regressiva de IOF e IR baseada no tempo de aquisição.
5. Poupança tratada como ativo próprio com aniversários; Previdência Privada como `private_pension`.
6. Resgates usam FIFO; encerramentos movem posições para histórico.
7. Ativos em moeda estrangeira exibidos na moeda da carteira; conversão via lançamentos de câmbio.
8. Consolidações do Portfólio mantêm valores exibidos na moeda original, mas expõem valor atual normalizado em BRL para a escala das barras visuais, usando cotação do fechamento anterior quando a moeda não é BRL.
9. A UI do Portfólio carrega a aba **Posição** primeiro; Análise, Histórico e rentabilidade detalhada são renderizados/carregados sob demanda.
10. Renda fixa e Poupança exibem variação do dia calculada como a diferença do valor na curva entre hoje e o dia anterior (base limitada à data de aquisição), reutilizando `fixed_income_value_as_of`/`savings_value_as_of` com cache de fatores compartilhado; dias sem taxa publicada produzem variação zero em pós-fixados.

Ver [[investimentos-portfolio]].

### Cockpit e Relatórios

1. `GET /api/cockpit?month=AAAA-MM` consolida lançamentos de conta pelo mês selecionado e lançamentos de cartão pela fatura (`invoice_month`).
2. `GET /api/cockpit/calendar` retorna contas a receber/pagar atrasadas e vencimentos de renda fixa em 30 e 60 dias, calculados pela data atual do servidor, independentemente do mês selecionado. Ver [[specs/cockpit-calendario]].
3. O Cockpit usa um seletor mensal compartilhado pelas abas **Situação do mês**, **Calendário**, **Tendências** e **Saúde Financeira**.
4. Planejamento do mês considera receitas/despesas/investimentos recorrentes, incluindo recorrências de cartão.
5. Faturas de cartão de crédito continuam visíveis no Cockpit pelo mês de competência mesmo após pagamento; o pagamento agregado em conta-corrente permanece excluído das despesas analíticas.
6. Relatórios no frontend agrupam por categoria, subcategoria, conta, tag e fluxo diário.
7. Lançamentos de cartão entram em relatórios e limites pela competência da fatura.
8. `GET /api/reports/category-evolution` retorna séries mensais por categoria/subcategoria para o drawer de evolução, com `periodo` igual a `3m`, `6m`, `12m`, `ytd` ou `all`.

Ver [[relatorios]], [[limites-gastos]], [[specs/cockpit-calendario]].

### Importação de Arquivos

1. Parser de arquivos externos legados (`.xls`/`.csv`) em `imports.py`.
2. Importação estruturada via modelos `.xlsx` do próprio sistema.

Ver [[importacao-dados]].

### Configuração de E-mail

1. Usuário autenticado abre Preferências > Recuperação por e-mail.
2. `GET /api/email-config` retorna status e remetente configurado do usuário autenticado, sem expor senha de app.
3. `POST /api/email-config` salva a configuração criptografada em `secure_configs` e mantém compatibilidade de leitura com `data/email_config_user_{id}.enc`.
4. Presets: Gmail (`smtp.gmail.com:587`) e Outlook/Microsoft (`smtp.office365.com:587`), ambos com STARTTLS.
5. Configuração manual permite servidor SMTP, porta e uso de STARTTLS.

Ver [[recuperacao-senha]].

---

## Convenções

- Valores monetários persistidos em centavos.
- Datas de lançamento em ISO `YYYY-MM-DD`.
- Registros históricos preferem arquivamento quando houver impacto financeiro.
- Escritas que alteram saldos devem usar deltas atômicos (`saldo atual = saldo atual + delta`) ou uma transação curta que proteja o cálculo.
- Erros de domínio expõem mensagem amigável e status HTTP; sem detalhes internos.
- Novas tabelas e colunas devem ser criadas de forma idempotente.
- **Novos documentos e funcionalidades devem nascer duplicando [[templates/spec-template|`docs/templates/spec-template.md`]] como base.** Ver [[sdd]].

---

## Decisões técnicas

Decisões não triviais estão documentadas como ADRs para preservar o raciocínio:

- [[adr/0001-stack-local-sem-framework]] — Sem framework web: servidor HTTP puro em Python para manter o app simples e portável.
- [[adr/0002-modularizacao-frontend]] — ES Modules nativos sem build step; fronteiras de responsabilidade entre views, utilitários e domínio Python.
- [[adr/0003-sqlite-fonte-de-verdade]] — SQLite local como fonte de verdade: offline-first, sem servidor de banco externo.
- [[adr/0004-importador-xls-sem-dependencia]] — Parser `.xls` implementado sem pacote externo para reduzir requisitos de instalação.
- [[adr/0005-smtp-criptografado-local]] — Configuração SMTP criptografada no próprio ambiente; pacotes distribuíveis nunca incluem credenciais.
- [[adr/0006-classificacao-assistida-local]] — Correspondência exata normalizada como MVP local; ML local reservado para V2.
- [[adr/0014-desconcentracao-fachadas-e-roteamento]] — Fachadas compatíveis, roteamento declarativo e módulos internos menores para a fundação v2.

## Changelog

- `3.60` — 2026-08-31 — Documentados `bank-logos.js`, os catálogos de assets compartilhados por Contas/Cartões e o gate automatizado efetivamente aplicado por `tests/test_code_quality.py`.
- `3.59` — 2026-08-30 — Carregamentos de Preferências, Histórico, Extrato e Simulações adotam política compartilhada `dirty + loadedAt + in-flight`, invalidada centralmente após mutações HTTP.
- `3.58` — 2026-08-30 — Portfólio adota ciclo seletivo `onEnter()`/`onLeave()`, snapshot fresco por 30 segundos e invalidação imediata após mutações para reduzir memória e chamadas redundantes.
- `3.57` — 2026-08-30 — Documentada a extração de `app-state.js` e `app-data-loader.js`, preservando `app.js` como composition root e as regras financeiras no núcleo Python.

- `3.56` — 2026-08-30 — [[qualidade-codigo]] incorporada como referência implementada de fronteiras de responsabilidade, sinais de alerta e prevenção de regressões arquiteturais.
- `3.55` — 2026-08-30 — Projeções de saldos/faturas migram de `app.js` para `balance_projections.py` e `portfolio-view.js` passa a coordenar módulos dedicados de gráfico, agrupamento e formulário.
- `3.54` — 2026-08-30 — Roteamento declarativo e fronteiras internas de Portfólio/Cockpit reduzem concentração sem alterar contratos públicos. Ver [[specs/desconcentracao-arquitetura-v2]] e [[adr/0014-desconcentracao-fachadas-e-roteamento]].
- `3.53` — 2026-08-30 — Documentados os utilitários puros de dinheiro, calendário, identificadores e recorrência compartilhados pelo núcleo. Ver [[specs/utilitarios-dominio]].
- `3.52` — 2026-08-30 — Documentada manutenção automática do `quote_cache` com retenção stale, limites e `VACUUM` condicionado. Ver [[specs/manutencao-cache-cotacoes]].
- `3.51` — 2026-08-30 — ApexCharts 4.7.0 incorporado localmente e isolado por `chart-adapter.js`; gráficos atuais migrados sem alterar contratos de dados.
- `3.50` — 2026-08-30 — Documentada a fundação planejada do frontend v2: ApexCharts 4.7.0/IMask locais, Command Palette nativa por `Cmd/Ctrl+K` e virtualização compartilhada, mantendo ES Modules sem build step. Ver [[specs/frontend-fundacao-v2]] e [[adr/0013-dependencias-frontend-v2]].
- `3.49` — 2026-08-30 — Persistência passa a usar baseline v2 `user_version = 20000` e migração automática, validada e recuperável do legado, preservando `finance-v1.bkp` e mantendo `finance.db` como banco ativo. Ver [[specs/migracao-banco-v2]].
- `3.48` — 2026-08-29 — Metas de alocação passam a integrar o contexto minimizado dos cards `alocacao_perfil` e `analise_carteira`; auditoria aceita a entidade `portfolio_allocation_goals`.
- `3.47` — 2026-08-29 — Adicionada persistência `portfolio_allocation_goals` e rota `PUT /api/portfolio/allocation-goals`; consolidação por classe usa valores normalizados em BRL para atual versus meta.
- `3.46` — 2026-08-29 — Adicionada `investment_redemption_summaries` para preservar o snapshot financeiro de cada resgate e alimentar a aba Histórico sem recálculo retroativo.
- `3.45` — 2026-08-29 — Portfólio documenta catálogo local compartilhado de ativos e resgate quantitativo persistido em `investment_redemptions`, com baixa FIFO e crédito líquido em `transactions`.
- `3.44` — 2026-08-29 — Resolvedor do Yahoo passa a aceitar alias explícito de bolsa para VWRA em USD (`VWRA.L`).
- `3.43` — 2026-08-29 — `DELETE /api/portfolio/value` remove o override manual de uma posição e recarrega sua cotação automática.
- `3.42` — 2026-08-29 — Portfólio passa a distinguir Stablecoins de criptoativos voláteis, preservando cotação pela moeda da conta e compatibilidade de posições legadas.
- `3.41` — 2026-08-28 — Efeito Borboleta substitui cortes semanais por `daily_projection` de 15 dias e `daily_projection_summary`, identificando a primeira data negativa e se o cenário causa ou evita o risco; `weekly_projection` permanece como alias transitório. Ver [[specs/efeito-borboleta]] v1.5.
- `3.40` — 2026-08-28 — Inventário arquitetural sincronizado com `decision-modal.js`, `theme-utils.js`, `privacy-utils.js`, `simulations-view.js` e `financeiro/reports.py`; despacho das rotas `GET` de perfil e coleções passa a exigir caminho exato. Ver [[specs/frontend-modularizacao]] v2.9 e [[specs/seguranca-autenticacao]] v1.4.
- `3.39` — 2026-08-23 — Relatórios: nova rota `GET /api/reports/tags?month=AAAA-MM` e módulo `financeiro/reports.py` responsáveis pelo agrupamento por tag com Receitas, Despesas, Saldo e Investimentos; `web/modules/reports-view.js` renderiza a tabela a partir do backend. Ver [[specs/relatorios]] v2.13.
- `3.38` — 2026-08-23 — Efeito Borboleta: rota `POST /api/simulations/butterfly-effect` passa a retornar `weekly_projection` (saldo atual + 8 semanas, com linhas Previsto, Simulado e Diferença); `financeiro/simulations.py` e `web/modules/simulations-view.js` responsáveis pelo cálculo e renderização. Ver [[specs/efeito-borboleta]] v1.3.
- `3.37` — 2026-08-22 — Consultor: catálogo ampliado para 9 análises com o card `evolucao_score_tempo` (Evolução do Score no Tempo), que envia série histórica dos 5 pilares do Score para 6 ou 12 meses; `AnalysisCard` passa a declarar `period_window_options` por card e o frontend renderiza as opções declaradas pelo backend. Ver [[specs/consultor]] v1.7.
- `3.36` — 2026-08-22 — `consultor-view.js` passa a exibir seletor fechado de análises, botão único de geração e período condicional para ralos; a resposta ocupa a largura abaixo dos controles. Ver [[specs/consultor]] v1.6.
- `3.35` — 2026-08-20 — Sincronizada a data do callout de status com o frontmatter; documentadas a rota `POST /api/simulations/butterfly-effect` e a responsabilidade de `financeiro/simulations.py`. Ver [[specs/efeito-borboleta]].
- `3.34` — 2026-08-16 — Consultor: prompt do card `analise_carteira` orienta a IA a encerrar todas as seções obrigatórias dentro do teto de 900 tokens de saída (encurtando justificativas se preciso, sem deixar seção pela metade), eliminando truncamento que bloqueava a entrega da análise; `max_tokens` do usuário na homologação elevado para 900. Ver [[specs/consultor]] v1.5.
- `3.33` — 2026-08-15 — Consultor: correções no pós-processamento em `financeiro/consultor.py` — `has_section` passa a reconhecer cabeçalhos markdown (`###`) e `contains_forbidden_recommendation` ignora negações/ressalvas na janela anterior ao match (frases defensivas da IA), mantendo bloqueio de recomendações afirmativas. Ver [[specs/consultor]] v1.4.
- `3.32` — 2026-08-15 — Consultor: todos os cards passam a receber `investor_profile` e Perfil Complementar (quando preenchido) no payload, com enriquecimento centralizado em `build_analysis_context` (perfil injetado também no card `analise_carteira`, cujo builder delegou a leitura ao contexto central) e regra global no `system_prompt` para contextualizar qualquer análise com esses dados. Ver [[specs/consultor]] v1.3.
- `3.31` — 2026-08-15 — Card `analise_carteira` do Consultor aprofundado: contexto enriquecido com `investor_profile`, Perfil Complementar e pilar Reserva do Score; prompt exige tabela por classe de ativo e seção Adequação ao Perfil Configurado; concisão suspensa para o card e `consultor-view.js` passa a renderizar tabelas markdown como HTML. Ver [[specs/consultor]] v1.2.
- `3.30` — 2026-08-15 — Catálogo do Consultor ampliado para 8 análises com o card `analise_carteira` (contexto consolidado por classe/moeda/mercado via `summarize_portfolio` + `group_positions_by`, sem nomes/identificadores de ativos). Ver [[specs/consultor]] v1.1.
- `3.29` — 2026-08-13 — Pagamento parcial de fatura documentado: `POST /api/credit-card-invoice/pay` aceita `amount` opcional; no parcial, saldo residual é lançado na próxima fatura aberta (categoria Empréstimos, `Saldo da fatura MM/AAAA`) na mesma transação atômica. Ver [[specs/cartoes]] v2.9.
- `3.28` — 2026-08-10 — Renda fixa e Poupança passam a calcular variação do dia no Portfólio pela diferença do valor na curva entre hoje e o dia anterior, via `day_variation_cents` com cache de fatores compartilhado. Ver [[specs/investimentos-portfolio]] v2.22.
- `3.27` — 2026-08-10 — Arquitetura sincronizada após implementação do Consultor: removidas marcações de "futuro", documentado fluxo Preferências/Cockpit, catálogo fechado de 7 análises, histórico em subaba própria e persistência criptografada do Perfil Complementar.
- `3.26` — 2026-08-10 — `consultor-view.js` documentado com grade de cards, execução sob demanda e histórico da aba Consultor no Cockpit. Ver [[specs/consultor]] v0.33.
- `3.25` — 2026-08-10 — Preferências documentadas com ativação do Consultor, seleção de perfil e Perfil Complementar opcional. Ver [[specs/consultor]] v0.32.
- `3.24` — 2026-08-10 — Documentadas as rotas autenticadas do Consultor (`/api/consultor/config`, `/api/consultor/perfil-complementar`, `/api/consultor/analyze` e `/api/consultor/history`). Ver [[specs/consultor]] v0.31.
- `3.23` — 2026-08-10 — `financeiro/consultor.py` documentado com persistência somente de execuções bem-sucedidas, quota diária e cooldown por falha de card. Ver [[specs/consultor]] v0.30.
- `3.22` — 2026-08-10 — `financeiro/consultor.py` documentado com pós-processamento de respostas para estrutura obrigatória, disclaimer, risco e bloqueio de recomendações vedadas. Ver [[specs/consultor]] v0.29.
- `3.21` — 2026-08-10 — `financeiro/consultor.py` documentado com executor de IA que reutiliza `user_ai_settings`, respeita timeout configurado e limita tokens de resposta a 900. Ver [[specs/consultor]] v0.28.
- `3.20` — 2026-08-10 — `financeiro/consultor.py` documentado com metadados de cotações herdados do Portfólio (`market_data`), sem novas fontes de mercado no Consultor. Ver [[specs/consultor]] v0.27.
- `3.19` — 2026-08-10 — `financeiro/consultor.py` documentado com construtores de contexto minimizado por `analysis_id`, reaproveitando agregados existentes sem transações cruas. Ver [[specs/consultor]] v0.26.
- `3.18` — 2026-08-10 — `financeiro/consultor.py` documentado com Perfil Complementar criptografado por usuário em `consultor_perfil_complementar.payload_enc`. Ver [[specs/consultor]] v0.25.
- `3.17` — 2026-08-10 — `financeiro/consultor.py` documentado com configuração por usuário e expurgo de histórico quando Consultor/consentimento/IA geral são desabilitados. Ver [[specs/consultor]] v0.24.
- `3.16` — 2026-08-10 — Documentado `financeiro/consultor.py` como domínio base futuro do Consultor, ainda sem rotas ou execução de IA. Ver [[specs/consultor]] v0.23.
- `3.15` — 2026-08-10 — Documentadas as tabelas futuras do Consultor (`consultor_settings`, `consultor_analyses`, `consultor_perfil_complementar`) criadas por migrações idempotentes. Ver [[specs/consultor]] v0.21.
- `3.14` — 2026-08-10 — Documentada rota `GET /api/portfolio/fund-quote?cnpj={cnpj}` para busca assistida de cota de fundos via Mais Retorno no formulário de Lançamentos.
- `3.13` — 2026-08-09 — Ajustes finais de performance: índice `idx_investment_closed_positions_user_closed`, filtro por intervalo de datas nas Tendências, widget terceiro assíncrono e modo privacidade sem `filter: blur()` em massa.
- `3.12` — 2026-08-09 — Documentadas revalidação HTTP com `ETag`/`Last-Modified`, gzip para JSON grande, cache em memória limitado para cotações/câmbio e lazy rendering das abas do Portfólio.
- `3.11` — 2026-08-09 — Documentada a tabela `secure_configs`, a migração compatível de arquivos `.enc` legados e a chave mestra padrão em `secure/config.key` fora de `data/`.
- `3.10` — 2026-08-07 — Saldo de conta-corrente passa a ser reconciliação curta (`current_balance_cents = saldo inicial + soma dos deltas de lançamentos com data <= hoje`) dentro da mesma transação imediata de escrita; `apply_balance_delta` deixa de existir; lançamentos futuros não movem o saldo. Ver [[specs/contas-correntes]].
- `3.9` — 2026-08-07 — Aba **Saúde Financeira** extraída para módulo próprio `web/modules/financial-health-view.js` (fábrica `registerFinancialHealthView`), seguindo o padrão de `trends-view.js`/`consultor-view.js`; estado local de tela migra para o módulo e `invalidateFinancialHealth` passa a ser delegado pelo `cockpit-view.js`.
- `3.8` — 2026-08-06 — Rota `GET /api/portfolio/returns`: série mensal por moeda (BRL/USD em %) com benchmarks CDI e IPCA; gráfico de linhas no drawer. Ver [[specs/rentabilidade-portfolio]].
- `3.7` — 2026-08-06 — Ajustada rota `GET /api/portfolio/returns`: série mensal consolidada (carteira inteira em BRL) vs CDI do mês, últimos 12 meses ou todo o período disponível. Ver [[specs/rentabilidade-portfolio]].
- `3.6` — 2026-08-06 — Documentada rota `GET /api/portfolio/returns` para rentabilidade da carteira por moeda com benchmark CDI. Ver [[specs/rentabilidade-portfolio]].
- `3.5` — 2026-08-06 — Documentada implementação da rota `GET /api/cockpit/calendar` e do módulo `financeiro/calendar.py`, com autenticação e validação de `Host`/`Origin`. UI da aba **Calendário** ainda pendente. Ver [[specs/cockpit-calendario]].
- `3.4` — 2026-08-04 — Documentada rota `GET /api/cockpit/calendar` para a futura aba **Calendário** do Cockpit, com contas a receber/pagar atrasadas e vencimentos de renda fixa em 30 e 60 dias. Ver [[specs/cockpit-calendario]].
- `3.3` — 2026-08-04 — Documentada rota pública `/api/latest-version`, módulo `financeiro/version_check.py` e fluxo de detecção de nova versão no Cockpit.
- `3.2` — 2026-08-04 — Atualizada descrição de `instructions-view.js` para incluir botões contextuais `?` e responsividade em telas estreitas.
- `3.1` — 2026-08-04 — Documentada view `instructions-view.js` da central de ajuda, integrada ao menu Usuário e ao orquestrador `web/app.js`.
- `3.0` — 2026-08-04 — Documentado módulo utilitário `instructions-content.js` com conteúdo estático, offline e versionado da central de ajuda.
- `2.9` — 2026-08-02 — Documentada normalização em BRL de lançamentos de conta e cartão por cotação manual ou última PTAX de venda disponível, incluindo `amount_brl_cents` em cartões.
- `2.8` — 2026-08-02 — Documentada aba **Tendências** no Cockpit (`trendsPanel`, `trends-view.js`) integrada à rota `GET /api/financial-health-trends` com gráfico mês a mês, Budget x Realizado e achados local.
- `2.7` — 2026-08-02 — Documentada UI de Preferências para configuração de IA (`aiConfigForm`, `user-admin-view.js`) integrada às rotas `/api/ai-settings`.
- `2.6` — 2026-08-02 — Documentadas rotas de Tendências (`/api/financial-health-trends`, `/api/ai-settings`, `/api/financial-health-trends/ai-summary`) e módulo `financeiro/ai_summary.py`.
- `2.5` — 2026-08-02 — Documentado módulo `financeiro/trends.py` como núcleo local de cálculo de tendências para a aba Tendências.
- `2.4` — 2026-08-02 — Documentada a tabela `user_ai_settings` e o armazenamento criptografado local de segredos de IA por usuário para a futura aba de Tendências.
- `2.3` — 2026-08-02 — Fluxo do Cockpit documentado com seletor mensal compartilhado e faturas de cartão preservadas por competência após pagamento.
- `2.2` — 2026-07-29 — Documentado metadado `emergency_reserve_eligible` também em `investment_operations`, permitindo marcar aportes de Renda Fixa/Poupança como reserva de emergência.
- `2.1` — 2026-07-29 — Documentadas rotas do Score de Saúde Financeira (`/api/financial-health-score` e `/api/financial-health-score/history`) e a validação de `months` (1-36) no histórico; descrição de `financial_health.py` atualizada para incluir função de histórico.
- `2.0` — 2026-07-28 — Documentado módulo `financial_health.py` como núcleo analítico do Score de Saúde Financeira.
- `1.9` — 2026-07-28 — Documentado metadado `emergency_reserve_eligible` em posições iniciais do Portfólio para suporte ao Score de Saúde Financeira.
- `1.8` — 2026-07-27 — Documentado endpoint público `/api/app-info` para metadados centralizados de nome e versão do app.
- `1.7` — 2026-07-23 — Documentados módulo, rota, colunas, índices e fluxo do MVP de classificação assistida local.
- `1.6` — 2026-07-09 — Histórico de Operações documentado na arquitetura com view, módulo Python e rotas de auditoria.
- `1.5` — 2026-07-05 — Configuração SMTP documentada como preferência criptografada por usuário autenticado.
- `1.4` — 2026-07-04 — Configuração de origem/rede documentada para `APP_ALLOWED_HOSTS`, `APP_ALLOWED_ORIGINS`, modo LAN e reverse-proxy HTTPS.
- `1.3` — 2026-07-03 — Persistência documenta WAL, espera por locks, transações imediatas curtas e regra de deltas atômicos para saldos.
- `1.2` — 2026-06-30 — Rotas de Cockpit/relatórios documentadas, método de `/api/portfolio/value` corrigido para `PUT`, índices atuais de performance detalhados, regra de template alinhada ao SDD e escala BRL das barras de consolidação do Portfólio documentada.
- `1.1` — 2026-06-29 — Frontmatter, tabelas de rotas e módulos por área, wikilinks e referência para ADRs.
- `1.0` — versão original.

## Relacionados

- [[requisitos]]
- [[sdd]]
- [[glossario]]
- [[adr/0001-stack-local-sem-framework]]
- [[adr/0002-modularizacao-frontend]]
