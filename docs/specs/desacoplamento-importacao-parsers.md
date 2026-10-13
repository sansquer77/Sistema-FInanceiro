---
tipo: arquitetura
area: importacao
status: implementado
versao: 1.0
atualizado: 2026-10-12
relacionados:
  - "[[importacao-dados]]"
  - "[[../adr/0004-importador-xls-sem-dependencia]]"
  - "[[../qualidade-codigo]]"
  - "[[../arquitetura]]"
tags: [arquitetura, "area/importacao", "status/implementado"]
aliases: ["Desacoplamento dos parsers de importação"]
---

# Desacoplamento dos parsers de importação

> [!info] Status
> **implementado** · versão: `1.0` · área: `importacao` · atualizado em 2026-10-12 · relacionados: [[importacao-dados]], [[../adr/0004-importador-xls-sem-dependencia]], [[../qualidade-codigo]], [[../arquitetura]]

## Problema

O módulo `financeiro/imports.py` acumula três responsabilidades distintas: leitura de arquivos em múltiplos formatos (`.xls`, `.xlsx`, `.csv`, `.ofx`, `.qfx`), geração de modelos `.xlsx` e orquestração do processo de importação (preview, deduplicação, aprendizado de ajustes e persistência). Com 2.260 linhas, ele ultrapassa o sinal de alerta de tamanho definido em [[../qualidade-codigo]] e dificulta revisões direcionadas, testes isolados de parsing e manutenção do parser `.xls` próprio (decidido em [[../adr/0004-importador-xls-sem-dependencia]]).

## Usuário

Desenvolvedores e agentes de IA que mantêm o módulo de importação, precisam localizar rapidamente onde uma determinada regra de parsing ou de geração de modelo é implementada, sem navegar por um arquivo monolítico.

## Jornada

1. Um desenvolvedor precisa corrigir a leitura de uma data serial do Excel.
2. Ele abre o projeto e encontra `financeiro/import_parsers.py`, responsável exclusivo por ler formatos tabulares.
3. A alteração fica isolada do processo de importação e do gerador de templates, reduzindo o risco de efeitos colaterais.

## Dados

| Campo | Tipo | Descrição |
|---|---|---|
| `parsed_rows` | lista de dicts | Linhas normalizadas produzidas por qualquer parser, com campos como `date`, `description`, `amount`, `category`, `subcategory`, `tags`, etc. |
| `format` | texto | Identificador do formato de origem: `xls`, `xlsx`, `csv`, `ofx`, `qfx`, `system_template`. |
| `target` | texto | Destino da importação: `account` ou `card`. |

## Regras

- Parsers são funções puras que recebem bytes/string e devolvem uma estrutura de dados normalizada; eles não acessam banco de dados, não aplicam regras de negócio financeiro e não escrevem lançamentos.
- Formatos tabulares (`.xls`, `.xlsx`, `.csv`) compartilham helpers de cabeçalho, célula e data, mas permanecem independentes do formato XML/SGML usado por OFX.
- OFX (`.ofx`/`.qfx`) vive em módulo próprio devido à natureza diferente do parsing (XML/SGML, campos `STMTTRN`, `DTPOSTED`, `TRNAMT`) e à conversão específica de receita/despesa.
- A geração de modelos `.xlsx` vive em módulo separado dos parsers, pois é uma responsabilidade de escrita, não de leitura.
- Helpers compartilhados entre parsers e orquestração (normalização de chave, data, valor monetário, exceção `ImportError`) vivem em `financeiro/import_utils.py`, evitando dependência circular entre os novos módulos.
- `financeiro/imports.py` continua como fachada/orquestrador: recebe a requisição, escolhe o parser adequado, executa o pipeline de preview/duplicidade/aprendizado e persiste.
- O comportamento observável do usuário não muda: mesmas rotas, mesmas colunas reconhecidas, mesmos limites de segurança e mesmos critérios de aceite de [[importacao-dados]].
- Parser `.xls` continua sem dependência externa, conforme [[../adr/0004-importador-xls-sem-dependencia]]; a refatoração apenas move o código de lugar.

## API e dados

- Nenhuma rota nova ou alterada.
- Tabelas existentes permanecem inalteradas: `transactions`, `credit_card_transactions`, `transaction_tags`, `credit_card_transaction_tags`, `categories`, `subcategories`, `tags`, `checking_accounts`, `credit_cards`, `import_adjustments`.
- Novos módulos de domínio:
  - `financeiro/import_utils.py` — utilitários compartilhados (`ImportError`, normalização de chave, data, valor monetário, cabeçalho, célula etc.).
  - `financeiro/import_parsers.py` — parsers de formatos tabulares (`xls`, `xlsx`, `csv`) e helpers de leitura.
  - `financeiro/import_ofx.py` — parser de OFX/QFX.
  - `financeiro/import_templates.py` — geração de modelos `.xlsx` do sistema.
  - `financeiro/imports.py` — orquestração do pipeline de importação (reduzido).

## Critérios de aceite

- Dado o código atual, quando a refatoração for concluída, então `financeiro/imports.py` conterá apenas orquestração, preview, deduplicação, aprendizado de ajustes e persistência.
- Dado um arquivo `.xls` legado, `.xlsx` ou `.csv` compatível, quando processado pela importação, então `financeiro/import_parsers.py` será responsável por produzir as linhas normalizadas, sem alterar o resultado observável do usuário.
- Dado um arquivo `.ofx` ou `.qfx` compatível, quando processado pela importação, então `financeiro/import_ofx.py` será responsável por produzir as linhas normalizadas, sem alterar o resultado observável do usuário.
- Dado o download de modelo do sistema, quando acionado, então `financeiro/import_templates.py` será responsável por gerar o arquivo `.xlsx`, sem alterar o conteúdo do modelo.
- Dado o módulo `financeiro/import_parsers.py`, quando inspecionado, então ele não conterá lógica de negócio de importação (duplicidade, aprendizado, persistência) nem acesso ao banco de dados.
- Dado o módulo `financeiro/import_ofx.py`, quando inspecionado, então ele não conterá lógica de negócio de importação nem acesso ao banco de dados.
- Dado o módulo `financeiro/import_templates.py`, quando inspecionado, então ele não conterá lógica de negócio de importação nem acesso ao banco de dados.
- Dado o módulo `financeiro/import_utils.py`, quando inspecionado, então ele conterá apenas funções puras de normalização compartilhadas, sem acesso ao banco de dados.
- Dada a suíte de testes existente, quando executada após a refatoração, então todos os testes em `tests/test_imports.py`, `tests/test_code_quality.py` e a suíte completa continuarão passando sem alteração de comportamento.
- Dado um módulo extraído, quando medido, então seu tamanho deve ficar abaixo do sinal de alerta de ~1.200 linhas definido em [[../qualidade-codigo]].

## Pendências

> [!question] Pendências
> - [x] Confirmar se OFX deve ter módulo próprio separado dos parsers tabulares — **sim**, pela diferença de formato e semântica de parsing.
> - [x] Confirmar se geração de templates deve ter módulo próprio — **sim**, pois é responsabilidade de escrita, distinta da leitura.
> Nenhuma pendência conhecida. Helpers genéricos (`normalize_import_date`, `normalize_amount` etc.) foram centralizados em `import_utils.py`; `parse_system_template_file` migrou para `import_parsers.py` e `parse_legacy_file` permaneceu em `imports.py` como fachada de escolha de parser.

## Fora de escopo

- Alterar o comportamento observável do usuário (colunas reconhecidas, regras de validação, mensagens de erro, fluxo de telas).
- Alterar as rotas HTTP ou o contrato da API.
- Alterar o esquema do banco de dados.
- Adicionar novos formatos de importação.
- Remover a dependência zero de bibliotecas externas para `.xls`.
- Refatorar a interface em `web/modules/imports-view.js`.

## Plano de implementação

- [x] Passo 1 — Mapear todos os símbolos (funções, classes, constantes) de `financeiro/imports.py` e identificar consumidores em `app.py`, `tests/test_imports.py` e demais testes. Fecha: critérios 1 e 8.
- [x] Passo 2 — Criar `financeiro/import_utils.py` com as funções de normalização compartilhadas entre parsers e orquestração. Fecha: critério 10.
- [x] Passo 3 — Criar `financeiro/import_parsers.py` com as funções de leitura de `.xls`, `.xlsx` e `.csv`, incluindo helpers de cabeçalho, célula e data. Fecha: critérios 2 e 5.
- [x] Passo 4 — Criar `financeiro/import_ofx.py` com as funções de leitura de `.ofx`/`.qfx` e helpers específicos (`first_ofx_value`, `format_ofx_date` etc.). Fecha: critérios 3 e 6.
- [x] Passo 5 — Criar `financeiro/import_templates.py` com as funções de geração de modelos `.xlsx` do sistema. Fecha: critérios 4 e 7.
- [x] Passo 6 — Reescrever `financeiro/imports.py` como orquestrador, importando os novos módulos e preservando as funções públicas usadas por `app.py` e pelos testes. Fecha: critérios 1 e 8.
- [x] Passo 7 — Ajustar `tests/test_code_quality.py`: atualizar o tamanho revisado de `imports.py` para o novo valor pós-extração. Fecha: critérios 8 e 9.
- [x] Passo 8 — Executar `tests/test_imports.py` e a suíte completa, corrigindo imports ou referências quebradas (testes de limite XLSX passaram a mockar `financeiro.import_parsers`). Fecha: critério 8.
- [x] Passo 9 — Atualizar `docs/arquitetura.md` (tabela de módulos e fluxo de importação) e `docs/specs/importacao-dados.md` (changelog e referência aos novos módulos). Fecha: critérios 1 a 7.
- [x] Passo 10 — Revisar tamanho dos módulos extraídos; `import_parsers.py` (439 linhas), `import_ofx.py` (136), `import_templates.py` (126) e `import_utils.py` (120) ficaram abaixo do limiar de ~1.200 linhas. Fecha: critério 9.

## Changelog

- `1.0` — 2026-10-12 — Implementação concluída: extraídos `import_utils.py`, `import_parsers.py`, `import_ofx.py` e `import_templates.py`; `imports.py` reduzido de 2.260 para ~1.560 linhas e transformado em orquestrador; testes e documentação sincronizados; suíte completa passando (750 testes).
- `0.2` — 2026-10-12 — Spec promovida para `em-implementacao`; aprovada a divisão por família de formato (tabulares em `import_parsers.py`, OFX em `import_ofx.py`, templates em `import_templates.py`).
- `0.1` — 2026-10-12 — Spec inicial de refatoração arquitetural: separação dos parsers de importação (`import_parsers.py`, `import_ofx.py`) e do gerador de templates (`import_templates.py`) a partir de `financeiro/imports.py`, sem mudança de comportamento.

## Relacionados

- [[importacao-dados]]
- [[../adr/0004-importador-xls-sem-dependencia]]
- [[../qualidade-codigo]]
- [[../arquitetura]]
