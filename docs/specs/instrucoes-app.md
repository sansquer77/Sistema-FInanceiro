---
tipo: spec
area: usuario
status: implementado
versao: 1.8
atualizado: 2026-08-10
relacionados:
  - "[[sobre-app]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[score-saude-financeira]]"
  - "[[specs/consultor]]"
tags: [spec, "area/usuario", "status/implementado"]
aliases: ["Instruções do App", "Central de Ajuda Local"]
---

# Instruções do App

> [!info] Status
> **implementado** · área: `usuario` · atualizado em 2026-08-10 · relacionados: [[sobre-app]], [[lancamentos]], [[cartoes]], [[investimentos-portfolio]], [[score-saude-financeira]], [[specs/consultor]]

### Problema

O Sistema Financeiro deixou de ser usado apenas como projeto pessoal e já atende um grupo maior de usuários. Com isso, fluxos mais ricos — como lançamentos, faturas, portfólio, renda fixa, conciliação e saúde financeira — podem gerar dúvidas operacionais recorrentes. O app precisa de uma área de instruções acessível dentro da própria interface, sem depender de explicações externas ou suporte individual.

### Usuário

Usuário final que usa o app no dia a dia, sozinho ou em ambiente familiar, e precisa entender rapidamente como executar tarefas comuns sem conhecer a documentação técnica do projeto.

Também atende usuários novos que acabaram de instalar o app e precisam de uma trilha inicial para configurar contas, cartões, categorias e primeiros lançamentos.

### Jornada

1. O usuário cria uma conta um email válido
2. O usuário acessa o menu lateral em **Usuário**.
3. O usuário abre o novo módulo **Instruções**.
4. O usuário visualiza uma página de ajuda prática, organizada por temas e módulos.
5. O usuário pesquisa ou seleciona um tópico, como “Como cadastrar CDB?”, “Como pagar fatura?” ou “O que é conciliado?”.
6. O usuário expande um card/accordion e lê passos curtos com exemplos.
7. O usuário volta ao módulo funcional correspondente com clareza sobre a ação esperada.

### Dados

- `id`: identificador estável do tópico de instrução.
- `grupo`: seção principal do conteúdo, como `primeiros-passos`, `lancamentos-contas`, `cartoes`, `portfolio`, `cockpit`, `privacidade-rede`.
- `titulo`: título curto exibido no card ou accordion.
- `resumo`: descrição breve do objetivo do tópico.
- `conteudo`: passos e explicações em linguagem simples.
- `termos_busca`: palavras-chave associadas ao tópico para busca local.
- `modulo_relacionado`: módulo do app ao qual a instrução se refere, quando aplicável.
- `rota_modulo`: identificador interno de navegação para o módulo relacionado, quando houver link “Ir para o módulo”.
- `topico_contextual`: identificador do tópico que pode ser aberto a partir de um botão contextual `?` em telas funcionais.

### Regras

- O módulo **Instruções** deve aparecer no menu lateral dentro do grupo **Usuário**, entre **Preferências** e **Sobre**, salvo ajuste posterior de UX.
- O módulo **Sobre** permanece institucional; o módulo **Instruções** deve ser operacional e didático.
- O conteúdo deve ser estático, versionado no frontend e disponível offline.
- O conteúdo deve usar linguagem clara, direta e orientada a tarefas, evitando termos técnicos quando não forem necessários.
- O conteúdo deve conter exemplos práticos, mas sem usar dados reais do desenvolvedor, homologação ou usuários.
- A página deve permitir busca textual local por título, resumo, conteúdo e termos de busca.
- A organização visual deve usar cards por tema e accordions para leitura progressiva.
- O módulo não deve depender de IA, API externa, servidor adicional ou conexão com internet.
- O módulo não deve alterar dados financeiros, criar lançamentos ou executar ações; ele apenas orienta o usuário.
- Quando houver botão ou link contextual para um módulo funcional, a navegação deve ser interna e não deve alterar filtros ou dados do módulo de destino.
- A primeira versão deve ter links internos “Ir para o módulo” nos tópicos que correspondem a módulos funcionais já implantados.
- Cada tela funcional deve poder exibir futuramente um botão contextual `?` pequeno e discreto ao lado do nome da tela, abrindo diretamente o tópico correspondente em **Instruções**.
- A primeira versão deve cobrir todos os módulos operacionais atualmente implantados: Cockpit, Minhas Contas, Meus Cartões, Extrato de Contas, Fatura de Cartões, Portfólio, Limites, Simulação, Relatórios, Categorias, Importação, Histórico, Preferências, Privacidade e Instruções.
- O módulo **Sobre** fica fora do conteúdo operacional, pois já é institucional e não exige instrução de uso.
- O tópico de **Preferências** deve explicar as abas **Geral** (aparência, email, senha e recuperação SMTP), **APIs** (integrações opcionais de IA e Mais Retorno para cotas de fundos) e **Perigo** (apagar lançamentos e conta).
- O tópico de **Preferências** deve explicar que a IA opcional também habilita o **Consultor**, desde que o usuário ative o módulo, aceite o consentimento de acesso aos dados e escolha o perfil de investidor.
- O tópico de **Cockpit** deve explicar o uso da aba **Consultor**: cards de análise pré-formatados, ausência de prompt livre, seletor de período em "Ralos Financeiros", histórico em subaba própria e expurgo do histórico quando IA/Consultor/consentimento forem desligados.
- O tópico de **Portfólio e ativos** deve explicar claramente a diferença entre cadastro da posição e movimentação financeira: o ativo descreve a posição, enquanto aportes e resgates posteriores devem ser registrados pelos lançamentos da conta.
- O tópico de **Portfólio e ativos** deve explicar também sobre a atualização manual dos valores e encerramento de posição (área histórico).
- O tópico de **Portfólio e ativos** deve detalhar fluxos complexos em formato tutorial, incluindo fundos de investimento: **Quantidade** representa cotas e **Preço unitário/Preço médio** representa o valor da cota usado como custo histórico, permanecendo editável mesmo quando houver cotação automática.
- O tópico de **Portfólio e ativos** deve incluir instrução sobre cotações automáticas de fundos via **Mais Retorno**: acesso ao site, criação de conta, geração da chave de API na plataforma e configuração em **Preferências > APIs**, com a nota de que sem a chave a posição mantém `Cotação manual pendente` e com a integração ativa fundos com CNPJ em carteira em reais consultam a cota diária.
- O tópico de **Renda fixa** deve diferenciar pré-fixada, pós-fixada e híbrida em linguagem prática.
- O tópico de **Cartões** deve explicar diferença entre compra parcelada/recorrente, fatura, pagamento de fatura e antecipação de parcelas. Além disso, deixar claro que uma vez paga a fatura os dados não são alterados.
- O tópico de **Lançamentos de contas** deve explicar diferença entre saldo previsto e saldo conciliado, além de entre compra parcelada/recorrente.
- O módulo deve respeitar o design system existente e a identidade visual do app, sem criar nova linguagem visual.

### Conteúdo inicial

A lista abaixo é a **versão de referência** para o conteúdo estático do módulo. Cada item deve estar disponível offline, sem dependência de backend, e usar linguagem direta orientada a tarefas. Os identificadores (`id`) e os nomes de grupo são estáveis; os textos podem ser ajustados por critérios de clareza em releases futuros.

#### Grupo `primeiros-passos`

- **ID**: `criar-conta`
  - **Título**: Criar minha conta
  - **Resumo**: Como fazer o primeiro acesso ao app de forma segura.
  - **Conteúdo**: Na tela inicial, escolha **Criar acesso**, preencha nome, e-mail e uma senha com pelo menos 8 caracteres. Guarde bem a senha: ela não pode ser recuperada sem o processo de redefinição por e-mail configurado em Preferências.
  - **Termos de busca**: cadastro, login, acesso, senha, primeiro acesso
  - **Módulo relacionado**: Login
  - **Rota do módulo**: *(tela de autenticação)*
  - **Tópico contextual**: —

- **ID**: `primeira-conta`
  - **Título**: Cadastrar minha primeira conta-corrente
  - **Resumo**: Contas representam dinheiro que você tem hoje em banco, corretora ou carteira.
  - **Conteúdo**: Vá em **Cadastro > Minhas Contas**, clique em **Nova conta**, dê um nome (ex.: "Conta corrente", "Investimentos"), escolha o tipo e informe o saldo inicial. O saldo inicial é apenas o ponto de partida; depois você poderá lançar movimentações reais.
  - **Termos de busca**: conta, banco, saldo inicial, cadastrar conta
  - **Módulo relacionado**: Minhas Contas
  - **Rota do módulo**: `accounts`
  - **Tópico contextual**: `primeira-conta`

- **ID**: `primeiro-cartao`
  - **Título**: Cadastrar meu primeiro cartão de crédito
  - **Resumo**: Cartões são usados para acompanhar compras e faturas, sem alterar o saldo da conta-corrente imediatamente.
  - **Conteúdo**: Em **Cadastro > Meus Cartões**, clique em **Novo cartão**, informe nome, melhor dia de compra e dia de vencimento. Opcionalmente, escolha uma conta preferencial para pagamento da fatura. O cartão não mexe no saldo da conta até você pagar a fatura.
  - **Termos de busca**: cartão, crédito, fatura, vencimento, fechamento
  - **Módulo relacionado**: Meus Cartões
  - **Rota do módulo**: `creditCards`
  - **Tópico contextual**: `primeiro-cartao`

- **ID**: `categorias-tags`
  - **Título**: Criar categorias e tags
  - **Resumo**: Categorias organizam seus lançamentos por natureza; tags permitem agrupar lançamentos de formas personalizadas.
  - **Conteúdo**: Acesse **Gestão > Categorias e tags**. Crie categorias como "Moradia", "Alimentação" e "Transporte". Dentro de cada categoria, crie subcategorias (ex.: "Supermercado" dentro de "Alimentação"). Use tags livremente para marcações extras, como "Viagem 2026".
  - **Termos de busca**: categoria, subcategoria, tag, classificação, grupo
  - **Módulo relacionado**: Categorias
  - **Rota do módulo**: `classifications`
  - **Tópico contextual**: `categorias-tags`

- **ID**: `primeiro-lancamento`
  - **Título**: Fazer meu primeiro lançamento
  - **Resumo**: Um lançamento registra entrada, saída ou movimentação do seu dinheiro.
  - **Conteúdo**: Em **Lançamentos > Extrato de Contas**, clique em **Novo lançamento**, escolha o tipo (receita, despesa, transferência, investimento etc.), selecione a conta, data, valor e categoria. Salve. O saldo da conta será atualizado automaticamente.
  - **Termos de busca**: lançamento, receita, despesa, extrato, movimentação
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `primeiro-lancamento`

#### Grupo `lancamentos-contas`

- **ID**: `lancar-receitas-despesas`
  - **Título**: Lançar receitas e despesas
  - **Resumo**: Registre entradas e saídas simples na conta-corrente.
  - **Conteúdo**: No Extrato de Contas, use o tipo **Receita** para salários, rendimentos ou reembolsos. Use **Despesa** para gastos do dia a dia. Preencha descrição, valor, data, categoria e, se quiser, tags. O saldo da conta muda imediatamente.
  - **Termos de busca**: receita, despesa, gasto, entrada, saída
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `lancar-receitas-despesas`

- **ID**: `previsto-conciliado`
  - **Título**: Diferença entre saldo previsto e saldo conciliado
  - **Resumo**: O saldo previsto considera todos os lançamentos; o saldo conciliado considera apenas os já confirmados.
  - **Conteúdo**: Cada lançamento pode estar **previsto** (registrado, mas ainda não confirmado) ou **conciliado** (já constatado na realidade, como uma compra que já passou no extrato bancário). O saldo previsto mostra o futuro próximo; o saldo conciliado mostra o que de fato aconteceu. Conciliar um lançamento não altera o valor, apenas marca que ele está confirmado.
  - **Termos de busca**: previsto, conciliado, saldo, confirmar, reconciliação
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `previsto-conciliado`

- **ID**: `parcelamento-recorrencia-contas`
  - **Título**: Parcelamento e recorrência no extrato
  - **Resumo**: Divida uma compra em parcelas ou repita lançamentos automaticamente.
  - **Conteúdo**: Ao criar um lançamento, escolha **Parcelada** para gerar várias parcelas iguais em meses seguintes. Escolha **Recorrente** para repetir o mesmo valor em intervalos fixos (mensal, quinzenal etc.). Você pode editar ou excluir a série inteira ou apenas uma parcela futura.
  - **Termos de busca**: parcela, parcelado, recorrente, série, repetir
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `parcelamento-recorrencia-contas`

- **ID**: `transferencias`
  - **Título**: Transferências entre contas
  - **Resumo**: Mova dinheiro de uma conta para outra sem criar receita ou despesa.
  - **Conteúdo**: No Extrato de Contas, use o tipo **Transferência**. Selecione a conta de origem, a conta de destino e o valor. A transferência não entra como receita nem como despesa no Cockpit. Para transferências em moeda estrangeira, informe a taxa de câmbio.
  - **Termos de busca**: transferência, entre contas, movimentação interna, câmbio
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `transferencias`

- **ID**: `investimentos-aportes`
  - **Título**: Lançar investimentos e aportes
  - **Resumo**: Registre compras, aportes e aplicações que aumentam uma posição existente ou criam uma nova no Portfólio.
  - **Conteúdo**: No Extrato de Contas, use o tipo **Investimento/Aporte** quando comprar um ativo, aplicar em um fundo, reforçar uma previdência ou fazer novo aporte em uma posição já existente. Esse lançamento reduz o saldo da conta escolhida e cria uma operação de investimento para o Portfólio. Comece pelo valor financeiro da operação: informe o valor total que saiu da conta, a data, a carteira/conta de custódia e os custos da operação, como corretagem, emolumentos, impostos ou outras taxas. Depois preencha a identificação do ativo. Para ações, ETFs, FIIs e cripto, use o ticker ou código mais reconhecível. Para fundos de investimento, informe o nome do fundo e o CNPJ. Quantidade e Preço unitário trabalham juntos: em fundos, a **Quantidade** é a quantidade de cotas compradas e o **Preço unitário** é o valor de cada cota na data da aplicação. Exemplo: se você aplicou R$ 1.000,00 em um fundo cuja cota era R$ 2,50, a quantidade será 400 cotas. Se já houver uma posição com os mesmos dados principais (mesma carteira, tipo, ticker/nome, CNPJ, indexador e vencimento), o aporte é somado a ela. Se não houver, o app cria uma nova posição automaticamente. **Não use Transferência para isso**: transferência apenas move saldo entre contas e não cria operação de ativo. Resgates, vendas, dividendos, juros sobre capital próprio e rendimentos devem ser lançados com os tipos apropriados.
  - **Termos de busca**: investimento, aporte, compra, aplicação, posição, ativo, transferência, conta investimento, fundo, cotas, preço unitário, CNPJ
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `investimentos-aportes`

- **ID**: `cambio-moedas`
  - **Título**: Lançar câmbio e moedas estrangeiras
  - **Resumo**: Registre receitas, despesas e transferências em moedas diferentes do Real.
  - **Conteúdo**: No Extrato de Contas, ao criar um lançamento em uma conta com moeda estrangeira (ex.: USD, EUR), informe o valor na moeda original e a taxa de câmbio. O app converte o valor para BRL usando a taxa informada ou, quando não houver cotação manual, a última PTAX de venda disponível até a data do lançamento. O valor original é preservado para consulta e o valor em BRL é usado nos relatórios e no Cockpit.
  - **Termos de busca**: câmbio, moeda estrangeira, dólar, euro, taxa de câmbio, PTAX, USD, EUR
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `cambio-moedas`

- **ID**: `conciliar-lancamento`
  - **Título**: Como conciliar um lançamento
  - **Resumo**: Marque um lançamento como confirmado para aproximar o saldo do extrato bancário real.
  - **Conteúdo**: No Extrato de Contas, localize o lançamento e clique na ação de conciliação (ícone de conferência). O lançamento passa do estado previsto para conciliado. Você pode desfazer a conciliação se necessário.
  - **Termos de busca**: conciliar, confirmar, banco, extrato, real
  - **Módulo relacionado**: Extrato de Contas
  - **Rota do módulo**: `transactions`
  - **Tópico contextual**: `conciliar-lancamento`

#### Grupo `cartoes`

- **ID**: `cadastrar-cartao`
  - **Título**: Cadastrar um cartão de crédito
  - **Resumo**: Registre seus cartões para acompanhar compras e faturas.
  - **Conteúdo**: Em **Cadastro > Meus Cartões**, clique em **Novo cartão**, dê um nome, escolha o melhor dia de compra e o vencimento. Se quiser, defina uma conta-corrente preferencial para pagar a fatura. O cartão aparecerá nas telas de Fatura e no Cockpit.
  - **Termos de busca**: cartão, cadastro, crédito, vencimento, fechamento
  - **Módulo relacionado**: Meus Cartões
  - **Rota do módulo**: `creditCards`
  - **Tópico contextual**: `cadastrar-cartao`

- **ID**: `lancar-compras-cartao`
  - **Título**: Lançar compras no cartão
  - **Resumo**: Cada compra é registrada separadamente e agrupada na fatura do mês.
  - **Conteúdo**: Em **Lançamentos > Fatura de Cartões**, escolha o cartão e a fatura, depois clique em **Nova compra**. Informe descrição, valor, categoria e data. A compra entra na fatura correspondente à data e ao fechamento do cartão.
  - **Termos de busca**: compra, cartão, fatura, lançar, despesa cartão
  - **Módulo relacionado**: Fatura de Cartões
  - **Rota do módulo**: `cardLaunches`
  - **Tópico contextual**: `lancar-compras-cartao`

- **ID**: `fatura-pagamento`
  - **Título**: Diferença entre fatura e pagamento de fatura
  - **Resumo**: Pagar a fatura registra a saída de dinheiro da conta-corrente, mas mantém o histórico das compras.
  - **Conteúdo**: A **fatura** é a lista de compras feitas no cartão durante um período. O **pagamento da fatura** é uma transferência da sua conta-corrente para quitar essa dívida. Ao pagar, o app cria um lançamento de saída na conta-corrente, mas as compras continuam registradas no cartão para histórico e relatórios. O pagamento não apaga nem altera as compras.
  - **Termos de busca**: fatura, pagamento, quitar, conta corrente, compras cartão
  - **Módulo relacionado**: Fatura de Cartões
  - **Rota do módulo**: `cardLaunches`
  - **Tópico contextual**: `fatura-pagamento`

- **ID**: `parcelada-recorrente-cartao`
  - **Título**: Compra parcelada e recorrente no cartão
  - **Resumo**: Divida uma compra em parcelas ou repita gastos fixos do cartão.
  - **Conteúdo**: Ao lançar uma compra no cartão, escolha **Parcelada** para dividir o valor em meses seguintes (ex.: 3x de R$ 100). Escolha **Recorrente** para gastos fixos, como assinaturas mensais. A fatura de cada mês mostra apenas a parcela ou recorrência daquele mês.
  - **Termos de busca**: parcelado, recorrente, assinatura, cartão, mensalidade
  - **Módulo relacionado**: Fatura de Cartões
  - **Rota do módulo**: `cardLaunches`
  - **Tópico contextual**: `parcelada-recorrente-cartao`

- **ID**: `antecipar-parcelas`
  - **Título**: Como antecipar parcelas
  - **Resumo**: Mova parcelas futuras para a fatura atual quando fizer um pagamento antecipado.
  - **Conteúdo**: No app, você pode alterar a fatura de uma compra parcelada para uma fatura anterior, desde que ela ainda esteja aberta. Isso é útil quando o banco antecipa parcelas ou quando você decide pagar tudo de uma vez. O valor total da fatura será ajustado.
  - **Termos de busca**: antecipar, parcela, adiantar, pagamento antecipado
  - **Módulo relacionado**: Fatura de Cartões
  - **Rota do módulo**: `cardLaunches`
  - **Tópico contextual**: `antecipar-parcelas`

- **ID**: `pagar-fatura`
  - **Título**: Como pagar a fatura
  - **Resumo**: Registre o pagamento da fatura para atualizar a conta-corrente.
  - **Conteúdo**: Na tela de Fatura de Cartões, clique em **Pagar fatura**, selecione a conta de saída e a data do pagamento. O app cria um lançamento de saída na conta-corrente. A fatura passa a ser considerada paga, mas as compras continuam visíveis.
  - **Termos de busca**: pagar fatura, quitar, conta, data pagamento
  - **Módulo relacionado**: Fatura de Cartões
  - **Rota do módulo**: `cardLaunches`
  - **Tópico contextual**: `pagar-fatura`

#### Grupo `portfolio`

- **ID**: `entender-portfolio`
  - **Título**: O que é o Portfólio
  - **Resumo**: O Portfólio mostra tudo o que você possui em investimentos, consolidado por tipo e moeda.
  - **Conteúdo**: Acesse **Gestão > Portfólio**. A tela exibe suas posições abertas (ações, fundos, renda fixa, cripto, previdência, poupança etc.), o valor investido, o valor atual e o resultado. Posições encerradas vão para a área de histórico.
  - **Termos de busca**: portfólio, investimentos, posições, carteira, ativos
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `entender-portfolio`

- **ID**: `posicao-movimentacao`
  - **Título**: Diferença entre posição e movimentação
  - **Resumo**: O Portfólio registra a posição inicial; aportes, compras e resgates são registrados pelos lançamentos da conta.
  - **Conteúdo**: Cadastre um ativo no Portfólio **apenas para registrar o que você já possui em carteira antes de começar a usar o app** (posição inicial). A partir daí, toda nova compra, aporte, resgate ou dividendo deve ser registrado como lançamento na conta-corrente ou de investimento, usando os tipos apropriados. O Portfólio consolida essas movimentações e calcula o resultado. Aportes criam novas posições se o ativo ainda não existir ou somam à posição existente. Não use o Portfólio como substituto do Extrato de Contas.
  - **Termos de busca**: posição, movimentação, aporte, resgate, lançamento, ativo, posição inicial, carteira
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `posicao-movimentacao`

- **ID**: `cadastrar-renda-fixa`
  - **Título**: Como cadastrar renda fixa
  - **Resumo**: Registre CDBs, LCIs, LCAs, tesouro e outros títulos de renda fixa.
  - **Conteúdo**: No Portfólio, clique em **Novo ativo**, escolha o tipo **Renda Fixa**, informe o valor investido, data de aplicação, vencimento, indexador e taxa. Se for pós-fixado ou híbrido, o app pode buscar o indexador (CDI, IPCA, SELIC) automaticamente.
  - **Termos de busca**: renda fixa, CDB, LCI, LCA, tesouro, título
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `cadastrar-renda-fixa`

- **ID**: `tipos-renda-fixa`
  - **Título**: Pré-fixada, pós-fixada e híbrida
  - **Resumo**: Entenda as três modalidades de renda fixa em linguagem prática.
  - **Conteúdo**: **Pré-fixada**: você já sabe o percentual total de retorno no momento da aplicação (ex.: 10% ao ano). **Pós-fixada**: o rendimento acompanha um indexador, como o CDI (ex.: 100% do CDI). **Híbrida**: parte do rendimento é fixa e parte acompanha um indexador (ex.: CDI + 2% ao ano ou IPCA + 5%). A escolha depende da sua expectativa sobre juros e inflação.
  - **Termos de busca**: pré-fixada, pós-fixada, híbrida, CDI, IPCA, SELIC, indexador
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `tipos-renda-fixa`

- **ID**: `acoes-fundos`
  - **Título**: Ações, fundos, cripto e previdência
  - **Resumo**: Cadastre posições iniciais de renda variável, cripto, fundos e previdência que você já possui em carteira.
  - **Conteúdo**: Use essa tela apenas para registrar ativos que você **já possui antes de começar a usar o app** (posição inicial). Aportes e compras futuras devem ser registrados pelo Extrato de Contas como lançamentos do tipo **Investimento/Aporte**. No formulário, preencha: **Carteira** (conta onde o ativo está custodiado), **Data de aquisição**, **Custo total** do lote, **Ativo** (ticker ou código, ex.: PETR4, BTC, XPML11) e **Nome do ativo**. Para fundos, informe também o **CNPJ do fundo**. Para previdência, escolha a subcategoria PGBL ou VGBL. Quando aplicável, preencha **Quantidade** e **Preço médio** para que o app acompanhe a evolução. Em fundos de investimento, Quantidade é a quantidade de cotas e Preço médio é o valor médio pago por cota na posição inicial. Para ativos com fonte de mercado disponível, o app atualiza o valor atual automaticamente: ações e FIIs via Yahoo, cripto via CoinGecko, indicadores e renda fixa via BACEN, e fundos via Mais Retorno quando a integração estiver configurada. O custo histórico informado por você permanece como base da posição.
  - **Termos de busca**: ações, fundos, cripto, previdência, cotação, posição inicial, ticker, quantidade, preço médio, CNPJ
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `acoes-fundos`

- **ID**: `fundos-cotas-preco-unitario`
  - **Título**: Fundos: cotas e preço unitário
  - **Resumo**: Entenda como preencher quantidade de cotas, valor da cota e CNPJ ao lançar fundos de investimento.
  - **Conteúdo**: Fundos de investimento são registrados por cotas. A **Quantidade** é o número de cotas que você comprou ou já possui; o **Preço unitário** é o valor de uma cota na data da aplicação ou da posição inicial. Use o informe da corretora ou do administrador do fundo para conferir valor aplicado, quantidade de cotas e valor da cota. Se o documento mostrar apenas valor aplicado e valor da cota, divida o valor aplicado pelo valor da cota para chegar à quantidade. O **CNPJ** identifica o fundo, evita misturar fundos com nomes parecidos e permite que a integração da Mais Retorno consulte a cota diária no Portfólio, desde que a API esteja configurada em **Preferências > APIs**. A cotação automática da Mais Retorno atualiza o valor atual da posição no Portfólio. O preço unitário informado no lançamento ou na posição inicial continua editável, porque representa o seu preço de compra/custo histórico, não necessariamente a cota mais recente. Se houver divergência com o comprovante da corretora, mantenha o valor do comprovante no lançamento.
  - **Termos de busca**: fundos, fundo de investimento, cotas, preço unitário, preço médio, valor da cota, CNPJ, Mais Retorno
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `fundos-cotas-preco-unitario`

- **ID**: `cadastrar-poupanca`
  - **Título**: Como cadastrar poupança
  - **Resumo**: Registre posições de poupança com as datas de aniversário para cálculo automático de rendimento.
  - **Conteúdo**: No Portfólio, clique em **Novo ativo** e escolha o tipo **Poupança**. Informe a conta, o nome do ativo e o valor investido. No campo **Aniversários da poupança**, cadastre cada data de aniversário seguida do valor aplicado naquele dia, usando o formato `AAAA-MM-DD; valor`. Por exemplo: `2026-01-05; 1.000,00`. Use uma linha para cada aniversário. O app usa essas datas para calcular o rendimento mês a mês com a regra da poupança (TR + 0,5% ou TR + 70% da Selic).
  - **Termos de busca**: poupança, aniversário, rendimento, data, formato, AAAA-MM-DD
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `cadastrar-poupanca`

- **ID**: `atualizar-valores`
  - **Título**: Como atualizar valores manualmente
  - **Resumo**: Substitua a cotação automática por um valor informado por você.
  - **Conteúdo**: Para ativos sem cotação disponível ou quando você discordar do valor de mercado, use a opção de atualizar valor manual no Portfólio. O novo valor passa a ser usado no cálculo do patrimônio até que seja alterado novamente.
  - **Termos de busca**: atualizar valor, cotação manual, valor de mercado, patrimônio
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `atualizar-valores`

- **ID**: `resgatar-encerrar`
  - **Título**: Como resgatar ou encerrar uma posição
  - **Resumo**: Transforme uma posição aberta em histórico quando ela deixar de existir.
  - **Conteúdo**: No Portfólio, use **Resgatar** para registrar uma retirada parcial e **Encerrar** quando a posição for totalmente liquidada. O app move os dados para a área de histórico e, se houver, atualiza a conta-corrente correspondente.
  - **Termos de busca**: resgatar, encerrar, histórico, liquidação, vender
  - **Módulo relacionado**: Portfólio
  - **Rota do módulo**: `portfolio`
  - **Tópico contextual**: `resgatar-encerrar`

- **ID**: `cota-fundos-mais-retorno`
  - **Título**: Cotações de fundos (Mais Retorno)
  - **Resumo**: Ative as cotações automáticas de fundos de investimento cadastrados com CNPJ.
  - **Conteúdo**: Acesse o site da Mais Retorno (www.maisretorno.com) e crie sua conta gratuita, ou entre na sua conta existente. Na sua conta, gere uma chave de API na área de API/desenvolvedor da plataforma e copie a chave gerada. No app, abra **Usuário > Preferências**, aba **APIs**, seção **Mais Retorno**: cole a chave, marque a opção de ativação e salve. Com a integração ativa, posições de fundos com CNPJ preenchido em carteira em reais consultam a cota diária automaticamente. Sem a chave, a posição mantém o valor de custo com o status `Cotação manual pendente`.
  - **Termos de busca**: mais retorno, fundo, cotação de fundos, chave de API, CNPJ, integração, API, cota
  - **Módulo relacionado**: Preferências
  - **Rota do módulo**: `user`
  - **Tópico contextual**: `cota-fundos-mais-retorno`

#### Grupo `cockpit`

- **ID**: `entender-cockpit`
  - **Título**: O que é o Cockpit
  - **Resumo**: O Cockpit é a tela inicial que resume sua situação financeira do mês.
  - **Conteúdo**: Acesse **Cockpit** no menu lateral. Você verá receitas, despesas, aportes, taxa de poupança, saldos por moeda, planejamento do mês, dívidas, maiores despesas e receitas, além de resumo do portfólio. Use o seletor de mês para navegar no tempo.
  - **Termos de busca**: cockpit, resumo, dashboard, visão geral, mês
  - **Módulo relacionado**: Cockpit
  - **Rota do módulo**: `cockpit`
  - **Tópico contextual**: `entender-cockpit`

- **ID**: `taxa-poupanca`
  - **Título**: Como interpretar a taxa de poupança
  - **Resumo**: A taxa de poupança mede quanto do que entrou no mês sobrou após despesas de consumo.
  - **Conteúdo**: A fórmula é: (receitas do mês - despesas de consumo do mês) / receitas do mês. Investimentos, transferências, câmbio e pagamentos de fatura não entram como despesa de consumo. Uma taxa positiva indica que você gastou menos do que recebeu.
  - **Termos de busca**: taxa de poupança, poupança, economia, sobra
  - **Módulo relacionado**: Cockpit
  - **Rota do módulo**: `cockpit`
  - **Tópico contextual**: `taxa-poupanca`

- **ID**: `planejamento-mes`
  - **Título**: Como usar o planejamento do mês
  - **Resumo**: Veja receitas e despesas recorrentes esperadas antes que elas aconteçam.
  - **Conteúdo**: A seção **Planejamento do mês** lista lançamentos recorrentes previstos para o mês selecionado. Ela ajuda a antecipar contas fixas e receitas garantidas. Os valores são projetados e podem mudar quando você cadastrar lançamentos reais.
  - **Termos de busca**: planejamento, recorrente, previsão, mês, contas fixas
  - **Módulo relacionado**: Cockpit
  - **Rota do módulo**: `cockpit`
  - **Tópico contextual**: `planejamento-mes`

- **ID**: `tendencias`
  - **Título**: Como usar a aba Tendências
  - **Resumo**: Análise mensal local com evolução de receitas e despesas, Budget x Realizado e achados.
  - **Conteúdo**: No Cockpit, acesse a aba **Tendências**. O app mostra gráficos mês a mês, compara o orçamento planejado com o gasto real e destaca padrões, como assinaturas recorrentes e eventos pontuais. A análise é feita localmente, sem depender de internet.
  - **Termos de busca**: tendências, budget, realizado, análise, gráfico
  - **Módulo relacionado**: Cockpit
  - **Rota do módulo**: `cockpit`
  - **Tópico contextual**: `tendencias`

- **ID**: `saude-financeira`
  - **Título**: Como usar a aba Saúde Financeira
  - **Resumo**: Acompanhe sua saúde financeira através de indicadores e histórico.
  - **Conteúdo**: A aba **Saúde** mostra o score de saúde financeira com base em pilares como liquidez, endividamento, poupança e diversificação. Use o histórico para ver a evolução ao longo dos meses.
  - **Termos de busca**: saúde financeira, score, indicadores, endividamento, liquidez
  - **Módulo relacionado**: Cockpit
  - **Rota do módulo**: `cockpit`
  - **Tópico contextual**: `saude-financeira`

#### Grupo `gestao`

- **ID**: `limites-gastos`
  - **Título**: Limites de gastos
  - **Resumo**: Defina orçamentos mensais por categoria ou subcategoria.
  - **Conteúdo**: Em **Gestão > Limites**, crie um limite para uma categoria (ex.: "Alimentação") e informe o valor máximo do mês. O Cockpit e a tela de Limites mostram quanto já foi consumido e quanto resta. Limites são sempre por mês.
  - **Termos de busca**: limite, orçamento, meta, gasto, categoria
  - **Módulo relacionado**: Limites
  - **Rota do módulo**: `limits`
  - **Tópico contextual**: `limites-gastos`

- **ID**: `relatorios`
  - **Título**: Relatórios
  - **Resumo**: Analise seus lançamentos agrupados de várias formas.
  - **Conteúdo**: Em **Gestão > Relatórios**, escolha uma aba: categorias, subcategorias, contas, tags ou fluxo diário. Selecione o mês e, se quiser, filtros adicionais. Use o relatório de evolução por categoria para ver a série histórica.
  - **Termos de busca**: relatório, análise, categoria, evolução, fluxo diário
  - **Módulo relacionado**: Relatórios
  - **Rota do módulo**: `reports`
  - **Tópico contextual**: `relatorios`

- **ID**: `importacao-dados`
  - **Título**: Importação de dados
  - **Resumo**: Traga lançamentos de planilhas do Organizze ou do modelo do próprio sistema.
  - **Conteúdo**: Em **Gestão > Importação**, escolha a origem (Organizze ou modelo próprio), selecione o arquivo e a conta ou cartão de destino. Para o modelo próprio, baixe o arquivo exemplo, preencha e envie. Sempre revise o resultado antes de continuar.
  - **Termos de busca**: importar, organizze, planilha, modelo
  - **Módulo relacionado**: Importação
  - **Rota do módulo**: `imports`
  - **Tópico contextual**: `importacao-dados`

- **ID**: `historico-operacoes`
  - **Título**: Histórico de Operações
  - **Resumo**: Consulte tudo o que foi alterado no app para fins de auditoria.
  - **Conteúdo**: Em **Gestão > Histórico**, você encontra registros de criação, alteração e exclusão de contas, cartões, lançamentos, categorias, limites e outras operações. Use filtros por data, módulo, tipo e conta/cartão. O histórico não pode ser editado.
  - **Termos de busca**: histórico, auditoria, operações, log, rastreabilidade
  - **Módulo relacionado**: Histórico
  - **Rota do módulo**: `operationHistory`
  - **Tópico contextual**: `historico-operacoes`

- **ID**: `simulacao-borboleta`
  - **Título**: Simulação (Efeito Borboleta)
  - **Resumo**: Simule o impacto de uma despesa ou receita futura no saldo da conta.
  - **Conteúdo**: Em **Gestão > Efeito Borboleta**, crie uma simulação informando data, valor, tipo e se é parcelada ou recorrente. O app projeta o saldo da conta ao longo do tempo e mostra a diferença em relação à situação atual. A simulação não cria lançamentos reais.
  - **Termos de busca**: simulação, efeito borboleta, projeção, futuro, impacto
  - **Módulo relacionado**: Simulação
  - **Rota do módulo**: `simulations`
  - **Tópico contextual**: `simulacao-borboleta`

#### Grupo `preferencias`

- **ID**: `recuperacao-email`
  - **Título**: Configurar recuperação por e-mail
  - **Resumo**: Ative a recuperação de senha por SMTP para não ficar preso caso esqueça a senha.
  - **Conteúdo**: Em **Usuário > Preferências**, acesse a seção **Recuperação por e-mail**. Informe servidor SMTP, porta, remetente e senha de app. A configuração é criptografada e armazenada localmente. Quando ativada, você poderá solicitar um código de redefinição de senha na tela de login.
  - **Termos de busca**: SMTP, e-mail, recuperação de senha, senha de app, configuração
  - **Módulo relacionado**: Preferências
  - **Rota do módulo**: `user`
  - **Tópico contextual**: `recuperacao-email`

- **ID**: `configurar-ia`
  - **Título**: Configurar IA para Tendências
  - **Resumo**: A IA é opcional e só reescreve o resumo da aba Tendências.
  - **Conteúdo**: Ainda em **Usuário > Preferências**, a seção **Configuração de IA** permite ligar um provedor externo (OpenAI, Groq etc.) para reescrever o resumo do mês. A análise numérica continua sendo feita localmente. Se a IA estiver desligada ou falhar, o app exibe o resumo local automaticamente.
  - **Termos de busca**: IA, inteligência artificial, tendências, resumo, OpenAI, Groq
  - **Módulo relacionado**: Preferências
  - **Rota do módulo**: `user`
  - **Tópico contextual**: `configurar-ia`

- **ID**: `tema-privacidade`
  - **Título**: Tema e privacidade
  - **Resumo**: Ajuste o tema claro/escuro e oculte valores na tela.
  - **Conteúdo**: Em **Usuário > Preferências**, escolha entre tema claro ou escuro. Use o botão de olho no topo do app (ou pressione a tecla **P**) para ativar o modo de privacidade, que oculta valores numéricos sensíveis. A preferência de tema é salva no navegador local.
  - **Termos de busca**: tema, escuro, claro, privacidade, ocultar valores
  - **Módulo relacionado**: Preferências
  - **Rota do módulo**: `user`
  - **Tópico contextual**: `tema-privacidade`

#### Grupo `privacidade-rede`

- **ID**: `ocultar-valores`
  - **Título**: Como ocultar valores na tela
  - **Resumo**: Proteja valores sensíveis quando alguém estiver próximo.
  - **Conteúdo**: Clique no ícone de olho no canto superior direito ou pressione **P** no teclado. Todos os valores monetários serão substituídos por traços ou máscaras enquanto o modo estiver ativo. Clique novamente para desativar.
  - **Termos de busca**: privacidade, ocultar, valores, olho, atalho
  - **Módulo relacionado**: *(global)*
  - **Rota do módulo**: —
  - **Tópico contextual**: `ocultar-valores`

- **ID**: `modo-lan`
  - **Título**: Como funciona o modo LAN
  - **Resumo**: Use o app em outros dispositivos da mesma rede local.
  - **Conteúdo**: O modo LAN permite acessar o Sistema Financeiro pelo IP da máquina onde ele está rodando, a partir de celulares, tablets ou outros computadores conectados à mesma rede. Para ativá-lo, siga os passos abaixo.
    1. **Encerre o app** se ele estiver rodando.
    2. **Defina a variável de ambiente** `APP_HOST` como `0.0.0.0` antes de iniciar o app. Exemplos:
       - Windows (Prompt ou PowerShell): `$env:APP_HOST="0.0.0.0"; python app.py`
       - macOS/Linux (Terminal): `APP_HOST=0.0.0.0 python app.py`
       - Se usar um script de inicialização (`.command`, `.bat`, `.sh` etc.), adicione `export APP_HOST=0.0.0.0` (macOS/Linux) ou `$env:APP_HOST="0.0.0.0"` (Windows) antes da linha que executa o app.
    3. **Descubra o IP local** da máquina onde o app está rodando:
       - Windows: abra o Prompt e execute `ipconfig`. Procure por "Endereço IPv4" na sua rede Wi-Fi/Ethernet.
       - macOS/Linux: abra o Terminal e execute `ifconfig` ou `ip addr`. Procure pelo endereço IPv4 da interface ativa (geralmente começa com `192.168.` ou `10.`).
    4. **No outro dispositivo**, abra o navegador e acesse `http://IP_DA_MAQUINA:8010`. A porta padrão é `8010`; se você alterou `APP_PORT`, use o valor correspondente.
    5. **Firewall**: se o acesso não funcionar, o firewall do sistema operacional pode estar bloqueando a porta `8010`. Você precisará criar uma regra para permitir conexões na porta usada pelo app. Caso não saiba como fazer isso, uma IA externa (ChatGPT, Claude, Copilot etc.) pode ajudar a montar o comando ou o passo a passo específico para o seu sistema operacional e firewall.
    6. **Segurança**: use o modo LAN apenas em redes confiáveis (sua casa ou escritório). Não exponha o app diretamente na internet. Para acesso remoto real, use um reverse-proxy com HTTPS (por exemplo, Nginx, Traefik ou Cloudflare Tunnel) e autenticação adicional. Uma IA externa também pode auxiliar na montagem da configuração de reverse-proxy, desde que você revise as recomendações e não compartilhe senhas, chaves ou arquivos de dados.
  - **Termos de busca**: LAN, rede, compartilhar, IP, acesso remoto, HTTPS, firewall, APP_HOST, 0.0.0.0
  - **Módulo relacionado**: *(infraestrutura)*
  - **Rota do módulo**: —
  - **Tópico contextual**: `modo-lan`

#### Grupo `ajuda`

- **ID**: `nao-encontrei-topico`
  - **Título**: Não encontrei o que procurava
  - **Resumo**: O que fazer quando um assunto ainda não está documentado aqui.
  - **Conteúdo**: A central de ajuda cobre os fluxos principais do app. Para dúvidas técnicas, bugs ou sugestões, use o contato disponível na tela **Sobre**. Evite compartilhar senhas, chaves ou arquivos de dados ao pedir ajuda.
  - **Termos de busca**: dúvida, suporte, contato, não encontrei, ajuda externa
  - **Módulo relacionado**: Sobre
  - **Rota do módulo**: `about`
  - **Tópico contextual**: —

### API e dados

- Nenhuma rota backend nova prevista no MVP.
- Nenhuma tabela SQLite nova prevista no MVP.
- Nenhuma alteração em `financeiro/` prevista no MVP.
- Conteúdo inicial pode ser definido em módulo JavaScript estático, por exemplo `web/modules/instructions-content.js`, ou estrutura equivalente alinhada ao padrão de modularização frontend.
- A view deve seguir o contrato de fábrica dos módulos em `web/modules/`, por exemplo `createInstructionsView({ state, elements, services, formatters, actions })`.
- `web/app.js` deve orquestrar a navegação para o novo módulo.

### Critérios de aceite

- Dado um usuário autenticado, quando abre o menu **Usuário**, então visualiza o item **Instruções** entre **Preferências** e **Sobre**.
- Dado um usuário autenticado, quando clica em **Instruções**, então a tela principal exibe a central de instruções sem alterar dados financeiros.
- Dado um usuário na tela de instruções, quando não digitou busca, então visualiza grupos de ajuda por tema.
- Dado um usuário na tela de instruções, quando digita um termo de busca existente, então a lista mostra apenas tópicos relacionados ao termo.
- Dado um usuário na tela de instruções, quando digita um termo de busca inexistente, então a página exibe estado vazio amigável.
- Dado um usuário lendo um grupo com muitos tópicos, quando abre um tópico, então apenas o conteúdo detalhado daquele tópico fica visível em formato expansível.
- Dado um usuário lendo o tópico de Portfólio e ativos, quando chega à explicação de aportes e resgates, então entende que movimentações posteriores devem ser feitas pelos lançamentos da conta.
- Dado um usuário lendo instruções de fundos de investimento, quando consulta Quantidade e Preço unitário, então entende que Quantidade representa cotas e Preço unitário representa o valor da cota/custo histórico editável.
- Dado um usuário lendo o tópico de Renda fixa, quando compara modalidades, então entende a diferença entre pré-fixada, pós-fixada e híbrida.
- Dado um usuário lendo o tópico de Cartões, quando compara fatura e pagamento de fatura, então entende que o pagamento da fatura não substitui o histórico detalhado das compras.
- Dado um usuário lendo o tópico de Lançamentos de contas, quando compara saldos diários, então entende a diferença entre previsto e conciliado.
- Dado um usuário em tela estreita, quando acessa Instruções, então a navegação por grupos, busca e tópicos permanece legível sem rolagem horizontal.
- Dado um usuário sem conexão com internet, quando acessa Instruções, então o conteúdo continua disponível.
- Dado um visitante sem sessão válida, quando tenta acessar diretamente o módulo Instruções pelo app, então o comportamento segue a proteção normal de autenticação do aplicativo.
- Dado um usuário lendo um tópico de módulo operacional, quando clica em “Ir para o módulo”, então o app navega internamente para o módulo relacionado sem executar alterações de dados.
- Dado um usuário em uma tela funcional com tópico de ajuda associado, quando clica no botão contextual `?` ao lado do nome da tela, então o app abre o tópico correspondente em **Instruções**.
- Dado um usuário lendo o tópico de Preferências, quando consulta SMTP e IA, então entende que SMTP apoia recuperação de senha e IA é opcional para Tendências.
- Dado um usuário lendo o tópico de Consultor, quando acessa Preferências e Cockpit, então entende como ativar o módulo, consentir o uso de dados, escolher um card, consultar histórico e desligar sabendo que o histórico será apagado.

### Pendências

> [!question] Pendências
> Toda pergunta em aberto, decisão não tomada ou premissa não validada entra aqui. Nenhum agente de IA deve implementar uma seção que dependa de um item desta lista sem confirmação humana antes. Remova o item somente quando a resposta já estiver refletida no restante da spec.

Nenhuma pendência conhecida.

### Fora de escopo

- Chatbot, assistente por IA ou geração dinâmica de ajuda.
- Tutorial interativo que executa ações no app.
- Vídeos, imagens externas ou documentação hospedada fora do app.
- Sistema de feedback, avaliação de artigos ou telemetria de leitura.
- Tradução multilíngue.
- Alterações em regras financeiras, cálculos, saldos, faturas ou portfólio.

### Plano de implementação

- [x] Passo 1 — Refinar a lista final de tópicos, grupos, termos de busca e textos didáticos na própria spec. Fecha: critérios 3, 7, 8, 9, 10 e 16.
- [x] Passo 2 — Criar o conteúdo estático versionado no frontend, sem dependência de backend ou internet. Fecha: critérios 11, 12 e 16.
- [x] Passo 3 — Criar a view `Instruções` em `web/modules/` seguindo o contrato modular do frontend. Fecha: critérios 2, 3, 4, 5, 6 e 14.
- [x] Passo 4 — Adicionar o item **Instruções** no menu **Usuário** e conectar a navegação em `web/app.js`. Fecha: critérios 1, 13 e 14.
- [x] Passo 5 — Ajustar responsividade, estados vazios, acessibilidade básica, links internos, botões contextuais `?` e aderência ao design system. Fecha: critérios 5, 6, 11, 14 e 15.
- [x] Passo 6 — Validar manualmente no app local/homologação os fluxos de menu, busca, accordion, sessão e responsividade. Fecha: todos os critérios.

### Changelog

- `1.8` — 2026-08-10 — Conteúdo de ajuda atualizado para cobrir o uso do Consultor: ativação via Preferências > APIs, consentimento, perfil de investidor, cards pré-formatados no Cockpit, histórico e expurgo por privacidade.
- `1.7` — 2026-08-10 — Textos de Portfólio e Investimento/Aporte expandidos em formato mais didático; novo tópico **Fundos: cotas e preço unitário** explica cotas, valor da cota, CNPJ, custo histórico editável e relação com a Mais Retorno.
- `1.6` — 2026-08-08 — Novo tópico no grupo Portfólio: **Cotações de fundos (Mais Retorno)** — como criar conta na plataforma, gerar a chave de API e configurar em Preferências > APIs; regra correspondente adicionada.
- `1.5` — 2026-08-08 — Tópico Preferências atualizado para refletir as abas **Geral**, **APIs** e **Perigo** e a integração opcional Mais Retorno ([[preferencias-abas]]).
- `1.3` — 2026-08-04 — Tópico `importacao-dados` ajustado: removida menção a formatos `.xls` e `.csv` do Organizze.
- `1.2` — 2026-08-04 — Tópicos `acoes-fundos` e `investimentos-aportes` revisados: explicados campos de cadastro de ações, fundos, cripto e previdência, e diferenciado aporte de investimento de transferência entre contas. Tópico `posicao-movimentacao` reforça que o cadastro no Portfólio é para posição inicial já existente na carteira.
- `1.1` — 2026-08-04 — Adicionado tópico `cadastrar-poupanca` ao grupo `portfolio`, explicando o cadastro de aniversários no formato `AAAA-MM-DD; valor` e o cálculo automático de rendimento.
- `1.0` — 2026-08-04 — Spec implementada: módulo **Instruções** finalizado no menu Usuário, com central de ajuda local, busca, grupos colapsáveis, accordion, links internos, botões contextuais `?`, responsividade e aderência ao design system. Versão do produto elevada para `1.2.0`.
- `0.9` — 2026-08-04 — Passo 5 do plano concluído: adicionado botão contextual `?` no header com mapeamento de tópicos por tela, ajustes de responsividade para telas estreitas, refinamento de estado vazio, atributos ARIA no accordion e estilos alinhados ao design system.
- `0.8` — 2026-08-04 — Passo 4 do plano concluído: item **Instruções** confirmado no menu **Usuário** entre Preferências e Sobre, navegação interna conectada em `web/app.js` e proteção de autenticação herdada do fluxo normal do app.
- `0.7` — 2026-08-04 — Passo 3 do plano concluído: criada `web/modules/instructions-view.js` com renderização de grupos, busca local, accordion, estado vazio e links internos; adicionada seção `#instructionsView` em `web/index.html`, integração em `web/app.js` e estilos básicos em `web/styles.css`.
- `0.6` — 2026-08-04 — Passo 2 do plano concluído: criado `web/modules/instructions-content.js` com todo o conteúdo estático, offline e versionado da central de ajuda, incluindo funções utilitárias de busca e navegação por tópico.
- `0.5` — 2026-08-04 — Expandido o tópico `modo-lan` com instruções técnicas detalhadas de configuração (`APP_HOST=0.0.0.0`, descoberta de IP, firewall, reverse-proxy) e orientação sobre uso de IA externa como auxílio.
- `0.4` — 2026-08-04 — Adicionado tópico `cambio-moedas` ao grupo `lancamentos-contas`, cobrindo lançamentos em moeda estrangeira, taxa de câmbio e normalização para BRL.
- `0.3` — 2026-08-04 — Passo 1 do plano concluído: adicionada a seção **Conteúdo inicial** com a lista final de tópicos, grupos, termos de busca e textos didáticos que cobrem os critérios 3, 7, 8, 9, 10 e 16.
- `0.2` — 2026-08-04 — Fechadas as pendências iniciais: primeira versão terá links internos “Ir para o módulo”, botões contextuais `?` nas telas funcionais e cobertura de todos os módulos operacionais, incluindo Preferências para SMTP e IA.
- `0.1` — 2026-08-04 — Spec inicial em rascunho para o módulo **Instruções** no menu Usuário, com central de ajuda local, busca, grupos por tema e destaque para fluxos de Portfólio, Renda Fixa, Cartões e Lançamentos.

### Relacionados

- [[sobre-app]]
- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[score-saude-financeira]]
- [[specs/consultor]]
