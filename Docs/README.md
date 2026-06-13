# Docs

Esta pasta registra as decisões de produto, estrutura e arquitetura do Sistema Financeiro.
O objetivo é manter o app evoluindo por SDD (Spec Development Driven): cada mudança relevante nasce de uma especificação pequena, revisável e ligada ao comportamento esperado.

## Documentos

- [Visão do produto](./visao-produto.md): direção funcional, inspiração e experiência desejada.
- [Arquitetura](./arquitetura.md): camadas, responsabilidades e fluxo de dados.
- [SDD](./sdd.md): como escrever e usar especificações antes de implementar.
- [Padrões de codificação](./referencias/padroes-codificacao.md): regras para código seguro, replicável, testável e fácil de manter.
- [Segurança da aplicação](./referencias/seguranca-aplicacao.md): controles obrigatórios contra IDOR, SQL Injection, falhas de autenticação e autorização.
- [Referência Organizze](./referencias/organizze-visao-geral.md): padrões observados para orientar produto e navegação.
- [Replicação local](./replicacao-local.md): roteiro macro para reproduzir as funcionalidades localmente.
- [Referência de lançamentos](./referencias/organizze-lancamentos.md): lista, filtros, ações e regras de movimentações.
- [Referência de cartões](./referencias/organizze-cartoes.md): cadastro, faturas, limites e pagamento.
- [Referência de categorias e tags](./referencias/organizze-categorias-tags.md): taxonomia financeira e classificação.
- [Referência de relatórios](./referencias/organizze-relatorios.md): tipos de relatório, filtros e saídas.

## Regra prática

Antes de criar uma nova área do app, descreva:

1. O problema do usuário.
2. A jornada esperada.
3. Os dados necessários.
4. As regras de negócio.
5. Os critérios de aceite.

Depois disso, a implementação deve apenas materializar o que foi especificado.
