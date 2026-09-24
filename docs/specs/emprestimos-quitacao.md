---
tipo: spec
area: emprestimos-quitacao
status: em-implementacao
versao: 0.25
atualizado: 2026-09-24
relacionados:
  - "[[relatorios]]"
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[score-saude-financeira]]"
  - "[[efeito-borboleta]]"
  - "[[../requisitos]]"
  - "[[../arquitetura]]"
tags: [spec, "area/emprestimos-quitacao", "status/em-implementacao"]
aliases: ["Empréstimos e plano de quitação"]
---

# Empréstimos e plano de quitação

> [!info] Status
> **em-implementacao** · versão: `0.25` · área: `emprestimos-quitacao` · atualizado em 2026-09-24 · relacionados: [[relatorios]], [[contas-correntes]], [[lancamentos]], [[efeito-borboleta]]

## Problema

O app mostra parcelas em aberto de compras e cartões, mas não representa empréstimos bancários nem dívidas contratuais de maior porte, como financiamento de veículo ou imóvel, com saldo devedor, taxa, pagamentos e prazo. O usuário precisa visualizar essas dívidas e comparar, por cálculos determinísticos, cenários de pagamento adicional e estratégias de quitação. Compras parceladas de consumo, como celular, já pertencem aos fluxos existentes de Lançamentos e Cartões e não devem ser cadastradas neste módulo.

## Usuário

Pessoa que acompanha manualmente empréstimos bancários e dívidas contratuais relevantes — por exemplo, empréstimo pessoal ou consignado, financiamento de veículo ou imóvel, ou dívida renegociada — e quer entender como pagamentos adicionais podem alterar o prazo e o custo estimado.

## Jornada

1. O usuário cadastra uma dívida com moeda, quantidade e valor das parcelas restantes, taxa efetiva mensal e data da próxima parcela; para um contrato novo, informa a quantidade total e a data da primeira parcela.
2. No formulário de lançamentos, seleciona a categoria de despesas **Empréstimos e Financiamentos** e, opcionalmente, o contrato ativo correspondente; o vínculo é validado pela identidade da categoria, mesmo após renomeá-la.
3. O módulo atualiza o acompanhamento do saldo usando os pagamentos vinculados, sem criar um segundo débito na conta.
4. Na aba **Empréstimos** do Efeito Borboleta, o usuário simula um valor adicional mensal ou uma amortização extraordinária e compara juros estimados, prazo e valor de quitação.
5. Na mesma aba, para um conjunto de empréstimos, compara as estratégias avalanche e bola de neve.
6. O módulo Empréstimos concentra cadastro, acompanhamento e vínculos de pagamentos; estudos de quitação ficam no Efeito Borboleta e não gravam pagamentos nem alteram saldos reais.

## Dados

- `loan`: contrato acompanhado manualmente, com nome, modalidade, compromisso nominal restante, moeda, taxa e estado ativo/arquivado.
- `currency`: moeda original do empréstimo; obrigatória e mantida em todas as visões e cálculos.
- `monthly_rate`: taxa efetiva mensal normalizada e usada como fonte de verdade nas projeções Price; pode ser informada diretamente ou derivada do CET efetivo anual.
- `annual_cet`: CET efetivo anual informado pelo usuário, quando disponível; já representa o custo total e não recebe adição separada de seguros ou tarifas.
- `scheduled_installment`: valor da parcela contratada; se houver variação no valor final, informa-se o cronograma ou o total nominal restante.
- `remaining_installment_count`: quantidade obrigatória de parcelas ainda não pagas; para contrato novo, quantidade total contratada.
- `next_due_date`: data da próxima parcela; corresponde à primeira data de pagamento em um contrato novo.
- `remaining_commitment`: total nominal das parcelas ainda não pagas, na moeda original. É o valor de compromissos futuros, não o principal devedor.
- `estimated_principal`: valor presente estimado das parcelas restantes pelo modelo Price, usado internamente na simulação e não confundido com o compromisso nominal.
- `shared_monthly_extra_budget`: orçamento mensal adicional por moeda, alocado a um empréstimo prioritário por vez nas simulações avalanche/bola de neve.
- `linked_transaction_id`: referência opcional a um lançamento de saída da conta categorizado pela identidade `loan_payment` (categoria padrão **Empréstimos e Financiamentos**); um lançamento pode ser associado a no máximo um empréstimo.
- `extra_monthly_payment`: valor adicional mensal usado somente na simulação.
- `extraordinary_amortization`: valor e data de amortização extraordinária usados somente na simulação.

## Regras

- Cadastro, atualização de saldo e dados contratuais são manuais; a funcionalidade não exige conexão bancária nem usa IA.
- Cada empréstimo é calculado, exibido e acompanhado exclusivamente em sua moeda nativa; valores de moedas distintas nunca são somados nem convertidos implicitamente.
- O painel apresenta totais, projeções e resultados de estratégia separados por moeda. Avalanche e bola de neve são calculadas em grupos independentes de empréstimos da mesma moeda.
- Um excedente mensal destinado a uma estratégia pertence a uma única moeda e não pode ser distribuído entre empréstimos de moedas diferentes.
- A primeira versão permite acompanhar dívidas bancárias e contratuais de maior porte, separadas das compras parceladas de consumo já registradas em Contas e Cartões.
- A primeira versão calcula simulações de contratos pelo sistema Price, com parcelas fixas e taxa efetiva mensal fixa; o cálculo é determinístico e executado no backend, com valores monetários em centavos.
- O valor inicial exibido para empréstimo em andamento é a soma nominal das parcelas ainda não pagas; para contrato novo, é a soma das parcelas contratadas.
- Quando as parcelas restantes forem iguais, o compromisso nominal é calculado automaticamente multiplicando o valor da parcela pela quantidade de parcelas restantes. Se a última parcela tiver valor diferente, o usuário pode informar o valor ajustado do compromisso total.
- A data da próxima parcela é obrigatória e define o início do cronograma de pagamentos vinculados. Em contrato novo, o usuário informa a data da primeira parcela.
- A quantidade de parcelas restantes é obrigatória no cadastro; para contrato novo, o usuário informa o prazo total contratado. O sistema não infere nem preenche o prazo automaticamente.
- O compromisso nominal restante é diferente do principal devedor: o principal estimado para as projeções Price é calculado como valor presente das parcelas restantes com a taxa mensal e o cronograma informados.
- Dívidas de outros sistemas de amortização ou com saldo corrigido por indexador podem ser cadastradas e acompanhadas com atualização manual, mas não recebem projeções de juros e amortização até haver suporte explícito ao respectivo modelo.
- A taxa efetiva mensal informada é a fonte de verdade para decompor pagamentos e projetar juros no modelo Price.
- O usuário pode informar a taxa efetiva mensal ou o CET efetivo anual. O CET anual é convertido em taxa mensal equivalente pela conversão de taxas efetivas: `i_m = (1 + CET_a)^(1/12) - 1`.
- Encargos embutidos no CET anual e nos valores totais das parcelas não são somados uma segunda vez ao cálculo.
- O valor da parcela e o compromisso restante são informados pelo total cobrado pelo credor, incluindo seguros e tarifas embutidos; a V1 não pede nem mantém uma separação desses encargos.
- Se encargos embutidos fizerem a composição real diferir do modelo Price, o cálculo permanece uma estimativa simplificada baseada no valor total informado; a tela não apresenta a decomposição como demonstrativo oficial do credor.
- Com a taxa mensal conhecida, o principal estimado é o valor presente do cronograma restante; juros de cada período incidem sobre o principal anterior e a amortização corresponde à parcela destinada a principal após os juros.
- A quantidade de parcelas e o cronograma informados são usados para conferir a projeção, não para recalibrar silenciosamente a taxa.
- Se o cronograma e a taxa não fecharem exatamente por arredondamento ou particularidade do contrato, o cadastro é mantido e a diferença é apresentada como estimativa; não se altera a taxa informada.
- Se faltar taxa mensal, o app pode acompanhar o compromisso nominal e os pagamentos, mas não apresenta cálculo de juros economizados nem ordenação avalanche baseada em taxa até haver taxa suficiente.
- O cadastro não exige nem mantém o valor originalmente financiado ou um principal confirmado pelo credor; o principal de projeção é estimado a partir do cronograma restante e da taxa, quando informada.
- O histórico de pagamentos totais e o prazo, sem taxa ou saldo principal, não permitem identificar a parcela de juros de cada mês nem o total de juros; o sistema não deduz essa divisão dos débitos bancários.
- Um pagamento efetivo é representado pelo lançamento de saída já existente na conta e associado à categoria de despesas identificada internamente como `loan_payment`, cujo nome padrão é **Empréstimos e Financiamentos**. Renomear a categoria não rompe o vínculo semântico. Associá-lo ao contrato não cria lançamento, transferência ou débito adicional na conta.
- A moeda do lançamento associado deve ser igual à moeda do empréstimo; vínculos que exigiriam conversão cambial são rejeitados.
- O vínculo ao empréstimo é explícito; a categoria com identidade `loan_payment`, isoladamente, não converte uma compra parcelada ou dívida de cartão em contrato de empréstimo.
- O nome padrão da categoria é **Empréstimos e Financiamentos**; o `system_key=loan_payment` permanece no mesmo ID quando o usuário renomeia a categoria.
- Parcelamentos de compras de consumo, inclusive compras de celular, permanecem nos módulos existentes e não entram no painel nem nas estratégias deste módulo.
- O fluxo de pagamento é unidirecional: dinheiro sai de uma conta e é destinado a um empréstimo. Não há fluxo de empréstimo para conta nesta funcionalidade.
- Somente empréstimos ativos podem ser selecionados para novos vínculos de pagamentos. Arquivar um empréstimo não apaga seu histórico nem os vínculos existentes.
- Um lançamento associado não pode liquidar dois empréstimos; enquanto válido, sua associação identifica o pagamento sem criar atividade financeira duplicada.
- Se um lançamento vinculado for editado, reclassificado, conciliado, estornado ou removido, o vínculo é invalidado e o card do empréstimo exibe um alerta para revisar/atualizar os dados.
- A invalidação do vínculo não desfaz cálculos nem altera automaticamente o compromisso ou o estado do empréstimo; o usuário revisa e atualiza manualmente os dados do contrato.
- O alerta de revisão permanece até o usuário revisar/salvar os dados do empréstimo; o sistema não infere um novo saldo a partir do lançamento alterado.
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

- Dado um usuário sem empréstimos cadastrados, quando abre o módulo Empréstimos, então vê um estado vazio com ação para cadastrar o primeiro contrato.
- Dado empréstimos em moedas diferentes, quando o usuário consulta o painel, então saldos, pagamentos e projeções aparecem em grupos separados sem total convertido ou agregado.
- Dado empréstimos em moedas diferentes, quando o usuário executa avalanche ou bola de neve, então a ordenação e o orçamento excedente são aplicados separadamente em cada moeda.
- Dado um lançamento de conta em moeda diferente da moeda do empréstimo, quando o usuário tenta associá-lo, então o vínculo é rejeitado sem conversão nem alteração financeira.
- Dado um empréstimo ativo com parcelas Price, quando o usuário informa taxa efetiva mensal, valor e quantidade das parcelas restantes, então o módulo calcula o compromisso nominal e projeta a decomposição estimada entre juros e amortização.
- Dado um empréstimo cadastrado com CET efetivo anual, quando o app calcula a projeção, então converte o CET para a taxa mensal equivalente sem somar encargos embutidos novamente.
- Dado que o valor cobrado inclui seguro ou tarifa embutidos, quando o usuário cadastra a parcela e o compromisso restante, então informa os valores totais sem precisar separar esses encargos.
- Dada uma dívida contratual de sistema diferente do Price, quando o usuário a cadastra, então pode acompanhar os dados informados e pagamentos vinculados sem receber uma projeção incompatível com esse sistema.
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
- Dado um lançamento vinculado que é editado, reclassificado, conciliado, estornado ou removido, quando o sistema detecta a alteração, então invalida o vínculo e sinaliza revisão no card sem alterar automaticamente os dados do empréstimo.
- Dado um empréstimo com alerta de revisão, quando o usuário revisa e salva os dados do contrato, então o alerta é removido sem o app inferir valores do lançamento desvinculado.
- Dado um empréstimo arquivado, quando o usuário consulta seu histórico, então os pagamentos anteriormente associados continuam visíveis e preservados.
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

## Pendências

Não há decisões de produto pendentes para a V1. Detalhes técnicos podem ser resolvidos durante a implementação sem alterar estas regras.

## Fora de escopo

- Compras parceladas de consumo, como celulares, eletrodomésticos e outras compras já acompanhadas em Contas e Cartões.
- Conexão bancária, Open Finance, importação automática de saldo ou credor.
- Uso de modelos de IA para cadastrar contratos, categorizar empréstimos ou sugerir decisões.
- Garantia de que a projeção corresponda ao valor oficial de quitação do credor.
- Suporte inicial a SAC, a taxas variáveis ou indexadas (como TR, IPCA ou CDI), a seguros, tarifas, multas e renegociações com regras não representadas pelos campos disponíveis.
- Criar um segundo lançamento de conta para representar o mesmo pagamento associado ao empréstimo.

## Plano de implementação

- [x] Passo 1 — Persistir empréstimos e vínculos a lançamentos existentes com migração idempotente e isolamento por usuário/moeda.
- [x] Passo 2 — Implementar projeções Price, pagamentos adicionais compartilhados e amortização extraordinária no domínio Python.
- [x] Passo 3 — Invalidar vínculos quando lançamentos forem alterados e apresentar alertas de revisão/vencimento.
- [x] Passo 4 — Criar o menu e a tela Gestão → Empréstimos para cadastro, painel e vínculos.
- [x] Passo 5 — Implementar avalanche e bola de neve com alocação de excedente por moeda.
- [x] Passo 6 — Implementar amortização extraordinária com as alternativas de redução de prazo/parcela e os lembretes do Cockpit.
- [x] Passo 7 — Associar pagamentos no lançamento de conta, recolher o formulário, consolidar o histórico e exibir o gráfico de valores pagos com confirmação de arquivamento.
- [ ] Passo 8 — Revisar critérios automatizáveis e concluir validação funcional da integração.

## Changelog

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
