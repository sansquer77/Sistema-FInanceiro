---
tipo: spec
area: persistencia
status: implementado
versao: 1.0
atualizado: 2026-08-30
relacionados:
  - "[[migracao-banco-v2]]"
  - "[[investimentos-portfolio]]"
  - "[[../arquitetura]]"
  - "[[../adr/0003-sqlite-fonte-de-verdade]]"
tags: [spec, "area/persistencia", "status/implementado"]
aliases: ["Manutenção do cache de cotações", "Retenção de quote_cache"]
---

# Manutenção do cache de cotações

> [!info] Status
> **implementado** · área: `persistencia` · atualizado em 2026-08-30 · relacionados: [[migracao-banco-v2]], [[investimentos-portfolio]], [[../arquitetura]], [[../adr/0003-sqlite-fonte-de-verdade]]

## Problema

O banco local pode crescer desproporcionalmente ao uso financeiro porque respostas integrais de provedores de cotação permanecem em `quote_cache` após expirar. O usuário precisa que o app preserve fallback offline recente sem acumular indefinidamente dados regeneráveis.

## Usuário

Usuário que utiliza Portfólio, rentabilidade e Consultor e espera que o banco continue compacto sem perder lançamentos, posições ou configurações.

## Jornada

1. O usuário abre o app normalmente.
2. Antes de aceitar requisições, o app remove cache expirado além da janela de segurança e aplica limites por provedor.
3. Se a limpeza liberar parcela relevante do arquivo, o SQLite compacta o banco uma vez nessa abertura.
4. Cotações válidas e fallback recente continuam disponíveis; dados financeiros não participam da limpeza.

## Dados

- `quote_cache.expires_at`: instante até o qual a resposta é válida.
- `quote_cache.updated_at`: recência usada para preservar as entradas mais novas quando houver excesso.
- `provider`: prefixo de `cache_key` anterior ao primeiro `:`.
- Retenção stale: 30 dias após `expires_at`.
- Limite total: 1.500 entradas.
- Limite por provedor: 1.000 entradas.

## Regras

- A manutenção atua exclusivamente em `quote_cache`.
- Entrada válida nunca é removida apenas por idade.
- Entrada expirada permanece por até 30 dias para fallback offline.
- Ao exceder limites, as entradas expiradas mais antigas são removidas antes das demais; entradas válidas mais recentes têm prioridade.
- A compactação física só ocorre após remoção, com pelo menos 1 MiB e 20% das páginas no freelist.
- Falha de manutenção não impede o app de abrir e não é exposta com dados sensíveis.
- Payloads dos provedores mantêm o formato atual nesta entrega; substituir JSON bruto por fatores calculados exige contrato próprio por consumidor.

## API e dados

- Nenhuma rota nova.
- Nenhuma tabela ou coluna nova.
- `financeiro/database.py` executa poda e compactação controlada durante a inicialização.

## Critérios de aceite

1. Dado cache expirado há mais de 30 dias, quando o app inicializa, então a entrada é removida.
2. Dado cache expirado há menos de 30 dias, quando o app inicializa, então a entrada permanece como fallback.
3. Dado cache ainda válido, quando o app inicializa, então a entrada permanece.
4. Dado provedor acima de 1.000 entradas, quando ocorre a manutenção, então as entradas menos prioritárias são removidas até o limite.
5. Dado cache acima de 1.500 entradas, quando ocorre a manutenção, então o conjunto é reduzido ao limite total.
6. Dado limpeza que libera menos de 1 MiB ou 20% das páginas, quando a manutenção termina, então `VACUUM` não é executado.
7. Dado limpeza que libera ao menos 1 MiB e 20% das páginas, quando a manutenção termina, então o arquivo é compactado.
8. Dado falha durante a manutenção, quando o app inicializa, então o schema e os dados financeiros continuam disponíveis.

## Fora de escopo

- Alterar payloads recebidos de Yahoo, CoinGecko, Mais Retorno ou BCB.
- Guardar fatores calculados no lugar do JSON bruto sem validar todos os consumidores.
- Executar `VACUUM` em toda abertura.

## Plano de implementação

- [x] Passo 1 — implementar retenção e limites em `financeiro/database.py`. Fecha: critérios 1 a 5 e 8.
- [x] Passo 2 — implementar limiar de compactação física. Fecha: critérios 6 a 8.
- [x] Passo 3 — adicionar testes isolados e medir o banco de homologação. Fecha: critérios 1 a 8.

## Changelog

- `1.0` — 2026-08-30 — Implementadas poda automática, retenção stale de 30 dias, limites por provedor/global e compactação física condicionada; homologação reduzida de 7,04 MB para 2,84 MB.
- `0.1` — 2026-08-30 — Definida política de retenção, limites e compactação controlada do cache persistente de cotações.

## Relacionados

- [[migracao-banco-v2]]
- [[investimentos-portfolio]]
- [[../arquitetura]]
- [[../adr/0003-sqlite-fonte-de-verdade]]
