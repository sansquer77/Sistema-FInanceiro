---
tipo: adr
area: investimentos
status: implementado
versao: 1.0
atualizado: 2026-09-04
relacionados:
  - "[[../specs/investimentos-portfolio]]"
  - "[[../arquitetura]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
  - "[[0004-importador-xls-sem-dependencia]]"
tags: [adr, "area/investimentos", "status/implementado"]
aliases: ["ADR-0016", "Calendário ANBIMA"]
---

# ADR-0016 — Calendário nacional ANBIMA persistido localmente

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-09-04 · relacionados: [[../specs/investimentos-portfolio]], [[0003-sqlite-fonte-de-verdade]], [[0004-importador-xls-sem-dependencia]]

## Problema

Eventos da B3 informam `lastDatePrior`, mas a Data ex derivada precisa avançar para o próximo dia útil operacional. Considerar apenas sábado e domingo produz datas incorretas em feriados nacionais. Fazer uma consulta remota a cada evento também contraria o comportamento offline-first e aumenta latência e fragilidade.

## Decisão

Usar exclusivamente a planilha nacional publicada pela ANBIMA como calendário operacional local:

- baixar o XLS oficial na primeira inicialização do aplicativo;
- validar TLS, `Content-Length`, tamanho efetivamente lido e estrutura XLS;
- reutilizar o parser BIFF/OLE interno, sem dependência externa;
- substituir os registros em uma transação somente depois da validação completa;
- persistir apenas o calendário vigente, sem histórico de arquivos;
- verificar atualização no máximo uma vez por ano e não repetir falha mais de uma vez no mesmo dia;
- preservar a última cópia válida se a ANBIMA estiver indisponível;
- não consultar BrasilAPI ou outra fonte alternativa.

## Consequências

- A derivação de Data ex funciona offline após a primeira importação bem-sucedida.
- A abertura do aplicativo continua mesmo se a fonte estiver indisponível.
- Mudanças futuras da estrutura XLS exigem ajuste no parser, mas não afetam o calendário já persistido.
- Feriados municipais e o último dia do ano permanecem fora do escopo da lista ANBIMA e não são inferidos pelo app.

## API e dados

- Nenhuma rota HTTP nova.
- `market_holidays`: data, nome e fonte do calendário atual.
- `market_calendar_state`: última importação/tentativa, ano verificado, hash do arquivo e contagem de registros.
- Fonte: `https://www.anbima.com.br/feriados/arqs/feriados_nacionais.xls`.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| BrasilAPI | Rejeitada: adiciona outra dependência operacional e uma segunda interpretação do calendário. |
| Consultar a ANBIMA em cada evento | Rejeitada: aumenta latência, tráfego e indisponibilidade percebida. |
| Considerar somente fins de semana | Rejeitada: calcula incorretamente datas próximas a feriados. |
| Versionar o XLS na distribuição | Rejeitada: duplica um artefato externo mutável e dificulta sua atualização controlada. |

## Critérios de aceite

- Dado banco sem calendário, quando o app inicia com rede disponível, então importa a planilha ANBIMA no SQLite.
- Dado calendário válido existente, quando a atualização falha, então nenhum feriado existente é removido.
- Dado certificado inválido ou arquivo acima do limite, quando a atualização ocorre, então a importação falha de forma segura.
- Dado feriado após `lastDatePrior`, quando a Data ex é derivada, então o dia é ignorado.
- Dado uma tentativa falha no dia, quando o app reinicia, então não repete a mesma consulta naquele dia.

## Changelog

- `1.0` — 2026-09-04 — Adotada a planilha ANBIMA como fonte única, local e atualizável do calendário nacional usado na derivação de datas de eventos B3.

## Relacionados

- [[../specs/investimentos-portfolio]]
- [[../arquitetura]]
- [[0003-sqlite-fonte-de-verdade]]
- [[0004-importador-xls-sem-dependencia]]
