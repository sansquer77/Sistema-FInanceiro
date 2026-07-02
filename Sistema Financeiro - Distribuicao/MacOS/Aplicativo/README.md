# Sistema Financeiro Local

Runtime macOS do Sistema Financeiro gerado com PyInstaller.

## Como abrir

Depois da instalacao, abra `Sistema Financeiro` pela pasta Aplicativos.

O app inicia o servidor local e abre:

```text
http://sistema-financeiro.localhost:8010
```

## Dados locais

Os dados do usuario ficam fora do executavel, em:

```text
~/Documents/Sistema Financeiro/data/finance.db
```

Este pacote nao inclui banco de dados, logs, usuarios, contas, cartoes, lancamentos, categorias, tags, posicoes pessoais nem configuracoes SMTP locais.

## Estrutura do pacote

```text
SistemaFinanceiro/       Runtime gerado por PyInstaller
Sistema Financeiro.app   Launcher instalado em /Applications
README.md                Este arquivo
```
