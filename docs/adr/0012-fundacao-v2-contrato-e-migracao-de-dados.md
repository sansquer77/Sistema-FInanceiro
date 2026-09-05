---
tipo: adr
area: arquitetura-v2
status: implementado
versao: 0.2
atualizado: 2026-08-30
relacionados:
  - "[[../arquitetura]]"
  - "[[../sdd]]"
  - "[[../specs/open-finance]]"
  - "[[../specs/consolidacao-familiar]]"
  - "[[../specs/migracao-banco-v2]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
tags: [adr, "area/arquitetura-v2", "status/implementado"]
aliases: ["Fundação da v2.0", "Contrato congelado e migração para a v2"]
---

# ADR-0012 — Fundação da v2.0, congelamento do contrato e migração para um banco limpo

> [!info] Status
> **implementado** · área: `arquitetura-v2` · atualizado em 2026-08-30 · relacionados: [[../arquitetura]], [[../sdd]], [[../specs/open-finance]], [[../specs/consolidacao-familiar]], [[0003-sqlite-fonte-de-verdade]]

## Contexto

O Sistema Financeiro evoluiu por sucessivas inclusões de funcionalidades, tabelas, colunas, índices e compatibilizações de bancos SQLite antigos. Essa evolução preservou dados reais e permitiu atualização incremental, mas concentrou no processo de inicialização dezenas de verificações e transformações legadas que não são necessárias para uma instalação nova.

Ao mesmo tempo, alguns módulos cresceram e acumularam responsabilidades, adaptadores transitórios e funções semelhantes. A futura linha 2.x pretende usar a implementação atual como base confiável, congelar seu contrato observável e reorganizar internamente o código antes de receber capacidades de maior alcance, especialmente [[../specs/open-finance|Open Finance]] e [[../specs/consolidacao-familiar|Consolidação Familiar]].

Somente limpar, modularizar ou reduzir o código de compatibilidade não constitui, por si só, uma mudança incompatível suficiente para elevar a versão do produto para `2.0.0`. Entretanto, esse trabalho será tratado como a fundação técnica da linha 2.x. A publicação de `2.0.0` dependerá do conjunto de mudanças de produto e dos contratos incompatíveis efetivamente aprovados nas respectivas specs.

## Decisão

### 1. A v2 parte do contrato atual congelado

Antes de alterar estruturas internas, a linha v2 deve registrar e proteger por testes de caracterização:

- rotas, métodos, códigos HTTP e formatos JSON atualmente suportados;
- regras financeiras e invariantes de saldo, fatura, recorrência, investimento e auditoria;
- schema lógico final da versão 1.x, incluindo tipos, restrições, índices e relacionamentos relevantes;
- formatos de importação, configurações criptografadas e arquivos transportáveis suportados;
- contratos dos módulos frontend e fluxos críticos do usuário.

O congelamento não declara todo comportamento atual como ideal. Divergências entre código, teste e spec devem ser investigadas e resolvidas pelo processo SDD antes de serem incorporadas ao contrato da v2.

### 2. A modernização será incremental, não uma reescrita integral

A v2 reutilizará regras de negócio e testes comprovados. Refatorações serão entregues em passos pequenos, cada um mantendo o contrato congelado, salvo quando uma spec da linha 2.x aprovar explicitamente uma mudança incompatível.

A stack definida pelos ADRs vigentes permanece válida: biblioteca padrão do Python no servidor, SQLite como fonte local de verdade e ES Modules nativos sem etapa de build. Qualquer revisão dessas restrições exige ADR próprio.

### 3. Bancos novos usarão um schema-base canônico da v2

O banco de uma instalação nova da v2 será criado diretamente no schema canônico da linha 2.x. A inicialização cotidiana não executará a cadeia completa de compatibilizações históricas da versão 1.x.

O schema terá versão explícita e monotônica, registrada por `PRAGMA user_version` ou mecanismo equivalente documentado. Depois do baseline v2, apenas migrações v2 posteriores e ainda suportadas serão executadas na inicialização normal.

### 4. A passagem da v1 para a v2 será uma importação controlada

A v2 oferecerá um migrador dedicado que lê um banco 1.x e produz um banco 2.x separado. O processo seguirá as seguintes propriedades:

1. o arquivo 1.x é aberto em modo somente leitura e nunca é transformado no lugar;
2. um banco 2.x temporário é criado do zero pelo schema-base canônico;
3. os dados são copiados em ordem de dependência, com mapeamentos explícitos por versão de origem;
4. valores monetários permanecem inteiros em centavos e datas mantêm os contratos documentados;
5. segredos não são descriptografados, registrados ou convertidos para texto puro durante a migração;
6. a importação ocorre em transação e qualquer falha descarta o banco temporário incompleto;
7. antes da promoção, são executadas validações estruturais, referenciais e financeiras;
8. o banco 1.x original é preservado como cópia recuperável;
9. a troca para o banco 2.x ocorre somente após sucesso integral e confirmação adequada na jornada definida pela spec de migração;
10. o processo é idempotente ou detecta inequivocamente que aquela origem já foi migrada.

O migrador não será uma coleção indefinida das antigas chamadas `ensure_column`. Ele possuirá uma quantidade limitada de adaptadores de entrada, correspondentes às versões 1.x que a política de suporte declarar migráveis.

### 5. Open Finance e Consolidação Familiar entram depois da fundação

As estruturas de Open Finance e Consolidação Familiar não serão adicionadas ao baseline até que suas specs e decisões pendentes estejam aprovadas. Quando implementadas, nascerão sobre o schema versionado da v2, com isolamento por usuário, rastreabilidade e migrações incrementais próprias.

Essas funcionalidades ajudam a compor a proposta da linha 2.x, mas não autorizam antecipar tabelas, integrações externas ou dependências enquanto suas specs estiverem em `rascunho`.

### 6. O número 2.0.0 depende de incompatibilidade de produto confirmada

A fundação pode ser desenvolvida antes do lançamento da v2 e não altera automaticamente `APP_VERSION`. A versão `2.0.0` será atribuída quando houver mudança incompatível aprovada em fluxo, dados, configuração, API ou operação que exija migração ou ação do usuário — possivelmente a adoção do novo banco e da nova jornada de migração, em conjunto com as capacidades planejadas da linha 2.x.

## Validações mínimas do migrador

Antes de considerar uma migração bem-sucedida, o processo deve verificar pelo menos:

- integridade SQLite por `PRAGMA integrity_check` e relacionamentos por `PRAGMA foreign_key_check`;
- quantidade de registros por usuário e por entidade migrada, admitindo diferenças apenas quando documentadas;
- somatórios monetários e saldos reconciliados por conta e moeda;
- totais de faturas, pagamentos e lançamentos de cartão por competência;
- posições, custos, resgates e resultados realizados do Portfólio;
- isolamento de usuários e propriedade de todas as referências;
- presença e legibilidade dos registros criptografados sem exposição de seus conteúdos;
- equivalência de payloads analíticos selecionados entre a execução 1.x e a 2.x;
- execução da suíte de regressão contra bancos novos e amostras migradas.

Um relatório local deve registrar contagens, verificações e resultado final sem incluir descrições financeiras sensíveis, credenciais ou outros segredos.

## Alternativas consideradas

### Continuar acumulando compatibilizações na inicialização

Rejeitada como estratégia principal da v2. Preserva atualização in-place, mas mantém o custo cognitivo, amplia combinações históricas a testar e faz instalações novas atravessarem lógica legada desnecessária.

### Modificar o banco 1.x diretamente até chegar ao schema v2

Rejeitada. Uma falha intermediária pode deixar o único arquivo do usuário em estado difícil de recuperar, e a validação posterior não oferece a mesma capacidade de comparação entre origem e destino.

### Começar um aplicativo inteiramente novo e importar somente dados básicos

Rejeitada. Perderia regras financeiras amadurecidas, compatibilidade funcional e cobertura de regressão sem benefício proporcional.

### Copiar o arquivo SQLite 1.x e remover colunas ou tabelas consideradas antigas

Rejeitada. Uma cópia física ainda carrega decisões históricas e não prova que o destino corresponde ao contrato canônico da v2.

## Consequências

### Positivas

- instalações novas deixam de pagar o custo de compatibilizações anteriores à v2;
- o schema canônico fica auditável e reproduzível;
- a migração preserva o arquivo original e permite comparação antes da promoção;
- a modularização pode ocorrer com proteção explícita contra regressões;
- Open Finance e Consolidação Familiar passam a evoluir sobre uma base versionada.

### Negativas e custos

- durante a transição existirão dois caminhos testados: criação nova e importação da v1;
- o migrador precisa de fixtures representativas de diferentes idades de banco 1.x;
- a migração pode exigir espaço temporário próximo ao dobro do tamanho do banco;
- versões 1.x muito antigas podem precisar passar primeiro por uma versão-ponte ou ser declaradas fora da política de suporte;
- a equivalência financeira exige validações mais fortes do que simples contagem de linhas.

## Limites desta decisão

Este ADR não define ainda:

- a versão mínima 1.x aceita como origem;
- a estrutura final do schema v2;
- a jornada visual, os endpoints ou a interface de linha de comando do migrador;
- a política de rollback após o primeiro uso efetivo da v2;
- quais mudanças de Open Finance ou Consolidação Familiar comporão o lançamento `2.0.0`.

Esses contratos devem ser definidos em specs antes da implementação. Este ADR autoriza a direção arquitetural, não a execução antecipada das funcionalidades futuras.

## Changelog

- `0.2` — 2026-08-30 — Implementada a primeira peça da fundação: schema v2 marcado por `user_version = 20000` e migrador automático com backup legado, validação e promoção recuperável. Ver [[../specs/migracao-banco-v2]].
- `0.1` — 2026-08-30 — Decisão inicial: contrato atual congelado como fundação da v2, modernização incremental, schema-base canônico e importação controlada do banco 1.x para um novo banco 2.x.

## Relacionados

- [[../arquitetura]]
- [[../sdd]]
- [[../specs/open-finance]]
- [[../specs/consolidacao-familiar]]
- [[../specs/migracao-banco-v2]]
- [[0003-sqlite-fonte-de-verdade]]
