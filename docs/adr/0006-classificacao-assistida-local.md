---
tipo: adr
area: classificacao
status: implementado
versao: 1.0
atualizado: 2026-07-23
relacionados:
  - "[[../specs/classificacao-assistida]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
  - "[[../arquitetura]]"
tags: [adr, "area/classificacao", "status/implementado"]
aliases: ["ADR-0006", "Aprendizado Local de Classificação"]
---

# ADR-0006 — Classificação assistida por hábitos locais

> [!info] Status
> **implementado** · área: `classificacao` · atualizado em 2026-07-23 · relacionados: [[../specs/classificacao-assistida]], [[0003-sqlite-fonte-de-verdade]], [[../arquitetura]]

## Problema

Descrições recorrentes carregam um sinal pessoal forte para categoria e subcategoria. É necessário decidir como transformar esse histórico em sugestões rápidas sem contrariar o funcionamento offline-first, a privacidade dos dados financeiros, a distribuição sem dependências pesadas e a disciplina de transações SQLite curtas.

## Usuário

Usuários que desejam cadastrar lançamentos repetidos com menos interações, inclusive sem internet e em computadores sem capacidade para executar modelos locais.

## Jornada

1. O app aprende somente com classificações confirmadas pelo usuário.
2. Uma consulta local indexada tenta resolver a descrição.
3. O formulário aplica apenas resultados de alta confiança e permite correção.
4. Serviços externos, se adicionados no futuro, atendem somente casos desconhecidos e nunca bloqueiam o fluxo local.

## Dados

- Descrição normalizada persistida e indexada nas tabelas de lançamentos de conta e cartão.
- Contagens calculadas somente sobre as correspondências exatas alcançadas pelos índices, evitando um segundo estado materializado sujeito a dessincronização.
- Nenhum vetor, embedding ou cópia do histórico em serviço externo na solução inicial.

## Regras

### Decisão recomendada

Adotar uma solução híbrida em fases:

1. **Primeira fase — hábito local determinístico:** correspondência exata normalizada e indexada em SQLite.
2. **Segunda fase — ML local:** somente após medir a cobertura e reunir amostras suficientes por usuário; permanece fora do MVP.
3. **Terceira fase — API de IA opcional:** somente para descrições sem histórico suficiente, com opt-in, chave configurada localmente, timeout, cache e saída restrita às categorias já existentes.

### Motivos

- Os exemplos `Estacionamento` e `Vaga 55` são padrões pessoais repetidos, um problema de recuperação de histórico, não de conhecimento geral.
- Uma consulta por chave indexada tem custo previsível e muito inferior a inferência local ou chamada de rede.
- O resultado é explicável por suporte e dominância, corrigível pelo usuário e totalmente offline.
- As colunas e os índices dedicados evitam normalizar ou percorrer todo o histórico a cada pausa de digitação; o `UNION` agrega apenas as correspondências exatas recuperadas pelos dois índices.
- O desenho preserva o SQLite como fonte de verdade e não adiciona dependências ao pacote.

### Performance

- Leitura esperada: busca pontual em índice B-tree, proporcional ao logaritmo do número de hábitos.
- Escrita esperada: persistência do texto normalizado na própria linha do lançamento, sem tabela derivada adicional.
- Frontend: debounce de 250–350 ms, cancelamento lógico por identificador da requisição e nenhum bloqueio do botão de salvar.
- API externa: fora do caminho padrão; nunca executada com conexão SQLite aberta.

### Segurança e privacidade

- Hábitos pertencem ao usuário autenticado e toda consulta filtra por `user_id`.
- A sugestão retorna IDs já validados contra o usuário e o grupo da categoria.
- Chaves de API não podem ir para o frontend nem para o SQLite em texto puro.
- Uma futura integração externa precisa informar que a descrição será enviada a terceiro, minimizar o payload e ser desativada por padrão.

## API e dados

A rota e a tabela propostas estão descritas em [[../specs/classificacao-assistida]]. A implementação exigirá atualização de [[../arquitetura]], [[../requisitos]] e das specs de lançamentos/cartões quando o rascunho for aprovado.

## Critérios de aceite

- A solução inicial funciona sem internet e sem pacote Python adicional.
- A consulta de sugestão usa índice dedicado e não varre as tabelas de lançamentos.
- A gravação financeira não aguarda rede nem inferência.
- O usuário mantém controle e pode reconhecer e corrigir uma sugestão.
- A classificação nunca atravessa a fronteira entre usuários ou grupos.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Consultar e agrupar todo o histórico a cada digitação | Simples de prototipar, mas custo cresce com o histórico e repete trabalho; rejeitada para o fluxo definitivo. |
| Regras fixas globais por palavra-chave | Rápidas, porém não aprendem hábitos pessoais e falham em descrições ambíguas; úteis apenas como dados iniciais explícitos. |
| Modelo local de machine learning | Mantém privacidade, mas aumenta tamanho, dependências, tempo de inicialização e complexidade de distribuição; desnecessário para correspondências recorrentes. |
| Embeddings locais | Ajudam semântica, mas exigem modelo/dependência e busca vetorial; custo injustificado antes de medir falhas da correspondência normalizada. |
| API de IA em toda digitação | Entende descrições inéditas, mas adiciona latência, custo, internet obrigatória e exposição de texto financeiro; rejeitada como caminho principal. |
| API de IA somente para desconhecidos | Possível evolução opt-in, desde que tenha cache, timeout, privacidade explícita e nunca seja necessária para salvar. |

## Fora de escopo

- Escolher agora um fornecedor ou modelo externo.
- Implementar o schema, a rota ou a interface.
- Definir correspondência fuzzy antes de medir o uso da primeira fase.

## Changelog

- `1.0` — 2026-07-23 — Decisão aprovada para o MVP de correspondência exata; ML local reservado para V2 e persistência refinada para colunas normalizadas indexadas.
- `0.1` — 2026-07-23 — Decisão recomendada registrada para discussão, sem implementação.

## Relacionados

- [[../specs/classificacao-assistida]]
- [[0003-sqlite-fonte-de-verdade]]
- [[../arquitetura]]
