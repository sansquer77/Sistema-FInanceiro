---
tipo: adr
area: importacao
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[specs/importacao-organizze]]"
  - "[[arquitetura]]"
tags: [adr, importacao]
aliases: ["ADR-0004", "Parser XLS sem dependência"]
---

# ADR-0004 — Parser `.xls` implementado sem dependência externa

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-06-29

## Contexto

A importação de exportações do Organizze requer leitura de arquivos `.xls` (formato binário legado). A biblioteca `xlrd` é o pacote Python mais comum para isso, mas adiciona uma dependência externa que precisa ser instalada pelo usuário.

## Decisão

Implementar um **parser `.xls` mínimo internamente** em `financeiro/imports.py`, sem instalar `xlrd` ou qualquer outra biblioteca externa.

## Consequências positivas

- O usuário instala e executa o app com `python app.py` sem etapa extra de `pip install`.
- O pacote distribuível não carrega dependências que possam quebrar por mudança de versão.
- O parser cobre apenas os campos utilizados pelo Organizze, mantendo o código pequeno.

## Consequências negativas / trade-offs

- Suporte limitado a variantes do formato `.xls`; arquivos gerados por ferramentas muito antigas ou exóticas podem não ser lidos.
- Manutenção manual se o formato mudar (improvável dado que `.xls` é um formato legado e estável).
- Recursos avançados do formato (fórmulas, imagens, múltiplas planilhas) não são suportados — aceitável pois a importação só precisa de dados tabulares simples.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| `xlrd` | Dependência externa que aumenta fricção de instalação. |
| Exigir que o usuário converta para `.csv` antes | Piora a experiência; o Organizze exporta `.xls` por padrão. |
| `openpyxl` | Não lê `.xls` (apenas `.xlsx`); não resolve o problema. |

## Relacionados

- [[specs/importacao-organizze]]
- [[arquitetura]]
