---
tipo: spec
area: consolidacao-familiar
status: rascunho
versao: 0.6
atualizado: 2026-08-28
relacionados:
  - "[[relatorios]]"
  - "[[score-saude-financeira]]"
  - "[[importacao-dados]]"
  - "[[preferencias-abas]]"
  - "[[seguranca-autenticacao]]"
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
  - "[[../adr/0011-criptografia-snapshots-familiares]]"
tags: [spec, "area/consolidacao-familiar", "status/rascunho"]
aliases: ["Consolidação Familiar", "Score Familiar", "Snapshots Familiares"]
---

# Consolidação Familiar

> [!info] Status
> **rascunho** · área: `consolidacao-familiar` · atualizado em 2026-08-28 · relacionados: [[relatorios]], [[score-saude-financeira]], [[importacao-dados]], [[preferencias-abas]], [[seguranca-autenticacao]], [[investimentos-portfolio]], [[../adr/0011-criptografia-snapshots-familiares]]

## Problema

Uma família pode usar o Sistema Financeiro em instalações independentes, uma em cada computador, sem compartilhar banco de dados ou credenciais. Nesse cenário, o responsável pela visão familiar não consegue acompanhar receitas, despesas, capacidade de poupança, reserva, endividamento, limites e concentração patrimonial do grupo ao longo dos meses.

A funcionalidade deve permitir que cada integrante gere uma fotografia analítica mensal, protegida por uma senha conhecida pela família, e que uma instalação consolidadora importe e mantenha essas fotografias em uma área isolada. Os dados importados não podem criar lançamentos, alterar saldos nem interferir no Cockpit, nos relatórios ou no Score individual do usuário.

## Usuário

- **Integrante exportador:** usuário autenticado que deseja compartilhar somente a fotografia financeira de um mês com seu grupo familiar.
- **Responsável consolidador:** usuário autenticado que mantém o grupo familiar, importa as fotografias dos integrantes e consulta a evolução consolidada.
- A mesma pessoa pode exercer os dois papéis e incluir seus próprios dados no grupo por meio do mesmo contrato de snapshot.

## Jornada

### Configuração do grupo

1. O responsável acessa **Consolidação Familiar** e cria um grupo com nome identificável.
2. Cadastra os integrantes esperados, usando apenas nome ou apelido e estado ativo/inativo.
3. Define os limites familiares usados no pilar de Aderência aos Limites.
4. Associa um dos integrantes a si próprio para permitir a geração local do snapshot.

### Inclusão dos dados do consolidador

1. O responsável escolhe o mês de referência na Consolidação Familiar.
2. Se ainda não houver snapshot local vigente, aciona **Incluir meus dados do mês**.
3. Se já houver snapshot local vigente, aciona **Atualizar meus dados do mês** e confirma sua substituição.
4. O app produz o mesmo snapshot analítico canônico usado pela exportação, valida-o em memória e persiste suas métricas diretamente no SQLite.
5. O app atualiza cobertura, consolidação, Score Familiar e o horário visível da última atualização.

### Exportação mensal

1. O integrante escolhe o mês de referência e seu nome ou apelido no grupo.
2. O app apresenta quais dados analíticos serão incluídos e quais dados sensíveis ficarão de fora.
3. O integrante informa e confirma a senha familiar.
4. O app gera um arquivo mensal criptografado e autenticado, contendo somente o snapshot previsto nesta spec.
5. O integrante transporta o arquivo pelo meio que escolher, fora do controle do app.

### Importação e consolidação

1. O responsável escolhe o grupo e envia o arquivo recebido.
2. Informa a senha familiar para abrir o arquivo.
3. O app valida autenticidade, versão, integrante, mês, tamanho, estrutura e duplicidade antes de persistir.
4. Se já houver snapshot do integrante para o mesmo mês, o app apresenta comparação resumida e exige confirmação para substituir.
5. O app recalcula a visão mensal e o Score Familiar usando os snapshots vigentes daquele grupo e mês.

### Consulta histórica

1. O responsável abre a visão familiar e escolhe um mês.
2. Visualiza receitas, despesas de consumo, saldo, investimentos/aportes e despesas por categoria/subcategoria.
3. Visualiza o Score Familiar, seus cinco pilares, a cobertura de integrantes e os avisos de dados insuficientes.
4. Consulta a evolução mensal do grupo, podendo identificar alterações de cobertura entre os meses.

## Dados

### Grupo e integrantes

| Campo | Tipo | Regra |
|---|---|---|
| `family_group_id` | inteiro | Identificador local do grupo; pertence ao usuário autenticado. |
| `group_name` | texto | Nome obrigatório e único entre os grupos do usuário. |
| `member_id` | inteiro | Identificador local do integrante dentro do grupo. |
| `member_name` | texto | Nome ou apelido obrigatório; não precisa corresponder ao nome civil. |
| `member_key` | texto opaco | Identificador estável usado para associar exportações ao integrante sem expor `user_id`, e-mail ou IDs internos. |
| `active` | booleano | Define se o integrante é esperado no cálculo de cobertura dos meses atuais. |

### Envelope transportável

| Campo | Tipo | Regra |
|---|---|---|
| `format` | texto | Identificador fixo do formato familiar. |
| `schema_version` | inteiro | Versão do contrato do arquivo. |
| `kdf` | objeto | Identifica `scrypt` e seus parâmetros versionados. |
| `salt` | texto codificado | Aleatório e exclusivo por arquivo. |
| `encryption` | objeto | Identifica `AES-256-GCM` e seus parâmetros. |
| `nonce` | texto codificado | Aleatório e exclusivo por arquivo. |
| `ciphertext` | texto codificado | Snapshot criptografado; nenhum dado financeiro fica exposto no envelope externo. |

### Snapshot mensal descriptografado

| Campo | Tipo | Regra |
|---|---|---|
| `export_id` | UUID aleatório | Identifica unicamente uma geração e participa da detecção de duplicidade. |
| `source_installation_id` | texto opaco | Identifica a instalação de origem sem revelar caminho, usuário do sistema operacional ou chave local. |
| `member_key` | texto opaco | Associa o snapshot ao integrante cadastrado. |
| `member_label` | texto | Apelido informado pelo exportador e confirmado na importação. |
| `source_type` | enum | `local` quando gerado diretamente pelo consolidador; `imported` quando recebido em arquivo. |
| `reference_month` | `AAAA-MM` | Um arquivo representa exatamente um mês. |
| `generated_at` | data/hora UTC | Momento da exportação. |
| `score_formula_version` | inteiro | Versão das entradas e regras usadas para reproduzir o diagnóstico. |
| `income_brl_cents` | inteiro | Receitas do mês normalizadas em BRL. |
| `consumption_expenses_brl_cents` | inteiro | Despesas de consumo normalizadas em BRL. |
| `investments_brl_cents` | inteiro | Investimentos e aportes do mês, separados de despesas. |
| `month_debt_installments_brl_cents` | inteiro | Parcelas de dívidas com competência/vencimento no mês. |
| `open_debt_stock_brl_cents` | inteiro | Estoque futuro de dívidas, apenas informativo. |
| `eligible_reserve_brl_cents` | inteiro | Valor atual das posições explicitamente marcadas como reserva. |
| `expenses_by_category` | lista | Totais em BRL por categoria e subcategoria; sem descrição de lançamento. |
| `portfolio_by_class` | lista | Classe e valor atual em BRL. |
| `savings_portfolio_brl_cents` | inteiro | Parcela do portfólio mantida em Poupança. |
| `original_currency_totals` | lista | Totais analíticos por moeda original, para transparência. |

### Dados deliberadamente ausentes do snapshot

- Descrições de lançamentos e nomes de estabelecimentos.
- Números de conta, cartão, agência, corretora ou documento pessoal.
- E-mail, senha de login, token de sessão, chaves locais e configurações de APIs.
- Observações, tags livres e IDs internos das tabelas de origem.
- Quantidade de ativos, preço médio e histórico de operações do Portfólio.

## Regras

### Isolamento e persistência

- Snapshots familiares pertencem a um grupo do usuário autenticado e ficam isolados dos lançamentos financeiros pessoais.
- Depois de autenticados e validados, snapshots importados são persistidos em colunas analíticas normais no SQLite, sob o mesmo modelo de segurança local dos demais dados financeiros.
- A senha familiar protege o arquivo transportável somente até sua importação; os dados persistidos não permanecem criptografados por essa senha.
- O processamento descriptografado ocorre somente em memória; a conexão de escrita é aberta apenas depois da autenticação e validação integral do arquivo.
- O integrante associado ao usuário consolidador pode ter seu snapshot gerado localmente por ação explícita no mês selecionado.
- A geração local reutiliza o mesmo contrato e as mesmas regras analíticas da exportação, mas não cria senha, envelope ou arquivo criptografado.
- Sem snapshot local vigente, a interface oferece **Incluir meus dados do mês**; com snapshot vigente, oferece **Atualizar meus dados do mês** e exibe a data/hora da última geração.
- Atualizar o snapshot local exige confirmação, substitui somente a versão vigente daquele grupo/integrante/mês e nunca altera os lançamentos pessoais de origem.
- A abertura da tela não recalcula nem substitui automaticamente snapshots locais, evitando mudança silenciosa do histórico.
- Importar, substituir, arquivar ou remover um snapshot nunca altera `transactions`, `credit_card_transactions`, saldos, faturas, limites pessoais, posições do Portfólio ou o Score individual.
- Deve existir no máximo um snapshot vigente por grupo, integrante e mês.
- Reimportar o mesmo `export_id` é uma duplicidade e não cria novo registro.
- Um novo arquivo do mesmo integrante e mês somente substitui o snapshot vigente após confirmação explícita.
- Substituições arquivam a versão anterior por prazo indeterminado, sem somar os dois snapshots; uma versão arquivada pode ser restaurada explicitamente.
- Não existe limpeza automática de snapshots arquivados. Exclusão definitiva ocorre somente ao apagar o grupo familiar, mediante confirmação e senha atual de login.
- Arquivar um integrante preserva os meses históricos e o retira da cobertura esperada dos meses posteriores ao arquivamento.

### Competência e valores

- Lançamentos de cartão entram no snapshot pela competência da fatura (`invoice_month`).
- Pagamentos de fatura ficam excluídos das despesas analíticas para evitar duplicidade.
- Transferências e câmbio entre contas ficam excluídos de receitas e despesas familiares.
- Investimentos e aportes permanecem separados das despesas de consumo.
- Valores monetários são inteiros em centavos; os cálculos familiares usam valores normalizados em BRL.
- O snapshot preserva totais por moeda original e a base BRL calculada na instalação de origem.
- Categorias e subcategorias são textos analíticos do snapshot e não criam nem alteram classificações locais.

### Cobertura mensal

- A cobertura informa quantos integrantes ativos esperados possuem snapshot vigente no mês.
- Um mês sem todos os integrantes esperados é exibido como **incompleto**.
- O Score Familiar pode ser calculado com cobertura incompleta, mas deve permanecer acompanhado do aviso e da relação dos integrantes ausentes.
- Cobertura incompleta não reduz artificialmente a pontuação; o resultado é calculado apenas com os snapshots vigentes e identificado como **parcial**.
- Gráficos históricos devem sinalizar mudanças de cobertura para evitar comparações silenciosamente enganosas.

### Score Familiar

- O Score Familiar é recalculado sobre as entradas consolidadas; nunca é a média dos scores individuais.
- Mantém escala de `0` a `1000`, zonas e pesos da [[score-saude-financeira]]: Poupança 250, Reserva 250, Endividamento 200, Limites 150 e Concentração 150.
- **Poupança:** `(receitas familiares - despesas familiares de consumo) / receitas familiares`.
- **Reserva:** soma das reservas elegíveis familiares dividida pela média das despesas familiares de consumo do mês consultado e dos dois meses anteriores.
- **Endividamento:** soma das parcelas familiares do mês dividida pelas receitas familiares do mês; o estoque aberto é apenas contexto.
- **Limites:** usa limites familiares recorrentes mensais cadastrados no grupo consolidador e despesas consolidadas por categoria; limites pessoais exportados não entram neste pilar.
- Categorias familiares são comparadas por nome normalizado exato. Nomes diferentes não são unidos automaticamente; o responsável pode cadastrar aliases explícitos, por exemplo `Mercado` → `Supermercado`.
- Categorias sem limite ou alias continuam visíveis como **Sem limite familiar**, sem correspondência aproximada ou inferência automática.
- **Concentração:** combina somente valores familiares por classe de ativo, preservando a penalidade de Poupança definida no Score individual; o MVP não exporta nem tenta reconciliar ativos individuais, ticker ou CNPJ.
- O Score Familiar aplica as mesmas regras de nota neutra para denominadores insuficientes da [[score-saude-financeira]].
- Se não houver três meses de despesas familiares, o pilar Reserva deve indicar histórico insuficiente e a confiança do diagnóstico.
- O resultado mensal registra a versão da fórmula; mudanças futuras não podem alterar silenciosamente o significado do histórico.
- O Score individual exportado pode ser exibido como contexto, mas não participa do cálculo familiar.

### Segurança e privacidade

- A implementação criptográfica transportável usa a dependência consolidada `cryptography`, deriva a chave da senha com `scrypt` e protege o snapshot com `AES-256-GCM`, conforme [[../adr/0011-criptografia-snapshots-familiares]].
- O envelope é versionado e registra somente formato, versão e parâmetros necessários à derivação e descriptografia; integrante, grupo, mês e dados financeiros permanecem dentro do texto cifrado.
- O arquivo transportável deve oferecer confidencialidade e integridade autenticada; arquivo adulterado e senha incorreta não podem produzir dados parciais.
- A senha familiar é fornecida a cada exportação e importação e nunca é persistida pelo app.
- A senha existe somente em memória durante a operação; não é gravada em Preferências, SQLite, arquivos temporários, logs, respostas de API ou envelopes exportados.
- A senha não é usada diretamente como chave criptográfica; cada arquivo usa salt e nonce aleatórios.
- A exportação exige confirmação da senha; não existe opção **Lembrar nesta máquina** nem recuperação da senha pelo app.
- Cada exportação possui sua própria senha, que deve ter entre 8 e 128 caracteres e incluir ao menos uma letra maiúscula e um número; letras minúsculas e símbolos são opcionais.
- A validação não remove espaços nem transforma silenciosamente a senha; a interface orienta o uso de uma frase-senha fácil de compartilhar com segurança e alerta, sem criar armazenamento, quando a senha estiver apenas no mínimo ou for previsível.
- Arquivos futuros podem usar outra senha sem migração ou alteração dos arquivos anteriores.
- A inclusão ou revogação de integrantes ocorre pelo compartilhamento ou interrupção do compartilhamento das senhas e arquivos futuros; o app não consegue revogar acesso a arquivos que já foram distribuídos.
- Falha de senha e falha de integridade retornam mensagem amigável que não revela detalhes criptográficos.
- O app valida limite de tamanho e estrutura antes de descriptografar ou persistir o conteúdo.
- Dados descriptografados não são escritos em arquivos temporários nem registrados em logs.
- A interface explica que a senha familiar protege o arquivo em transporte e que, depois da importação, as colunas analíticas passam a ter a mesma proteção local do restante do `finance.db`.
- A aprovação da implementação fica condicionada a round-trip no runtime PyInstaller e interoperabilidade comprovada entre os pacotes macOS, Windows e Linux.
- O arquivo usa obrigatoriamente a extensão `.sffamily` e tamanho máximo de 1 MB; arquivos maiores são rejeitados antes de executar `scrypt` ou descriptografar o conteúdo.
- O nome sugerido é `familia-AAAA-MM.sffamily`, sem nome do grupo ou integrante; a validação usa o conteúdo do envelope e não confia apenas na extensão.

### Comunicação do diagnóstico

- O Score Familiar usa mensagens estáticas e educativas, derivadas da linguagem do Score individual, sem IA generativa.
- A visão exibe o aviso: **Indicador educacional calculado a partir dos snapshots disponíveis. Não constitui recomendação financeira. Confira a cobertura do mês antes de comparar períodos.**
- Mensagens usam termos coletivos como **A família** ou **Neste grupo**, não atribuem culpa a um integrante e não exibem ranking de melhor ou pior pessoa.
- Nenhuma mensagem recomenda compra, venda ou alocação de ativo.

## API e dados

> [!warning] Contrato preliminar
> Rotas, nomes de tabelas e formato de arquivo são candidatos para revisão. Nenhum deles está autorizado para implementação enquanto as pendências de criptografia não forem resolvidas em ADR.

### Rotas candidatas

| Método | Rota | Comportamento proposto |
|---|---|---|
| `GET` | `/api/family-groups` | Lista grupos do usuário autenticado. |
| `POST` | `/api/family-groups` | Cria grupo familiar. |
| `PUT` | `/api/family-groups/{id}` | Atualiza nome, integrantes e estado. |
| `GET` | `/api/family-consolidation?group_id=&month=` | Retorna consolidação, cobertura e Score Familiar do mês. |
| `GET` | `/api/family-consolidation/history?group_id=&months=` | Retorna evolução mensal e cobertura. |
| `POST` | `/api/family-snapshots/export` | Gera arquivo criptografado do mês do usuário autenticado. |
| `POST` | `/api/family-snapshots/import` | Valida e prepara importação; substituição exige confirmação. |
| `DELETE` | `/api/family-snapshots/{id}` | Arquiva snapshot familiar sem afetar dados pessoais. |
| `POST` | `/api/family-snapshots/{id}/restore` | Restaura explicitamente uma versão arquivada. |
| `DELETE` | `/api/family-groups/{id}` | Exclui definitivamente o grupo e seus snapshots após confirmação e senha atual. |

Todas as mutações exigem sessão autenticada e validação de `Host`/`Origin` conforme as regras gerais do app.

### Tabelas candidatas

- `family_groups`: grupo pertencente ao usuário consolidador.
- `family_members`: integrantes, chave opaca, período de atividade e estado.
- `family_monthly_snapshots`: metadados e colunas analíticas do mês, versões, hash e estado vigente/substituído/arquivado; não armazena o envelope transportável nem a senha familiar.
- `family_spending_limits`: limites mensais ou recorrentes definidos para o grupo.
- `family_category_aliases`: correspondências explícitas entre nomes normalizados de categoria e a categoria familiar de destino.
- `family_score_history`: resultado reproduzível do Score Familiar, cobertura e versão da fórmula, caso a decisão seja persistir o cálculo em vez de recalculá-lo sob demanda.

O desenho final deve usar migrações idempotentes em `financeiro/database.py` e manter SQLite como única fonte de verdade local.

## Critérios de aceite

1. Dado um usuário autenticado com dados no mês, quando exporta um snapshot familiar com senha válida, então recebe um arquivo que não expõe dados financeiros em texto legível.
2. Dado o arquivo exportado, quando aberto com a senha correta em outra instalação, então o mês, integrante e totais analíticos são recuperados integralmente.
3. Dado um arquivo com um byte alterado, quando importado, então a operação é rejeitada sem persistir snapshot parcial.
4. Dado um arquivo e uma senha incorreta, quando importado, então a operação é rejeitada sem expor detalhes criptográficos.
5. Dado um snapshot contendo dados pessoais ou campos fora do contrato, quando validado, então campos desconhecidos não são persistidos nem exibidos.
6. Dado um arquivo acima de 1 MB, quando enviado, então é rejeitado antes de executar `scrypt` ou descriptografar o conteúdo.
7. Dado um snapshot válido de cartão, quando exportado, então suas despesas pertencem ao `invoice_month` da fatura.
8. Dado um pagamento de fatura, quando o snapshot é calculado, então ele não aumenta as despesas familiares.
9. Dado uma transferência ou câmbio entre contas, quando o snapshot é calculado, então o movimento não aumenta receitas nem despesas familiares.
10. Dado um investimento ou aporte, quando o snapshot é calculado, então ele aparece separado das despesas de consumo.
11. Dado valores em moedas diferentes, quando o snapshot é gerado, então preserva totais por moeda e valores normalizados em centavos de BRL.
12. Dado um snapshot importado, quando o Cockpit ou Score pessoal é consultado, então os dados familiares não alteram nenhum resultado individual.
13. Dado o mesmo `export_id` importado novamente, quando a operação é confirmada, então nenhum snapshot duplicado é criado.
14. Dado outro arquivo do mesmo integrante e mês, quando importado, então o app exige confirmação antes de substituir o snapshot vigente.
15. Dado a substituição confirmada, quando a consolidação é recalculada, então somente a nova versão participa dos totais.
16. Dado um grupo com três integrantes ativos e dois snapshots no mês, quando a consolidação é exibida, então mostra cobertura `2 de 3`, estado incompleto e o integrante ausente.
17. Dado meses com coberturas diferentes, quando o histórico é exibido, então cada ponto informa sua cobertura.
18. Dado snapshots completos do mês, quando o Score Familiar é calculado, então os pilares usam a soma das entradas familiares e não a média dos scores individuais.
19. Dado receitas e despesas familiares válidas, quando o pilar Poupança é calculado, então usa `(receitas - despesas de consumo) / receitas` com limite de 250 pontos.
20. Dado três meses de despesas e reservas familiares elegíveis, quando o pilar Reserva é calculado, então usa reserva total dividida pela média das despesas familiares dos três meses.
21. Dado menos de três meses disponíveis, quando o pilar Reserva é exibido, então informa histórico insuficiente e a confiança reduzida.
22. Dado parcelas de dívida e receitas familiares no mês, quando o pilar Endividamento é calculado, então usa parcelas do mês divididas pelas receitas familiares.
23. Dado limites recorrentes cadastrados no grupo, quando o pilar Limites é calculado, então compara as despesas familiares consolidadas aos limites familiares.
24. Dado portfólios de vários integrantes, quando o pilar Concentração é calculado, então combina exposições somente por classe de ativo e aplica a regra familiar documentada.
25. Dado denominador familiar igual ou inferior a zero, quando um pilar relativo é calculado, então aplica a mesma nota neutra e aviso de dados insuficientes do Score individual.
26. Dado uma mudança futura na fórmula, quando um resultado histórico é exibido, então a versão usada no cálculo permanece identificável.
27. Dado um integrante arquivado, quando meses anteriores ao arquivamento são consultados, então seus snapshots históricos permanecem disponíveis.
28. Dado um usuário sem acesso ao grupo, quando tenta consultar, importar, substituir ou remover snapshots, então recebe erro de autorização sem acesso aos dados.
29. Dado um snapshot removido, quando a operação termina, então ele deixa de participar da consolidação sem excluir lançamentos pessoais.
30. Dado a tela de Consolidação Familiar, quando valores e pilares são exibidos, então o usuário consegue distinguir claramente diagnóstico familiar, diagnóstico individual e cobertura do mês.
31. Dado um arquivo autenticado e validado, quando sua importação é confirmada, então suas métricas são persistidas em colunas analíticas no SQLite sem gravar senha, envelope transportável, arquivo temporário ou conteúdo descriptografado em log.
32. Dado uma exportação ou importação concluída, quando a operação termina, então a senha familiar não permanece em Preferências, SQLite, arquivos, logs, respostas ou envelopes.
33. Dado arquivos gerados pelos pacotes macOS, Windows e Linux, quando abertos nos pacotes das outras plataformas com a senha correta, então todos os pares suportados concluem o round-trip com os mesmos dados analíticos.
34. Dado uma senha com menos de 8 caracteres, mais de 128 caracteres, sem letra maiúscula ou sem número, quando o usuário tenta exportar, então o arquivo não é gerado e a exigência não atendida é informada de modo amigável.
35. Dado uma senha válida e sua confirmação diferente, quando o usuário tenta exportar, então o arquivo não é gerado.
36. Dado que um integrante deixou de participar do grupo, quando novos snapshots são exportados com outra senha e não são compartilhados com ele, então o app informa que isso protege apenas os novos arquivos e não revoga arquivos anteriormente distribuídos.
37. Dado o consolidador sem snapshot local vigente no mês selecionado, quando aciona **Incluir meus dados do mês**, então o app persiste diretamente no SQLite o mesmo conteúdo analítico que seria produzido pela exportação, sem gerar senha, envelope ou arquivo.
38. Dado o consolidador com snapshot local vigente no mês selecionado, quando aciona **Atualizar meus dados do mês**, então o app solicita confirmação antes de substituir a versão vigente.
39. Dado uma atualização local confirmada, quando o processamento termina, então cobertura, consolidação, Score Familiar e data/hora da última atualização refletem o novo snapshot sem alterar lançamentos pessoais.
40. Dado um snapshot local vigente, quando o usuário apenas abre a tela de Consolidação Familiar, então o snapshot não é recalculado ou substituído automaticamente.
41. Dado cobertura incompleta no mês, quando o Score Familiar é calculado, então usa os snapshots disponíveis sem penalidade adicional e exibe resultado parcial, cobertura e integrantes ausentes.
42. Dado categorias com o mesmo nome normalizado, quando as despesas são consolidadas, então participam da mesma categoria familiar.
43. Dado categorias com nomes diferentes e sem alias, quando consolidadas, então permanecem separadas e aparecem como **Sem limite familiar** sem correspondência automática.
44. Dado um alias familiar explícito, quando a consolidação é calculada, então a categoria de origem contribui para a categoria familiar de destino.
45. Dado um arquivo com extensão diferente de `.sffamily` ou envelope incompatível, quando enviado, então é rejeitado sem confiar apenas no nome do arquivo.
46. Dado uma versão substituída, quando o histórico técnico é consultado, então ela permanece arquivada, não participa dos cálculos e pode ser restaurada explicitamente.
47. Dado um grupo familiar existente, quando o usuário solicita exclusão definitiva, então o app exige confirmação e senha atual antes de remover grupo, integrantes, snapshots, limites e aliases.
48. Dado a exibição do Score Familiar, quando as mensagens são renderizadas, então apresentam aviso educacional, cobertura e linguagem coletiva sem ranking, culpa ou recomendação de ativo.

## Pendências

> [!question] Pendências
> Nenhuma pendência funcional conhecida. A implementação continua bloqueada pelas validações técnicas pendentes em [[../adr/0011-criptografia-snapshots-familiares]].

## Fora de escopo

- Sincronização automática entre instalações, servidor central, conta familiar online ou armazenamento em nuvem administrado pelo app.
- Importação dos lançamentos familiares para contas, cartões, saldos ou faturas do consolidador.
- Edição de um lançamento individual a partir da instalação consolidadora.
- Compartilhamento de senha, envio de arquivo ou recuperação da senha familiar pelo app.
- Recomendação personalizada de compra, venda ou alocação de investimentos.
- Compatibilidade com planilhas genéricas, bancos externos ou formatos contábeis nesta primeira versão.
- Consolidação entre moedas sem valor BRL normalizado fornecido pela instalação de origem.

## Plano de implementação

- [ ] Passo 1 — Concluir as validações técnicas do ADR criptográfico e promovê-lo somente depois das provas de empacotamento. Fecha: critérios 1 a 6, 13 a 17, 21, 24, 26, 28, 32, 33 e 45.
- [ ] Passo 2 — Atualizar [[requisitos]], [[arquitetura]], [[visao-produto]] e [[roadmap]] com o escopo aprovado, sem alterar as regras dos módulos pessoais. Fecha: critérios 12, 28, 29 e 30.
- [ ] Passo 3 — Criar migrações idempotentes das estruturas familiares e testes de isolamento, unicidade, substituição, arquivamento/restauração, aliases, persistência analítica e autorização. Fecha: critérios 12 a 17, 27 a 31 e 42 a 47.
- [ ] Passo 4 — Implementar geração canônica do snapshot mensal no núcleo Python, reutilizando as regras de competência, exclusão de pagamentos, transferências, investimentos e normalização monetária tanto na exportação quanto na inclusão local. Fecha: critérios 7 a 11 e 37 a 40.
- [ ] Passo 5 — Implementar o envelope versionado com `cryptography`, `scrypt` e `AES-256-GCM`, incluindo validação defensiva, senha somente em memória, política de força e testes unitários. Fecha: critérios 1 a 6, 32 e 34 a 36.
- [ ] Passo 6 — Implementar importação, comparação, confirmação de substituição e persistência analítica curta/atômica depois da validação integral em memória. Fecha: critérios 2 a 6, 13 a 15 e 31.
- [ ] Passo 7 — Extrair ou reutilizar funções puras dos cinco pilares para calcular o Score Familiar com cobertura parcial, limites recorrentes, aliases, concentração por classe e versão de fórmula. Fecha: critérios 18 a 26 e 41 a 44.
- [ ] Passo 8 — Implementar rotas autenticadas e validação de propriedade/Host/Origin para grupos, integrantes, snapshots, restauração, limites, aliases, consolidação e histórico. Fecha: critérios 13 a 17, 27 a 29 e 42 a 47.
- [ ] Passo 9 — Implementar a view modular de Consolidação Familiar, incluindo exportação, importação, inclusão/atualização local, cobertura parcial, aliases, arquivo histórico, mensagens educativas, visão mensal, pilares e evolução. Fecha: critérios 14, 16, 17, 21, 26, 30 e 37 a 48.
- [ ] Passo 10 — Criar testes automatizados por critério de domínio/API/segurança e validar round-trip PyInstaller e interoperabilidade cruzada entre instalações limpas de macOS, Windows e Linux. Fecha: critérios 1 a 48.

## Changelog

- `0.6` — 2026-08-28 — Fechado o MVP funcional: extensão `.sffamily` e limite de 1 MB; Portfólio somente por classe; Score parcial sem penalidade e com cobertura; limites recorrentes com aliases manuais; versões substituídas arquivadas/restauráveis; exclusão definitiva apenas com o grupo; mensagens estáticas, coletivas e educativas. Pendências restantes concentram-se no ADR criptográfico.
- `0.5` — 2026-08-28 — Definida a participação do consolidador: botões **Incluir meus dados do mês** e **Atualizar meus dados do mês** geram sob demanda o snapshot analítico canônico e o persistem diretamente no SQLite, sem senha ou arquivo, com confirmação para substituição e sem recálculo silencioso ao abrir a tela.
- `0.4` — 2026-08-28 — Definido o ciclo de vida não persistido da senha por arquivo: 8 a 128 caracteres, ao menos uma maiúscula e um número, confirmação obrigatória, troca livre em exportações futuras e aviso de que o app não revoga acesso a arquivos já distribuídos. [[../adr/0011-criptografia-snapshots-familiares]] atualizado.
- `0.3` — 2026-08-28 — Definido o envelope transportável com `cryptography`, `scrypt` e `AES-256-GCM`; senha fornecida a cada operação e nunca persistida; aprovação condicionada a round-trip PyInstaller e interoperabilidade entre macOS, Windows e Linux. Criado [[../adr/0011-criptografia-snapshots-familiares]].
- `0.2` — 2026-08-28 — Decidido que snapshots importados serão persistidos em colunas analíticas normais no SQLite, sob a segurança local geral da aplicação. A senha familiar protege somente o transporte; descriptografia e validação ocorrem integralmente em memória antes da transação de escrita.
- `0.1` — 2026-08-28 — Rascunho inicial da Consolidação Familiar com snapshots mensais criptografados entre instalações, persistência isolada, cobertura por integrante, evolução histórica e Score Familiar recalculado pelos cinco pilares.

## Relacionados

- [[relatorios]]
- [[score-saude-financeira]]
- [[importacao-dados]]
- [[preferencias-abas]]
- [[seguranca-autenticacao]]
- [[investimentos-portfolio]]
- [[arquitetura]]
- [[../adr/0011-criptografia-snapshots-familiares]]
