---
tipo: adr
area: ia-remota
status: implementado
versao: 0.1
atualizado: 2026-11-18
relacionados:
  - "[[../specs/consultor]]"
  - "[[0010-segredos-criptografados-sqlite]]"
tags: [adr, "area/ia-remota", "status/implementado"]
aliases: ["Configurações de IA por provedor"]
---

# Configurações remotas isoladas por provedor

> [!info] Status
> **implementado** · área: `ia-remota` · atualizado em 2026-11-18 · relacionados: [[../specs/consultor]], [[0010-segredos-criptografados-sqlite]]

## Contexto

O aplicativo permite usar somente um provedor remoto de IA por vez, mas o armazenamento anterior mantinha uma única URL, modelo e chave por usuário. Ao trocar Gemini por outro provedor, a nova gravação podia reutilizar ou substituir a credencial anterior, dificultando o retorno ao provedor original.

## Decisão

Manter uma configuração ativa por usuário em `user_ai_settings`, mas armazenar os parâmetros de cada provedor separadamente em `user_ai_provider_settings`, com chave única por usuário e provedor. As credenciais ficam no envelope criptografado `secure_configs` e são organizadas por provedor no payload. O campo legado `api_key` continua como alias da configuração ativa para compatibilidade de leitura.

O formulário consulta a configuração do provedor selecionado antes de editar ou salvar. O preset DeepSeek usa a API compatível com OpenAI em `https://api.deepseek.com` e `deepseek-flash`; a seleção de outro provedor não apaga seus dados.

## Consequências

- O usuário pode alternar Gemini, DeepSeek ou outro provedor sem recadastrar a chave.
- Apenas o provedor ativo participa da execução remota.
- Configurações antigas de um único provedor são migradas de forma aditiva para o provedor que estava ativo.
- O banco passa a ter uma tabela adicional e o payload criptografado precisa suportar múltiplas credenciais.

## Alternativas consideradas

- Reutilizar a única chave global: descartada porque mistura credenciais e perde a configuração anterior.
- Criar um cadastro de múltiplos provedores ativos: descartada; o requisito é manter as opções salvas, mas usar somente uma por vez.

## Changelog

- `0.1` — 2026-11-18 — Decisão inicial para isolamento de configurações remotas por provedor.

## Relacionados

- [[../specs/consultor]]
- [[0010-segredos-criptografados-sqlite]]
