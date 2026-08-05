// spec: docs/specs/instrucoes-app.md v1.3 — conteúdo estático da central de ajuda
// Este módulo é puro e sem estado: o conteúdo é versionado no frontend e
// disponível offline, sem dependência de backend ou internet.

export const INSTRUCTIONS_CONTENT = [
  {
    id: "primeiros-passos",
    title: "Primeiros passos",
    topics: [
      {
        id: "criar-conta",
        title: "Criar minha conta",
        summary: "Como fazer o primeiro acesso ao app de forma segura.",
        content: [
          "Na tela inicial, escolha Criar acesso, preencha nome, e-mail e uma senha com pelo menos 8 caracteres.",
          "Guarde bem a senha: ela não pode ser recuperada sem o processo de redefinição por e-mail configurado em Preferências.",
        ],
        searchTerms: ["cadastro", "login", "acesso", "senha", "primeiro acesso"],
        relatedModule: "Login",
        route: null,
        contextualTopicId: null,
      },
      {
        id: "primeira-conta",
        title: "Cadastrar minha primeira conta-corrente",
        summary: "Contas representam dinheiro que você tem hoje em banco, corretora ou carteira.",
        content: [
          "Vá em Cadastro > Minhas Contas, clique em Nova conta, dê um nome (ex.: Conta corrente, Investimentos), escolha o tipo e informe o saldo inicial.",
          "O saldo inicial é apenas o ponto de partida; depois você poderá lançar movimentações reais.",
        ],
        searchTerms: ["conta", "banco", "saldo inicial", "cadastrar conta"],
        relatedModule: "Minhas Contas",
        route: "accounts",
        contextualTopicId: "primeira-conta",
      },
      {
        id: "primeiro-cartao",
        title: "Cadastrar meu primeiro cartão de crédito",
        summary: "Cartões são usados para acompanhar compras e faturas, sem alterar o saldo da conta-corrente imediatamente.",
        content: [
          "Em Cadastro > Meus Cartões, clique em Novo cartão, informe nome, melhor dia de compra e dia de vencimento.",
          "Opcionalmente, escolha uma conta preferencial para pagamento da fatura. O cartão não mexe no saldo da conta até você pagar a fatura.",
        ],
        searchTerms: ["cartão", "crédito", "fatura", "vencimento", "fechamento"],
        relatedModule: "Meus Cartões",
        route: "creditCards",
        contextualTopicId: "primeiro-cartao",
      },
      {
        id: "categorias-tags",
        title: "Criar categorias e tags",
        summary: "Categorias organizam seus lançamentos por natureza; tags permitem agrupar lançamentos de formas personalizadas.",
        content: [
          "Acesse Gestão > Categorias e tags. Crie categorias como Moradia, Alimentação e Transporte.",
          "Dentro de cada categoria, crie subcategorias (ex.: Supermercado dentro de Alimentação). Use tags livremente para marcações extras, como Viagem 2026.",
        ],
        searchTerms: ["categoria", "subcategoria", "tag", "classificação", "grupo"],
        relatedModule: "Categorias",
        route: "classifications",
        contextualTopicId: "categorias-tags",
      },
      {
        id: "primeiro-lancamento",
        title: "Fazer meu primeiro lançamento",
        summary: "Um lançamento registra entrada, saída ou movimentação do seu dinheiro.",
        content: [
          "Em Lançamentos > Extrato de Contas, clique em Novo lançamento, escolha o tipo (receita, despesa, transferência, investimento etc.), selecione a conta, data, valor e categoria.",
          "Salve. O saldo da conta será atualizado automaticamente.",
        ],
        searchTerms: ["lançamento", "receita", "despesa", "extrato", "movimentação"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "primeiro-lancamento",
      },
    ],
  },
  {
    id: "lancamentos-contas",
    title: "Lançamentos de contas",
    topics: [
      {
        id: "lancar-receitas-despesas",
        title: "Lançar receitas e despesas",
        summary: "Registre entradas e saídas simples na conta-corrente.",
        content: [
          "No Extrato de Contas, use o tipo Receita para salários, rendimentos ou reembolsos. Use Despesa para gastos do dia a dia.",
          "Preencha descrição, valor, data, categoria e, se quiser, tags. O saldo da conta muda imediatamente.",
        ],
        searchTerms: ["receita", "despesa", "gasto", "entrada", "saída"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "lancar-receitas-despesas",
      },
      {
        id: "previsto-conciliado",
        title: "Diferença entre saldo previsto e saldo conciliado",
        summary: "O saldo previsto considera todos os lançamentos; o saldo conciliado considera apenas os já confirmados.",
        content: [
          "Cada lançamento pode estar previsto (registrado, mas ainda não confirmado) ou conciliado (já constatado na realidade, como uma compra que já passou no extrato bancário).",
          "O saldo previsto mostra o futuro próximo; o saldo conciliado mostra o que de fato aconteceu. Conciliar um lançamento não altera o valor, apenas marca que ele está confirmado.",
        ],
        searchTerms: ["previsto", "conciliado", "saldo", "confirmar", "reconciliação"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "previsto-conciliado",
      },
      {
        id: "parcelamento-recorrencia-contas",
        title: "Parcelamento e recorrência no extrato",
        summary: "Divida uma compra em parcelas ou repita lançamentos automaticamente.",
        content: [
          "Ao criar um lançamento, escolha Parcelada para gerar várias parcelas iguais em meses seguintes.",
          "Escolha Recorrente para repetir o mesmo valor em intervalos fixos (mensal, quinzenal etc.). Você pode editar ou excluir a série inteira ou apenas uma parcela futura.",
        ],
        searchTerms: ["parcela", "parcelado", "recorrente", "série", "repetir"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "parcelamento-recorrencia-contas",
      },
      {
        id: "transferencias",
        title: "Transferências entre contas",
        summary: "Mova dinheiro de uma conta para outra sem criar receita ou despesa.",
        content: [
          "No Extrato de Contas, use o tipo Transferência. Selecione a conta de origem, a conta de destino e o valor.",
          "A transferência não entra como receita nem como despesa no Cockpit. Para transferências em moeda estrangeira, informe a taxa de câmbio.",
        ],
        searchTerms: ["transferência", "entre contas", "movimentação interna", "câmbio"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "transferencias",
      },
      {
        id: "investimentos-aportes",
        title: "Lançar investimentos e aportes",
        summary: "Registre compras, aportes e aplicações que aumentam uma posição existente ou criam uma nova no Portfólio.",
        content: [
          "No Extrato de Contas, use o tipo Investimento/Aporte quando comprar um ativo, fazer um aporte ou receber uma aplicação. Esse lançamento sai do saldo da conta-corrente e é contabilizado como uma operação do ativo.",
          "Se já houver uma posição com os mesmos dados (mesma carteira, tipo, ticker/nome, CNPJ, indexador e vencimento) no Portfólio, o aporte é somado a ela. Se não houver, o app cria uma nova posição automaticamente.",
          "Não é o mesmo que Transferência: uma transferência apenas move saldo entre contas e não cria operação de ativo. Preencha Valor investido, Ativo (ticker/código), Nome do ativo, CNPJ (para fundos), Quantidade e Preço unitário (quando aplicável), além de custos como corretagem, emolumentos, impostos e outros. Resgates e dividendos devem ser lançados com os tipos apropriados.",
        ],
        searchTerms: ["investimento", "aporte", "compra", "aplicação", "posição", "ativo", "transferência", "conta investimento"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "investimentos-aportes",
      },
      {
        id: "cambio-moedas",
        title: "Lançar câmbio e moedas estrangeiras",
        summary: "Registre receitas, despesas e transferências em moedas diferentes do Real.",
        content: [
          "No Extrato de Contas, ao criar um lançamento em uma conta com moeda estrangeira (ex.: USD, EUR), informe o valor na moeda original e a taxa de câmbio.",
          "O app converte o valor para BRL usando a taxa informada ou, quando não houver cotação manual, a última PTAX de venda disponível até a data do lançamento. O valor original é preservado para consulta e o valor em BRL é usado nos relatórios e no Cockpit.",
        ],
        searchTerms: ["câmbio", "moeda estrangeira", "dólar", "euro", "taxa de câmbio", "PTAX", "USD", "EUR"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "cambio-moedas",
      },
      {
        id: "conciliar-lancamento",
        title: "Como conciliar um lançamento",
        summary: "Marque um lançamento como confirmado para aproximar o saldo do extrato bancário real.",
        content: [
          "No Extrato de Contas, localize o lançamento e clique na ação de conciliação (ícone de conferência).",
          "O lançamento passa do estado previsto para conciliado. Você pode desfazer a conciliação se necessário.",
        ],
        searchTerms: ["conciliar", "confirmar", "banco", "extrato", "real"],
        relatedModule: "Extrato de Contas",
        route: "transactions",
        contextualTopicId: "conciliar-lancamento",
      },
    ],
  },
  {
    id: "cartoes",
    title: "Cartões",
    topics: [
      {
        id: "cadastrar-cartao",
        title: "Cadastrar um cartão de crédito",
        summary: "Registre seus cartões para acompanhar compras e faturas.",
        content: [
          "Em Cadastro > Meus Cartões, clique em Novo cartão, dê um nome, escolha o melhor dia de compra e o vencimento.",
          "Se quiser, defina uma conta-corrente preferencial para pagar a fatura. O cartão aparecerá nas telas de Fatura e no Cockpit.",
        ],
        searchTerms: ["cartão", "cadastro", "crédito", "vencimento", "fechamento"],
        relatedModule: "Meus Cartões",
        route: "creditCards",
        contextualTopicId: "cadastrar-cartao",
      },
      {
        id: "lancar-compras-cartao",
        title: "Lançar compras no cartão",
        summary: "Cada compra é registrada separadamente e agrupada na fatura do mês.",
        content: [
          "Em Lançamentos > Fatura de Cartões, escolha o cartão e a fatura, depois clique em Nova compra.",
          "Informe descrição, valor, categoria e data. A compra entra na fatura correspondente à data e ao fechamento do cartão.",
        ],
        searchTerms: ["compra", "cartão", "fatura", "lançar", "despesa cartão"],
        relatedModule: "Fatura de Cartões",
        route: "cardLaunches",
        contextualTopicId: "lancar-compras-cartao",
      },
      {
        id: "fatura-pagamento",
        title: "Diferença entre fatura e pagamento de fatura",
        summary: "Pagar a fatura registra a saída de dinheiro da conta-corrente, mas mantém o histórico das compras.",
        content: [
          "A fatura é a lista de compras feitas no cartão durante um período. O pagamento da fatura é uma transferência da sua conta-corrente para quitar essa dívida.",
          "Ao pagar, o app cria um lançamento de saída na conta-corrente, mas as compras continuam registradas no cartão para histórico e relatórios. O pagamento não apaga nem altera as compras.",
        ],
        searchTerms: ["fatura", "pagamento", "quitar", "conta corrente", "compras cartão"],
        relatedModule: "Fatura de Cartões",
        route: "cardLaunches",
        contextualTopicId: "fatura-pagamento",
      },
      {
        id: "parcelada-recorrente-cartao",
        title: "Compra parcelada e recorrente no cartão",
        summary: "Divida uma compra em parcelas ou repita gastos fixos do cartão.",
        content: [
          "Ao lançar uma compra no cartão, escolha Parcelada para dividir o valor em meses seguintes (ex.: 3x de R$ 100).",
          "Escolha Recorrente para gastos fixos, como assinaturas mensais. A fatura de cada mês mostra apenas a parcela ou recorrência daquele mês.",
        ],
        searchTerms: ["parcelado", "recorrente", "assinatura", "cartão", "mensalidade"],
        relatedModule: "Fatura de Cartões",
        route: "cardLaunches",
        contextualTopicId: "parcelada-recorrente-cartao",
      },
      {
        id: "antecipar-parcelas",
        title: "Como antecipar parcelas",
        summary: "Mova parcelas futuras para a fatura atual quando fizer um pagamento antecipado.",
        content: [
          "No app, você pode alterar a fatura de uma compra parcelada para uma fatura anterior, desde que ela ainda esteja aberta.",
          "Isso é útil quando o banco antecipa parcelas ou quando você decide pagar tudo de uma vez. O valor total da fatura será ajustado.",
        ],
        searchTerms: ["antecipar", "parcela", "adiantar", "pagamento antecipado"],
        relatedModule: "Fatura de Cartões",
        route: "cardLaunches",
        contextualTopicId: "antecipar-parcelas",
      },
      {
        id: "pagar-fatura",
        title: "Como pagar a fatura",
        summary: "Registre o pagamento da fatura para atualizar a conta-corrente.",
        content: [
          "Na tela de Fatura de Cartões, clique em Pagar fatura, selecione a conta de saída e a data do pagamento.",
          "O app cria um lançamento de saída na conta-corrente. A fatura passa a ser considerada paga, mas as compras continuam visíveis.",
        ],
        searchTerms: ["pagar fatura", "quitar", "conta", "data pagamento"],
        relatedModule: "Fatura de Cartões",
        route: "cardLaunches",
        contextualTopicId: "pagar-fatura",
      },
    ],
  },
  {
    id: "portfolio",
    title: "Portfólio",
    topics: [
      {
        id: "entender-portfolio",
        title: "O que é o Portfólio",
        summary: "O Portfólio mostra tudo o que você possui em investimentos, consolidado por tipo e moeda.",
        content: [
          "Acesse Gestão > Portfólio. A tela exibe suas posições abertas (ações, fundos, renda fixa, cripto, previdência, poupança etc.), o valor investido, o valor atual e o resultado.",
          "Posições encerradas vão para a área de histórico.",
        ],
        searchTerms: ["portfólio", "investimentos", "posições", "carteira", "ativos"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "entender-portfolio",
      },
      {
        id: "posicao-movimentacao",
        title: "Diferença entre posição e movimentação",
        summary: "O Portfólio registra a posição inicial; aportes, compras e resgates são registrados pelos lançamentos da conta.",
        content: [
          "Cadastre um ativo no Portfólio apenas para registrar o que você já possui em carteira antes de começar a usar o app (posição inicial).",
          "A partir daí, toda nova compra, aporte, resgate ou dividendo deve ser registrado como lançamento na conta-corrente ou de investimento, usando os tipos apropriados. O Portfólio consolida essas movimentações e calcula o resultado. Aportes criam novas posições se o ativo ainda não existir ou somam à posição existente. Não use o Portfólio como substituto do Extrato de Contas.",
        ],
        searchTerms: ["posição", "movimentação", "aporte", "resgate", "lançamento", "ativo", "posição inicial", "carteira"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "posicao-movimentacao",
      },
      {
        id: "cadastrar-renda-fixa",
        title: "Como cadastrar renda fixa",
        summary: "Registre CDBs, LCIs, LCAs, tesouro e outros títulos de renda fixa.",
        content: [
          "No Portfólio, clique em Novo ativo, escolha o tipo Renda Fixa, informe o valor investido, data de aplicação, vencimento, indexador e taxa.",
          "Se for pós-fixado ou híbrido, o app pode buscar o indexador (CDI, IPCA, SELIC) automaticamente.",
        ],
        searchTerms: ["renda fixa", "CDB", "LCI", "LCA", "tesouro", "título"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "cadastrar-renda-fixa",
      },
      {
        id: "tipos-renda-fixa",
        title: "Pré-fixada, pós-fixada e híbrida",
        summary: "Entenda as três modalidades de renda fixa em linguagem prática.",
        content: [
          "Pré-fixada: você já sabe o percentual total de retorno no momento da aplicação (ex.: 10% ao ano).",
          "Pós-fixada: o rendimento acompanha um indexador, como o CDI (ex.: 100% do CDI).",
          "Híbrida: parte do rendimento é fixa e parte acompanha um indexador (ex.: CDI + 2% ao ano ou IPCA + 5%). A escolha depende da sua expectativa sobre juros e inflação.",
        ],
        searchTerms: ["pré-fixada", "pós-fixada", "híbrida", "CDI", "IPCA", "SELIC", "indexador"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "tipos-renda-fixa",
      },
      {
        id: "acoes-fundos",
        title: "Ações, fundos, cripto e previdência",
        summary: "Cadastre posições iniciais de renda variável, cripto, fundos e previdência que você já possui em carteira.",
        content: [
          "Use essa tela apenas para registrar ativos que você já possui antes de começar a usar o app (posição inicial). Aportes e compras futuras devem ser registrados pelo Extrato de Contas como lançamentos do tipo Investimento/Aporte.",
          "Preencha Carteira (conta onde o ativo está custodiado), Data de aquisição, Custo total do lote, Ativo (ticker ou código, ex.: PETR4, BTC, XPML11) e Nome do ativo. Para fundos, informe também o CNPJ do fundo. Para previdência, escolha a subcategoria PGBL ou VGBL.",
          "Quando aplicável, preencha Quantidade e Preço médio para que o app acompanhe a evolução. Para ações, fundos e cripto, o app busca cotações de mercado automaticamente.",
        ],
        searchTerms: ["ações", "fundos", "cripto", "previdência", "cotação", "posição inicial", "ticker", "quantidade", "preço médio", "CNPJ"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "acoes-fundos",
      },
      {
        id: "cadastrar-poupanca",
        title: "Como cadastrar poupança",
        summary: "Registre posições de poupança com as datas de aniversário para cálculo automático de rendimento.",
        content: [
          "No Portfólio, clique em Novo ativo e escolha o tipo Poupança. Informe a conta, o nome do ativo e o valor investido.",
          "No campo Aniversários da poupança, cadastre cada data de aniversário seguida do valor aplicado naquele dia, usando o formato AAAA-MM-DD; valor. Por exemplo: 2026-01-05; 1.000,00. Use uma linha para cada aniversário.",
          "O app usa essas datas para calcular o rendimento mês a mês com a regra da poupança (TR + 0,5% ou TR + 70% da Selic).",
        ],
        searchTerms: ["poupança", "aniversário", "rendimento", "data", "formato", "AAAA-MM-DD"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "cadastrar-poupanca",
      },
      {
        id: "atualizar-valores",
        title: "Como atualizar valores manualmente",
        summary: "Substitua a cotação automática por um valor informado por você.",
        content: [
          "Para ativos sem cotação disponível ou quando você discordar do valor de mercado, use a opção de atualizar valor manual no Portfólio.",
          "O novo valor passa a ser usado no cálculo do patrimônio até que seja alterado novamente.",
        ],
        searchTerms: ["atualizar valor", "cotação manual", "valor de mercado", "patrimônio"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "atualizar-valores",
      },
      {
        id: "resgatar-encerrar",
        title: "Como resgatar ou encerrar uma posição",
        summary: "Transforme uma posição aberta em histórico quando ela deixar de existir.",
        content: [
          "No Portfólio, use Resgatar para registrar uma retirada parcial e Encerrar quando a posição for totalmente liquidada.",
          "O app move os dados para a área de histórico e, se houver, atualiza a conta-corrente correspondente.",
        ],
        searchTerms: ["resgatar", "encerrar", "histórico", "liquidação", "vender"],
        relatedModule: "Portfólio",
        route: "portfolio",
        contextualTopicId: "resgatar-encerrar",
      },
    ],
  },
  {
    id: "cockpit",
    title: "Cockpit",
    topics: [
      {
        id: "entender-cockpit",
        title: "O que é o Cockpit",
        summary: "O Cockpit é a tela inicial que resume sua situação financeira do mês.",
        content: [
          "Acesse Cockpit no menu lateral. Você verá receitas, despesas, aportes, taxa de poupança, saldos por moeda, planejamento do mês, dívidas, maiores despesas e receitas, além de resumo do portfólio.",
          "Use o seletor de mês para navegar no tempo.",
        ],
        searchTerms: ["cockpit", "resumo", "dashboard", "visão geral", "mês"],
        relatedModule: "Cockpit",
        route: "cockpit",
        contextualTopicId: "entender-cockpit",
      },
      {
        id: "taxa-poupanca",
        title: "Como interpretar a taxa de poupança",
        summary: "A taxa de poupança mede quanto do que entrou no mês sobrou após despesas de consumo.",
        content: [
          "A fórmula é: (receitas do mês - despesas de consumo do mês) / receitas do mês.",
          "Investimentos, transferências, câmbio e pagamentos de fatura não entram como despesa de consumo. Uma taxa positiva indica que você gastou menos do que recebeu.",
        ],
        searchTerms: ["taxa de poupança", "poupança", "economia", "sobra"],
        relatedModule: "Cockpit",
        route: "cockpit",
        contextualTopicId: "taxa-poupanca",
      },
      {
        id: "planejamento-mes",
        title: "Como usar o planejamento do mês",
        summary: "Veja receitas e despesas recorrentes esperadas antes que elas aconteçam.",
        content: [
          "A seção Planejamento do mês lista lançamentos recorrentes previstos para o mês selecionado.",
          "Ela ajuda a antecipar contas fixas e receitas garantidas. Os valores são projetados e podem mudar quando você cadastrar lançamentos reais.",
        ],
        searchTerms: ["planejamento", "recorrente", "previsão", "mês", "contas fixas"],
        relatedModule: "Cockpit",
        route: "cockpit",
        contextualTopicId: "planejamento-mes",
      },
      {
        id: "tendencias",
        title: "Como usar a aba Tendências",
        summary: "Análise mensal local com evolução de receitas e despesas, Budget x Realizado e achados.",
        content: [
          "No Cockpit, acesse a aba Tendências. O app mostra gráficos mês a mês, compara o orçamento planejado com o gasto real e destaca padrões, como assinaturas recorrentes e eventos pontuais.",
          "A análise é feita localmente, sem depender de internet.",
        ],
        searchTerms: ["tendências", "budget", "realizado", "análise", "gráfico"],
        relatedModule: "Cockpit",
        route: "cockpit",
        contextualTopicId: "tendencias",
      },
      {
        id: "saude-financeira",
        title: "Como usar a aba Saúde Financeira",
        summary: "Acompanhe sua saúde financeira através de indicadores e histórico.",
        content: [
          "A aba Saúde mostra o score de saúde financeira com base em pilares como liquidez, endividamento, poupança e diversificação.",
          "Use o histórico para ver a evolução ao longo dos meses.",
        ],
        searchTerms: ["saúde financeira", "score", "indicadores", "endividamento", "liquidez"],
        relatedModule: "Cockpit",
        route: "cockpit",
        contextualTopicId: "saude-financeira",
      },
    ],
  },
  {
    id: "gestao",
    title: "Gestão",
    topics: [
      {
        id: "limites-gastos",
        title: "Limites de gastos",
        summary: "Defina orçamentos mensais por categoria ou subcategoria.",
        content: [
          "Em Gestão > Limites, crie um limite para uma categoria (ex.: Alimentação) e informe o valor máximo do mês.",
          "O Cockpit e a tela de Limites mostram quanto já foi consumido e quanto resta. Limites são sempre por mês.",
        ],
        searchTerms: ["limite", "orçamento", "meta", "gasto", "categoria"],
        relatedModule: "Limites",
        route: "limits",
        contextualTopicId: "limites-gastos",
      },
      {
        id: "relatorios",
        title: "Relatórios",
        summary: "Analise seus lançamentos agrupados de várias formas.",
        content: [
          "Em Gestão > Relatórios, escolha uma aba: categorias, subcategorias, contas, tags ou fluxo diário.",
          "Selecione o mês e, se quiser, filtros adicionais. Use o relatório de evolução por categoria para ver a série histórica.",
        ],
        searchTerms: ["relatório", "análise", "categoria", "evolução", "fluxo diário"],
        relatedModule: "Relatórios",
        route: "reports",
        contextualTopicId: "relatorios",
      },
      {
        id: "importacao-dados",
        title: "Importação de dados",
        summary: "Traga lançamentos de planilhas do Organizze ou do modelo do próprio sistema.",
        content: [
          "Em Gestão > Importação, escolha a origem (Organizze ou modelo próprio), selecione o arquivo e a conta ou cartão de destino.",
          "Para o modelo próprio, baixe o arquivo exemplo, preencha e envie. Sempre revise o resultado antes de continuar.",
        ],
        searchTerms: ["importar", "organizze", "planilha", "modelo"],
        relatedModule: "Importação",
        route: "imports",
        contextualTopicId: "importacao-dados",
      },
      {
        id: "historico-operacoes",
        title: "Histórico de Operações",
        summary: "Consulte tudo o que foi alterado no app para fins de auditoria.",
        content: [
          "Em Gestão > Histórico, você encontra registros de criação, alteração e exclusão de contas, cartões, lançamentos, categorias, limites e outras operações.",
          "Use filtros por data, módulo, tipo e conta/cartão. O histórico não pode ser editado.",
        ],
        searchTerms: ["histórico", "auditoria", "operações", "log", "rastreabilidade"],
        relatedModule: "Histórico",
        route: "operationHistory",
        contextualTopicId: "historico-operacoes",
      },
      {
        id: "simulacao-borboleta",
        title: "Simulação (Efeito Borboleta)",
        summary: "Simule o impacto de uma despesa ou receita futura no saldo da conta.",
        content: [
          "Em Gestão > Efeito Borboleta, crie uma simulação informando data, valor, tipo e se é parcelada ou recorrente.",
          "O app projeta o saldo da conta ao longo do tempo e mostra a diferença em relação à situação atual. A simulação não cria lançamentos reais.",
        ],
        searchTerms: ["simulação", "efeito borboleta", "projeção", "futuro", "impacto"],
        relatedModule: "Simulação",
        route: "simulations",
        contextualTopicId: "simulacao-borboleta",
      },
    ],
  },
  {
    id: "preferencias",
    title: "Preferências",
    topics: [
      {
        id: "recuperacao-email",
        title: "Configurar recuperação por e-mail",
        summary: "Ative a recuperação de senha por SMTP para não ficar preso caso esqueça a senha.",
        content: [
          "Em Usuário > Preferências, acesse a seção Recuperação por e-mail.",
          "Informe servidor SMTP, porta, remetente e senha de app. A configuração é criptografada e armazenada localmente. Quando ativada, você poderá solicitar um código de redefinição de senha na tela de login.",
        ],
        searchTerms: ["SMTP", "e-mail", "recuperação de senha", "senha de app", "configuração"],
        relatedModule: "Preferências",
        route: "user",
        contextualTopicId: "recuperacao-email",
      },
      {
        id: "configurar-ia",
        title: "Configurar IA para Tendências",
        summary: "A IA é opcional e só reescreve o resumo da aba Tendências.",
        content: [
          "Ainda em Usuário > Preferências, a seção Configuração de IA permite ligar um provedor externo (OpenAI, Groq etc.) para reescrever o resumo do mês.",
          "A análise numérica continua sendo feita localmente. Se a IA estiver desligada ou falhar, o app exibe o resumo local automaticamente.",
        ],
        searchTerms: ["IA", "inteligência artificial", "tendências", "resumo", "OpenAI", "Groq"],
        relatedModule: "Preferências",
        route: "user",
        contextualTopicId: "configurar-ia",
      },
      {
        id: "tema-privacidade",
        title: "Tema e privacidade",
        summary: "Ajuste o tema claro/escuro e oculte valores na tela.",
        content: [
          "Em Usuário > Preferências, escolha entre tema claro ou escuro.",
          "Use o botão de olho no topo do app (ou pressione a tecla P) para ativar o modo de privacidade, que oculta valores numéricos sensíveis. A preferência de tema é salva no navegador local.",
        ],
        searchTerms: ["tema", "escuro", "claro", "privacidade", "ocultar valores"],
        relatedModule: "Preferências",
        route: "user",
        contextualTopicId: "tema-privacidade",
      },
    ],
  },
  {
    id: "privacidade-rede",
    title: "Privacidade e rede",
    topics: [
      {
        id: "ocultar-valores",
        title: "Como ocultar valores na tela",
        summary: "Proteja valores sensíveis quando alguém estiver próximo.",
        content: [
          "Clique no ícone de olho no canto superior direito ou pressione P no teclado.",
          "Todos os valores monetários serão substituídos por traços ou máscaras enquanto o modo estiver ativo. Clique novamente para desativar.",
        ],
        searchTerms: ["privacidade", "ocultar", "valores", "olho", "atalho"],
        relatedModule: null,
        route: null,
        contextualTopicId: "ocultar-valores",
      },
      {
        id: "modo-lan",
        title: "Como funciona o modo LAN",
        summary: "Use o app em outros dispositivos da mesma rede local.",
        content: [
          "O modo LAN permite acessar o Sistema Financeiro pelo IP da máquina onde ele está rodando, a partir de celulares, tablets ou outros computadores conectados à mesma rede confiável.",
          "1. Encerre o app se ele estiver rodando.",
          "2. Defina a variável de ambiente APP_HOST como 0.0.0.0 antes de iniciar. Exemplos: Windows PowerShell: $env:APP_HOST=\"0.0.0.0\"; python app.py — macOS/Linux: APP_HOST=0.0.0.0 python app.py — ou ajuste seu script de inicialização (.command, .bat, .sh) exportando a variável antes da linha que executa o app.",
          "3. Descubra o IP local da máquina onde o app está rodando: no Windows, abra o Prompt e execute ipconfig; no macOS/Linux, execute ifconfig ou ip addr. Procure o endereço IPv4 da interface ativa (geralmente começa com 192.168. ou 10.).",
          "4. No outro dispositivo, abra o navegador e acesse http://IP_DA_MAQUINA:8010. Se você alterou APP_PORT, use a porta correspondente.",
          "5. Se o acesso não funcionar, o firewall pode estar bloqueando a porta. Crie uma regra para permitir conexões na porta usada. Se não souber como fazer, uma IA externa (ChatGPT, Claude, Copilot etc.) pode ajudar a montar o comando ou passo a passo específico para o seu sistema operacional e firewall.",
          "6. Use o modo LAN apenas em redes confiáveis (casa ou escritório). Não exponha o app diretamente na internet. Para acesso remoto real, use um reverse-proxy com HTTPS (ex.: Nginx, Traefik ou Cloudflare Tunnel) e autenticação adicional. Uma IA externa também pode auxiliar na montagem dessa configuração, mas nunca compartilhe senhas, chaves ou arquivos de dados.",
        ],
        searchTerms: ["LAN", "rede", "compartilhar", "IP", "acesso remoto", "HTTPS", "firewall", "APP_HOST", "0.0.0.0"],
        relatedModule: null,
        route: null,
        contextualTopicId: "modo-lan",
      },
    ],
  },
  {
    id: "ajuda",
    title: "Ajuda",
    topics: [
      {
        id: "nao-encontrei-topico",
        title: "Não encontrei o que procurava",
        summary: "O que fazer quando um assunto ainda não está documentado aqui.",
        content: [
          "A central de ajuda cobre os fluxos principais do app.",
          "Para dúvidas técnicas, bugs ou sugestões, use o contato disponível na tela Sobre. Evite compartilhar senhas, chaves ou arquivos de dados ao pedir ajuda.",
        ],
        searchTerms: ["dúvida", "suporte", "contato", "não encontrei", "ajuda externa"],
        relatedModule: "Sobre",
        route: "about",
        contextualTopicId: null,
      },
    ],
  },
];

function normalizeText(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function buildTopicHaystack(topic) {
  return normalizeText(
    [topic.title, topic.summary, ...topic.content, ...topic.searchTerms].join(" ")
  );
}

const topicsCache = new Map();
const groupsCache = new Map();

function getCachedTopic(topic) {
  if (!topicsCache.has(topic.id)) {
    topicsCache.set(topic.id, { ...topic, _haystack: buildTopicHaystack(topic) });
  }
  return topicsCache.get(topic.id);
}

function getCachedGroup(group) {
  if (!groupsCache.has(group.id)) {
    groupsCache.set(group.id, {
      id: group.id,
      title: group.title,
      topics: group.topics.map(getCachedTopic),
    });
  }
  return groupsCache.get(group.id);
}

export function getAllInstructionTopics() {
  return INSTRUCTIONS_CONTENT.flatMap((group) => group.topics.map(getCachedTopic));
}

export function getInstructionGroups() {
  return INSTRUCTIONS_CONTENT.map(getCachedGroup);
}

export function findTopicById(topicId) {
  if (!topicId) return null;
  for (const group of INSTRUCTIONS_CONTENT) {
    const topic = group.topics.find((t) => t.id === topicId);
    if (topic) return getCachedTopic(topic);
  }
  return null;
}

export function findTopicByContextualId(contextualTopicId) {
  if (!contextualTopicId) return null;
  for (const group of INSTRUCTIONS_CONTENT) {
    const topic = group.topics.find((t) => t.contextualTopicId === contextualTopicId);
    if (topic) return getCachedTopic(topic);
  }
  return null;
}

export function searchInstructions(query) {
  const normalizedQuery = normalizeText(query).trim();
  if (!normalizedQuery) return getInstructionGroups();

  const terms = normalizedQuery.split(/\s+/).filter(Boolean);

  return INSTRUCTIONS_CONTENT
    .map((group) => {
      const topics = group.topics
        .map(getCachedTopic)
        .filter((topic) => terms.every((term) => topic._haystack.includes(term)));
      return topics.length > 0
        ? { id: group.id, title: group.title, topics }
        : null;
    })
    .filter(Boolean);
}
