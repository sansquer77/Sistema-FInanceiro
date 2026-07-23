---
tipo: spec
area: classificacao
status: implementado
versao: 1.0
atualizado: 2026-07-23
relacionados:
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[categorias-tags-gestao]]"
  - "[[../adr/0006-classificacao-assistida-local|ADR-0006]]"
tags: [spec, "area/classificacao", "status/implementado"]
aliases: ["Classificação Assistida", "Sugestão de Categorias"]
---

# Classificação Assistida

> [!info] Status
> **implementado** · área: `classificacao` · atualizado em 2026-07-23 · relacionados: [[lancamentos]], [[cartoes]], [[categorias-tags-gestao]], [[../adr/0006-classificacao-assistida-local|ADR-0006]]

## Problema

O usuário repete descrições de lançamentos e precisa selecionar novamente a mesma categoria e subcategoria. O sistema deve aprender essas escolhas anteriores para reduzir o tempo de cadastro, sem depender de internet, degradar a resposta do formulário ou classificar silenciosamente com baixa confiança.

Exemplos:

- `Estacionamento` costuma corresponder à categoria `Transporte` e à subcategoria `Estacionamento`.
- `Vaga 55` costuma corresponder sempre à classificação usada para recarga do carro - categoria `Transporte` e à subcategoria `Recarga`.

## Usuário

Qualquer usuário autenticado que registre manualmente despesas, receitas ou investimentos em contas-correntes e cartões.

## Jornada

1. O usuário escolhe o tipo do lançamento e começa a preencher a descrição.
2. Depois de uma pequena pausa na digitação, o sistema procura hábitos anteriores do próprio usuário.
3. Quando existe uma correspondência com confiança suficiente, o formulário sugere e preenche categoria e subcategoria, identificando visualmente que a escolha foi sugerida.
4. O usuário pode aceitar a sugestão ao salvar ou alterá-la normalmente.
5. A escolha efetivamente salva passa a reforçar ou corrigir o hábito local.
6. Se não houver sugestão confiável, o formulário permanece inalterado e o cadastro manual continua funcionando offline.

## Dados

- `user_id`: usuário proprietário do hábito; obrigatório e isolado dos demais usuários.
- `group_type`: grupo do lançamento (`income`, `expense` ou `investment`); obrigatório.
- `normalized_description`: descrição normalizada para comparação; obrigatória.
- `category_id`: categoria escolhida anteriormente; obrigatória e pertencente ao usuário e grupo.
- `subcategory_id`: subcategoria escolhida anteriormente; opcional e pertencente à categoria.
- `usage_count`: quantidade de confirmações dessa combinação; inteiro positivo.
- `last_used_at`: data/hora da confirmação mais recente; usada como desempate e para futura expiração.
- `source_context`: origem opcional (`account` ou `credit_card`) e seu identificador, usada somente como sinal de desempate.

A normalização deve:

- remover espaços nas extremidades e condensar espaços repetidos;
- converter o texto para minúsculas;
- comparar letras acentuadas e não acentuadas de forma equivalente;
- preservar números significativos, de modo que `Vaga 55` não seja confundida com outra vaga;
- remover apenas sufixos gerados pelo próprio sistema, como índices de parcelas, quando comprovadamente aplicável.

## Regras

- O histórico de um usuário nunca pode gerar sugestão para outro usuário.
- Apenas lançamentos salvos com categoria válida alimentam o aprendizado.
- Tipo/grupo é parte obrigatória da correspondência; uma descrição de receita não sugere categoria de despesa.
- A primeira versão usa correspondência exata da descrição normalizada.
- O sistema só preenche automaticamente quando a combinação vencedora tiver suporte mínimo e dominância configurados; valor inicial proposto: pelo menos 2 confirmações e 80% das ocorrências.
- Uma única ocorrência pode ser exibida como sugestão de baixa confiança, mas não deve alterar os campos automaticamente.
- Em empate ou baixa confiança, o sistema não altera o formulário.
- A categoria pode ser sugerida sem subcategoria quando não houver dominância suficiente para a subcategoria.
- A sugestão nunca sobrescreve categoria ou subcategoria que o usuário já tenha alterado na edição atual.
- Edição de lançamento existente não deve disparar substituição automática da classificação carregada.
- A correção manual do usuário deve atualizar o aprendizado após o lançamento ser salvo.
- Exclusão e edição devem manter as contagens consistentes; a atualização ocorre dentro da mesma transação curta da mutação financeira.
- Categorias ou subcategorias arquivadas, removidas ou incompatíveis não podem ser sugeridas.
- A busca deve ocorrer após pausa curta na digitação (proposta: 250–350 ms), ser cancelável e ignorar respostas obsoletas.
- A ausência de rede ou de chave para serviço externo nunca pode impedir a sugestão pelo histórico nem o cadastro manual.
- Chamadas externas não podem ocorrer enquanto uma conexão SQLite estiver aberta.
- Descrições financeiras não devem ser enviadas a terceiros sem ativação explícita e informação clara ao usuário.
- A primeira entrega não usa IA generativa, embeddings, biblioteca de machine learning ou modelo local.

## API e dados

Proposta para implementação futura:

- `GET /api/classification-suggestion?description={texto}&group_type={grupo}&source={origem}&source_id={id}`
- Coluna `normalized_description` em `transactions` e `credit_card_transactions`, preenchida nas mutações e retroalimentada de forma idempotente para bancos existentes.
- Índices de leitura em `(user_id, type, normalized_description)` nas duas tabelas.
- A consulta agrega somente as linhas alcançadas pelos índices de correspondência exata; não materializa um segundo estado derivado que precise ser sincronizado em edições e exclusões.

Resposta proposta:

```json
{
  "suggestion": {
    "category_id": 12,
    "subcategory_id": 31,
    "confidence": 0.96,
    "support": 8,
    "reason": "historico_exato"
  }
}
```

Uma integração opcional futura com API de IA deve usar rota separada, timeout curto, cache local, saída estruturada limitada aos IDs de classificações existentes e fallback imediato para o fluxo local.

## Critérios de aceite

- Dado que `Estacionamento` foi salvo pelo menos duas vezes com a mesma classificação e dominância mínima, quando o usuário digita novamente a descrição em uma despesa, então a categoria e a subcategoria são preenchidas sem uma varredura completa do histórico.
- Dado que `Vaga 55` possui uma classificação dominante, quando a descrição é informada no mesmo grupo, então o sistema sugere essa classificação preservando o número `55` na chave de comparação.
- Dado que uma descrição foi classificada de formas divergentes sem dominância mínima, quando ela é digitada, então nenhum campo é alterado automaticamente.
- Dado que o usuário já alterou manualmente categoria ou subcategoria, quando uma resposta tardia de sugestão chega, então a escolha manual permanece.
- Dado que a descrição está sendo editada rapidamente, quando respostas anteriores chegam fora de ordem, então apenas a resposta correspondente ao texto atual pode afetar a tela.
- Dado que o computador está sem internet, quando uma descrição conhecida é digitada, então a sugestão local continua disponível.
- Dado que não existe hábito conhecido, quando a descrição é digitada sem integração externa ativa, então o formulário continua utilizável e sem erro.
- Dado que o usuário corrige uma sugestão e salva o lançamento, quando a descrição é usada novamente após confirmações suficientes, então a nova escolha passa a prevalecer.
- Dado que dois usuários usam a mesma descrição, quando cada um registra seus lançamentos, então as sugestões permanecem independentes.
- Dado um banco com grande volume de lançamentos, quando a sugestão exata é consultada, então o plano de consulta usa o índice da tabela de hábitos e não percorre `transactions` ou `credit_card_transactions`.

## Fora de escopo

- Criar automaticamente novas categorias ou subcategorias.
- Classificar transferências e câmbio.
- Sugerir tags, conta, cartão, valor, data, recorrência ou parcelamento.
- Treinar ou distribuir um modelo local.
- Enviar histórico financeiro completo para uma API externa.
- Corrigir em lote lançamentos antigos.
- Correspondência semântica/fuzzy na primeira entrega.

## Changelog

- `1.0` — 2026-07-23 — MVP implementado nos formulários de conta e cartão, com migração idempotente, índices dedicados, debounce e proteção da escolha manual.
- `0.2` — 2026-07-23 — MVP aprovado e iniciado; persistência simplificada para descrições normalizadas indexadas nas tabelas de lançamentos, preservando consistência automática em edições e exclusões.
- `0.1` — 2026-07-23 — Estudo inicial e proposta de classificação local baseada em hábitos, com API de IA apenas como evolução opcional.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[../adr/0006-classificacao-assistida-local|ADR-0006]]
