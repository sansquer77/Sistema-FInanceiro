---
tipo: adr
area: meta
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[arquitetura]]"
  - "[[adr/0003-sqlite-fonte-de-verdade]]"
tags: [adr, meta]
aliases: ["ADR-0001", "Sem framework web"]
---

# ADR-0001 — Stack local sem framework web

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-06-29

## Contexto

O Sistema Financeiro precisa rodar localmente em macOS com requisitos de instalação mínimos. O usuário final não é um desenvolvedor e não deve precisar de Docker, gerenciador de processos ou serviços externos.

## Decisão

Usar **servidor HTTP puro em Python 3** (biblioteca padrão, sem Flask/FastAPI/Django) para servir o frontend estático e os endpoints JSON da API.

## Consequências positivas

- Zero dependências de framework para o servidor: `python app.py` inicia o app.
- Distribuível sem `requirements.txt` extenso.
- Comportamento totalmente previsível — o código que trata a requisição é o código que você lê.
- Nenhum middleware escondido que possa conflitar com as regras de segurança do app.

## Consequências negativas / trade-offs

- Mais código manual para parsing de rotas, cookies e uploads multipart.
- Sem autenticação, cache ou middleware prontos — precisam ser implementados explicitamente.
- Escalar para múltiplos usuários em rede exigiria reescrever a camada de servidor.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Flask | Dependência externa que aumenta fricção de instalação e distribuição. |
| FastAPI | Requer `uvicorn` e `pydantic`, complexidade desnecessária para uso local monousuário. |
| Django | Overhead muito alto para um app local offline-first. |

## Relacionados

- [[arquitetura]]
- [[adr/0003-sqlite-fonte-de-verdade]]
