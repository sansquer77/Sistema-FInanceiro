---
tipo: spec
area: distribuicao
status: implementado
versao: 1.0
atualizado: 2026-06-30
relacionados:
  - "[[sdd]]"
  - "[[templates/spec-template|Template de spec]]"
  - "[[arquitetura]]"
  - "[[requisitos]]"
tags: [spec, "area/distribuicao"]
aliases: ["Distribuicao", "Pacote de Distribuicao", "Instalador macOS"]
---

# Distribuicao

> [!info] Status
> **implementado** · área: `distribuicao` · atualizado em 2026-06-30 · relacionados: [[sdd]], [[templates/spec-template|Template de spec]], [[arquitetura]], [[requisitos]]

## Problema

O Sistema Financeiro precisa ser entregue a um novo usuario de macOS como um pacote limpo, instalavel e sem dados pessoais ou arquivos de desenvolvimento da maquina original.

## Usuario

Usuario final que vai instalar o Sistema Financeiro em outro Mac e mantenedor responsavel por gerar uma nova versao do pacote de distribuicao.

## Jornada

1. O mantenedor atualiza a pasta `Sistema Financeiro - Distribuicao` a partir da versao corrente do projeto.
2. O pacote preserva os scripts e instrucoes de instalacao, mas substitui os arquivos de aplicacao pelos arquivos atuais.
3. O pacote exclui dados locais, testes, caches e metadados desnecessarios.
4. O mantenedor gera `Sistema Financeiro - Distribuicao.zip` a partir da pasta de distribuicao.
5. O novo usuario descompacta o zip, executa `Instalar Sistema Financeiro.command` e abre `Sistema Financeiro` pela pasta Aplicativos.
6. No primeiro uso, o app cria um banco SQLite vazio em `~/Documents/Sistema Financeiro/data/finance.db`.

## Dados

| Artefato | Tipo | Regra |
|---|---|---|
| `Sistema Financeiro - Distribuicao/` | diretorio | Raiz do pacote a ser compactado. Deve conter somente itens necessarios para instalacao. |
| `Sistema Financeiro - Distribuicao/Aplicativo/` | diretorio | Copia limpa da aplicacao atual, sem `data/`, `tests/`, caches ou metadados temporarios. |
| `Sistema Financeiro - Distribuicao/Aplicativo/Sistema Financeiro.app` | bundle macOS | App instalado em `/Applications`. Deve usar launcher portatil para `~/Documents/Sistema Financeiro`. |
| `Sistema Financeiro - Distribuicao/Instalar Sistema Financeiro.command` | script executavel | Copia os arquivos para `~/Documents/Sistema Financeiro` e instala o `.app` em `/Applications`. |
| `Sistema Financeiro - Distribuicao/README-INSTALACAO.md` | documento | Instrui instalacao, primeiro uso, dados nao incluidos, URL local e atualizacao. |
| `Sistema Financeiro - Distribuicao.zip` | arquivo zip | Arquivo final enviado ao usuario. Deve preservar permissoes executaveis. |

## Regras

- O pacote nao deve conter nenhum arquivo ou subdiretorio de `data/`.
- O pacote nao deve conter nenhum arquivo ou subdiretorio de `tests/`.
- O pacote nao deve conter `__pycache__/`, `.DS_Store`, `_CodeSignature` ou arquivos AppleDouble `._*`.
- O pacote nao deve conter banco SQLite, logs, configuracoes SMTP criptografadas, chaves locais, usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais.
- A pasta `Aplicativo/` deve conter os arquivos atuais de runtime: `app.py`, `financeiro/`, `web/`, `docs/`, `README.md` e `Sistema Financeiro.app`.
- O bundle `Sistema Financeiro.app` dentro da distribuicao deve usar launcher portatil baseado em `$HOME/Documents/Sistema Financeiro`, nao caminhos absolutos da maquina de desenvolvimento.
- O launcher do app e `Instalar Sistema Financeiro.command` devem ter permissao de execucao.
- Se o binario do launcher dentro do `.app` for substituido, assinaturas antigas em `Contents/_CodeSignature` devem ser removidas para evitar assinatura inconsistente.
- O instalador deve copiar a aplicacao para `~/Documents/Sistema Financeiro`, excluindo `data/`, `__pycache__/`, `.DS_Store`, `launcher_distribuicao.c` e `Sistema Financeiro.app/`.
- O instalador deve instalar `Sistema Financeiro.app` em `/Applications` e pedir permissao administrativa via macOS quando necessario.
- A URL padrao do app distribuido deve ser `http://sistema-financeiro.localhost:8010`.
- A porta padrao deve ser `8010`; conflito de porta deve ser tratado como orientacao operacional no README de instalacao.
- A geracao do zip deve ser feita a partir da pasta `Sistema Financeiro - Distribuicao`, mantendo essa pasta como raiz do arquivo compactado.

## API e dados

Nao ha rotas de API nem tabelas novas para distribuicao.

Arquivos e diretorios afetados:

| Caminho | Papel |
|---|---|
| `Sistema Financeiro - Distribuicao/` | Fonte do pacote instalavel. |
| `Sistema Financeiro - Distribuicao.zip` | Zip final para envio. |
| `Sistema Financeiro.app/Contents/MacOS/launcher` | Referencia de launcher do app local, mas nao deve ser usado se apontar para caminho absoluto da maquina de desenvolvimento. |
| `Sistema Financeiro - Distribuicao/Aplicativo/Sistema Financeiro.app/Contents/MacOS/launcher` | Launcher portatil do pacote. |

## Critérios de aceite

- Dado o pacote gerado, quando o zip for inspecionado, entao nao existe nenhum caminho contendo `/data/` ou `/tests/`.
- Dado o pacote gerado, quando o zip for inspecionado, entao nao existem `__pycache__`, `.DS_Store`, `_CodeSignature` ou arquivos `._*`.
- Dado o bundle `Sistema Financeiro.app` da distribuicao, quando o binario `launcher` for inspecionado, entao ele referencia `$HOME/Documents/Sistema Financeiro` ou formato equivalente portatil, sem caminho absoluto da maquina do mantenedor.
- Dado o zip final, quando `zip -T` for executado, entao a integridade do arquivo e confirmada.
- Dado o zip final, quando os metadados forem inspecionados, entao `Instalar Sistema Financeiro.command` e `Contents/MacOS/launcher` estao executaveis.
- Dado a pasta `Aplicativo/`, quando os arquivos Python forem compilados com `py_compile`, entao nao ha erro de sintaxe.
- Dado um Mac de destino sem dados anteriores, quando o usuario executar o instalador e abrir o app, entao o banco vazio e criado em `~/Documents/Sistema Financeiro/data/finance.db`.
- Dado um Mac de destino com banco anterior, quando o usuario reinstalar, entao o instalador atualiza arquivos do app sem copiar dados do pacote para `data/`.

## Fora de escopo

- Notarizacao Apple e assinatura Developer ID.
- Empacotamento como `.pkg` ou `.dmg`.
- Instalacao de Python ou de dependencias externas.
- Migracao automatica de bancos entre maquinas.
- Inclusao de dados demonstrativos ou dados reais de usuario.

## Changelog

- `1.0` — 2026-06-30 — Spec criada para documentar regras de geracao, limpeza, validacao e instalacao do pacote macOS.

## Relacionados

- [[sdd]]
- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[requisitos]]
