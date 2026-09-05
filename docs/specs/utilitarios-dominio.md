---
tipo: spec
area: arquitetura
status: implementado
versao: 1.0
atualizado: 2026-08-30
relacionados:
  - "[[../arquitetura]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[efeito-borboleta]]"
tags: [spec, "area/arquitetura", "status/implementado"]
aliases: ["Utilitários de domínio compartilhados"]
---

# Utilitários de domínio compartilhados

> [!info] Status
> **implementado** · área: `arquitetura` · atualizado em 2026-08-30 · relacionados: [[../arquitetura]], [[lancamentos]], [[cartoes]], [[investimentos-portfolio]], [[efeito-borboleta]]

## Problema

Regras elementares de dinheiro, calendário, identificadores e recorrência estavam repetidas em diferentes módulos financeiros. Isso aumenta o risco de arredondamentos, datas-limite e validações evoluírem de formas incompatíveis.

## Usuário

Usuários de todos os módulos financeiros, que precisam receber resultados idênticos ao criar contas, lançamentos, faturas, simulações e posições, independentemente do fluxo utilizado.

## Jornada

1. O usuário informa valores, datas, identificadores e repetição em um fluxo financeiro existente.
2. O módulo funcional preserva suas mensagens e validações de domínio.
3. Operações elementares compartilhadas usam uma única implementação conceitual.
4. O resultado observável permanece compatível com a versão anterior.

## Dados

- Dinheiro persistido continua representado em centavos inteiros e arredondado por `ROUND_HALF_UP`.
- Datas continuam no formato ISO `AAAA-MM-DD`; competências mensais usam `AAAA-MM`.
- Identificadores aceitos são inteiros estritamente positivos.
- Recorrências suportam as frequências já previstas por cada fluxo.

## Regras

- `financeiro/money.py` concentra escala, conversão, formatação canônica e divisão exata de centavos.
- `financeiro/calendar_rules.py` concentra aritmética e normalização elementar de datas e meses.
- `financeiro/identifiers.py` concentra parsing de identificadores positivos obrigatórios ou opcionais.
- `financeiro/recurrence.py` concentra vocabulário e avanço de ocorrências, reutilizando calendário.
- Utilitários compartilhados são puros e levantam `ValueError`; cada módulo funcional traduz a falha para seu erro de domínio e mantém sua mensagem pública.
- Não existe módulo genérico `utils.py`.
- A extração não altera rotas, schema, valores persistidos nem regras financeiras observáveis.

## API e dados

- Nenhuma rota nova ou alterada.
- Nenhuma tabela ou migração nova.

## Critérios de aceite

1. Dado um valor decimal, quando convertido em centavos, então usa arredondamento `ROUND_HALF_UP` de forma única.
2. Dado um total em centavos dividido em parcelas, quando houver resto, então a soma das partes permanece igual ao total.
3. Dado uma data no fim do mês, quando avançada para um mês mais curto, então usa o último dia válido desse mês.
4. Dado uma recorrência suportada, quando uma ocorrência é calculada, então contas e cartões obtêm a mesma data para a mesma entrada.
5. Dado um identificador vazio, não numérico, zero ou negativo, quando normalizado, então é rejeitado sem aceitar IDs inválidos.
6. Dado uma falha de valor, data ou ID em um módulo funcional, quando apresentada ao usuário, então preserva o tipo de erro e a mensagem pública daquele domínio.
7. Dado o núcleo Python inspecionado, quando buscados utilitários compartilhados, então existem módulos conceituais e não existe `utils.py` genérico.
8. Dado a suíte existente, quando executada após a extração, então os comportamentos financeiros permanecem compatíveis.

## Fora de escopo

- Mover regras de saldo, propriedade, autorização ou persistência para os utilitários.
- Unificar mensagens específicas de cada domínio.
- Alterar contratos do frontend ou do banco de dados.

## Plano de implementação

- [x] Passo 1 — criar módulos puros para dinheiro, calendário, identificadores e recorrência. Fecha: critérios 1 a 5 e 7.
- [x] Passo 2 — integrar Contas, Lançamentos, Cartões, Simulações, Importação e Portfólio preservando suas fronteiras de erro. Fecha: critérios 4, 6 e 8.
- [x] Passo 3 — adicionar testes unitários dos contratos compartilhados e executar a suíte de regressão. Fecha: critérios 1 a 8.

## Changelog

- `1.0` — 2026-08-30 — Extraídos utilitários conceituais compartilhados de dinheiro, calendário, identificadores e recorrência, sem mudança de contrato funcional.

## Relacionados

- [[../arquitetura]]
- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[efeito-borboleta]]
