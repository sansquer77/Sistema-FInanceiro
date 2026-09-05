---
tipo: spec
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-09-03
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[consultor]]"
  - "[[alerta-nova-versao]]"
  - "[[../arquitetura]]"
tags: [spec, "area/seguranca", "status/implementado"]
aliases: ["Segurança do transporte externo"]
---

# Segurança do transporte externo

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-09-03 · relacionados: [[investimentos-portfolio]], [[consultor]], [[alerta-nova-versao]], [[../arquitetura]]

## Problema

Respostas externas não confiáveis não podem desabilitar a validação TLS nem provocar alocação ilimitada de memória antes de serem interpretadas como JSON.

## Usuário

Todo usuário que utiliza cotações, PTAX, IA, Consultor ou verificação de versão deve receber falha segura sem comprometer valores financeiros ou a disponibilidade do app.

## Jornada

1. O app consulta um serviço externo usando TLS validado e timeout do fluxo.
2. A resposta é lida até o limite específico daquele serviço e só então interpretada.
3. Em certificado inválido, excesso de tamanho ou JSON inválido, o fluxo aplica sua mensagem ou fallback seguro existente.

## Dados

- `Content-Length`: indicação opcional e não confiável do tamanho da resposta.
- corpo JSON: bytes UTF-8 limitados antes da decodificação.

## Regras

- Uma falha de certificado não pode gerar nova tentativa com contexto TLS não verificado.
- A leitura efetiva deve solicitar no máximo o limite acrescido de um byte, independentemente do `Content-Length`.
- Respostas declaradas acima do limite devem falhar antes da leitura do corpo.
- Cotações gerais aceitam até 4 MiB; IA e Consultor até 1 MiB; PTAX até 1 MiB; versão até 256 KiB.
- Falhas de transporte preservam os fallbacks públicos existentes, inclusive cache vencido de cotação quando disponível.

## API e dados

- Nenhuma rota ou tabela nova.
- Afeta apenas o transporte de saída usado pelas APIs existentes.

## Critérios de aceite

1. Dado um erro de certificado em uma cotação, quando a consulta falha, então ocorre uma única tentativa TLS validada.
2. Dada uma resposta com `Content-Length` acima do limite, quando ela é recebida, então o corpo não é lido.
3. Dada uma resposta sem `Content-Length`, quando ela excede o limite, então a leitura limitada detecta o excesso.
4. Dado `Content-Length` falso, malformado ou negativo, quando o corpo é lido, então o limite efetivo continua aplicado.
5. Dado JSON inválido ou UTF-8 inválido, quando a resposta é interpretada, então o chamador recebe seu erro ou fallback público.
6. Dada uma resposta válida no limite, quando ela é interpretada, então o fluxo legítimo permanece funcional.
7. Dada uma cotação indisponível ou excessiva com cache vencido válido, quando consultada, então o fallback de cache permanece disponível.

## Fora de escopo

Alterar provedores, timeouts, formatos de payload ou políticas de cache.

## Plano de implementação

- [x] Criar leitor JSON externo compartilhado com limites por integração. Fecha: critérios 2, 3, 4, 5 e 6.
- [x] Remover o retry TLS não verificado e integrar cotações/ PTAX. Fecha: critérios 1 e 7.
- [x] Integrar IA, Consultor e verificação de versão preservando seus contratos. Fecha: critérios 5 e 6.
- [x] Adicionar testes automatizados de limite, certificado e compatibilidade. Fecha: critérios 1 a 7.

## Changelog

- `1.0` — 2026-09-03 — TLS de cotações passa a falhar fechado e respostas JSON externas recebem limites efetivos por integração.

## Relacionados

- [[investimentos-portfolio]]
- [[consultor]]
- [[alerta-nova-versao]]
- [[../arquitetura]]
