---
tipo: spec
area: alerta-nova-versao
status: implementado
versao: 1.1
atualizado: 2026-08-09
relacionados:
  - "[[landing-page]]"
  - "[[sobre-app]]"
  - "[[../adr/0007-landing-page-institucional-isolada|ADR-0007]]"
tags: [spec, "area/alerta-nova-versao", "status/implementado"]
aliases: ["Alerta de Nova Versão no Cockpit"]
---

# Alerta de Nova Versão no Cockpit

> [!info] Status
> **implementado** · área: `alerta-nova-versao` · atualizado em 2026-08-09 · relacionados: [[landing-page]], [[sobre-app]], [[../adr/0007-landing-page-institucional-isolada|ADR-0007]]

### Problema

O usuário do app local não tem uma forma simples de saber quando uma nova versão do Sistema Financeiro foi publicada. Ele precisa acessar manualmente o site institucional ou a página de releases para descobrir se há atualização disponível.

### Usuário

Usuário do app local que quer ser notificado dentro da própria interface quando existir uma versão mais recente do aplicativo, com link direto para download.

### Jornada

1. O usuário abre o app e acessa o Cockpit.
2. O app consulta, em segundo plano, a versão mais recente publicada no site oficial.
3. Se a versão publicada for maior que a versão local, um alerta discreto aparece no Cockpit.
4. O usuário clica no alerta e é direcionado para a seção de downloads do site oficial.
5. Se a consulta falhar ou a versão publicada não for maior, nenhum alerta é exibido.

### Dados

- `current_version`: versão atual do app, vinda de `financeiro.app_metadata.APP_VERSION`.
- `latest_version`: versão mais recente publicada, vinda do site institucional.
- `download_url`: URL direta para o download da release mais recente (GitHub Releases).
- `release_url`: URL da página geral de releases do GitHub.
- `landing_download_url`: URL da seção `#downloads` do site institucional.

### Regras

- O app deve comparar a versão local com a versão publicada usando comparação semântica (MAJOR.MINOR.PATCH).
- A consulta à versão mais recente deve ser feita pelo backend Python, nunca diretamente pelo frontend, para respeitar a restrição `connect-src 'self'` do CSP.
- O backend deve cachear o resultado por até 1 hora para evitar requisições excessivas ao site institucional.
- A URL da landing page pode ser sobrescrita pela variável de ambiente `SISTEMA_FINANCEIRO_LANDING_URL` para fins de teste.
- A consulta deve ter timeout curto (máximo 5 segundos) e nunca bloquear o carregamento do Cockpit.
- Se o site institucional ou a rede estiver indisponível, o app deve silenciosamente omitir o alerta.
- O alerta deve aparecer apenas quando `latest_version` for estritamente maior que `current_version`.
- O link do alerta deve apontar para `https://sistemafinanceiropage.vercel.app/#downloads`.
- O alerta deve ser renderizado no Cockpit, acima dos KPIs, e pode ser dispensado na sessão atual.
- O site institucional deve expor um endpoint JSON próprio (`/api/latest-version`) com os dados necessários, reutilizando a lógica de busca da release mais recente já existente.

### API e dados

- `GET /api/latest-version` (app principal): retorna metadados de versão.
  - Resposta de sucesso: `{"current_version": "1.2.0", "latest_version": "1.3.0", "update_available": true, "download_url": "...", "release_url": "...", "landing_url": "https://sistemafinanceiropage.vercel.app/#downloads"}`
  - Resposta quando indisponível: `{"current_version": "1.2.0", "latest_version": null, "update_available": false, ...}`
- `GET /api/latest-version` (landing page): retorna versão e links da release mais recente.
  - Resposta: `{"version": "v1.3.0", "download_url": "...", "release_url": "..."}`
- Nenhuma tabela nova no SQLite.
- Nenhuma alteração em esquemas existentes.

### Critérios de aceite

- Dado que o app está na versão `1.2.0`, quando a landing page publica a versão `v1.3.0`, então o Cockpit exibe um alerta informando que há uma nova versão disponível.
- Dado que o app está na versão `1.2.0`, quando a landing page publica a versão `v1.2.0`, então nenhum alerta é exibido no Cockpit.
- Dado que a landing page ou a internet está indisponível, quando o app tenta consultar a versão, então o Cockpit carrega normalmente sem exibir alerta de erro.
- Dado que o alerta está visível, quando o usuário clica nele, então uma nova aba é aberta em `https://sistemafinanceiropage.vercel.app/#downloads`.
- Dado que o usuário dispensou o alerta na sessão atual, quando ele recarrega o Cockpit, então o alerta continua oculto até a próxima sessão.
- Dado que o backend já consultou a versão nos últimos 60 minutos, quando outra requisição chega, então o resultado em cache é retornado sem nova chamada HTTP.

### Pendências

- [x] Decidir se o frontend faz a chamada diretamente ou via backend: decisão é via backend para respeitar o CSP.
- [x] Definir URL canônica da landing page: `https://sistemafinanceiropage.vercel.app/#downloads`.
- [x] Definir tempo de cache: 1 hora.

### Fora de escopo

- Download ou instalação automática de atualizações.
- Notificações por e-mail, push ou qualquer canal fora do app.
- Alterar o processo de release ou versionamento do app.
- Adicionar endpoint de versionamento na landing page além do JSON mínimo necessário.

### Plano de implementação

- [x] Passo 1 — Criar endpoint `/api/latest-version` na landing page (`sistemafinanceiropage/app/api/latest-version/route.ts`) reutilizando `getLatestRelease()`. Fecha: critérios 1, 2 e 4.
- [x] Passo 2 — Criar `financeiro/version_check.py` com fetch da landing, cache de 1h, timeout curto e comparação semver. Fecha: critérios 1, 2, 3 e 6.
- [x] Passo 3 — Adicionar rota `GET /api/latest-version` em `app.py` expondo o resultado do módulo de versionamento. Fecha: critérios 1, 2, 3 e 6.
- [x] Passo 4 — Adicionar elemento de alerta no `web/index.html`, estilos no `web/styles.css` e lógica de renderização em `web/modules/cockpit-view.js` e `web/app.js`. Fecha: critérios 1, 2, 4 e 5.
- [x] Passo 5 — Atualizar documentação (`docs/specs/alerta-nova-versao.md`, `docs/specs/landing-page.md`, `docs/arquitetura.md`) e testar localmente. Fecha: critérios 1, 2, 3, 4, 5 e 6.

### Changelog

- `1.1` — 2026-08-09 — Status visual da nota sincronizado com o frontmatter e com o MoC.
- `1.0` — 2026-08-04 — Spec implementada: endpoint `/api/latest-version` na landing page, módulo `financeiro/version_check.py`, rota no `app.py` e alerta no Cockpit com testes automatizados.

### Relacionados

- [[landing-page]]
- [[sobre-app]]
- [[../adr/0007-landing-page-institucional-isolada|ADR-0007]]
