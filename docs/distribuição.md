---
tipo: spec
area: distribuicao
status: implementado
versao: 1.3
atualizado: 2026-07-02
relacionados:
  - "[[sdd]]"
  - "[[templates/spec-template|Template de spec]]"
  - "[[arquitetura]]"
  - "[[requisitos]]"
tags: [spec, "area/distribuicao"]
aliases: ["Distribuicao", "Pacotes de Distribuicao", "Instalador macOS", "Instalador Windows"]
---

# Distribuicao

> [!info] Status
> **implementado** · área: `distribuicao` · atualizado em 2026-07-02 · relacionados: [[sdd]], [[templates/spec-template|Template de spec]], [[arquitetura]], [[requisitos]]

## Problema

O Sistema Financeiro precisa ser entregue a novos usuarios de macOS e Windows como pacotes limpos, instalaveis e sem dados pessoais ou arquivos de desenvolvimento da maquina original.

## Usuario

Usuario final que vai instalar o Sistema Financeiro em outro computador e mantenedor responsavel por gerar novas versoes dos pacotes de distribuicao por plataforma.

## Jornada

1. O mantenedor atualiza a subpasta da plataforma em `Sistema Financeiro - Distribuicao/` a partir da versao corrente do projeto.
2. O pacote preserva os scripts e instrucoes de instalacao da plataforma, mas substitui os arquivos de aplicacao pelos arquivos atuais.
3. O pacote exclui dados locais, testes, documentacao tecnica, caches e metadados desnecessarios.
4. O mantenedor gera o zip final a partir da subpasta da plataforma.
5. No macOS, o novo usuario descompacta o zip, executa `Instalar Sistema Financeiro.command` e abre `Sistema Financeiro` pela pasta Aplicativos.
6. No Windows, o novo usuario descompacta o zip, executa `Instalar Sistema Financeiro.bat` e abre o app pelo atalho/script gerado para a plataforma.
7. No primeiro uso, o app cria um banco SQLite vazio na pasta local de dados definida pelo instalador da plataforma.

## Dados

| Artefato | Tipo | Regra |
|---|---|---|
| `Sistema Financeiro - Distribuicao/` | diretorio | Raiz organizadora dos pacotes por plataforma. Nao e, por si so, o pacote final de uma plataforma. |
| `Sistema Financeiro - Distribuicao/MacOS/` | diretorio | Raiz do pacote macOS a ser compactado. Deve conter somente itens necessarios para instalacao no macOS. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/` | diretorio | Runtime macOS gerado por PyInstaller, sem `data/`, `tests/`, `docs/`, caches ou metadados temporarios. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/Sistema Financeiro.app` | bundle macOS | App instalado em `/Applications`. Deve usar launcher portatil para `~/Documents/Sistema Financeiro`. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/SistemaFinanceiro/` | diretorio | Saida one-folder do PyInstaller para macOS. Deve conter o executavel `SistemaFinanceiro` e seus arquivos internos. |
| `Sistema Financeiro - Distribuicao/MacOS/Instalar Sistema Financeiro.command` | script executavel | Copia os arquivos para `~/Documents/Sistema Financeiro` e instala o `.app` em `/Applications`. |
| `Sistema Financeiro - Distribuicao/MacOS/README-INSTALACAO.md` | documento | Instrui instalacao, primeiro uso, dados nao incluidos, URL local e atualizacao no macOS. |
| `Sistema Financeiro - Distribuicao/MacOS/Sistema Financeiro - Distribuicao MacOS.zip` | arquivo zip | Zip final do macOS, gerado a partir de `Sistema Financeiro - Distribuicao/MacOS/`. |
| `Sistema Financeiro - Distribuicao/Windows/` | diretorio | Raiz do pacote Windows a ser compactado. Deve conter somente itens necessarios para instalacao no Windows. |
| `Sistema Financeiro - Distribuicao/Windows/Aplicativo/` | diretorio | Copia limpa da aplicacao atual para Windows, sem `data/`, `tests/`, `docs/`, caches ou metadados temporarios. |
| `Sistema Financeiro - Distribuicao/Windows/Instalar Sistema Financeiro.bat` | script | Instalador Windows. |
| `Sistema Financeiro - Distribuicao/Windows/README-INSTALACAO-WINDOWS.md` | documento | Instrui instalacao, primeiro uso, dados nao incluidos, URL local e atualizacao no Windows. |
| `Sistema Financeiro - Distribuicao/Windows/Sistema Financeiro - Distribuicao Windows.zip` | arquivo zip | Zip final do Windows, gerado a partir de `Sistema Financeiro - Distribuicao/Windows/`. |

## Regras

- O pacote nao deve conter nenhum arquivo ou subdiretorio de `data/`.
- O pacote nao deve conter nenhum arquivo ou subdiretorio de `tests/`.
- O pacote final nao deve conter a pasta `docs/`; a documentacao tecnica fica apenas no repositorio de desenvolvimento.
- O pacote nao deve conter `__pycache__/`, `.DS_Store`, `_CodeSignature` ou arquivos AppleDouble `._*`.
- O pacote nao deve conter banco SQLite, logs, configuracoes SMTP criptografadas, chaves locais, usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais.
- O pacote macOS deve usar o runtime one-folder gerado por PyInstaller em `MacOS/Aplicativo/SistemaFinanceiro/`, sem expor `app.py`, `financeiro/` ou `web/` como arvore fonte de runtime.
- O pacote Windows deve usar runtime PyInstaller equivalente quando gerado em ambiente Windows; quando ainda estiver no modo fonte, deve manter `app.py`, `financeiro/`, `web/` e scripts `.bat`.
- O pacote macOS tambem deve conter `Sistema Financeiro.app` dentro de `MacOS/Aplicativo/`.
- O bundle `Sistema Financeiro.app` dentro da distribuicao macOS deve usar launcher portatil baseado em `$HOME/Documents/Sistema Financeiro`, chamando `SistemaFinanceiro/SistemaFinanceiro` e nao caminhos absolutos da maquina de desenvolvimento.
- O launcher do app e `MacOS/Instalar Sistema Financeiro.command` devem ter permissao de execucao.
- Se o binario do launcher dentro do `.app` for substituido, assinaturas antigas em `Contents/_CodeSignature` devem ser removidas para evitar assinatura inconsistente.
- O instalador macOS deve copiar a aplicacao para `~/Documents/Sistema Financeiro`, excluindo `data/`, `tests/`, `docs/`, `__pycache__/`, `.DS_Store`, `launcher_distribuicao.c` e `Sistema Financeiro.app/`.
- O instalador macOS deve instalar `Sistema Financeiro.app` em `/Applications` e pedir permissao administrativa via macOS quando necessario.
- O instalador Windows deve manter os dados locais fora do pacote e nao deve copiar dados de desenvolvimento.
- Builds PyInstaller devem ser gerados no sistema operacional alvo; o build Windows deve ser feito em Windows, nao em macOS.
- A URL padrao do app distribuido deve ser `http://sistema-financeiro.localhost:8010` quando suportada pela plataforma.
- A porta padrao deve ser `8010`; conflito de porta deve ser tratado como orientacao operacional no README de instalacao de cada plataforma.
- A geracao do zip macOS deve ser feita a partir da pasta `Sistema Financeiro - Distribuicao/MacOS`, mantendo `MacOS/` como raiz do arquivo compactado.
- A geracao do zip Windows deve ser feita a partir da pasta `Sistema Financeiro - Distribuicao/Windows`, mantendo `Windows/` como raiz do arquivo compactado.

## API e dados

Nao ha rotas de API nem tabelas novas para distribuicao.

Arquivos e diretorios afetados:

| Caminho | Papel |
|---|---|
| `Sistema Financeiro - Distribuicao/` | Raiz organizadora dos pacotes por plataforma. |
| `Sistema Financeiro - Distribuicao/MacOS/` | Fonte do pacote instalavel macOS. |
| `Sistema Financeiro - Distribuicao/MacOS/Sistema Financeiro - Distribuicao MacOS.zip` | Zip final macOS para envio. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/SistemaFinanceiro/SistemaFinanceiro` | Executavel macOS gerado por PyInstaller. |
| `Sistema Financeiro - Distribuicao/Windows/` | Fonte do pacote instalavel Windows. |
| `Sistema Financeiro - Distribuicao/Windows/Sistema Financeiro - Distribuicao Windows.zip` | Zip final Windows para envio. |
| `Sistema Financeiro.app/Contents/MacOS/launcher` | Referencia de launcher do app local, mas nao deve ser usado se apontar para caminho absoluto da maquina de desenvolvimento. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/Sistema Financeiro.app/Contents/MacOS/launcher` | Launcher portatil do pacote macOS. |

## Critérios de aceite

- Dado qualquer pacote gerado, quando o zip for inspecionado, entao nao existe nenhum caminho contendo `/data/` ou `/tests/`.
- Dado qualquer pacote gerado, quando o zip for inspecionado, entao nao existe nenhum caminho contendo `/docs/`.
- Dado qualquer pacote gerado, quando o zip for inspecionado, entao nao existem `__pycache__`, `.DS_Store`, `_CodeSignature` ou arquivos `._*`.
- Dado o bundle `Sistema Financeiro.app` da distribuicao macOS, quando o binario `launcher` for inspecionado, entao ele referencia `$HOME/Documents/Sistema Financeiro` ou formato equivalente portatil, sem caminho absoluto da maquina do mantenedor.
- Dado o pacote macOS gerado, quando inspecionado, entao o runtime principal e `Aplicativo/SistemaFinanceiro/SistemaFinanceiro` e nao `Aplicativo/app.py`.
- Dado o zip final de cada plataforma, quando `zip -T` for executado, entao a integridade do arquivo e confirmada.
- Dado o zip final macOS, quando os metadados forem inspecionados, entao `Instalar Sistema Financeiro.command` e `Contents/MacOS/launcher` estao executaveis.
- Dado a pasta `Aplicativo/`, quando os arquivos Python forem compilados com `py_compile`, entao nao ha erro de sintaxe.
- Dado um computador de destino sem dados anteriores, quando o usuario executar o instalador e abrir o app, entao um banco vazio e criado na pasta local de dados da plataforma.
- Dado um computador de destino com banco anterior, quando o usuario reinstalar, entao o instalador atualiza arquivos do app sem copiar dados do pacote para `data/`.

## Fora de escopo

- Notarizacao Apple e assinatura Developer ID.
- Empacotamento como `.pkg`, `.dmg` ou instalador MSI/EXE.
- Instalacao de Python ou de dependencias externas.
- Migracao automatica de bancos entre maquinas.
- Inclusao de dados demonstrativos ou dados reais de usuario.
- Inclusao de documentacao tecnica, specs, ADRs ou referencias internas nos pacotes finais.

## Changelog

- `1.3` — 2026-07-02 — Pacote macOS passa a usar runtime PyInstaller; build Windows PyInstaller documentado como dependente de ambiente Windows.
- `1.2` — 2026-07-02 — Pacotes finais passam a excluir `docs/` para reduzir superficie de engenharia reversa e entregar somente runtime e instrucoes de instalacao.
- `1.1` — 2026-07-01 — Spec atualizada para refletir pacotes por plataforma em `MacOS/` e `Windows/`.
- `1.0` — 2026-06-30 — Spec criada para documentar regras de geracao, limpeza, validacao e instalacao do pacote macOS.

## Relacionados

- [[sdd]]
- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[requisitos]]
