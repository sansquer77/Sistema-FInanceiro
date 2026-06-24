# Documentacao

Esta pasta e a fonte principal de requisitos, arquitetura e especificacoes do Sistema Financeiro.

## Documentos principais

- [Requisitos](./requisitos.md): escopo funcional, regras e estado atual.
- [Arquitetura](./arquitetura.md): camadas, fluxos, dados e decisoes tecnicas.
- [Visao do produto](./visao-produto.md): direcao de produto e modulos planejados.
- [SDD](./sdd.md): fluxo para evoluir o sistema por especificacoes pequenas.
- [Replicacao local](./replicacao-local.md): mapa de evolucao inspirado no Organizze.

## Especificacoes por modulo

- [Contas-correntes](./specs/contas-correntes.md)
- [Lancamentos](./specs/lancamentos.md)
- [Gestao de categorias e tags](./specs/categorias-tags-gestao.md)
- [Importacao Organizze](./specs/importacao-organizze.md)
- [Recuperacao de senha](./specs/recuperacao-senha.md)
- [Cartoes](./specs/cartoes.md)
- [Limites de gastos](./specs/limites-gastos.md)
- [Investimentos e Portfólio](./specs/investimentos-portfolio.md)
- [Relatorios](./specs/relatorios.md)
- [Modularizacao do frontend](./specs/frontend-modularizacao.md)

## Referencias

Os arquivos em [referencias](./referencias/) registram analises de produto, seguranca e padroes de codificacao. Eles servem como apoio para novas specs, mas nao substituem os documentos principais.

## Regra pratica

Antes de criar ou alterar uma area do app, atualize a spec correspondente com:

1. Problema do usuario.
2. Jornada esperada.
3. Dados necessarios.
4. Regras de negocio.
5. Criterios de aceite.
6. Impactos em API, banco e interface.
