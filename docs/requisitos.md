---
tipo: produto
area: meta
status: implementado
versao: 1.8
atualizado: 2026-08-02
relacionados:
  - "[[arquitetura]]"
  - "[[visao-produto]]"
  - "[[sdd]]"
tags: [produto, meta]
---

# Requisitos

> [!info] Status
> **implementado** (escopo vivo) · área: `meta` · atualizado em 2026-08-02 · relacionados: [[arquitetura]], [[visao-produto]]

## Objetivo

Manter um sistema financeiro local, privado e simples para controlar contas, saldos, lançamentos e classificações financeiras em SQLite, com interface web servida pelo próprio app Python.

## Escopo atual implementado

- **Autenticação local**: cadastro, login, logout e sessão por cookie HTTP-only. Ver [[seguranca-autenticacao]].
- **Gestão de Perfil**: alteração de e-mail, alteração de senha e exclusão da conta do usuário autenticado.
- **Recuperação de senha**: código temporário enviado por e-mail SMTP configurado localmente de forma segura, com assistente para Gmail e Outlook/Microsoft usando senha de app. Ver [[recuperacao-senha]].
- **Contas-correntes**: cadastro, edição, listagem, arquivamento e restauração de contas com suporte a naturezas distintas (`liquidity` - liquidez, `wallet` - carteira física, `investment` - investimento) e moedas múltiplas (`BRL`, `USD`, `EUR`, `GBP`). Ver [[contas-correntes]].
- **Lançamentos normais**: receitas, despesas, transferências, câmbio e investimentos manuais com impacto em saldo e suporte a taxas de câmbio históricas quando houver conversão entre moedas. Ver [[lancamentos]].
- **Recorrência e Parcelamento**: suporte a séries de lançamentos periódicos ou parcelados com acompanhamento de índice de parcelas e conciliação bancária (`reconciled_at`). Ver [[lancamentos]].
- **Cartões de Crédito**: cadastro de cartões com limite, emissor, bandeira, fechamento, vencimento e conta preferencial de pagamento. Lançamentos de despesas e receitas no cartão por fatura mensal (formato `AAAA-MM`), conciliação de lançamentos, compras parceladas/recorrentes, movimentação entre faturas e fluxo de pagamento de fatura integrado às contas-correntes. Ver [[cartoes]].
- **Limites de Gastos (Metas/Budgets)**: estabelecimento de limites de despesas mensais por categoria e subcategoria. Ver [[limites-gastos]].
- **Portfólio de Investimentos**: posições iniciais (`opening positions`) e operações de investimento. Suporte a tipos de ativos como ações/ETFs/BDRs (`stock`), cripto (`crypto`), fundos (`fund`), renda fixa (`fixed_income`), previdência privada (`private_pension`), poupança (`savings`) e outros (`other`). Ver [[investimentos-portfolio]].
- **Precificação e Validação de Ativos**:
  - Integração com Yahoo Finance (ações e fundos) e CoinGecko/Yahoo (criptoativos) para cotações automáticas.
  - Integração com o Sistema Gerenciador de Séries Temporais (SGS) do Banco Central para obter CDI, SELIC, IPCA, IGP-M e TR para o cálculo do rendimento acumulado de renda fixa (com fallback local seguro).
  - Cálculo de impostos de renda fixa: IOF (tabela regressiva até 30 dias) e Imposto de Renda (tabela regressiva de 22,5% a 15% por prazo de retenção).
  - Ver [[investimentos-portfolio]].
- **Categorias e Tags**: cadastro, edição, listagem e exclusão de categorias (tipo receita, despesa, investimento), subcategorias e múltiplos marcadores (tags) por transação. Ver [[categorias-tags-gestao]].
- **Classificação Assistida**: sugestão local de categoria e subcategoria por correspondência exata normalizada com o histórico do próprio usuário, sem dependência de internet. Ver [[classificacao-assistida]].
- **Cockpit e Relatórios**: resumo financeiro mensal com seletor de mês, saldos por moeda, planejamento recorrente, dívidas parceladas, portfólio por tipo, maiores receitas/despesas, relatórios por categoria, subcategoria, conta, tag e fluxo diário. Ver [[relatorios]] e [[arquitetura]].
- **Importação de Dados**:
  - Leitura e importação de extratos do Organizze em formato `.csv` ou `.xls`.
  - Importação de lançamentos por meio de planilhas de modelo do sistema (`.xlsx`) para contas e cartões.
  - Ver [[importacao-organizze]].
- **Histórico de Operações**: auditoria funcional somente leitura com filtros, busca, agrupamentos e rastreio de lotes por `operation_batch_id`. Ver [[historico-operacoes]].
- **Sobre o app**: tela informativa no grupo Usuário com objetivo, funcionalidades, tecnologias, contato e infraestrutura mínima. Ver [[sobre-app]].
- **Interface web estática**: painéis locais em `web/`, sem dependências externas de frontend. Ver [[arquitetura]] e [[adr/0001-stack-local-sem-framework]].
- **Distribuição desktop**: pacotes macOS e Windows com instaladores, modo local e launchers opcionais para rede local confiável. Ver [[distribuição]].

## Fora do escopo atual

- Open Finance, sincronização em nuvem ou integrações bancárias automáticas diretas.
- Multiusuário concorrente em rede; o modo LAN é apenas exposição local controlada para redes confiáveis, sem transformar o app em serviço multiusuário.

## Regras funcionais

- Toda operação de dados financeiros exige usuário autenticado.
- Dados financeiros pertencem ao usuário autenticado e não podem ser acessados por outro usuário.
- Contas e cartões arquivados não aparecem na lista principal, mas podem ser restaurados.
- A moeda de uma conta com lançamentos ativos não pode ser alterada.
- Receitas aumentam o saldo da conta de origem.
- Despesas reduzem o saldo da conta de origem.
- Transferências reduzem o saldo da conta de origem e aumentam o saldo da conta de destino.
- Transferências exigem contas diferentes e com a mesma moeda. Câmbio entre contas de moedas diferentes é registrado como tipo próprio, com valor de destino e taxa de câmbio.
- Cada lançamento exige descrição, data válida, valor maior que zero, conta/cartão e categoria quando o tipo exigir classificação. Tags são opcionais.
- Operações financeiras e administrativas relevantes devem gerar registro no Histórico de Operações, sem armazenar senhas, tokens ou segredos.
- Categorias, subcategorias e tags em uso por lançamentos não podem ser excluídas.
- Sugestões de classificação devem ser isoladas por usuário e grupo, não sobrescrever escolhas manuais e só preencher os campos quando houver suporte e dominância suficientes.
- Importações podem criar categorias, subcategorias e tags inexistentes para o usuário autenticado.
- Linhas importadas com situação diferente de `Pago` são ignoradas e reportadas.
- Pagamento de fatura de cartão de crédito só é permitido em contas da mesma moeda do cartão e gera uma transação de despesa automática na conta escolhida.
- Relatórios e limites consideram lançamentos de cartão pela competência da fatura (`invoice_month`), não pela data da compra.
- Cockpit considera receitas/despesas/aportes em múltiplas moedas no mês selecionado, e o planejamento recorrente inclui lançamentos recorrentes de cartões.
- Cockpit considera faturas de cartão por competência (`invoice_month`) no mês selecionado, mantendo a fatura visível mesmo após pagamento e excluindo o pagamento agregado das despesas analíticas para evitar duplicidade.

## Regras de segurança

- Senhas são armazenadas com PBKDF2-HMAC-SHA256 e salt por senha.
- Tokens de recuperação são armazenados como hash e expiram em 15 minutos.
- Tokens de sessão são armazenados somente como hash no banco.
- Sessões expiram definitivamente 30 dias após a criação.
- Ao trocar ou redefinir a senha, todas as sessões ativas do usuário são encerradas.
- Toda mutação exige `Host` e `Origin` válidos como proteção contra CSRF.
- A configuração SMTP fica criptografada por usuário em `data/email_config_user_{id}.enc`.
- A chave local fica em `data/email_config.key` ou na variável `SISTEMA_FINANCEIRO_CONFIG_KEY`.
- Pacotes distribuíveis não incluem credenciais SMTP; cada usuário configura seu próprio remetente localmente.
- Arquivos de runtime em `data/` não devem ser versionados.
- Upload de importação é limitado a 5 MB.
- Identificadores recebidos pela API devem ser validados contra o usuário autenticado.
- Detalhes completos de bloqueio de tentativas, cookies e headers defensivos em [[seguranca-autenticacao]] e [[recuperacao-senha]].
- Exposição em LAN deve configurar `APP_URL`, `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`; acesso remoto deve usar reverse-proxy com HTTPS.
- Exposição em LAN via HTTP deve gerar alerta de segurança sem impedir a inicialização; HTTP local continua permitido.

## Requisitos não funcionais

- O app deve rodar localmente em macOS com Python 3 e bibliotecas padrão (ou extensões mínimas offline).
- Pacotes distribuídos devem oferecer modo local por padrão e modo rede/LAN apenas por launcher explícito.
- O frontend deve continuar simples, responsivo e sem build step.
- Valores monetários devem ser persistidos em centavos.
- O banco SQLite deve ser criado automaticamente em `data/finance.db`.
- O SQLite deve operar com WAL e espera curta por locks para tolerar uso local compartilhado leve, sem transformar o app em sistema multiusuário em rede.
- Operações de escrita devem manter transações curtas e evitar chamadas externas enquanto seguram conexão aberta.
- Consultas de classificação assistida devem usar descrições normalizadas indexadas e não percorrer todo o histórico a cada digitação.
- Mudanças de schema devem ser idempotentes para preservar bancos locais existentes.
- Mensagens de erro devem ser claras para o usuário e não expor detalhes internos.

## Critérios de aceite gerais

- Um usuário novo consegue criar conta, categoria/tag e lançamento sem configuração externa.
- A lista de contas reflete imediatamente o impacto dos lançamentos.
- A importação informa total lido, importado, ignorado e motivos de rejeição.
- A documentação de arquitetura ([[arquitetura]]) deve ser atualizada quando endpoints, tabelas ou fluxos centrais mudarem.

## Changelog

- `1.8` — 2026-08-02 — Cockpit documentado como resumo mensal navegável por seletor de mês, preservando faturas de cartão por competência mesmo após pagamento.
- `1.7` — 2026-07-24 — Incluída a tela Sobre no escopo implementado do menu Usuário.
- `1.6` — 2026-07-23 — Incluído o MVP local de classificação assistida por correspondência exata normalizada.
- `1.5` — 2026-07-09 — Histórico de Operações incluído no escopo implementado e nas regras funcionais.
- `1.4` — 2026-07-05 — Regras de segurança atualizadas para configuração SMTP criptografada e isolada por usuário.
- `1.3` — 2026-07-04 — Escopo atualizado com distribuição desktop, modo rede/LAN confiável e exigência de configuração explícita de hosts/origens.
- `1.2` — 2026-07-03 — Requisitos não funcionais atualizados para explicitar WAL, espera por locks e transações curtas no SQLite.
- `1.1` — 2026-06-29 — Adição de frontmatter, wikilinks para specs por módulo e referência cruzada com ADRs.
- `1.0` — escopo original consolidado.

## Relacionados

- [[arquitetura]]
- [[visao-produto]]
- [[roadmap]]
- [[glossario]]
