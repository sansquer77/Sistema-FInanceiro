# Requisitos

## Objetivo

Manter um sistema financeiro local, privado e simples para controlar contas, saldos, lançamentos e classificações financeiras em SQLite, com interface web servida pelo próprio app Python.

## Escopo atual implementado

- **Autenticação local**: cadastro, login, logout e sessão por cookie HTTP-only.
- **Gestão de Perfil**: alteração de e-mail, alteração de senha e exclusão da conta do usuário autenticado.
- **Recuperação de senha**: código temporário enviado por e-mail SMTP configurado localmente de forma segura.
- **Contas-correntes**: cadastro, edição, listagem, arquivamento e restauração de contas com suporte a naturezas distintas (`liquidity` - liquidez, `wallet` - carteira física, `investment` - investimento) e moedas múltiplas (`BRL`, `USD`, `EUR`, `GBP`).
- **Lançamentos normais**: receitas, despesas e transferências manuais com impacto em saldo e suporte a taxas de câmbio históricas para conversão de moedas estrangeiras para BRL.
- **Recorrência e Parcelamento**: suporte a séries de lançamentos periódicos ou parcelados com acompanhamento de índice de parcelas e conciliação bancária (`reconciled_at`).
- **Cartões de Crédito**: cadastro de cartões com limite, emissor, bandeira, fechamento e vencimento. Lançamentos de despesas e receitas no cartão por fatura mensal (formato `AAAA-MM`), conciliação de lançamentos e fluxo de pagamento de fatura integrado às contas-correntes.
- **Limites de Gastos (Metas/Budgets)**: estabelecimento de limites de despesas mensais por categoria e subcategoria.
- **Portfólio de Investimentos**: posições iniciais (`opening positions`) e operações de investimento. Suporte a tipos de ativos como ações (`stock`), cripto (`crypto`), fundos (`fund`), renda fixa (`fixed_income`), poupança (`savings`) e outros (`other`).
- **Precificação e Validação de Ativos**:
  - Integração com Yahoo Finance (ações e fundos) e CoinGecko/Yahoo (criptoativos) para cotações automáticas.
  - Integração com o Sistema Gerenciador de Séries Temporais (SGS) do Banco Central para obter CDI, SELIC, IPCA, IGP-M e TR para o cálculo do rendimento acumulado de renda fixa (com fallback local seguro).
  - Cálculo de impostos de renda fixa: IOF (tabela regressiva até 30 dias) e Imposto de Renda (tabela regressiva de 22,5% a 15% por prazo de retenção).
- **Categorias e Tags**: cadastro, edição, listagem e exclusão de categorias (tipo receita, despesa, investimento), subcategorias e múltiplos marcadores (tags) por transação.
- **Importação de Dados**:
  - Leitura e importação de extratos do Organizze em formato `.csv` ou `.xls`.
  - Importação de lançamentos por meio de planilhas de modelo do sistema (`.xlsx`) para contas e cartões.
- **Interface web estática**: painéis locais em `web/`, sem dependências externas de frontend.

## Fora do escopo atual

- Open Finance, sincronização em nuvem ou integrações bancárias automáticas diretas.
- Multiusuário em rede (o uso esperado é local/monousuário).

## Regras funcionais

- Toda operação de dados financeiros exige usuário autenticado.
- Dados financeiros pertencem ao usuário autenticado e não podem ser acessados por outro usuário.
- Contas e cartões arquivados não aparecem na lista principal, mas podem ser restaurados.
- A moeda de uma conta com lançamentos ativos não pode ser alterada.
- Receitas aumentam o saldo da conta de origem.
- Despesas reduzem o saldo da conta de origem.
- Transferências reduzem o saldo da conta de origem e aumentam o saldo da conta de destino.
- Transferências exigem contas diferentes e com a mesma moeda (conversões e taxas de câmbio são aplicadas para fins de valorização em BRL, mas transferências diretas exigem mesma moeda).
- Cada lançamento exige descrição, data válida, valor maior que zero, conta/cartão, categoria e ao menos uma tag.
- Categorias, subcategorias e tags em uso por lançamentos não podem ser excluídas.
- Importações podem criar categorias, subcategorias e tags inexistentes para o usuário autenticado.
- Linhas importadas com situação diferente de `Pago` são ignoradas e reportadas.
- Pagamento de fatura de cartão de crédito só é permitido em contas da mesma moeda do cartão e gera uma transação de despesa automática na conta escolhida.

## Regras de segurança

- Senhas são armazenadas com PBKDF2-HMAC-SHA256 e salt por senha.
- Tokens de recuperação são armazenados como hash e expiram em 15 minutos.
- Ao redefinir a senha, sessões ativas do usuário são encerradas.
- A configuração SMTP fica criptografada em `data/email_config.enc`.
- A chave local fica em `data/email_config.key` ou na variável `SISTEMA_FINANCEIRO_CONFIG_KEY`.
- Arquivos de runtime em `data/` não devem ser versionados.
- Upload de importação é limitado a 5 MB.
- Identificadores recebidos pela API devem ser validados contra o usuário autenticado.

## Requisitos não funcionais

- O app deve rodar localmente com Python 3 e bibliotecas padrão (ou extensões mínimas offline).
- O frontend deve continuar simples, responsivo e sem build step.
- Valores monetários devem ser persistidos em centavos.
- O banco SQLite deve ser criado automaticamente em `data/finance.db`.
- Mudanças de schema devem ser idempotentes para preservar bancos locais existentes.
- Mensagens de erro devem ser claras para o usuário e não expor detalhes internos.

## Criterios de aceite gerais

- Um usuário novo consegue criar conta, categoria/tag e lançamento sem configuração externa.
- A lista de contas reflete imediatamente o impacto dos lançamentos.
- A importação informa total lido, importado, ignorado e motivos de rejeição.
- A documentação de arquitetura deve ser atualizada quando endpoints, tabelas ou fluxos centrais mudarem.
