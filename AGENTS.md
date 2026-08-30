# AGENTS.md — Guia para agentes de IA neste repositório

> Este arquivo é a fonte de regras para **qualquer ferramenta de IA** (assistentes de IDE, agentes de terminal, revisores automáticos de PR etc.) que leia, gere ou edite código neste repositório. Ele resume e aponta para a metodologia já definida em [`docs/sdd.md`](docs/sdd.md) e no restante de `docs/`. Em caso de conflito entre este arquivo e `docs/`, **`docs/` é a fonte canônica** — atualize este arquivo para refletir a mudança.
>
> **Use sempre `docs/README.md` como o ponto de entrada canônico do vault; não edite o `README.md` na raiz do repositório sem pedido explícito do usuário.**
>
> **Existem dois documentos chamados README, com propósitos diferentes — não confunda nem unifique os dois:**
> - **`README.md` (raiz)** — vitrine pública do projeto no GitHub: o que é o app, como instalar e rodar, link para as Releases, link de entrada para `docs/README.md` e para a licença. Conteúdo estável, direcionado a quem chega pelo repositório, não a agentes de IA.
> - **`docs/README.md`** — Map of Content (MoC) do vault Obsidian: índice de specs, ADRs, glossário, design system e do processo SDD. Usa wikilinks relativos que só resolvem dentro de `docs/`. É o ponto de entrada obrigatório para qualquer agente de IA antes de tocar em código (ver seção 0).
>
> Um agente de IA nunca deve mover, apagar ou mesclar um desses arquivos no outro. Atualizações de escopo funcional, specs e ADRs vão em `docs/README.md`; o `README.md` da raiz só muda quando a instalação, os requisitos de execução ou a descrição pública do projeto mudam — e mesmo assim só com pedido explícito do usuário.

## 0. Leia isto antes de tocar em qualquer arquivo

1. Abra [`docs/README.md`](docs/README.md) — é o Map of Content (MoC) do vault de documentação.
2. Localize a spec correspondente à área que você vai alterar em `docs/specs/`.
3. Se a mudança não tiver spec ainda, **não implemente antes de especificar**. Siga o processo SDD abaixo.
4. Nunca escreva código a partir de uma suposição sobre o comportamento do sistema — verifique a spec, a arquitetura (`docs/arquitetura.md`) e os ADRs relevantes (`docs/adr/`) primeiro.

Este projeto segue **Spec Driven Development (SDD)**, documentado em [`docs/sdd.md`](docs/sdd.md). O comportamento esperado é descrito em linguagem clara antes da implementação. Um agente de IA que pula essa etapa está violando o processo do projeto, mesmo que o código funcione.

## 1. Fluxo obrigatório para qualquer mudança

<!-- sync:fluxo-8-passos — espelha (resumido) docs/sdd.md, seção "## Fluxo" -->
```text
1. Localize ou crie a spec/documento a partir de docs/templates/spec-template.md
2. Atualize docs/requisitos.md se o escopo funcional geral mudar
3. Atualize docs/arquitetura.md se houver nova rota, tabela, módulo ou fluxo
4. Se a mudança envolver uma decisão técnica não trivial (biblioteca, trade-off
   de performance/segurança, padrão de dados), registre um ADR em docs/adr/
5. Se a spec tiver mais de 6 critérios de aceite ou tocar mais de um módulo de
   financeiro/, preencha a seção "Plano de implementação" da spec antes de
   codificar — é a decomposição em passos atômicos que o agente vai seguir
6. Implemente a menor mudança que cumpre a spec, citando-a em comentário nas
   regras de negócio não óbvias (ver "Rastreabilidade" abaixo)
7. Verifique com um teste automatizado por critério de aceite sempre que
   viável; sinalize na spec os critérios que só podem ser verificados manualmente
8. Atualize status, versao, atualizado e Changelog da spec afetada
```
<!-- /sync:fluxo-8-passos -->

<!-- sync:modelo-spec-anchored — espelha (resumido) docs/sdd.md, seção "## Modelo de maturidade: spec-anchored" -->
Este projeto é **spec-anchored**, não spec-as-source: a spec ancora a intenção e os critérios de aceite, mas o código e os testes são a fonte de verdade executável. Se o comportamento real divergir da spec, investigue a causa antes de presumir qual dos dois está errado — e depois de confirmar, atualize a spec (passo 8). Nunca use uma spec desatualizada como justificativa para reintroduzir um comportamento antigo.
<!-- /sync:modelo-spec-anchored -->

**Regra sem exceção:** nenhum arquivo novo de documentação começa como markdown livre. Todo documento novo — spec, ADR, design, roadmap etc. — nasce como cópia de `docs/templates/spec-template.md`, adaptando `tipo`, `area`, título e seções, mas preservando frontmatter, o callout `> [!info] Status`, `Changelog` e `Relacionados`.

### Frontmatter obrigatório em toda nota de `docs/`

```yaml
---
tipo: spec        # spec | adr | design | metodologia | produto | arquitetura | roadmap | glossario | template
area: slug-da-area
status: rascunho  # rascunho | em-implementacao | implementado | em-revisao | depreciado
versao: 0.1
atualizado: AAAA-MM-DD
relacionados:
  - "[[outra-spec]]"
tags: [spec, "area/slug-da-area", "status/rascunho"]
---
```

Um agente de IA que edita uma spec deve incrementar `versao`, atualizar `atualizado` e adicionar uma linha ao `Changelog` da nota — mesmo para mudanças pequenas.

### O que é spec vs. ADR vs. design

<!-- sync:spec-vs-adr-vs-design — espelha docs/sdd.md, seção "## Especificações (spec) vs. decisões técnicas (adr) vs. design (design)" -->
- **`docs/specs/`** — comportamento observável pelo usuário: jornada, dados, regras de negócio, API, critérios de aceite (formato dado/quando/então). Não deve conter detalhes de implementação internos.
- **`docs/adr/`** — por que uma decisão técnica não trivial foi tomada e quais alternativas foram descartadas.
- **`docs/design/design-system.md`** — tokens visuais que toda a interface deve respeitar.
<!-- /sync:spec-vs-adr-vs-design -->

### Rastreabilidade: código ↔ spec

<!-- sync:rastreabilidade-codigo-spec — espelha (resumido) docs/sdd.md, seção "## Rastreabilidade: código ↔ spec" -->
Para regra de negócio **não óbvia** — qualquer cálculo, validação ou efeito colateral que não seria previsível só lendo o nome da função — cite a spec de origem em comentário logo acima do trecho:

```python
# spec: investimentos-portfolio v1.3 — critério 4
```

Formato: `spec: <area>/<slug-do-arquivo em docs/specs/> vX.Y — critério N`, onde N é a posição do critério na lista "Critérios de aceite" da spec. Regras óbvias (validação simples de campo obrigatório etc.) não precisam da citação. Detalhes em [`docs/sdd.md`](docs/sdd.md), seção "Rastreabilidade: código ↔ spec".
<!-- /sync:rastreabilidade-codigo-spec -->

## 2. Stack e restrições arquiteturais (não negociáveis)

Estas restrições vêm de ADRs formais. Um agente de IA **não deve sugerir nem introduzir** nada que as contradiga sem antes propor um novo ADR.

| Restrição | ADR | Regra prática |
|---|---|---|
| Sem framework web no backend | [ADR-0001](docs/adr/0001-stack-local-sem-framework.md) | `app.py` usa apenas a biblioteca padrão do Python. Nunca adicionar Flask, FastAPI, Django ou similares. |
| Frontend sem build step | [ADR-0002](docs/adr/0002-modularizacao-frontend.md) | ES Modules nativos carregados via `<script type="module">`. Nunca introduzir bundler, transpiler, TypeScript compilado ou dependência de `npm run build`. |
| SQLite como única fonte de verdade | [ADR-0003](docs/adr/0003-sqlite-fonte-de-verdade.md) | Sem servidor de banco externo. Banco em `data/finance.db`, criado por migrações idempotentes em `financeiro/database.py`. Valores monetários sempre em **centavos** (inteiro), nunca ponto flutuante. |
| Parser `.xls` próprio | [ADR-0004](docs/adr/0004-importador-xls-sem-dependencia.md) | Não adicionar `xlrd` ou lib externa para importação de extratos; o parser mínimo vive em `financeiro/imports.py`. |
| Configuração SMTP criptografada local | [ADR-0005](docs/adr/0005-smtp-criptografado-local.md), [ADR-0010](docs/adr/0010-segredos-criptografados-sqlite.md) | Credenciais nunca em texto puro, nunca versionadas, nunca em pacotes distribuíveis. Usar `financeiro/secure_config.py` e `secure_configs`. |
| Classificação assistida local primeiro | [ADR-0006](docs/adr/0006-classificacao-assistida-local.md) | Sugestões vêm de correspondência exata indexada no SQLite do próprio usuário. IA externa é fallback opcional futuro, nunca bloqueante. |

### Contrato de módulos do frontend (`web/modules/`)

Toda view segue a fábrica:

```js
export function createXxxView({ state, elements, services, formatters, actions }) { … }
```

- **Utilitários** (`api.js`, `date-utils.js`, `money-utils.js`, `dom-utils.js`, `labels.js`, `month-picker.js`, `transaction-kind.js`): funções puras, sem estado.
- **Views** (`accounts-view.js`, `cards-view.js`, `transactions-view.js` etc.): estado local de tela, renderização e handlers de um único módulo funcional.
- **`app.js`**: orquestração geral, navegação e injeção de dependências.

**Regra de fronteira crítica:** a interface (`web/`) orquestra formulários, listas e navegação. **Regras financeiras, validações de propriedade e cálculo de saldo pertencem ao núcleo Python (`financeiro/`).** Um agente de IA nunca deve implementar regra de negócio em JavaScript.

### Núcleo Python (`financeiro/`)

Cada módulo tem responsabilidade única — não misture domínios entre módulos:

`database.py` (schema/migrações) · `money.py` (centavos/arredondamento) · `calendar_rules.py` (datas/meses) · `identifiers.py` (IDs positivos) · `recurrence.py` (séries/frequências) · `auth.py` (usuários/sessões) · `accounts.py` (contas-correntes) · `transactions.py` (lançamentos) · `categories.py` (categorias/tags) · `classification_suggestions.py` (sugestão local) · `credit_cards.py` (cartões/faturas) · `spending_limits.py` (limites) · `portfolio.py` (fachada de investimentos) · `portfolio_positions.py` (posições/lotes) · `portfolio_quotes.py` (cotações/cache) · `portfolio_calculations.py` (cálculos/agregações) · `cockpit.py` (agregações do Cockpit) · `http_routes.py` (resolução de rotas) · `imports.py` (importação) · `operation_logs.py` (auditoria) · `emailer.py` (envio SMTP) · `secure_config.py` (config criptografada).

Veja o mapeamento completo de rotas e tabelas em [`docs/arquitetura.md`](docs/arquitetura.md) antes de adicionar qualquer endpoint.

## 3. Convenções de dados e código

- **Dinheiro sempre em centavos** (inteiro) — nunca `float` para valores monetários.
- **Datas de lançamento em ISO `YYYY-MM-DD`**.
- **Homologação local oficial**: quando o usuário pedir para atualizar, copiar, publicar, validar ou testar a **homologação**, use exclusivamente a pasta `/Users/sansquer/Documents/Sistema Financeiro`.
  - Não use `Sistema Financeiro - Distribuicao/`, bundles MacOS/Linux/Windows, instaladores ou pastas empacotadas como destino de homologação, salvo pedido explícito do usuário para atualizar distribuição/pacote.
  - Antes de copiar arquivos para homologação, confirme que o destino possui a estrutura esperada (`app.py`, `web/`, `financeiro/`).
  - Preserve dados runtime da homologação: nunca sobrescreva `data/`, bancos SQLite, arquivos `.enc`, chaves locais, logs ou configurações locais.
  - Ao atualizar homologação, copie apenas os arquivos de código/documentação necessários para a alteração em validação e informe exatamente o que foi copiado.
- **Landing Page institucional oficial**: a página pública do produto vive em repositório próprio em `/Users/sansquer/Documents/GitHub/sistemafinanceiropage`.
  - Não use `landing-page/` deste repositório como fonte canônica de código, imagens, dependências, build ou deploy da landing, salvo pedido explícito para consultar/limpar legado.
  - Ao atualizar textos, imagens, QR Code, layout ou configuração da Landing Page, aplique as mudanças em `/Users/sansquer/Documents/GitHub/sistemafinanceiropage` e mantenha neste repositório apenas as specs/ADRs relacionadas.
  - O repositório do app principal não deve receber dependências Node, lockfiles, assets ou artefatos gerados da landing.
- **Versão do app centralizada** em `financeiro/app_metadata.py` e exposta por `/api/app-info`. A versão de produto parte de `1.0.50` e segue versionamento semântico:
  - `PATCH` (`3.0.5` → `3.0.6`): correção compatível, segurança, desempenho ou ajuste operacional sem nova capacidade relevante para o usuário.
  - `MINOR` (`3.0.5` → `3.1.0`): nova funcionalidade ou capacidade relevante, compatível com os fluxos e dados existentes.
  - `MAJOR` (`3.0.5` → `4.0.0`): mudança incompatível em fluxo, regra, dados, configuração ou operação que exija migração/ação dos usuários ou operadores.
  - Mudanças somente em documentação, testes, comentários ou refatorações sem efeito observável não incrementam a versão do produto.
  Ao concluir mudanças, sugira explicitamente se o incremento recomendado é `PATCH`, `MINOR`, `MAJOR` ou nenhum incremento, sem atualizar a constante automaticamente salvo pedido do usuário ou spec aplicável.
- Escritas que alteram saldo usam **deltas atômicos** (`saldo = saldo + delta`) ou uma transação SQLite curta e imediata que protege a leitura prévia. Nunca segurar uma conexão aberta durante uma chamada externa (SMTP, cotação, importação em lote).
- Novas tabelas e colunas são criadas **de forma idempotente** em `financeiro/database.py` — migrações devem rodar seguramente em bancos já existentes.
- Erros de domínio retornam mensagem amigável + status HTTP, **sem vazar detalhes internos** (stack trace, SQL, caminho de arquivo).
- Registros com impacto financeiro histórico preferem **arquivamento** a exclusão física.
- Toda rota de mutação exige `Host`/`Origin` validados contra `APP_URL` e as listas `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS` — não remova essa checagem.

## 4. Segurança — regras que um agente nunca deve contornar

- Sessões: cookie `HttpOnly`, `SameSite=Lax`; banco armazena apenas o **hash SHA-256** do token de sessão, nunca o token em claro.
- Troca ou recuperação de senha **revoga todas as sessões** do usuário.
- Credenciais SMTP, IA e integrações: criptografadas por usuário em `secure_configs.payload_enc`, chave mestra em `secure/config.key` ou env `SISTEMA_FINANCEIRO_CONFIG_KEY`/`SISTEMA_FINANCEIRO_CONFIG_KEY_PATH`. Arquivos legados `data/*_config_user_{id}.enc` e `data/email_config.key` continuam compatíveis, mas **nunca** devem ser commitados nem incluídos em pacotes de distribuição (`docs/distribuição.md`).
- O diretório `data/` inteiro é runtime local e **não deve ser versionado**.
- Modo LAN (`APP_HOST=0.0.0.0`) é só para redes confiáveis; acesso remoto real requer reverse-proxy com HTTPS. Não remova o alerta de inicialização quando essa exposição usa HTTP puro.
- Nunca logar senha, token de sessão, chave de criptografia ou payload de e-mail.

## 5. Design system — regras de UI

Consulte [`docs/design/design-system.md`](docs/design/design-system.md) para a paleta completa. Regra crítica que nenhum agente deve violar:

> As cores semânticas/numéricas (indicadores de receita, despesa, saldo etc.) têm significado financeiro estrito. `--secondary`/`--secondary-container` são exclusivos para ícones e itens de interface — **nunca** para valores numéricos ou como cor de botão genérico.

## 6. Checklist antes de abrir um PR gerado ou assistido por IA

- [ ] A spec correspondente em `docs/specs/` existe e reflete o comportamento implementado (status/versão/changelog atualizados).
- [ ] Se a spec tinha seção "Plano de implementação", os passos executados foram marcados e cobrem todos os critérios de aceite.
- [ ] `docs/arquitetura.md` foi atualizado se houve nova rota, tabela ou módulo.
- [ ] Um ADR foi criado em `docs/adr/` se houve decisão técnica não trivial.
- [ ] Nenhuma dependência nova de framework web, bundler frontend, ORM ou parser externo foi introduzida sem revisar o ADR correspondente.
- [ ] Valores monetários seguem centavos inteiros; datas seguem ISO `YYYY-MM-DD`.
- [ ] Nenhum arquivo de `data/` ou credencial foi commitado.
- [ ] Regra de negócio está em `financeiro/`, não em `web/`.
- [ ] Regras de negócio não óbvias citam a spec/critério de origem em comentário.
- [ ] Se este PR alterou `versao` de uma spec em `docs/specs/`, buscar por `# spec: <area>/<slug> vX.Y` (ou `// spec: ...`) no código e atualizar o número de versão nos comentários que citam essa spec — o critério referenciado normalmente continua válido (novos critérios costumam ser anexados ao final da lista), só o `vX.Y` fica desatualizado.
- [ ] Cores semânticas do design system foram respeitadas.

## 7. Referências rápidas

| Documento | Quando consultar |
|---|---|
| [`docs/README.md`](docs/README.md) | Ponto de entrada da documentação técnica — sempre primeiro. |
| [`README.md`](README.md) (raiz) | Vitrine pública do projeto; não é fonte de regras de desenvolvimento. |
| [`docs/sdd.md`](docs/sdd.md) | Processo completo, frontmatter, ciclo de vida de status. |
| [`docs/requisitos.md`](docs/requisitos.md) | Escopo funcional e requisitos não funcionais. |
| [`docs/arquitetura.md`](docs/arquitetura.md) | Rotas, tabelas, módulos, fluxos principais. |
| [`docs/glossario.md`](docs/glossario.md) | Vocabulário de domínio. |
| [`docs/templates/spec-template.md`](docs/templates/spec-template.md) | Base obrigatória para qualquer novo documento. |
| [`docs/design/design-system.md`](docs/design/design-system.md) | Tokens visuais e regras de UI. |
| [`docs/adr/`](docs/adr/) | Decisões técnicas e trade-offs aceitos. |
| [`docs/distribuição.md`](docs/distribuição.md) | Regras de empacotamento macOS/Windows. |

---

*Este arquivo deve ser mantido em sincronia com `docs/`. Se uma regra aqui ficar desatualizada em relação a uma spec, ADR ou ao design system, corrija este arquivo no mesmo PR que atualizou a documentação. Os blocos marcados com `<!-- sync:NOME -->` têm um par idêntico em `docs/sdd.md` — rode `grep -n "sync:" AGENTS.md docs/sdd.md` para localizar os dois lados antes de editar qualquer um deles.*
