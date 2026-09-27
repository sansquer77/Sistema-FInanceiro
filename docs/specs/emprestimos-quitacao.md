---
tipo: spec
area: emprestimos-quitacao
status: em-implementacao
versao: 0.57
atualizado: 2026-09-27
relacionados:
  - "[[relatorios]]"
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[score-saude-financeira]]"
  - "[[efeito-borboleta]]"
  - "[[../requisitos]]"
  - "[[../arquitetura]]"
tags: [spec, "area/emprestimos-quitacao", "status/em-implementacao"]
aliases: ["Empréstimos e Financiamentos", "Empréstimos e plano de quitação"]
---

# Empréstimos e Financiamentos

> [!info] Status
> **em-implementacao** · versão: `0.57` · área: `emprestimos-quitacao` · atualizado em 2026-09-27 · relacionados: [[relatorios]], [[contas-correntes]], [[lancamentos]], [[efeito-borboleta]]

## Problema

O app mostra parcelas em aberto de compras e cartões, mas não representa empréstimos bancários nem dívidas contratuais de maior porte, como financiamento de veículo ou imóvel, com saldo devedor, taxa, pagamentos e prazo. O usuário precisa visualizar essas dívidas e comparar, por cálculos determinísticos, cenários de pagamento adicional e estratégias de quitação. Compras parceladas de consumo, como celular, já pertencem aos fluxos existentes de Lançamentos e Cartões e não devem ser cadastradas neste módulo.

## Usuário

Pessoa que acompanha manualmente empréstimos bancários e dívidas contratuais relevantes — por exemplo, empréstimo pessoal ou consignado, financiamento de veículo ou imóvel, ou dívida renegociada — e quer entender como pagamentos adicionais podem alterar o prazo e o custo estimado.

## Jornada

1. O usuário cadastra uma dívida com moeda, quantidade e valor das parcelas restantes, taxa efetiva mensal e data da próxima parcela; para um contrato novo, informa a quantidade total e a data da primeira parcela.
2. No formulário de lançamentos, seleciona a categoria de despesas **Empréstimos e Financiamentos** e, opcionalmente, o contrato ativo correspondente; o vínculo é validado pela identidade da categoria, mesmo após renomeá-la.
3. O módulo atualiza o acompanhamento do saldo usando os pagamentos vinculados, sem criar um segundo débito na conta.
4. Na aba **Empréstimos** do Efeito Borboleta, o usuário simula um valor adicional mensal ou uma amortização extraordinária e compara juros estimados, prazo e valor de quitação.
   Quando os dados do contrato estão completos e atuais, pode comparar a economia estimada de juros com o rendimento bruto dos mesmos aportes investidos a 100% do CDI até o prazo original.
5. Na mesma aba, para um conjunto de empréstimos, compara as estratégias avalanche e bola de neve.
6. O módulo **Empréstimos e Financiamentos** concentra cadastro, acompanhamento e vínculos de pagamentos; estudos de quitação ficam no Efeito Borboleta e não gravam pagamentos nem alteram saldos reais.
7. Ao excluir definitivamente um contrato, o usuário confirma a ação com a senha atual; o contrato e as associações são removidos, enquanto os lançamentos da conta permanecem inalterados.

## Dados

- `loan`: contrato acompanhado manualmente, com nome, modalidade, compromisso nominal restante, moeda, taxa e estado ativo/arquivado.
- `amortization_system`: sistema de amortização `price` ou `sac`, obrigatório em novos cadastros e `price` para contratos anteriores à evolução.
- `currency`: moeda original do empréstimo; obrigatória e mantida em todas as visões e cálculos.
- `monthly_rate`: taxa efetiva mensal normalizada e usada como fonte de verdade nas projeções Price ou SAC prefixado; pode ser informada diretamente ou derivada do CET efetivo anual.
- `annual_cet`: CET efetivo anual informado pelo usuário, quando disponível; já representa o custo total e não recebe adição separada de seguros ou tarifas.
- `scheduled_installment`: valor da parcela contratada; se houver variação no valor final, informa-se o cronograma ou o total nominal restante.
- `remaining_installment_count`: quantidade obrigatória de parcelas ainda não pagas; para contrato novo, quantidade total contratada.
- `next_due_date`: data da próxima parcela; corresponde à primeira data de pagamento em um contrato novo.
- `remaining_commitment`: total nominal das parcelas ainda não pagas, na moeda original. É o valor de compromissos futuros, não o principal devedor.
- `principal_balance_cents`: para contrato indexado, saldo devedor principal informado no demonstrativo do credor, separado do total nominal restante.
- `principal_balance_date`: data-base do saldo principal informado; define o início da série de indexação aplicada pelo app.
- `indexer`: correção do saldo: nenhuma, TR, IPCA ou remuneração da poupança.
- `remuneratory_rate`: juros remuneratórios fixos do contrato, informados separadamente do CET quando há indexador.
- `estimated_principal`: principal devedor estimado conforme o sistema selecionado: valor presente das parcelas no Price; no SAC, amortização constante inferida da próxima parcela, taxa e prazo restante.
- `shared_monthly_extra_budget`: orçamento mensal adicional por moeda, alocado a um empréstimo prioritário por vez nas simulações avalanche/bola de neve.
- `linked_transaction_id`: referência opcional a um lançamento de saída da conta categorizado pela identidade `loan_payment` (categoria padrão **Empréstimos e Financiamentos**); um lançamento pode ser associado a no máximo um empréstimo.
- `recognized`: estado persistido que indica que o lançamento associado já foi conciliado e reconhecido uma única vez como pagamento do contrato.
- `extra_monthly_payment`: valor adicional mensal usado somente na simulação.
- `extraordinary_amortization`: valor e data de amortização extraordinária usados somente na simulação.

## Regras

- Cadastro, atualização de saldo e dados contratuais são manuais; a funcionalidade não exige conexão bancária nem usa IA.
- Cada empréstimo é calculado, exibido e acompanhado exclusivamente em sua moeda nativa; valores de moedas distintas nunca são somados nem convertidos implicitamente.
- O painel apresenta totais, projeções e resultados de estratégia separados por moeda. Avalanche e bola de neve são calculadas em grupos independentes de empréstimos da mesma moeda.
- Um excedente mensal destinado a uma estratégia pertence a uma única moeda e não pode ser distribuído entre empréstimos de moedas diferentes.
- A primeira versão permite acompanhar dívidas bancárias e contratuais de maior porte, separadas das compras parceladas de consumo já registradas em Contas e Cartões.
- Price e SAC prefixado são sistemas de amortização selecionados separadamente da modalidade do crédito; ambos usam taxa efetiva mensal fixa e cálculos determinísticos no backend, em centavos.
- No sistema Price, a parcela total permanece fixa durante o prazo quando taxa e condições não mudam; a composição começa com mais juros e passa gradualmente a amortizar mais principal.
- No SAC, o valor destinado à amortização do principal é constante e os juros caem com o saldo devedor; por isso a parcela começa maior e diminui ao longo do prazo.
- Sistemas de amortização e indexação são dimensões independentes. A evolução planejada acrescenta TR, IPCA e remuneração da poupança como correção do saldo, preservando Price ou SAC como regra de amortização.
- A ordem planejada para cada período indexado é atualizar o saldo devedor pelo fator publicado do período, calcular os juros contratuais sobre o saldo corrigido e aplicar a amortização; a prestação é estimada segundo Price ou SAC.
- Períodos futuros sem fator publicado usam a taxa efetiva acumulada dos últimos doze meses publicados, convertida para taxa mensal equivalente e aplicada somente ao cenário. A interface informa o intervalo observado e identifica a premissa como estimativa, nunca como previsão oficial.
- Para IPCA, o fator usa competências mensais publicadas; para TR, a série diária do período; para poupança, o cálculo existente de TR mais remuneração adicional conforme Selic e aniversário mensal. Os limites do período devem seguir a data-base e as condições registradas no contrato.
- O campo parcela mensal representa a próxima prestação contratual informada pelo usuário; em SAC, prestações futuras são estimadas e diminuem conforme o saldo cai.
- A orientação de cadastro compara os sistemas com o mesmo exemplo: principal de R$ 12.000,00, 12 meses e taxa de 1% a.m.; no SAC amortiza-se R$ 1.000,00 de principal por mês, começando em R$ 1.120,00 e terminando em R$ 1.010,00, enquanto no Price a parcela estimada fica próxima de R$ 1.066,19.
- O usuário escolhe o sistema informado no contrato ou demonstrativo do credor; a modalidade (veículo, imóvel, pessoal, consignado etc.) não determina automaticamente o sistema.
- Para contratos indexados, o cadastro exige saldo principal atual e data-base do demonstrativo, distintos do compromisso nominal das parcelas restantes; exige também a taxa remuneratória fixa contratual, separada do CET.
- Taxa remuneratória fixa representa os juros contratuais aplicados após a correção do saldo. CET pode incorporar tarifas, seguros e hipóteses de indexação, portanto não substitui nem é convertido em spread do contrato indexado.
- A cada vencimento, o saldo inicial do período é corrigido pelo fator do indexador entre a data-base anterior e o vencimento; os juros remuneratórios incidem sobre o saldo corrigido e depois se aplica a amortização do sistema selecionado.
- No Price indexado, o pagamento programado e o saldo são corrigidos pelo mesmo fator; juros são calculados sobre o saldo atualizado e a amortização corresponde à prestação corrigida menos os juros.
- No SAC indexado, a quota de amortização constante em termos-base é atualizada pelo fator acumulado do indexador; juros são calculados sobre o saldo atualizado e a parcela é a amortização corrigida mais juros.
- O ciclo de correção segue os limites de datas informados no contrato: fatores oficiais publicados são usados para períodos observados; fatores de períodos futuros usam a taxa efetiva acumulada dos últimos doze meses publicados, convertida para taxa mensal efetiva equivalente e identificada como premissa estimada.
- Histórico de índices macroeconômicos oficiais pode ser consultado desde a data-base informada, sem importar ou inferir histórico anterior de pagamentos do contrato.
- O valor inicial exibido para empréstimo em andamento é a soma nominal das parcelas ainda não pagas; para contrato novo, é a soma das parcelas contratadas.
- Quando as parcelas restantes forem iguais, o compromisso nominal é calculado automaticamente multiplicando o valor da parcela pela quantidade de parcelas restantes. Se a última parcela tiver valor diferente, o usuário pode informar o valor ajustado do compromisso total.
- A data da próxima parcela é obrigatória e define o início do cronograma de pagamentos vinculados. Em contrato novo, o usuário informa a data da primeira parcela.
- A quantidade de parcelas restantes é obrigatória no cadastro; para contrato novo, o usuário informa o prazo total contratado. O sistema não infere nem preenche o prazo automaticamente.
- O compromisso nominal restante é diferente do principal devedor: para Price, o principal estimado é o valor presente das parcelas; para SAC, é estimado pela parcela vigente dividida pela soma da taxa mensal e do inverso do prazo restante.
- Dívidas de sistemas não suportados ou indexadores fora de TR, IPCA e remuneração da poupança podem ser cadastradas como acompanhamento nominal apenas; não recebem projeções de juros ou amortização incompatíveis.
- A taxa efetiva mensal informada é a fonte de verdade para decompor pagamentos e projetar juros nos modelos Price e SAC.
- O usuário pode informar a taxa efetiva mensal ou o CET efetivo anual. O CET anual é convertido em taxa mensal equivalente pela conversão de taxas efetivas: `i_m = (1 + CET_a)^(1/12) - 1`.
- Encargos embutidos no CET anual e nos valores totais das parcelas não são somados uma segunda vez ao cálculo.
- O valor da parcela e o compromisso restante são informados pelo total cobrado pelo credor, incluindo seguros e tarifas embutidos; a V1 não pede nem mantém uma separação desses encargos.
- Se encargos embutidos fizerem a composição real diferir do modelo selecionado, o cálculo permanece uma estimativa simplificada baseada no valor total informado; a tela não apresenta a decomposição como demonstrativo oficial do credor.
- Com taxa mensal conhecida, os juros de cada período incidem sobre o principal anterior; Price estima o principal pelo valor presente das parcelas e SAC mantém a amortização de principal constante, estimando o principal pela parcela vigente e prazo restante.
- A quantidade de parcelas e o cronograma informados são usados para conferir a projeção, não para recalibrar silenciosamente a taxa.
- Se o cronograma e a taxa não fecharem exatamente por arredondamento ou particularidade do contrato, o cadastro é mantido e a diferença é apresentada como estimativa; não se altera a taxa informada.
- Se faltar taxa mensal, o app pode acompanhar o compromisso nominal e os pagamentos, mas não apresenta cálculo de juros economizados nem ordenação avalanche baseada em taxa até haver taxa suficiente.
- O cadastro não exige nem mantém o valor originalmente financiado ou um principal confirmado pelo credor; o principal de projeção é estimado a partir do cronograma restante e da taxa, quando informada.
- O histórico de pagamentos totais e o prazo, sem taxa ou saldo principal, não permitem identificar a parcela de juros de cada mês nem o total de juros; o sistema não deduz essa divisão dos débitos bancários.
- Um pagamento efetivo é representado pelo lançamento de saída já existente na conta e associado à categoria de despesas identificada internamente como `loan_payment`, cujo nome padrão é **Empréstimos e Financiamentos**. Renomear a categoria não rompe o vínculo semântico. Associá-lo ao contrato não cria lançamento, transferência ou débito adicional na conta.
- A moeda do lançamento associado deve ser igual à moeda do empréstimo; vínculos que exigiriam conversão cambial são rejeitados.
- O vínculo ao empréstimo é explícito; a categoria com identidade `loan_payment`, isoladamente, não converte uma compra parcelada ou dívida de cartão em contrato de empréstimo.
- Lançamentos associados que ainda não foram conciliados permanecem como pagamentos pendentes e não reduzem parcelas restantes, compromisso nominal, valor pago ou progresso da quitação; isso também vale para lançamentos agendados futuros.
- Ao conciliar um lançamento associado válido, o sistema reconhece o pagamento uma única vez, atualiza o compromisso e as parcelas restantes e mantém o vínculo para o histórico.
- O nome padrão da categoria é **Empréstimos e Financiamentos**; o `system_key=loan_payment` permanece no mesmo ID quando o usuário renomeia a categoria.
- Parcelamentos de compras de consumo, inclusive compras de celular, permanecem nos módulos existentes e não entram no painel nem nas estratégias deste módulo.
- O fluxo de pagamento é unidirecional: dinheiro sai de uma conta e é destinado a um empréstimo. Não há fluxo de empréstimo para conta nesta funcionalidade.
- Somente empréstimos ativos podem ser selecionados para novos vínculos de pagamentos. Arquivar um empréstimo não apaga seu histórico nem os vínculos existentes.
- Excluir definitivamente um empréstimo exige a senha atual e remove o contrato e suas associações de pagamento, mas preserva todos os lançamentos originais, suas categorias, valores, datas e conciliação; a exclusão não altera saldo ou histórico da conta.
- O card distingue o compromisso nominal restante do principal devedor e do custo futuro projetado pelo sistema selecionado.
- Com taxa efetiva mensal e parcelas restantes, o backend estima o principal como valor presente das parcelas no Price; no SAC, infere a amortização constante e o principal a partir da próxima prestação, taxa e prazo. O custo futuro estimado é o compromisso nominal menos o principal, sem decompor cada tarifa.
- Sem taxa, mantém o compromisso nominal e informa que principal e custo financeiro futuro não podem ser estimados. Se o principal Price superar o compromisso nominal, mantém o principal visível e pede revisão dos dados em vez de exibir custo negativo.
- A estimativa é identificada como teórica e pode divergir do credor por arredondamentos, parcela final diferente, tarifas ou características contratuais que o modelo não representa.
- Um lançamento associado não pode liquidar dois empréstimos; enquanto válido, sua associação identifica o pagamento sem criar atividade financeira duplicada.
- Se um lançamento vinculado for editado, reclassificado, desconciliado após reconhecimento, estornado ou removido, o vínculo é invalidado e o card do empréstimo exibe um alerta para revisar/atualizar os dados. Conciliar pela primeira vez reconhece o pagamento e mantém o vínculo.
- A invalidação do vínculo não desfaz cálculos nem altera automaticamente o compromisso ou o estado do empréstimo; o usuário revisa e atualiza manualmente os dados do contrato.
- O alerta de revisão permanece até o usuário revisar/salvar os dados do empréstimo; o sistema não infere um novo saldo a partir do lançamento alterado.
- Crédito Rotativo é um modelo contratual próprio, sem parcelas ou amortização programada; não deve ser calculado como Price ou SAC. A proposta está detalhada em [[#Proposta de desenho — Crédito Rotativo]].
- A Central de Notificações existente lembra o usuário do pagamento na data de vencimento da próxima parcela e permite navegar ao empréstimo correspondente.
- Se não houver pagamento registrado e vinculado até o fim do mês de vencimento, o card do empréstimo mostra um aviso para revisar e atualizar o compromisso devido a possíveis encargos ou juros de atraso.
- O aviso por falta de pagamento não calcula multa, juros de mora nem novo saldo; encargos e ajustes são informados manualmente pelo usuário.
- Quando um vínculo de pagamento é invalidado, o app mostra somente o alerta de revisão dos dados; não infere que houve ou não pagamento para gerar o aviso de inadimplência.
- As simulações são hipotéticas e não alteram lançamentos, saldo das contas ou saldo persistido dos contratos.
- Avalanche prioriza a maior taxa informada; bola de neve prioriza o menor saldo devedor. Ambas mantêm os pagamentos mínimos dos demais empréstimos e aplicam o excedente ao empréstimo prioritário; ao quitá-lo, o valor liberado passa ao próximo.
- Cadastro, acompanhamento, revisão e vínculos de pagamento ficam no módulo Empréstimos; estudos de quitação ficam na aba **Empréstimos** do Efeito Borboleta.
- A simulação de amortização extraordinária oferece ambas as alternativas: reduzir o prazo mantendo o valor da parcela ou reduzir o valor da parcela mantendo o prazo restante. O usuário escolhe por cenário.
- Para avalanche e bola de neve, o excedente mensal é um orçamento compartilhado dentro de cada moeda; ao quitar uma dívida, a parcela liberada e o excedente passam para a próxima dívida priorizada.
- Carência e pagamentos parciais ou irregulares ficam fora da V1; a simulação usa parcelas mensais regulares e pagamentos adicionais ou amortização extraordinária explícita.
- O Efeito Borboleta é a área de estudos teóricos, incluindo as simulações de empréstimos; nenhum estudo cria ações, pagamentos ou lançamentos.
- Projeções são estimativas baseadas nos dados e convenções de cálculo informados; encargos, indexadores e regras específicas do credor podem produzir valores reais diferentes.

## API e dados

- Rotas próprias permitem listar, cadastrar, atualizar e arquivar empréstimos; a associação principal é feita pelo campo opcional de empréstimo no lançamento avulso da conta, mantendo a rota de associação existente compatível.
- A associação de pagamento deve referenciar o lançamento original da conta e preservar a fonte única do movimento financeiro.
- O cálculo de juros, amortização e ordenação das estratégias pertence ao núcleo Python; a interface apenas coleta parâmetros e apresenta resultados.

## Critérios de aceite

- Dado um usuário sem empréstimos cadastrados, quando abre o módulo Empréstimos e Financiamentos, então vê um estado vazio com ação para cadastrar o primeiro contrato.
- Dado empréstimos em moedas diferentes, quando o usuário consulta o painel, então saldos, pagamentos e projeções aparecem em grupos separados sem total convertido ou agregado.
- Dado empréstimos em moedas diferentes, quando o usuário executa avalanche ou bola de neve, então a ordenação e o orçamento excedente são aplicados separadamente em cada moeda.
- Dado um lançamento de conta em moeda diferente da moeda do empréstimo, quando o usuário tenta associá-lo, então o vínculo é rejeitado sem conversão nem alteração financeira.
- Dado um empréstimo ativo com sistema Price ou SAC, quando o usuário informa a taxa efetiva mensal, o valor e a quantidade das parcelas restantes, então o módulo calcula o compromisso nominal e projeta a decomposição estimada conforme o sistema escolhido.
- Dado um empréstimo cadastrado com CET efetivo anual, quando o app calcula a projeção, então converte o CET para a taxa mensal equivalente sem somar encargos embutidos novamente.
- Dado que o valor cobrado inclui seguro ou tarifa embutidos, quando o usuário cadastra a parcela e o compromisso restante, então informa os valores totais sem precisar separar esses encargos.
- Dada uma dívida contratual de sistema diferente de Price ou SAC prefixado, quando o usuário a cadastra, então pode acompanhar os dados informados e pagamentos vinculados sem receber uma projeção incompatível com esse sistema.
- Dado um empréstimo sem taxa efetiva mensal informada, quando o usuário consulta o acompanhamento, então o app mostra o compromisso nominal e pagamentos sem alegar calcular juros economizados.
- Dado um empréstimo sem taxa efetiva mensal ou saldo principal, quando há prazo e pagamentos mensais registrados, então o app não infere juros mensais ou totais a partir apenas desses valores.
- Dado um empréstimo com taxa e cronograma informados que não coincidem exatamente com a fórmula Price, quando o usuário calcula a projeção, então a taxa informada governa o cálculo e a diferença é exibida como estimativa, sem rejeição ou ajuste automático.
- Dado um empréstimo em andamento, quando o usuário informa a quantidade de parcelas restantes, o valor nominal restante e a data da próxima parcela, então o cronograma começa nessa data.
- Dado um contrato novo, quando o usuário informa a quantidade de parcelas contratadas e a data da primeira parcela, então o cronograma usa essa data como próximo vencimento.
- Dado um empréstimo com parcelas restantes iguais, quando o usuário informa a quantidade e o valor de cada parcela, então o app calcula o compromisso nominal restante como quantidade multiplicada pelo valor da parcela.
- Dado que a última parcela tem valor diferente das demais, quando o usuário informa o compromisso nominal ajustado, então o painel usa esse total informado.
- Dado um cadastro sem a quantidade de parcelas restantes, quando o usuário tenta salvar a dívida, então o app solicita esse dado e não estima o prazo.
- Dado um lançamento de saída da conta categorizado pela identidade `loan_payment`, quando o usuário o associa a um empréstimo ativo, então o movimento existente passa a compor o histórico desse contrato.
- Dado um lançamento associado a um empréstimo, quando o vínculo é salvo, então nenhum segundo lançamento ou débito é criado na conta.
- Dado um lançamento já associado a um empréstimo, quando o usuário tenta vinculá-lo a outro empréstimo, então a operação é rejeitada sem alterar os vínculos existentes.
- Dado um lançamento válido associado a um empréstimo, quando o módulo o apresenta no histórico, então mostra a referência ao movimento original sem duplicar a atividade financeira.
- Dado um lançamento vinculado que é editado, reclassificado, desconciliado após reconhecimento, estornado ou removido, quando o sistema detecta a alteração, então invalida o vínculo e sinaliza revisão no card sem alterar automaticamente os dados do empréstimo; a primeira conciliação reconhece o pagamento e mantém o vínculo.
- Dado um lançamento associado ainda não conciliado, inclusive com data futura/agendada, quando o empréstimo é exibido, então o lançamento aparece como pendente e não conta como parcela paga, valor amortizado ou progresso.
- Dado um lançamento associado válido ainda não conciliado, quando o usuário o marca como conciliado, então o pagamento é reconhecido uma única vez, reduz o compromisso e as parcelas restantes e mantém o vínculo no histórico.
- Dado um empréstimo com alerta de revisão, quando o usuário revisa e salva os dados do contrato, então o alerta é removido sem o app inferir valores do lançamento desvinculado.
- Dado um empréstimo arquivado, quando o usuário consulta seu histórico, então os pagamentos anteriormente associados continuam visíveis e preservados.
- Dado um contrato quitado ou arquivado, quando o usuário abre a aba **Histórico**, então ele não aparece entre os ativos e seu status é identificado como quitado ou arquivado.
- Dado um contrato arquivado com parcelas ou saldo nominal restante, quando ele aparece no histórico, então o saldo é identificado como compromisso em aberto arquivado, sem ser apresentado como quitação.
- Dado um contrato encerrado, quando o usuário consulta seu histórico, então pagamentos conciliados e pendentes anteriormente associados continuam visíveis, sem alteração ou duplicação dos lançamentos.
- Dado um crédito rotativo encerrado como quitado, trocado ou arquivado, quando o usuário abre o histórico, então o card apresenta o motivo do encerramento e o saldo final registrado, sem reabrir ações de edição ou simulação.
- Dado um usuário na aba Ativos ou Histórico, quando navega pelas abas com mouse ou teclado, então apenas o painel selecionado fica visível e o estado acessível das abas é sincronizado.
- Dado um empréstimo com pagamentos associados, quando o usuário informa a senha atual e confirma a exclusão definitiva, então o contrato e seus vínculos são removidos, enquanto cada lançamento permanece intacto na conta e na categoria original; senha inválida não remove nenhum dado.
- Dado um usuário no card do empréstimo, quando consulta as ações de gestão, então **Editar / revisar**, **Arquivar** e **Excluir** ficam agrupados no canto superior direito.
- Dado um empréstimo com taxa informada e parcelas restantes, quando o card é exibido, então distingue compromisso nominal restante, principal devedor estimado e custo financeiro futuro estimado, todos na moeda do contrato.
- Dado um empréstimo sem taxa informada, quando o card é exibido, então mostra o compromisso nominal e informa que principal e custo financeiro futuro não podem ser estimados.
- Dado que a projeção Price não coincide com o compromisso nominal informado, quando o card é exibido, então mantém os valores separados e explica que são estimativas baseadas na taxa e na parcela cadastradas.
- Dado que a interface não recebeu os campos calculados pelo backend, quando exibe o card, então não os apresenta como R$ 0,00 e informa que o cálculo não foi carregado.
- Dado um novo contrato, quando o usuário não seleciona um sistema de amortização, então o cadastro não é salvo e solicita a escolha entre Price e SAC.
- Dado um contrato migrado criado antes da escolha do sistema, quando o banco recebe a migração, então ele permanece com Price sem alterar parcelas, pagamentos ou compromissos existentes.
- Dado que o usuário consulta a explicação de Price e SAC no cadastro, quando compara o exemplo numérico de R$ 12.000,00 por 12 meses a 1% a.m., então vê a parcela fixa aproximada de R$ 1.066,19 no Price e a parcela SAC decrescente de R$ 1.120,00 até R$ 1.010,00.
- Dado um contrato Price ou SAC com taxa e parcelas restantes, quando o card calcula o principal, então aplica o modelo correspondente e apresenta o sistema selecionado.
- Dado um contrato SAC com taxa e parcelas restantes, quando simula pagamento adicional ou amortização extraordinária, então mantém amortização constante para reduzir prazo ou recalcula a amortização para manter o prazo quando o usuário escolhe reduzir parcela.
- Dado um plano avalanche ou bola de neve com contratos Price e SAC na mesma moeda, quando é simulado, então cada contrato segue seu sistema de amortização e a estratégia mantém sua ordem de prioridade.
- Dado um contrato SAC sem taxa, quando o card ou estudo é consultado, então mantém o acompanhamento nominal e sinaliza que a projeção de principal, juros e pagamentos futuros não está disponível.
- Dado o módulo Empréstimos aberto, quando o usuário não está cadastrando ou editando um contrato, então o formulário fica recolhido e pode ser aberto por **+ Novo Empréstimo**; ao abrir, ele aparece no topo antes da lista e usa os mesmos botões e ações de formulário da aba Objetivos.
- Dado um lançamento avulso de despesa na categoria identificada como `loan_payment`, quando a conta tem moeda compatível, então o próprio formulário do lançamento oferece a associação opcional a um empréstimo ativo dessa moeda, independentemente do nome atual da categoria.
- Dado um lançamento associado a um empréstimo pelo formulário da conta, quando salvo, então permanece um único movimento financeiro e o histórico do contrato passa a referenciá-lo.
- Dado um empréstimo, quando o card é exibido, então uma barra compacta representa o compromisso nominal total como 100%, com a parte paga preenchida proporcionalmente às parcelas associadas e o percentual pago visível.
- Dado o usuário passando o ponteiro sobre a barra de quitação, quando o tooltip aparece, então informa o total pago e a quantidade de parcelas quitadas na moeda do empréstimo.
- Dado o usuário escolhendo arquivar, quando a confirmação é exibida, então fica explícito que o contrato sai da lista ativa, deixa de aceitar novos vínculos e preserva lançamentos e pagamentos anteriores.
- Dado um empréstimo ativo com próxima parcela, quando chega a data de vencimento, então a Central de Notificações mostra um lembrete e permite abrir o empréstimo.
- Dado que não há pagamento registrado e vinculado até o fim do mês de vencimento, quando o usuário consulta o painel, então o card mostra um aviso para revisar manualmente o compromisso por possíveis encargos e juros.
- Dado um vínculo de pagamento invalidado, quando o app atualiza os alertas do empréstimo, então sinaliza revisão sem deduzir se a parcela foi paga nem calcular inadimplência.
- Dado um plano com mais de um empréstimo, quando o usuário escolhe avalanche, então os pagamentos adicionais priorizam a maior taxa mensal.
- Dado um plano com mais de um empréstimo, quando o usuário escolhe bola de neve, então os pagamentos adicionais priorizam o menor saldo devedor.
- Dado um cenário de pagamento adicional, quando a simulação é calculada, então o resultado informa juros estimados e meses economizados em relação ao plano-base.
- Dado uma amortização extraordinária, quando o usuário escolhe reduzir prazo ou parcela, então o resultado apresenta o efeito correspondente sem persistir alterações reais.
- Dado uma simulação de quitação, quando o usuário altera seus parâmetros na aba Empréstimos do Efeito Borboleta, então o app atualiza os resultados sem gravar lançamento ou atualizar saldo real.
- Dado o módulo Empréstimos aberto, quando o usuário consulta dívidas, então encontra cadastro, acompanhamento e pagamentos vinculados; os formulários de estudo de pagamento adicional e plano por estratégia são apresentados no Efeito Borboleta.
- Dado que não existe conexão bancária ou configuração de IA, quando o usuário cadastra contratos e executa simulações, então toda a funcionalidade continua disponível.
- Dado que o usuário navega para o módulo de dívidas, quando consulta o item do menu ou o título da tela, então ambos exibem **Empréstimos e Financiamentos**.
- Dado um novo contrato, quando o usuário cadastra, então escolhe explicitamente Price ou SAC prefixado, independentemente da modalidade do crédito; SAC exige taxa mensal ou CET anual.
- Dado um contrato Price, quando estima prestações e simula pagamento adicional, então mantém a parcela regular fixa conforme o modelo.
- Dado um contrato SAC prefixado, quando estima prestações e simula pagamento adicional ou amortização extraordinária, então mantém a amortização do principal constante; juros e parcelas caem com o saldo, salvo cenário de redução de prazo/parcela indicado pelo usuário.
- Dado um estudo avalanche ou bola de neve com contratos Price e SAC na mesma moeda, quando simulado, então cada cronograma usa o sistema correspondente e valores mensais permanecem separados por moeda.
- Dado o formulário de cadastro, quando o usuário abre a explicação dos sistemas, então compara definições e exemplo de R$ 12.000,00 em 12 meses a 1% a.m.: Price cerca de R$ 1.066,19 fixos; SAC amortiza R$ 1.000,00 mensais, com primeira parcela de R$ 1.120,00 e última de R$ 1.010,00.
- Dado contrato atrelado a CDI ou outro indexador ainda não suportado, quando cadastrado, então a interface explica que a projeção não calcula a variação desse indexador.
- Dado empréstimo Price ou SAC indexado a TR, IPCA ou poupança, quando projetado, então o motor aplica a correção do período ao saldo antes de calcular os juros e a amortização do sistema escolhido.
- Dado que há índices oficiais publicados para o período do contrato, quando a projeção é calculada, então usa os fatores históricos disponíveis e respeita a data-base e periodicidade aplicáveis ao indexador.
- Dado um período futuro sem índice publicado, quando o usuário simula o contrato indexado, então o app usa como premissa a taxa efetiva acumulada dos últimos 12 meses publicados para aquele indexador, convertida em taxa mensal equivalente por `(1 + fator acumulado)^(1/12) - 1`, e identifica no resultado o intervalo observado e que se trata de uma estimativa, sem exigir uma taxa manual.
- Dado contrato indexado, quando o usuário consulta a parcela e o custo estimados, então a tela separa atualização do saldo, juros contratuais e amortização e identifica os resultados como estimativas.
- Dado um contrato com indexador, quando há pagamentos conciliados, então o saldo projetado conserva a moeda original e a mesma correção/amortização usada na simulação, sem criar lançamentos.
- Dado um contrato rotativo com taxa mensal e capitalização diária, quando o motor projeta o saldo, então converte a taxa para equivalente diária com referência de 30 dias, aplica dias corridos e identifica a conversão como estimativa.
- Dado um contrato rotativo com taxa diária informada, quando o motor projeta o saldo, então usa a taxa diária diretamente e capitaliza conforme o período registrado.
- Dado um pagamento conciliado com data posterior à data-base, quando o motor atualiza o saldo, então calcula juros pelos dias corridos anteriores à data efetiva e abate o pagamento no início dela, sem juros adicionais sobre o valor pago naquele dia.
- Dado um contrato rotativo, quando o usuário informa seu saldo-base, então esse valor representa o saldo atualizado pelo credor na data-base e a projeção não tenta reconstruir encargos anteriores.
- Dado um cálculo de juros de rotativo, quando ocorre capitalização, então o valor dos juros é arredondado para centavos e os valores permanecem separados por moeda.
- Dado o usuário que abre Empréstimos e Financiamentos, quando consulta o módulo, então vê no topo um aviso compacto recomendando ter o contrato e demonstrativo atualizado com sistema, indexador, saldo principal/data-base, taxa remuneratória, CET e cronograma, e esclarecendo que os resultados são estimativas.
- Dado um contrato indexado, quando o usuário salva o cadastro, então informa TR, IPCA ou poupança, saldo principal, data-base e taxa remuneratória mensal separada do CET; contratos antigos mantêm indexador nenhum.
- Dado uma estratégia de quitação com contratos indexados e prefixados na mesma moeda, quando simulada, então aplica fatores oficiais históricos e a estimativa futura derivada da taxa efetiva acumulada dos últimos 12 meses publicados, mantendo moeda, saldo e amortização próprios de cada contrato.
- Dado avalanche com contratos indexados, quando ordena a prioridade, então compara a taxa remuneratória mensal acrescida da taxa mensal equivalente derivada dos últimos 12 meses publicados do indexador; o resultado identifica essa ordenação como estimativa.
- Dado uma estratégia com contratos indexados, quando mostra o resultado, então apresenta separadamente juros e correção acumulada estimados, sem alterar contratos, lançamentos ou saldos reais.
- Dado um contrato indexado escolhido no estudo individual, quando existem fatores oficiais até a data corrente, então a simulação corrige o saldo por período, calcula juros remuneratórios e amortização Price/SAC nessa ordem, e distingue correção acumulada de juros; períodos futuros usam a taxa efetiva acumulada dos últimos 12 meses publicados convertida em taxa mensal equivalente e identificam essa premissa como estimativa.
- Dado um pagamento de conta conciliado associado a um contrato indexado, quando o pagamento altera o cronograma reconhecido, então o card sinaliza que a estimativa do principal precisa de revisão e não apresenta o principal previamente estimado como saldo atual confirmado.
- Dado um contrato Price ou SAC com dados completos e atuais, quando o usuário informa adicional mensal e/ou amortização extraordinária e ativa a comparação CDI, então o estudo compara a economia nominal estimada de juros com o rendimento bruto estimado dos mesmos aportes a 100% do CDI até o prazo-base original.
- Dado a comparação CDI, quando calcula a premissa futura, então usa a última taxa diária CDI publicada pelo BCB, anualiza pela convenção de 252 dias úteis e converte para taxa mensal equivalente; mostra a data da observação e mantém essa taxa constante pelo prazo restante original como cenário hipotético, sem chamar o resultado de previsão.
- Dado adicional mensal e amortização extraordinária, quando projeta o investimento alternativo, então aplica o extraordinário no início do horizonte e cada aporte mensal ao fim do mês até o prazo-base original; apresenta total aportado, saldo bruto projetado e rendimento bruto, sem descontar impostos, IOF, tarifas ou efeitos de liquidez.
- Dado que não há uma observação CDI publicada disponível, quando a comparação estiver ativa, então mantém o resultado da quitação e informa que o comparativo CDI não ficou disponível.
- Dado contrato rotativo, dados incompletos ou principal indexado marcado para revisão, quando o usuário tenta comparar com CDI, então a comparação fica indisponível com orientação para completar ou revisar o contrato; não infere dados faltantes.
- Dado uma comparação quitação × CDI, quando exibida, então informa que é estudo hipotético bruto, não considera o produto de investimento real do usuário e não recomenda automaticamente quitar ou investir.
- Dado um contrato Price/SAC selecionado no estudo individual, quando a pessoa ainda não escolheu a finalidade, então o formulário solicita primeiro **Quitar agora** ou **Amortizar** e não mostra os campos de amortização antes da escolha.
- Dado que a pessoa escolheu **Quitar agora**, quando inicia o estudo, então o sistema estima o valor de quitação com os dados atuais do contrato, calcula o custo financeiro futuro evitado (juros e, quando aplicável, correção do indexador) e compara o mesmo valor aplicado hoje a 100% CDI bruto pelo prazo restante original, sem solicitar valor adicional ou mensal.
- Dado o estudo **Quitar agora**, quando os resultados são apresentados, então mostra claramente o valor estimado de quitação, o custo financeiro futuro evitado, o saldo bruto estimado do investimento CDI, o rendimento bruto e qual cenário tem maior valor estimado, junto da taxa/data e limitações do cenário CDI.
- Dado contrato indexado elegível no estudo **Quitar agora**, quando usa o saldo principal informado, então exige data-base atual e taxa remuneratória; se a revisão do principal estiver pendente, bloqueia o estudo e explica a atualização necessária.
- Dado que a pessoa escolheu **Amortizar**, quando inicia o estudo, então revela os campos de adicional mensal, amortização extraordinária e efeito sobre prazo/parcela; a comparação CDI continua opcional e usa os mesmos aportes simulados.
- Dado contrato sem dados suficientes para estimar o valor de quitação ou os juros evitados, quando escolhe **Quitar agora**, então explica quais dados do contrato precisam ser informados/revistos e não mostra valores zerados como resultado válido.
- Dado um contrato rotativo selecionado, quando abre o estudo individual, então mantém a jornada de simulação própria do rotativo e não exibe as escolhas Quitar agora / Amortizar dos contratos parcelados.

Na premissa automática, TR usa as observações oficiais diárias publicadas na janela móvel de doze meses até a observação mais recente; IPCA e poupança usam as últimas doze observações mensais publicadas. A poupança usa a série oficial SGS 195. A comparação de investimento a 100% CDI usa a última taxa diária CDI publicada, anualizada pela convenção de 252 dias úteis e convertida em equivalente mensal, mantida constante no horizonte do contrato; a observação e a natureza hipotética do cenário são exibidas. Se não houver histórico completo disponível para os indexadores do contrato, a simulação informa que não foi possível estimar, sem substituir por taxa inventada ou solicitar entrada manual.

O principal indexado salvo é uma referência informada com data-base, não é recalculado silenciosamente pelo acompanhamento de pagamentos. Um pagamento conciliado posterior a essa data invalida sua apresentação como saldo atual e bloqueia estudos até o usuário atualizar principal e data-base com o demonstrativo do credor.

## Pendências

As regras de projeção indexada e revisão do principal após pagamento conciliado foram implantadas. A comparação quitação × CDI foi implementada para contratos Price/SAC completos e atuais. A validação visual da nova comparação na homologação permanece pendente. O CDI é bruto, usa como premissa constante a última taxa diária publicada (cenário hipotético, não previsão) e não substitui análise do produto, impostos, tarifas ou liquidez.

## Proposta de desenho — Crédito Rotativo

Esta proposta trata cheque especial e saldo de cartão mantido no rotativo como dívidas de saldo aberto. Ela amplia o domínio de acompanhamento de Empréstimos e Financiamentos, mas mantém os estudos hipotéticos na aba **Empréstimos** do Efeito Borboleta. Não exige conexão bancária nem IA.

### Dados e acompanhamento

- Cada contrato rotativo registra nome, modalidade (`cheque especial` ou `cartão rotativo`), moeda, saldo devedor informado, data-base do saldo e taxa efetiva com sua unidade temporal (diária ou mensal).
- O cadastro não exige prazo, quantidade de parcelas nem parcela fixa. Limite de crédito, vencimento de fatura, pagamento mínimo e encargos avulsos ficam fora da primeira versão, salvo decisão explícita nas pendências abaixo.
- Cada moeda mantém saldos e projeções independentes, conforme a regra geral do módulo.
- O saldo projetado parte do saldo e da data-base informados. Taxa e saldo são premissas do contrato e podem ser revisados; uma alteração da taxa vale a partir da data informada, sem recalcular períodos já encerrados.
- A data-base representa o saldo total atualizado informado pelo credor no início daquele dia. A projeção não reconstrói juros anteriores à data-base.
- A taxa efetiva mensal é a entrada preferencial; a taxa efetiva diária também pode ser informada quando constar no contrato ou demonstrativo. Unidade da taxa e frequência de capitalização são registradas separadamente.
- Se o credor informar taxa mensal com capitalização diária, o motor deriva a taxa diária equivalente com mês de referência de 30 dias: `i_diária = (1 + i_mensal)^(1/30) - 1`, capitalizada por dias corridos. A conversão é identificada como estimativa, pois o contrato pode usar dias úteis ou outra base.
- Se o credor informar uma taxa diária, ela é usada diretamente. Para taxa mensal com capitalização mensal, aplicam-se períodos mensais completos; períodos incompletos usam a taxa diária equivalente de 30 dias como pró-rata estimado.
- Em lançamentos sem horário ou data de valor específica, os juros acumulam pelos dias corridos desde a data-base até o dia anterior ao pagamento; o pagamento conciliado reduz o saldo no início da data efetiva, sem cobrar um dia adicional sobre o valor pago. Sem data de valor do credor, vale a data do lançamento conciliado.
- Os juros são arredondados para centavos a cada capitalização. Projeções permanecem identificadas como estimativas sujeitas à convenção contratual, à base de dias e à data de processamento do credor.
- A interface distingue saldo-base informado, juros acumulados estimados e saldo projetado até a data consultada. O cálculo é uma estimativa e não substitui o extrato do credor.

### Juros, pagamentos e simulações

- Sem pagamentos, o saldo cresce por capitalização composta na periodicidade contratual, usando valores em centavos e taxa efetiva diária ou mensal, com as conversões e bases de dias definidas nesta spec.
- Um pagamento real continua sendo um único lançamento de saída da conta. O vínculo é explícito, usa a mesma moeda e só é reconhecido após conciliação; o sistema não cria um segundo débito.
- Empréstimos e Financiamentos é um módulo de monitoramento e consulta: nenhum cadastro, edição, simulação, pagamento, quitação, arquivamento ou troca de dívida pode criar, editar ou excluir lançamento financeiro. A via de mão única é dos lançamentos e dos fluxos de Cartões para o acompanhamento do contrato; a associação nunca provoca ação de volta nesses domínios.
- No pagamento parcial de fatura, o processo existente já calcula e grava o saldo residual como lançamento na próxima fatura. Esse mesmo valor inicia o saldo do contrato rotativo, que referencia o pagamento e o lançamento residual; não se cria outra despesa nem outro saldo financeiro.
- Para esse fluxo, o vínculo do rotativo usa o pagamento da fatura e o lançamento residual do cartão (`credit_card_payments` e `credit_card_transactions`); não deve tentar associar o débito agregado da conta como se fosse um pagamento comum de empréstimo.
- O primeiro pagamento parcial de um cartão cria um único card de Crédito Rotativo vinculado àquele cartão e ao residual. Pagamentos parciais posteriores atualizam esse contrato e seu saldo a partir do novo residual, sem criar cards rotativos duplicados para o mesmo cartão.
- O card é criado mesmo que taxa e convenção de capitalização não estejam disponíveis. Nesse caso, um alerta pede que o usuário complete os dados do contrato; o módulo acompanha o valor nominal, mas não estima juros até que os dados necessários sejam informados.
- Se uma fatura que contém saldo rotativo for paga integralmente, o fluxo pergunta se foi quitação definitiva ou troca de dívida; ambos encerram o saldo rotativo, e a opção de troca também gera alerta para cadastrar manualmente o novo Price. O lançamento de pagamento já existente continua sendo a única saída da conta.
- Para atualizar o saldo, o motor acumula juros pelos dias corridos anteriores à data efetiva e abate o valor conciliado no início dessa data. Pagamentos anteriores à data-base exigem atualização manual do saldo/data-base, sem inferência retroativa.
- Pagamento maior que o saldo devido não cria saldo credor no contrato. O lançamento permanece intacto e o módulo sinaliza que o saldo requer revisão.
- No Efeito Borboleta, o estudo individual compara o saldo sem pagamento com cenários de pagamentos informados pelo usuário, mostrando juros, saldo projetado e tempo até zerar quando o cenário quita a dívida. Também permite comparar o rotativo com uma proposta Price mais barata informada pelo usuário, exibindo prazo, parcela e custo estimado lado a lado; só identifica a proposta como mais barata se o custo projetado total for menor. Os estudos são somente leitura e não atualizam contratos, lançamentos nem saldos de conta.
- Avalanche prioriza a maior taxa efetiva comparável; bola de neve prioriza o menor saldo atual. Para rotativos, a taxa efetiva precisa estar disponível para ordenar contratos por avalanche.
- Em avalanche e bola de neve, dívidas rotativas sempre formam a primeira faixa de prioridade, antes de contratos Price/SAC, por terem custo muito alto. Entre rotativos, avalanche prioriza a maior taxa efetiva conhecida e bola de neve o menor saldo; depois de quitá-los, a estratégia continua entre os contratos programados.
- Rotativos não têm parcela mínima presumida pelo app. O orçamento mensal adicional informado no estudo é direcionado primeiro aos rotativos conforme a estratégia; saldos rotativos ainda não priorizados continuam acumulando juros no cenário e devem permanecer visíveis no resultado.

### Conversão para parcelamento

- Quando o credor oferecer parcelar o rotativo em Price, o usuário escolhe **Troca de dívida**, encerra o acompanhamento rotativo e recebe um alerta para cadastrar manualmente o novo contrato a partir do demonstrativo: principal financiado, taxa, parcela ou prazo e próximo vencimento.
- O novo contrato Price só é criado quando o usuário preenche e salva o cadastro. O principal informado deve corresponder ao saldo efetivamente parcelado pelo credor; o sistema não presume que coincide com o saldo calculado localmente.
- A conversão é uma mudança de acompanhamento, não um movimento financeiro: não gera lançamento de conta/cartão nem altera saldo de conta. Pagamentos anteriores permanecem no histórico do rotativo; pagamentos futuros podem ser ligados ao novo contrato.
- O contrato rotativo convertido deixa de receber novos pagamentos e simulações de saldo aberto; o contrato Price relacionado segue as regras existentes de Empréstimos.
- Ao encerrar um rotativo, o usuário escolhe **Quitação definitiva (pago)** ou **Troca de dívida**. A escolha registra o motivo e não cria lançamento financeiro.
- Na quitação definitiva, o contrato é encerrado como pago com base no pagamento existente do fluxo de conta ou fatura; o app não cria um segundo débito.
- Na troca de dívida, o contrato rotativo é encerrado e a Central de Notificações recebe um alerta para cadastrar manualmente o novo contrato Price com as condições do credor. A troca não cria automaticamente um contrato nem presume taxa, prazo ou parcela; o saldo/valor informado no novo contrato segue o demonstrativo do credor.
- Ao abrir o cadastro manual do novo Price pelo alerta, o formulário sugere a moeda e exibe o saldo calculado do rotativo como referência editável, explicitamente identificado como estimativa do app. O usuário deve confirmar ou substituir o principal pelo valor do demonstrativo do novo credor antes de salvar. Taxa, CET, prazo, parcela e próximo vencimento não são reaproveitados do contrato encerrado.
- Ao salvar o novo Price iniciado por esse alerta, a notificação é marcada como lida e deixa de oferecer novamente a ação de cadastro; seu registro informativo permanece disponível no Cockpit.

### Decisões registradas — Crédito Rotativo

1. **Taxa mensal com capitalização diária:** converter para taxa efetiva diária equivalente sobre mês de referência de 30 dias e capitalizar pelos dias corridos reais. Divergências em relação à base contratual ficam identificadas como estimativas.
2. **Taxa diária informada:** usar diretamente a taxa do contrato. Para taxa mensal com capitalização mensal, aplicar períodos mensais completos e usar pró-rata diário equivalente de 30 dias nos períodos incompletos, identificado como estimativa.
3. **Data e ordem do pagamento:** considerar o saldo-base válido no início da data-base; calcular juros pelos dias corridos anteriores à data do pagamento e abater o pagamento no início dessa data. Sem data de valor do credor, usar a data do lançamento conciliado.
4. **Arredondamento:** arredondar juros para centavos a cada capitalização.
5. **Saldo inicial:** informar saldo total atualizado no demonstrativo na data-base, incluindo encargos já incorporados pelo credor; não reconstruir o histórico anterior.

### Regra operacional — Crédito Rotativo

- **Mudança de taxa e saldo:** exigir data de vigência, preenchida inicialmente com a data atual e ajustável para a data do demonstrativo. Manter o valor anterior no histórico e aplicar a nova premissa somente dali em diante, sem recalcular períodos já encerrados. Uma revisão de saldo inicia uma nova projeção com o saldo atualizado do credor naquela data.
- **Troca para Price:** sugerir a moeda e exibir o saldo calculado anterior como referência editável, exigindo confirmação ou substituição pelo saldo do credor; não reaproveitar outros termos.
- **Via de mão única:** lançamentos e fluxos de Cartões podem atualizar o acompanhamento do contrato; ações em Empréstimos nunca criam, editam ou excluem lançamentos. Simulações do Efeito Borboleta também não alteram contratos nem movimentos.

### Critérios de aceite — Crédito Rotativo

- Dado o módulo Empréstimos e Financiamentos, quando o usuário cria, edita, consulta, simula, quita, arquiva ou troca um contrato, então nenhuma dessas ações cria, altera ou exclui lançamentos de conta ou cartão.
- Dado um pagamento conciliado na conta associado a um rotativo, quando o vínculo é reconhecido, então o contrato é atualizado uma única vez e o lançamento original permanece inalterado.
- Dado o pagamento parcial de fatura, quando Cartões registra o residual na próxima fatura, então o módulo atualiza ou cria um único contrato rotativo para aquele cartão, usando o residual já existente e sem gerar outro lançamento.
- Dado pagamento parcial posterior no mesmo cartão, quando o residual da fatura é atualizado, então o mesmo contrato é atualizado sem duplicar contrato nem movimento financeiro.
- Dado uma fatura com saldo rotativo paga integralmente, quando o usuário informa quitação definitiva ou troca de dívida, então o contrato é encerrado e o pagamento existente segue como única movimentação financeira; troca gera alerta para cadastro manual do novo Price.
- Dado alerta de troca para Price, quando o usuário inicia o cadastro, então moeda e saldo calculado anterior são apresentados como sugestão identificada, e o principal só é salvo após confirmação ou substituição pelo valor do demonstrativo do credor; os demais termos do novo contrato são informados novamente.
- Dado alteração manual de taxa ou saldo, quando o usuário salva, então informa a data de vigência, a condição anterior permanece no histórico e projeções encerradas não são recalculadas.
- Dado saldo rotativo atualizado pelo credor, quando o usuário registra revisão, então o saldo/data-base informados iniciam a nova projeção sem reconstrução de juros anteriores.
- Dado contrato com moeda específica, quando há saldo, pagamento ou simulação, então valores permanecem naquela moeda e não são convertidos nem agregados a contratos de outras moedas.
- Dado o usuário executando uma simulação individual ou de estratégia no Efeito Borboleta, quando o resultado é atualizado, então nenhuma operação persistente altera contratos, lançamentos, saldos de conta ou faturas.
- Dado um rotativo ainda sem taxa suficiente para comparar avalanche, quando a estratégia é executada, então o rotativo continua na faixa prioritária e o resultado informa que sua ordenação por taxa depende de completar os dados; bola de neve ordena pelo menor saldo.
- Dado uma estratégia com dívidas rotativas ativas, quando o usuário informa orçamento mensal adicional, então os rotativos ficam antes dos contratos Price/SAC; avalanche ordena taxas rotativas conhecidas da maior para a menor e bola de neve ordena pelo menor saldo, sem presumir pagamento mínimo.
- Dado uma estratégia com dívida rotativa e sem parcela mínima, quando o sistema compara o cenário adicional com o cenário sem pagamento, então não apresenta prazo ou economia fictícios para o cenário sem pagamento; solicita um orçamento mensal adicional positivo para projetar quitação.
- Dado um contrato rotativo com taxa informada, quando o usuário simula pagamentos mensais em uma data definida e uma amortização extraordinária opcional, então o saldo é projetado pelas datas efetivas, os juros são calculados até o dia anterior a cada pagamento e o pagamento reduz o saldo no início de sua data.
- Dado um estudo de rotativo, quando o resultado é exibido, então apresenta lado a lado o saldo e juros sem pagamento no mesmo horizonte e o prazo, total pago e juros do cenário informado; o cenário sem pagamento não recebe prazo de quitação.
- Dado os campos de uma proposta Price informados pelo usuário (principal, taxa efetiva mensal e prazo), quando o estudo é calculado, então o app estima a parcela e o custo total pela fórmula Price e identifica a proposta como mais barata somente se o custo total estimado for menor que o custo total do cenário rotativo simulado.
- Dado um estudo individual do Crédito Rotativo, quando ele é recalculado, então nenhuma alteração persistente é feita no contrato, histórico, lançamentos, saldos ou faturas.
- Dado um contrato cuja taxa foi informada mensalmente com capitalização diária, quando o saldo é projetado, então é usada a conversão efetiva diária de 30 dias, capitalizada por dias corridos e identificada como estimativa.
- Dado um pagamento em data sem horário/data de valor contratual, quando o saldo é projetado, então os juros são calculados até o dia anterior e o pagamento é abatido no início de sua data, com arredondamento dos juros a centavos por capitalização.
- Dado indisponibilidade de taxa/convenção no contrato originado por pagamento parcial, quando o card é apresentado, então mostra saldo nominal sem estimar juros e oferece alerta para completar os dados.
- Dado cadastro, revisão ou encerramento de uma dívida rotativa, quando a operação é persistida, então seu registro de auditoria é gravado na mesma transação; se a auditoria falhar, a alteração inteira é revertida.
- Dado um rotativo nas estratégias, quando não há comparação visível sem pagamentos, então o sistema não calcula um baseline sem pagamento; se o cenário com orçamento informado exceder o limite numérico, apresenta uma mensagem acionável sem erro inesperado nem persistência.

### Plano de implementação — Crédito Rotativo

1. Adicionar modelo e migração idempotente para contratos rotativos, dados de taxa/capitalização, moeda, saldo/data-base e histórico de alterações, sem mudar lançamentos existentes.
2. Implementar no domínio Python cálculos de taxa equivalente, períodos corridos, ordem de pagamentos, arredondamento, projeção e validações de moeda; cobrir fronteiras de data e pagamento com testes automatizados.
3. Integrar o pagamento parcial/integral de fatura ao acompanhamento rotativo dentro da transação já existente, garantindo vínculo único por cartão e preservação do lançamento residual original.
4. Integrar pagamentos de conta já existentes e conciliados ao contrato, sem endpoint ou ação do módulo de empréstimos que crie movimentações; validar invalidação/revisão de vínculos.
5. Expor as operações necessárias de leitura e manutenção do contrato/histórico com validação de usuário, moeda, Host/Origin e regras de mutação existentes; atualizar a arquitetura quando as rotas e tabelas concretas forem definidas.
6. Atualizar a tela de Empréstimos para cadastro/monitoramento do saldo aberto, pagamentos conciliados, alertas, histórico de taxa/saldo e fluxo manual de troca para Price.
7. [x] Estender avalanche/bola de neve e o estudo individual no Efeito Borboleta, preservando moeda e caráter somente leitura, incluindo comparação com proposta Price informada.
8. Validar critérios de aceite com testes automatizados por regra financeira e fluxo de integração; documentar verificações visuais/manuais que não forem automatizáveis e atualizar instruções e changelogs.

### Progresso da implantação do Crédito Rotativo

- Concluído nesta etapa: schema `20010`, cadastro/revisão manual de cheque especial, histórico de saldo/taxa, projeção determinística, origem do rotativo de cartão pelo residual já existente e reconhecimento de pagamento de conta somente após conciliação.
- Concluído nesta etapa: inclusão de rotativos nas estratégias avalanche/bola de neve por moeda, com prioridade sobre Price/SAC e sem pagamento mínimo presumido.
- Concluído nesta etapa: estudo individual com pagamentos datados, amortização única, comparação com cenário sem pagamento e cálculo/avaliação de proposta Price.
- Concluído nesta etapa: ação do alerta de troca abre um rascunho Price editável, sugere moeda e saldo rotativo/data-base como referência, e exige o preenchimento manual das condições antes de salvar.
- Concluído nesta etapa: ao salvar o Price iniciado pelo alerta, a notificação de troca é marcada como lida e deixa de oferecer novamente o atalho.
- Pendente: validação visual/fim a fim dos critérios restantes da V1 e confirmação da apresentação do histórico de alterações no Cockpit.

### Exemplos de referência para validar o modelo

- **Sem pagamento:** saldo de R$ 1.000,00 a 1% efetivo ao mês por três períodos completos resulta em R$ 1.030,30 antes de novos pagamentos ou encargos adicionais.
- **Taxa diária:** saldo de R$ 1.000,00 a 0,1% ao dia por 10 dias resulta em R$ 1.010,05 antes de pagamento, se a convenção escolhida capitalizar uma vez ao fim de cada dia.
- **Pagamento no período:** o saldo-base é informado no início da data-base. Para pagamento conciliado em data posterior, acumulam-se juros pelos dias corridos anteriores à data efetiva e o pagamento reduz o saldo no início dessa data; não se cobra um dia adicional sobre o valor pago.
- **Conversão:** saldo informado pelo credor de R$ 2.400,00 convertido em 12 parcelas Price de R$ 230,00 cria a continuidade contratual no novo contrato; o total das parcelas não é lançado como despesa adicional na conta.
- **Estratégia:** se houver um rotativo de R$ 2.400,00 e um financiamento Price ativo, avalanche e bola de neve direcionam primeiro o orçamento adicional informado ao rotativo; a parcela contratual Price continua sendo considerada normalmente.

## Fora de escopo

- Compras parceladas de consumo, como celulares, eletrodomésticos e outras compras já acompanhadas em Contas e Cartões.
- Conexão bancária, Open Finance, importação automática de saldo ou credor.
- Uso de modelos de IA para cadastrar contratos, categorizar empréstimos ou sugerir decisões.
- Garantia de que a projeção corresponda ao valor oficial de quitação do credor.
- Rotativos não geram pagamentos ou lançamentos pelo módulo de Empréstimos; liquidações são informadas a partir dos fluxos já existentes de conta ou cartão.
- Suporte a indexadores além de TR, IPCA e remuneração da poupança na primeira evolução indexada, bem como indexação intradiária, defasagens especiais ou outras cláusulas contratuais não representadas pelos campos disponíveis.
- Criar um segundo lançamento de conta para representar o mesmo pagamento associado ao empréstimo.

## Plano de implementação

- [x] Passo 1 — Persistir empréstimos e vínculos a lançamentos existentes com migração idempotente e isolamento por usuário/moeda.
- [x] Passo 2 — Implementar projeções Price, pagamentos adicionais compartilhados e amortização extraordinária no domínio Python.
- [x] Passo 3 — Invalidar vínculos quando lançamentos forem alterados e apresentar alertas de revisão/vencimento.
- [x] Passo 4 — Criar o menu e a tela Gestão → Empréstimos para cadastro, painel e vínculos.
- [x] Passo 5 — Implementar avalanche e bola de neve com alocação de excedente por moeda.
- [x] Passo 6 — Implementar amortização extraordinária com as alternativas de redução de prazo/parcela e os lembretes do Cockpit.
- [x] Passo 7 — Associar pagamentos no lançamento de conta, recolher o formulário, consolidar o histórico e exibir o gráfico de valores pagos com confirmação de arquivamento.
- [x] Passo 8 — Revisar os critérios de aceite, conferir a integração funcional e registrar a aprovação do MVP pelo usuário em 2026-09-25. Fecha: critérios da V1.
- [x] Passo 9 — Distinguir vínculo de reconhecimento: lançamentos pendentes ficam associados sem reduzir saldo ou progresso; a conciliação reconhece uma única vez; contratos com vínculos pendentes legados recebem alerta de revisão. Fecha: critérios 41 e 42.
- [x] Passo 10 — Posicionar as ações no cabeçalho do card e permitir excluir o contrato após validação da senha, removendo somente suas associações e preservando lançamentos. Fecha: novos critérios de gestão e exclusão.
- [x] Passo 11 — Expor no resumo de cada contrato o compromisso nominal, principal Price estimado e juros futuros estimados; explicar indisponibilidade sem taxa e limitações da projeção. Fecha: novos critérios de transparência do saldo.
- [x] Passo 12 — Adicionar seleção persistida Price/SAC com migração de contratos existentes como Price. Fecha: critérios de seleção e compatibilidade.
- [x] Passo 13 — Estender estimativas, quitação extra e avalanche/bola de neve para cronogramas Price e SAC. Fecha: critérios de cálculo e simulação.
- [x] Passo 14 — Explicar a diferença na tela e na Central de Ajuda com exemplo comparável de principal, prazo e taxa, incluindo orientação para indexadores. Fecha: critério de orientação do usuário.
- [x] Passo 15 — Adicionar ao contrato indexador, principal e data-base; implementar consulta de fatores oficiais TR/IPCA/poupança fora de transações SQLite; aplicar fatores, juros remuneratórios e amortização Price/SAC em sequência na simulação individual.
- [x] Passo 16 — Estimar períodos futuros pela taxa efetiva acumulada dos últimos doze meses publicados, convertida para equivalente mensal e identificada como premissa estimada nos estudos individual e por estratégia.
- [x] Passo 17 — Atualizar cards e estudos para sinalizar principal desatualizado após pagamento conciliado posterior à data-base e exigir revisão manual do demonstrativo antes de nova simulação.
- [x] Passo 18 — Cobrir Price/SAC × TR/IPCA/poupança e a janela automática de observações publicadas com testes; atualizar arquitetura e documentação. A validação visual/fim a fim permanece manual.
- [x] Passo 19 — Implementar a comparação opcional entre juros economizados e investimento bruto dos mesmos aportes a 100% CDI até o prazo original, projetando a última taxa diária publicada pela convenção de 252 dias úteis e preservando a simulação de quitação se CDI estiver indisponível.
- [x] Passo 20 — Exibir a comparação e suas limitações nos resultados/ajuda; cobrir cálculos, indisponibilidade de dados e contratos inelegíveis com testes. A validação visual na homologação segue manual.
- [x] Passo 21 — Separar escolha de quitação e amortização no estudo individual; implementar a projeção de quitação integral a partir do saldo/principal vigente e a comparação CDI pelo mesmo valor e prazo original.
- [x] Passo 22 — Apresentar resultados específicos de quitar versus investir, manter a comparação opcional na jornada de amortização e preservar o estudo de Crédito Rotativo.
- [x] Passo 23 — Testar cálculos, dados incompletos e indisponibilidade CDI; atualizar ajuda, arquitetura, requisitos e critérios de aceite. Validação visual na homologação permanece pendente.
- [x] Passo 24 — Separar contratos ativos e encerrados em abas, incluindo status quitado/arquivado/trocado para rotativos e preservando pagamentos e vínculos no histórico.
- [x] Passo 25 — Cobrir leitura do histórico e separação das listas com testes de domínio e contrato frontend; atualizar arquitetura e documentação.

## Changelog

- `0.57` — 2026-09-27 — Adiciona aba Histórico para contratos quitados/arquivados e rotativos encerrados, preservando pagamentos e distinguindo saldo arquivado em aberto.
- `0.56` — 2026-09-27 — Separa estudo individual em Quitar agora e Amortizar; quitação estima o saldo à vista e compara com o CDI pelo prazo remanescente.
- `0.55` — 2026-09-27 — Simplifica a comparação quitação × investimento para projetar a última taxa diária CDI publicada, com data de referência, conversão pela convenção de 252 dias úteis e taxa constante identificada como cenário hipotético.
- `0.54` — 2026-09-27 — Implementa comparação entre juros economizados e rendimento bruto estimado dos mesmos aportes a 100% CDI no prazo original, com premissa histórica e limitações explícitas.
- `0.53` — 2026-09-26 — Implanta estimativa futura baseada nos últimos doze meses oficiais publicados e bloqueia a exibição/uso do principal indexado desatualizado após pagamento conciliado.
- `0.52` — 2026-09-26 — Define a estimativa futura dos indexadores pela taxa efetiva acumulada dos últimos 12 meses publicados, exige sinalização de revisão do principal após pagamento conciliado e amplia a matriz automatizada Price/SAC × TR/IPCA/poupança.
- `0.51` — 2026-09-25 — Corrige cadastro parcial por auditoria não reconhecida, torna mutação e auditoria atômicas e evita baseline sem pagamento para rotativos em avalanche/bola de neve.

- `0.50` — 2026-09-25 — Ao salvar um Price iniciado no alerta de troca, marca o lembrete como lido e remove a ação repetida, preservando o registro no Cockpit.
- `0.49` — 2026-09-25 — A ação do alerta de troca prepara um rascunho Price editável com moeda e saldo estimado do rotativo como referência; nenhum contrato é salvo automaticamente.
- `0.48` — 2026-09-25 — Implementa estudo individual de rotativo no Efeito Borboleta, com pagamentos por data e comparação determinística opcional com proposta Price.
- `0.47` — 2026-09-25 — Especifica estudo individual do rotativo com pagamentos datados, cenário sem pagamento e comparação determinística com proposta Price.
- `0.46` — 2026-09-25 — Inclui saldo rotativo nas estratégias avalanche/bola de neve, sempre antes de Price/SAC e sem inferir pagamento mínimo; o estudo individual permanece pendente.
- `0.45` — 2026-09-25 — Inicia a implantação do Crédito Rotativo: schema `20010`, domínio de saldo/data-base/histórico, integração inicial com pagamentos parciais do cartão e reconhecimento de pagamentos de conta somente após conciliação. Estudos individuais ainda não foram implementados.
- `0.44` — 2026-09-25 — Fecha decisões do Crédito Rotativo, formaliza a via de mão única sem lançamentos e adiciona critérios de aceite e plano de implementação.
- `0.43` — 2026-09-25 — Define conversão de taxa mensal para diária, base de 30 dias, dias corridos, ordem de incidência do pagamento, saldo-base e arredondamento para o Crédito Rotativo.
- `0.42` — 2026-09-25 — Define prioridade dos rotativos nas estratégias sem pagamento mínimo presumido e comparação de troca por proposta Price; encerramento pode registrar quitação ou troca com alerta de cadastro.
- `0.41` — 2026-09-25 — Rotativos entram em avalanche/bola de neve com prioridade sobre Price/SAC; encerramento distingue quitação definitiva de troca e alerta para novo cadastro Price manual.
- `0.40` — 2026-09-25 — Pagamento parcial de cartão passa a ser a origem do saldo do card rotativo e do alerta para completar dados, referenciando o residual da fatura sem criar dívida duplicada.
- `0.39` — 2026-09-25 — Iniciado o desenho de Crédito Rotativo para cheque especial e cartão, com capitalização composta, pagamentos conciliados e conversão acompanhada para Price; convenções de taxa e integração permanecem pendentes.
- `0.38` — 2026-09-25 — Estratégias avalanche/bola de neve passam a aceitar contratos TR, IPCA e poupança, com hipótese anual para períodos futuros e correção separada no resultado.
- `0.37` — 2026-09-25 — Simulação individual passa a consultar TR/IPCA/poupança no histórico, aplicar premissa anual futura e mostrar separadamente a correção estimada do saldo.
- `0.36` — 2026-09-25 — Cadastro e schema passam a persistir indexador, saldo principal/data-base e juros remuneratórios separados do CET; cálculo indexado segue pendente.
- `0.35` — 2026-09-25 — Cadastro de contratos indexados exige conceitualmente principal/data-base e taxa remuneratória separada do CET; módulo exibe aviso com checklist de informações para melhorar a precisão.
- `0.34` — 2026-09-25 — Amplia a cobertura planejada para Price/SAC indexados, define hipótese manual para fatores futuros e reserva Crédito Rotativo como modelo futuro sem amortização programada.
- `0.33` — 2026-09-25 — Refina as regras do SAC prefixado, confirma taxa obrigatória e documenta o comportamento da estratégia multi-sistema e dos indexadores.
- `0.32` — 2026-09-25 — Cadastro passa a exigir Price ou SAC prefixado; cards e simulações respeitam o sistema e a tela explica a escolha com exemplo numérico.
- `0.31` — 2026-09-25 — Valores estimados ausentes na resposta da API deixam de ser exibidos incorretamente como zero e orientam reiniciar o app.
- `0.30` — 2026-09-25 — Cards distinguem compromisso nominal, principal estimado e juros futuros do modelo Price, com estado explícito quando faltar taxa.
- `0.29` — 2026-09-25 — Ações de gestão agrupadas no cabeçalho do card; exclusão definitiva valida a senha, remove vínculos ao contrato e preserva lançamentos da conta.
- `0.28` — 2026-09-25 — Pagamentos vinculados só amortizam o empréstimo após conciliação; lançamentos agendados ficam pendentes e uma migração sinaliza contratos afetados pelo comportamento anterior.
- `0.27` — 2026-09-25 — MVP de Empréstimos e Financiamentos aprovado; spec promovida para implementado e versão do app atualizada para `2.1.0`.
- `0.26` — 2026-09-24 — Menu e título da tela passam a usar **Empréstimos e Financiamentos**; instruções de uso do módulo adicionadas à Central de Ajuda.
- `0.25` — 2026-09-24 — Ícone de navegação de Empréstimos diferencia o módulo do Portfólio com moeda, seta de pagamento e mão simplificada, mantendo o traço linear do app.
- `0.24` — 2026-09-24 — Pagamentos reconhecem a categoria por identidade estável ligada ao ID, mesmo após renomear; nome padrão atualizado para Empréstimos e Financiamentos.
- `0.23` — 2026-09-24 — Substitui o gráfico mensal por uma barra compacta de progresso da quitação, com total pago e parcelas quitadas no hover.
- `0.22` — 2026-09-24 — Alinha o formulário, ações e hierarquia de Empréstimos ao padrão de Objetivos; o cadastro abre no topo da lista.
- `0.21` — 2026-09-24 — Associação de pagamentos passa ao formulário do lançamento, cadastro recolhido por ação, histórico sem duplicação, gráfico mensal de valores pagos e confirmação explicativa ao arquivar.

- `0.20` — 2026-09-24 — Move os estudos de pagamento adicional e estratégia para a aba Empréstimos do Efeito Borboleta; Empréstimos concentra cadastro e acompanhamento.
- `0.19` — 2026-09-24 — Fecha as decisões finais, define orçamento compartilhado por moeda e inicia a implementação da V1.

- `0.18` — 2026-09-24 — Lembrete de vencimento na Central de Notificações e aviso de pagamento não registrado ao fim do mês, com revisão manual de encargos.
- `0.17` — 2026-09-24 — Alteração, reclassificação, conciliação, estorno ou remoção de lançamento invalida o vínculo e gera alerta manual sem rollback/inferência.
- `0.16` — 2026-09-24 — Amortização extraordinária passa a oferecer redução de prazo ou redução do valor da parcela, escolhidas por cenário.
- `0.15` — 2026-09-24 — Compromisso nominal restante calculado automaticamente como quantidade de parcelas vezes valor regular, com ajuste para última parcela diferente.
- `0.14` — 2026-09-24 — Explicitado que prazo e pagamentos observados, sem taxa ou saldo principal, não identificam juros mensais ou totais; registrada possível entrada de principal para estimativa.
- `0.13` — 2026-09-24 — Quantidade de parcelas restantes (ou prazo total em contrato novo) definida como obrigatória; o prazo não será inferido.
- `0.12` — 2026-09-24 — Cadastro passa a aceitar taxa efetiva mensal ou CET efetivo anual, convertido para taxa mensal equivalente sem duplicar encargos embutidos.
- `0.11` — 2026-09-24 — Prestação e compromisso passam a usar o valor total com seguros/tarifas embutidos, sem campos de separação; projeção explicitada como estimativa simplificada.
- `0.10` — 2026-09-24 — Definido o compromisso nominal restante como saldo inicial visível e a próxima parcela como início do cronograma; separado do principal Price estimado.
- `0.9` — 2026-09-24 — Registradas as pendências sobre significado/data-base do saldo inicial e encargos incluídos nos débitos de pagamento.
- `0.8` — 2026-09-24 — Quitação e simulações ficam dentro de Empréstimos; Efeito Borboleta permanece estudo visual independente, sem ações ou lançamentos.
- `0.7` — 2026-09-24 — Definida a taxa mensal contratual como fonte de verdade quando taxa e prazo coexistem; prazo vira referência de comparação e divergências aparecem como estimativa.
- `0.6` — 2026-09-24 — Definido tratamento independente por moeda para cadastro, pagamentos, painel e estratégias; vínculos entre moedas diferentes são rejeitados sem conversão implícita.
- `0.5` — 2026-09-24 — Delimitado o domínio a empréstimos e dívidas contratuais relevantes, excluindo compras parceladas de consumo; acompanhamento manual separado de simulações Price.
- `0.4` — 2026-09-24 — Delimitada a V1 ao sistema Price prefixado; SAC e contratos com indexadores ou taxas variáveis ficam fora do escopo inicial.
- `0.3` — 2026-09-24 — Cadastro passa a solicitar saldo atual, valor da parcela, taxa mensal e prazo restante, exigindo ao menos um dos dois últimos e preservando ambos quando conhecidos.
- `0.2` — 2026-09-24 — Definida a decomposição estimada de parcelas Price: saldo, prestação e taxa mensal ou prazo restante; removida a necessidade inicial de informar juros separados em cada pagamento.
- `0.1` — 2026-09-24 — Criado rascunho de cadastro e plano de quitação, com pagamentos vinculados aos lançamentos de conta existentes e sem duplicação de débitos.

## Relacionados

- [[relatorios]]
- [[contas-correntes]]
- [[lancamentos]]
- [[score-saude-financeira]]
- [[../requisitos]]
- [[../arquitetura]]
