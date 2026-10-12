---
tipo: spec
area: importacao
status: implementado
versao: 1.17
atualizado: 2026-10-12
relacionados:
  - "[[contas-correntes]]"
  - "[[cartoes]]"
  - "[[categorias-tags-gestao]]"
  - "[[lancamentos]]"
  - "[[adr/0004-importador-xls-sem-dependencia]]"
  - "[[arquitetura]]"
tags: [spec, "area/importacao", "status/implementado"]
aliases: ["Importação", "Importação de dados"]
---

# Importação de dados

> [!info] Status
> **implementado** · versão: `1.17` · área: `importacao` · atualizado em 2026-10-12 · relacionados: [[contas-correntes]], [[cartoes]], [[categorias-tags-gestao]], [[adr/0004-importador-xls-sem-dependencia]], [[desacoplamento-importacao-parsers]]

## Problema

O usuário precisa importar movimentações de contas e cartões a partir de arquivos externos ou de planilhas modelo do próprio sistema, preservando categorias, subcategorias, tags e competência de fatura correta.

## Usuário

Usuário que está migrando dados de outro sistema ou que deseja lançar movimentações em massa via planilha.

## Jornada

1. O usuário acessa a área de Importação.
2. Escolhe entre modelo do sistema, planilha externa (`.xls`/`.csv`) ou extrato OFX.
3. Seleciona a conta ou cartão de destino.
4. Faz upload do arquivo compatível com a origem escolhida (`.xls`, `.csv`, `.xlsx` ou `.ofx`/`.qfx`).
5. Revisa, edita e seleciona as transações antes de confirmar a importação.
6. Se uma linha editada for importada com sucesso ou explicitamente ignorada como duplicidade, o sistema aprende a descrição e classificação corrigidas para aquela conta ou cartão, sem alterar lançamentos no caso de ignorar.
7. Em arquivos seguintes do mesmo instrumento, as correções aprendidas aparecem aplicadas e identificadas na prévia.
8. O sistema exibe o resumo: total lido, novos, substituídos e ignorados, além de uma lista compacta em linha única para cada lançamento importado ou ignorado, com descrição e motivo quando houver.

## Dados — Colunas reconhecidas

| Coluna | Regra |
|---|---|
| Data | ISO (`YYYY-MM-DD`), `DD.MM.YYYY`, `DD/MM/YYYY`, `DD-MM-YYYY` ou data serializada pelo Excel. Data inválida rejeita a linha com motivo `Data invalida.` |
| Descrição | Obrigatório. |
| Categoria | Obrigatório para receitas, despesas e investimentos. |
| Subcategoria | Opcional. |
| Valor | Formato brasileiro com vírgula (`66,02`) ou numérico do Excel. |
| Situação | Apenas linhas com `Pago` são importadas. |
| Tags | Opcional. Múltiplas tags separadas por separador suportado. |
| Informações adicionais | Opcional. |
| Tipo | Tipo do lançamento. |
| Conta destino | FK para transferências e câmbio. |
| Competência da fatura | `invoice_month` para importações de cartão. |
| Repetição | Modelo próprio: `avulso` (padrão), `parcelado` ou `recorrente`. Aceita também `single`, `installment` e `recurring`. |
| Parcelas | Modelo próprio: quantidade de parcelas (2 a 120), obrigatória quando Repetição é `parcelado`. |
| Recorrência | Modelo próprio: frequência (`semanal`, `mensal`, `trimestral`, `semestral` ou `anual`), obrigatória quando Repetição é `recorrente`. |
| Média | Modelo próprio: `sim`/`não` para recorrentes usarem o valor médio do histórico (só se aplica a `recorrente`). |

## Modelos do sistema

- `GET /api/import/template?target=account` — download do modelo de contas (`.xlsx` com abas de lançamentos, categorias/subcategorias, tags e contas).
- `GET /api/import/template?target=card` — download do modelo de cartões (`.xlsx` com abas de lançamentos, categorias/subcategorias e tags).

## Regras

- A importação de conta exige que o usuário escolha uma conta ativa de destino.
- A importação de cartão exige que o usuário escolha um cartão ativo de destino.
- Cada linha importada deve ter descrição, data válida e valor diferente de zero.
- Categoria é obrigatória para receitas, despesas e investimentos. Transferências e câmbio não exigem categoria.
- Linhas com situação diferente de `Pago` não afetam saldo e aparecem como ignoradas no resultado.
- Valores positivos entram como receita; negativos como despesa.
- Na confirmação da prévia, categoria e subcategoria devem corresponder a itens já existentes do usuário; não são criadas a partir de texto digitado. Tags novas digitadas podem ser criadas para o usuário autenticado. Ver [[categorias-tags-gestao]].
- Quando a coluna Tags trouxer mais de uma tag, todas devem ser vinculadas ao lançamento.
- Arquivos Excel podem trazer valores numéricos formatados visualmente; o parser usa o valor real da célula sem multiplicações indevidas.
- Arquivos OFX (`.ofx`/`.qfx`) são aceitos como extratos bancários legados quando contêm `STMTTRN` com `DTPOSTED` e `TRNAMT`, convertendo valores positivos para receita e negativos para despesa e presumindo categoria genérica de `Outras Receitas` ou `Outras Despesas` quando a exportação não informa. São aceitos XML e SGML OFX 1.x, respeitando `CHARSET` comum do cabeçalho.
- A prévia OFX é uma etapa explícita da interface. Linhas válidas iniciam selecionadas, podem ter data, descrição, valor, categoria, subcategoria, tags e observações revisados, e somente linhas selecionadas são persistidas.
- A prévia exibe a descrição original do arquivo em campo somente de leitura e uma descrição separada editável chamada **Descrição Lançamento**, usada no lançamento. A origem é preservada mesmo quando há correção aprendida anteriormente.
- Na prévia de importação, categoria e subcategoria são seletores limitados às opções existentes do usuário; subcategorias são oferecidas conforme a categoria escolhida. Tags usam uma única linha com sugestões das opções existentes, permitindo digitar uma nova tag.
- OFX destina-se à importação em conta corrente; cartão não é um destino disponível nesse modo.
- Correções feitas em descrição, categoria, subcategoria ou tags são aprendidas após a linha selecionada ser importada com sucesso ou quando o usuário escolhe explicitamente **Ignorar esta linha** para uma duplicidade validada novamente na confirmação. Nesse caso, o aprendizado não cria nem altera lançamentos. Edições de data/valor, linhas apenas desmarcadas ou rejeitadas não atualizam o aprendizado.
- O aprendizado usa correspondência exata após normalização sem distinção de maiúsculas/minúsculas e acentos, preservando números, e é isolado por usuário, conta ou cartão e tipo de lançamento. Uma correção posterior bem-sucedida para a mesma chave substitui a anterior.
- A regra aprendida mantém a descrição original como chave principal e também permite localizar pela descrição editável corrigida; a correção contém os valores finais importados.
- Quando a descrição original ou a descrição editável previamente corrigida reaparece no mesmo instrumento, a prévia aplica a descrição, categoria, subcategoria e tags aprendidas e marca a linha como **Já ajustado**; o usuário ainda decide se importa.
- Importações de cartão preenchem `invoice_month` e consideram o mês da fatura para relatórios e limites. Ver [[cartoes]].
- No modelo próprio, uma linha com Repetição `parcelado` gera uma série de N lançamentos parcelados; uma linha `recorrente` gera uma série recorrente (até 120 ocorrências) e pode usar a Média do histórico. Transferências e câmbio são sempre avulsos, mesmo se a linha trouxer Repetição.
- Modelos gerados antes da coluna Repetição (sem `repeticao`, `parcelas`, `recorrencia` e `media`) continuam importando normalmente: as linhas entram como avulsas.
- A importação retorna resumo com total lido, novos, substituídos e ignorados, junto aos detalhes de todas as linhas importadas e ignoradas; nenhuma linha de resultado é truncada.
- A validação da prévia preserva a categoria/subcategoria escolhidas, limita categorias ao grupo compatível com o tipo do lançamento e rejeita seleções que não sejam opções existentes do usuário.
- A prévia identifica duplicidade somente quando instrumento, tipo, data, valor, categoria e subcategoria coincidem integralmente com lançamento ativo existente.
- Para duplicidade, o usuário pode ignorar a linha ou substituir descrição, categoria/subcategoria, tags e observações do lançamento existente; data, valor e instrumento permanecem inalterados, pois são parte da correspondência.
- Quando mais de um lançamento corresponde exatamente, substituir exige selecionar explicitamente qual candidato atualizar. Confirmação sem escolha de ação não cria duplicata; alterações de candidato entre prévia e confirmação são validadas novamente.
- Ao confirmar uma linha revisada, a categoria e os demais campos visíveis no formulário são enviados com seus valores atuais, inclusive se a edição ocorrer imediatamente antes da confirmação.
- Importações em lote devem processar a leitura/parsing fora da conexão SQLite e persistir cada linha em uma transação curta, preservando sucesso parcial sem segurar lock durante todo o arquivo.
- O parser `.xls` é implementado sem dependência externa. Ver [[adr/0004-importador-xls-sem-dependencia]].

## Regras de segurança

- A rota de importação exige sessão autenticada.
- A conta ou cartão de destino precisa pertencer ao usuário autenticado e estar ativo.
- O upload aceita arquivos de até **5 MB**.
- O parser XLSX reaplica o limite de **5 MB** fora da camada HTTP e rejeita pacotes com mais de **128 membros**, nomes duplicados ou caminhos inseguros, criptografia, compressão diferente de `stored`/`deflate`, membro expandido acima de **16 MB**, total expandido acima de **32 MB** ou razão de compressão acima de **100:1**.
- A aba importada aceita no máximo **20.000 linhas**, **250.000 células** e coluna `IV` (índice 256); `sharedStrings.xml` aceita no máximo **100.000 entradas**. Arquivos que ultrapassam os limites são rejeitados integralmente antes de qualquer escrita financeira.
- A importação não aceita identificadores de outro usuário para contas, cartões, categorias ou tags.
- Dados textuais importados são normalizados antes de persistir.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/import/template?target=account` |
| `GET` | `/api/import/template?target=card` |
| `POST` | `/api/import/legacy-transactions` — aceita prévia (`preview=true`) e confirmação das linhas selecionadas (`preview_rows`). |
| `POST` | `/api/import/system-template` |

Tabelas: `transactions`, `credit_card_transactions`, `transaction_tags`, `credit_card_transaction_tags`, `categories`, `subcategories`, `tags`, `checking_accounts`, `credit_cards`, `import_adjustments`.

Módulos de domínio:
- `financeiro/import_utils.py` — utilitários puros compartilhados (`ImportError`, normalização de chave, data, valor monetário).
- `financeiro/import_parsers.py` — leitura de formatos tabulares (`.xls`, `.xlsx`, `.csv`) e helpers de cabeçalho/célula.
- `financeiro/import_ofx.py` — leitura de extratos `.ofx`/`.qfx`.
- `financeiro/import_templates.py` — geração de modelos `.xlsx` do sistema.
- `financeiro/imports.py` — orquestração do pipeline de importação (prévia, validação, deduplicação, aprendizado e persistência).

## Critérios de aceite

- Dado um arquivo `.xls` legado de exportação externa, quando importado, é lido sem instalação manual de pacote externo.
- Dado um arquivo `.csv` ou `.xlsx` com colunas reconhecidas, quando importado, é aceito normalmente.
- Dado que o usuário escolheu Planilha externa, quando seleciona `.xls` ou `.csv`, então o sistema revisa o arquivo em contexto de conta corrente antes da confirmação.
- Dado um arquivo `.ofx` ou `.qfx` em padrão OFX com `STMTTRN` e `TRNAMT`, quando importado, cada transação é convertida para linha financeira com valor, data e descrição compatíveis com a importação legada.
- Dado que o usuário escolheu o modo Extrato OFX, quando seleciona um arquivo, então a tela aceita `.ofx`/`.qfx`, solicita uma conta e não oferece cartão como destino.
- Dado um arquivo OFX válido, quando selecionado, então a tela exibe a prévia antes de qualquer escrita financeira.
- Dado a prévia OFX, quando o usuário edita uma linha, então os valores revisados são usados na confirmação.
- Dado a prévia OFX, quando o usuário desmarca uma linha, então essa linha não é persistida.
- Dado a prévia de qualquer formato, quando o usuário revisa categoria/subcategoria, então escolhe somente opções existentes em combos, e pode criar tags novas sem digitar categorias ou subcategorias.
- Dado uma linha na prévia, quando exibida, então a descrição do arquivo é preservada sem edição e um campo Descrição separado determina o texto salvo no lançamento.
- Dado um ajuste de descrição aprendido, quando um arquivo posterior já trouxer o texto editável corrigido, então o ajuste contextual também é localizado.
- Dado o campo Tags na prévia, quando o usuário digita, então recebe sugestões das tags existentes em uma linha e ainda pode informar uma tag nova.
- Dado um arquivo OFX inválido, quando selecionado, então a interface exibe erro compreensível sem criar lançamentos.
- Dado que uma linha revisada altera descrição ou classificação e é importada com sucesso, quando um arquivo posterior da mesma conta/cartão contém a descrição original, então a prévia reaplica a correção e marca **Já ajustado**.
- Dado uma correção de descrição/classificação importada em uma conta ou cartão, quando outro instrumento do mesmo usuário contém a mesma descrição, então o aprendizado não é aplicado ao outro instrumento.
- Dado que a linha corrigida esteja desmarcada ou falhe na importação, quando um arquivo posterior contém a descrição original, então a correção não foi aprendida.
- Dado que duas descrições só diferem por maiúsculas ou acentos, quando o mesmo instrumento importa a descrição novamente, então a correção aprendida é encontrada sem confundir descrições com números distintos.
- Dado o final da importação de conta, quando consultado, os saldos refletem apenas as linhas importadas com situação `Pago`.
- Dado o final da importação de cartão, quando consultado, os lançamentos aparecem na fatura correta.
- Dado linhas rejeitadas, quando exibidas, mostram número da linha e motivo da rejeição.
- Dado a listagem de lançamentos importados, quando exibida, mostra categoria, subcategoria e tags quando existirem.
- Dado uma linha com data `02.05.2026` (DD.MM.YYYY) no modelo próprio, quando importada, é aceita normalmente.
- Dado uma linha com data inválida, quando importada, é rejeitada com motivo `Data invalida.` sem afetar as demais linhas.
- Dado uma linha parcelada com `parcelas` = 3, quando importada, gera 3 lançamentos da mesma série.
- Dado uma linha recorrente com Média `sim`, quando importada, a série usa o valor médio do histórico.
- Dado um modelo antigo sem as colunas de repetição, quando importado, continua funcionando (linhas avulsas).
- Dado um XLSX cuja expansão, razão de compressão, quantidade de membros ou membro individual exceda o orçamento seguro, quando importado, é rejeitado com mensagem amigável antes de abrir transação SQLite.
- Dado um XLSX com membro duplicado, criptografado, método de compressão não suportado ou caminho interno inseguro, quando importado, é rejeitado como modelo inválido.
- Dado uma worksheet acima dos limites de linhas, células ou coluna, quando analisada, é rejeitada sem preencher listas proporcionais ao índice malicioso.
- Dado o modelo XLSX oficial ou um modelo antigo dentro dos limites, quando importado, continua sendo aceito com as mesmas colunas e valores.
- Dado o painel de resultado antes do primeiro envio, quando a tela é aberta, então ele apresenta orientação semântica para baixar, preencher e selecionar o modelo.
- Dado que o usuário escolhe uma categoria/subcategoria válida na prévia, quando confirma a importação, então o lançamento mantém exatamente a classificação escolhida, sem ser trocado por outra categoria de grupo incompatível.
- Dado que instrumento, tipo, data, valor, categoria e subcategoria de uma linha coincidam integralmente com um lançamento ativo, quando a prévia é exibida, então alerta a possível duplicidade e oferece ignorar ou substituir o existente.
- Dado uma duplicidade com um único candidato, quando o usuário escolhe substituir, então descrição, tags e observações do lançamento existente são atualizadas sem criar outro lançamento nem alterar data/valor.
- Dado uma duplicidade com múltiplos candidatos, quando o usuário escolhe substituir, então precisa escolher explicitamente o lançamento existente que será atualizado.
- Dado uma duplicidade, quando o usuário escolhe ignorar, então nenhum lançamento novo é criado e nenhum lançamento existente é alterado.
- Dado uma linha sem correspondência integral de data, valor, categoria ou subcategoria, quando importada, então não é tratada como duplicata.
- Dado um arquivo com descrição original e um ajuste aprendido, quando a prévia é exibida, então a descrição original permanece no campo somente leitura e o valor aprendido aparece em **Descrição Lançamento**.
- Dado que o usuário altere a categoria na prévia, inclusive em uma linha com ajuste aprendido, quando confirmar a importação, então a categoria selecionada na tela é a categoria persistida.
- Dado uma importação com linhas importadas e ignoradas, quando o resultado é exibido, então cada linha aparece em uma faixa compacta de uma única linha, com sua descrição, situação e, para ignoradas, o motivo.
- Dado que o arquivo tenha mais de 50 linhas ignoradas, quando o resultado é exibido, então todas as linhas ignoradas são retornadas e listadas.
- Dado que uma linha tenha uma correção manual de descrição/classificação e corresponda a uma duplicidade ativa, quando o usuário escolhe explicitamente ignorá-la, então a correção é aprendida para a próxima prévia sem criar ou alterar lançamentos; se a duplicidade deixar de existir antes da confirmação, o aprendizado não é salvo.

## Plano de implementação

- [x] Passo 1 — adicionar modos de origem OFX e planilha externa, com escolha de arquivo/destino compatível. Fecha: critérios 3 e 5.
- [x] Passo 2 — expor prévia e confirmação seletiva na rota legada, mantendo validação e persistência existentes. Fecha: critérios 4 e 6 a 9.
- [x] Passo 3 — cobrir parsing, revisão/seleção e compatibilidade em testes automatizados. Fecha: critérios 1, 2, 4 e 6 a 9.
- [x] Passo 4 — oferecer revisão para OFX e planilhas legadas externas e restringir esse fluxo a conta corrente. Fecha: critérios 3 e 5.
- [x] Passo 5 — persistir ajustes validados por usuário e instrumento, aplicar na próxima prévia e validar o sucesso/isolamento. Fecha: critérios 10 a 13.
- [x] Passo 6 — manter a classificação escolhida na persistência e limitar combos ao grupo compatível com o tipo do lançamento. Fecha: critério 33.
- [x] Passo 7 — detectar duplicatas por igualdade integral, oferecer ignorar/substituir, permitir escolher o candidato ambíguo e revalidar na confirmação. Fecha: critérios 34 a 38.
- [x] Passo 8 — manter a descrição original visível quando houver aprendizado e serializar os valores atuais da revisão na confirmação. Fecha: critérios 39 e 40.
- [x] Passo 9 — listar todos os itens importados/ignorados em linhas compactas e remover o truncamento das mensagens por linha. Fecha: critérios 41 e 42.
- [x] Passo 10 — aprender correções de linhas explicitamente ignoradas como duplicadas, validando novamente a duplicidade e preservando os lançamentos. Fecha: critério 43.

## Changelog

- `1.17` — 2026-10-12 — Refatoração interna: parsers de formatos tabulares, parser OFX, gerador de templates e utilitários compartilhados extraídos para módulos especializados (`import_parsers.py`, `import_ofx.py`, `import_templates.py`, `import_utils.py`); `imports.py` permanece como orquestrador. Sem mudança de comportamento observável nem de contratos. Ver [[desacoplamento-importacao-parsers]].

- `1.16` — 2026-10-10 — Correções de linhas explicitamente ignoradas como duplicadas passam a alimentar o aprendizado local, após revalidar a duplicidade e sem alterar lançamentos.
- `1.15` — 2026-10-05 — Resultado passa a listar cada lançamento importado ou ignorado em uma única linha compacta e deixa de limitar as mensagens de linhas ignoradas a 50.
- `1.14` — 2026-10-05 — Preserva a descrição do arquivo na prévia quando existe aprendizado, renomeia o campo editável para Descrição Lançamento e envia os valores atuais da linha confirmada.
- `1.13` — 2026-10-05 — Corrige persistência de classificação escolhida e adiciona alerta de duplicidade com ignorar, substituir existente e seleção explícita entre candidatos.
- `1.12` — 2026-10-05 — Prévia separa descrição original (somente leitura) da editável, procura ajustes pelo texto original e pelo corrigido e usa autocomplete em uma linha para tags.
- `1.11` — 2026-10-05 — Categorias e subcategorias na prévia passam a ser combos dependentes do catálogo existente; tags têm seleção de opções existentes e criação explícita na importação.
- `1.10` — 2026-10-05 — Prévia de importação aprende correções de descrição/classificação somente após importação bem-sucedida, isoladas por usuário, conta/cartão e tipo.
- `1.9` — 2026-10-05 — Interface OFX passa a oferecer modo explícito, prévia editável e confirmação seletiva antes da persistência.
- `1.8` — 2026-10-05 — Suporte a arquivos OFX (`.ofx`/`.qfx`) na importação legada, com interpretação de `TRNAMT`, datas `DTPOSTED` e conversão de receitas/despesas para o fluxo interno.
- `1.7` — 2026-09-04 — Painel de resultado passa a exibir orientação inicial, carregamento e erro semântico.

- `1.6` — 2026-09-01 — Parser XLSX passa a limitar arquivo, membros ZIP, expansão, razão de compressão, caminhos, linhas, células, colunas e shared strings antes da persistência, mitigando ZIP/XML bombs sem alterar CSV/XLS.
- `1.5` — 2026-08-28 — Timestamp UTC dos modelos XLSX passa a usar `timezone.utc`, preservando o formato W3CDTF e a compatibilidade com o Python 3.9 usado pelo launcher da homologação.
- `1.4` — 2026-08-28 — Metadados dos modelos XLSX passam a gerar timestamp UTC com API de data consciente de fuso, preservando o formato W3CDTF terminado em `Z`.
- `1.3` — 2026-08-23 — Removidas referências a soluções concorrentes; rota de importação legada renomeada para `/api/import/legacy-transactions`.
- `1.2` — 2026-08-17 — Modelo próprio ganha colunas de repetição (`repeticao`, `parcelas`, `recorrencia`, `media`); datas aceitas ampliadas (`DD/MM/YYYY`, `DD-MM-YYYY`) e data inválida rejeita a linha com motivo explícito.
- `1.1` — 2026-07-03 — Regra de importação em lote atualizada para transações curtas por linha.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[lancamentos]]
- [[adr/0004-importador-xls-sem-dependencia]]
- [[arquitetura]]
