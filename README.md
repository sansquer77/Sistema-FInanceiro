# Sistema Financeiro

Sistema financeiro pessoal **local-first**: contas correntes, cartões de crédito, investimentos, categorias/tags, limites de gastos, importação de extratos e Score de Saúde Financeira — tudo rodando no seu próprio computador, sem depender de nuvem para operar no dia a dia.

Inspirado na clareza de apps como o Organizze, mas 100% seus: os dados ficam em um banco SQLite local, o backend é Python puro (sem framework web) e o frontend é HTML/JS nativo (sem build step).

## Funcionalidades

- Contas correntes multi-moeda (`BRL`, `USD`, `EUR`, `GBP`)
- Cartões de crédito com faturas e parcelamentos
- Portfólio de investimentos
- Categorias, subcategorias e tags, com classificação assistida local
- Limites de gastos por categoria
- Importação de extratos do Organizze e planilhas modelo
- Score de Saúde Financeira e tendências
- Modo Privacidade (ocultar valores em tela)
- Modo local ou exposição controlada na rede local (LAN)

## Como rodar localmente

Pré-requisito: Python 3 instalado — sem outras dependências.

```bash
python3 app.py
```

O app cria automaticamente um banco SQLite vazio na primeira execução e fica disponível em modo local no navegador.

## Instalação como aplicativo (macOS/Windows)

Pacotes prontos (sem precisar instalar Python) estão disponíveis nas [Releases do GitHub](../../releases). Descompacte o zip da sua plataforma e execute o instalador correspondente (`.command` no macOS, `.bat` no Windows).

## Documentação técnica

A documentação completa do produto — specs por módulo, arquitetura, ADRs, glossário e o processo de Spec Driven Development (SDD) usado neste repositório — vive no vault Obsidian em [`docs/README.md`](docs/README.md). Comece por ali antes de propor ou implementar qualquer mudança.

Para instruções de deploy em rede local ou servidor, veja [`README-deploy.md`](README-deploy.md).

## Licença

Distribuído gratuitamente como projeto open source sob a **Apache License 2.0**. Consulte [`LICENSE`](LICENSE).
