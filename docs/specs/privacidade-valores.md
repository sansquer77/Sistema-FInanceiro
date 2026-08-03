---
tipo: spec
area: privacidade
status: implementado
versao: 1.0
atualizado: 2026-08-02
relacionados:
  - "[[frontend-modularizacao]]"
  - "[[seguranca-autenticacao]]"
  - "[[../design/design-system|Design System]]"
tags: [spec, "area/privacidade", "status/implementado"]
aliases: ["Modo Privacidade", "Ocultar Valores", "Hide/Show Values"]
---

# Modo Privacidade — Ocultar Valores

> [!info] Status
> **implementado** · área: `privacidade` · atualizado em 2026-08-02 · relacionados: [[frontend-modularizacao]], [[seguranca-autenticacao]], [[../design/design-system|Design System]]

## Problema

O usuário pode precisar abrir o app em locais públicos, reuniões, coworking ou com outra pessoa por perto, mas a interface exibe muitos valores financeiros sensíveis: saldos, receitas, despesas, faturas, investimentos, dívidas, limites e indicadores do Cockpit.

## Usuário

Usuário autenticado que deseja navegar pelo app sem expor valores monetários sensíveis na tela, mantendo a estrutura da interface e a capacidade de entender onde cada informação está.

## Jornada

1. O usuário acessa o app autenticado.
2. No cabeçalho superior, aciona um botão discreto de privacidade com ícone de olho (ou pressiona a tecla de atalho `P`).
3. O app alterna imediatamente entre valores visíveis e valores ocultos usando desfoque suave (Opção A / Glass Blur).
4. Com valores ocultos, montantes financeiros aparecem desfocados (`blur(7px)`), preservando o alinhamento visual e a estrutura da tela.
5. Se o usuário passar o ponteiro do mouse (*hover*) sobre um valor mascarado específico, o desfoque daquele elemento reduz para `blur(0px)`, permitindo uma consulta rápida ("espiadinha") sem desativar o modo global.
6. O usuário aciona novamente o botão (ou pressiona a tecla `P`) para revelar todos os valores.
7. A preferência permanece salva localmente no navegador (`localStorage`) após reload.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `sistemaFinanceiro.privacyMode` | `localStorage` booleano textual | Preferência visual local do navegador (`"true"` ou `"false"`). Não sincroniza com banco. |
| `data-privacy` | atributo HTML no `documentElement` | Atributo global `data-privacy="true"` ou `"false"`. |
| `.money-value`, `.privacy-mask` | classe CSS | Marca valores monetários mascaráveis por desfoque. |

## Regras

- O modo privacidade é uma camada visual local e não altera valores, cálculos, persistência, APIs, exportações ou banco de dados.
- O controle deve ficar no cabeçalho superior para acesso rápido em qualquer módulo autenticado.
- O estado deve ser aplicado por classe/atributo global `data-privacy="true"` no `documentElement`.
- A preferência deve ser persistida apenas em `localStorage` sob a chave `sistemaFinanceiro.privacyMode`.
- O botão deve indicar claramente o estado e a próxima ação, com ícone e rótulo acessível: `Ocultar valores` ou `Mostrar valores`.
- **Efeito Visual (Opção A - Desfoque Suave / Glass Blur)**: Aplica `filter: blur(7px)` e `user-select: none` nos elementos de valor monetário (`.money-value`, `.privacy-mask`).
- **Revelação em Hover**: Ao passar o ponteiro do mouse sobre um elemento desfocado em modo privacidade, a propriedade é alterada para `filter: blur(0px)` com `transition: filter 0.2s ease`, permitindo a leitura individual temporária.
- **Atalhos de Teclado**: A tecla de atalho `P` alterna o modo privacidade instantaneamente, exceto quando o foco de digitação do teclado estiver ativo em elementos `<input>`, `<textarea>` ou `<select>`.
- O MVP deve mascarar valores monetários e totais financeiros, incluindo saldos, receitas, despesas, faturas, limites, dívidas, patrimônio e rentabilidade monetária.
- O MVP não precisa mascarar nomes de contas, cartões, categorias, descrições de lançamentos, datas, percentuais ou quantidades de ativos.
- O estado mascarado deve funcionar em tema claro e escuro, respeitando o contraste do design system.

## API e dados

- Nenhuma rota nova.
- Nenhuma tabela nova.
- Persistência local via `localStorage`.
- Módulos frontend afetados: shell/cabeçalho (`index.html`, `app.js`), utilitário `web/modules/privacy-utils.js` e estilos em `web/styles.css`.

## Critérios de aceite

- Dado o usuário autenticado com valores visíveis, quando aciona o botão de privacidade (ou digita a tecla `P`), então o atributo `data-privacy="true"` é adicionado ao `<html>` e todos os valores monetários marcados passam a exibir desfoque visual.
- Dado o modo privacidade ativo (`data-privacy="true"`), quando o usuário passa o mouse sobre um valor desfocado específico (`:hover`), então aquele valor torna-se legível temporariamente com transição suave (`blur(0px)`).
- Dado o usuário autenticado com valores ocultos, quando aciona o botão de privacidade novamente (ou digita `P`), então os valores reais voltam a aparecer com clareza.
- Dado uma tela com tabelas ou listas financeiras, quando o modo privacidade é alternado, então o alinhamento e a estrutura dos cards e tabelas permanecem 100% estáveis.
- Dado o usuário com modo privacidade ativo, quando recarrega a página no mesmo navegador, então o estado mascarado permanece ativo.
- Dado o usuário em tema claro ou escuro, quando ativa o modo privacidade, então o desfoque mantém contraste e estética adequados.
- Dado o modo privacidade ativo, quando o app faz cálculos ou chamadas de API, então os valores reais continuam sendo usados internamente sem alteração.

## Pendências

- Nenhuma pendência conhecida.

## Fora de escopo

- Criptografia, permissão ou controle de acesso adicional.
- Alteração de APIs ou banco de dados.
- Mascaramento de arquivos exportados.
- Mascaramento de dados no DevTools, rede ou respostas JSON.

## Plano de implementação

- [x] Passo 1 — Criar o módulo utilitário puramente frontend `web/modules/privacy-utils.js` para ler/gravar `localStorage`, alternar o atributo `data-privacy` e gerenciar o estado global. Fecha: critérios 1, 3 e 5.
- [x] Passo 2 — Adicionar as regras CSS de desfoque (`:root[data-privacy="true"] .money-value`) e transição em `:hover` em `web/styles.css`. Fecha: critérios 1, 2, 4 e 6.
- [x] Passo 3 — Adicionar o botão de alternância com ícone de Olho no cabeçalho em `web/index.html` e escutador da tecla `P` em `web/app.js`. Fecha: critérios 1 e 3.

## Changelog

- `1.0` — 2026-08-02 — MVP implementado com utilitário frontend, botão no cabeçalho, atalho `P`, persistência local e desfoque Glass Blur com revelação no hover.
- `0.2` — 2026-08-02 — Adicionada especificação do efeito de desfoque suave (Opção A / Glass Blur com hover reveal) e suporte ao atalho de teclado 'P'.
- `0.1` — 2026-08-02 — Spec inicial do Modo Privacidade para ocultar/exibir valores financeiros via camada visual local.

## Relacionados

- [[frontend-modularizacao]]
- [[seguranca-autenticacao]]
- [[../design/design-system|Design System]]
