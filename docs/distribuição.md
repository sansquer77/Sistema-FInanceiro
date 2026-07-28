---
tipo: spec
area: distribuicao
status: implementado
versao: 1.7
atualizado: 2026-07-27
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
> **implementado** · área: `distribuicao` · atualizado em 2026-07-27 · relacionados: [[sdd]], [[templates/spec-template|Template de spec]], [[arquitetura]], [[requisitos]]

## Problema

O Sistema Financeiro precisa ser entregue a novos usuarios de macOS e Windows como pacotes limpos, instalaveis e sem dados pessoais ou arquivos de desenvolvimento da maquina original.

## Usuario

Usuario final que vai instalar o Sistema Financeiro em outro computador e mantenedor responsavel por gerar novas versoes dos pacotes de distribuicao por plataforma.

## Jornada

1. O mantenedor atualiza a subpasta da plataforma em `Sistema Financeiro - Distribuicao/` a partir da versao corrente do projeto.
2. O pacote preserva os scripts e instrucoes de instalacao da plataforma, mas substitui os arquivos de aplicacao pelos arquivos atuais.
3. O pacote exclui dados locais, testes, documentacao tecnica, caches e metadados desnecessarios.
4. O mantenedor gera o zip final a partir da subpasta da plataforma.
5. No macOS, o novo usuario descompacta o zip, executa `Instalar Sistema Financeiro.command` e abre `Sistema Financeiro` pela pasta Aplicativos em modo local.
6. No macOS, quando quiser acesso pela LAN, o usuario executa `~/Documents/Sistema Financeiro/Abrir Sistema Financeiro na Rede.command`.
7. No Windows, o novo usuario descompacta o zip, executa `Instalar Sistema Financeiro.bat` e abre o app pelo atalho `Sistema Financeiro` em modo local.
8. No Windows, quando quiser acesso pela LAN, o usuario abre o atalho `Sistema Financeiro Rede`.
9. No primeiro uso, o app cria um banco SQLite vazio na pasta local de dados definida pelo instalador da plataforma.

## Dados

| Artefato | Tipo | Regra |
|---|---|---|
| `Sistema Financeiro - Distribuicao/` | diretorio | Raiz organizadora dos pacotes por plataforma. Nao e, por si so, o pacote final de uma plataforma. |
| `Sistema Financeiro - Distribuicao/MacOS/` | diretorio | Raiz do pacote macOS a ser compactado. Deve conter somente itens necessarios para instalacao no macOS. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/` | diretorio | Runtime macOS gerado por PyInstaller, sem `data/`, `tests/`, `docs/`, caches ou metadados temporarios. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/Sistema Financeiro.app` | bundle macOS | App instalado em `/Applications`. Deve usar launcher portatil para `~/Documents/Sistema Financeiro`. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/SistemaFinanceiro/` | diretorio | Saida one-folder do PyInstaller para macOS. Deve conter o executavel `SistemaFinanceiro` e seus arquivos internos. |
| `Sistema Financeiro - Distribuicao/MacOS/Aplicativo/Abrir Sistema Financeiro na Rede.command` | script executavel | Launcher macOS para expor o app na rede local com `APP_HOST=0.0.0.0`. |
| `Sistema Financeiro - Distribuicao/MacOS/Instalar Sistema Financeiro.command` | script executavel | Copia os arquivos para `~/Documents/Sistema Financeiro` e instala o `.app` em `/Applications`. |
| `Sistema Financeiro - Distribuicao/MacOS/README-INSTALACAO.md` | documento | Instrui instalacao, primeiro uso, dados nao incluidos, URL local e atualizacao no macOS. |
| `Sistema Financeiro - Distribuicao/MacOS/configurar_mac.sh` | script | Configura `/etc/hosts` em clientes macOS/Linux para acessar `sistema-financeiro.net`. |
| `Sistema Financeiro - Distribuicao/MacOS/Sistema Financeiro - Distribuicao MacOS.zip` | arquivo zip | Zip final do macOS, gerado a partir de `Sistema Financeiro - Distribuicao/MacOS/`. |
| `Sistema Financeiro - Distribuicao/Windows/` | diretorio | Raiz do pacote Windows a ser compactado. Deve conter somente itens necessarios para instalacao no Windows. |
| `Sistema Financeiro - Distribuicao/Windows/Aplicativo/` | diretorio | Runtime Windows gerado por PyInstaller e scripts de abertura, sem `app.py`, `financeiro/`, `web/`, `data/`, `tests/`, `docs/`, caches ou metadados temporarios. |
| `Sistema Financeiro - Distribuicao/Windows/Aplicativo/Abrir Sistema Financeiro.bat` | script | Launcher Windows local. |
| `Sistema Financeiro - Distribuicao/Windows/Aplicativo/Abrir Sistema Financeiro na Rede.bat` | script | Launcher Windows para expor o app na rede local via `EXPOSE_LAN=1`. |
| `Sistema Financeiro - Distribuicao/Windows/Instalar Sistema Financeiro.bat` | script | Instalador Windows. |
| `Sistema Financeiro - Distribuicao/Windows/README-INSTALACAO-WINDOWS.md` | documento | Instrui instalacao, primeiro uso, dados nao incluidos, URL local e atualizacao no Windows. |
| `Sistema Financeiro - Distribuicao/Windows/configurar_windows.ps1` | script | Configura o arquivo `hosts` em clientes Windows para acessar `sistema-financeiro.net`. |
| `Sistema Financeiro - Distribuicao/Windows/Sistema Financeiro - Distribuicao Windows.zip` | arquivo zip | Zip final do Windows, gerado a partir de `Sistema Financeiro - Distribuicao/Windows/`. |

## Regras

- O pacote nao deve conter nenhum arquivo ou subdiretorio de `data/`.
- O pacote nao deve conter nenhum arquivo ou subdiretorio de `tests/`.
- O pacote final nao deve conter a pasta `docs/`; a documentacao tecnica fica apenas no repositorio de desenvolvimento.
- O pacote nao deve conter `__pycache__/`, `.DS_Store`, `_CodeSignature` ou arquivos AppleDouble `._*`.
- O pacote nao deve conter banco SQLite, logs, configuracoes SMTP criptografadas, chaves locais, usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais.
- O pacote macOS deve usar o runtime one-folder gerado por PyInstaller em `MacOS/Aplicativo/SistemaFinanceiro/`, sem expor `app.py`, `financeiro/` ou `web/` como arvore fonte de runtime.
- O pacote Windows gerado por GitHub Actions deve usar runtime PyInstaller em `Windows/Aplicativo/SistemaFinanceiro/`, sem expor `app.py`, `financeiro/` ou `web/` como arvore fonte de runtime.
- Os atalhos Windows devem executar `SistemaFinanceiro/SistemaFinanceiro.exe`, nunca `python app.py`, para evitar uso acidental de arquivos fonte antigos.
- O pacote macOS tambem deve conter `Sistema Financeiro.app` dentro de `MacOS/Aplicativo/`.
- O bundle `Sistema Financeiro.app` dentro da distribuicao macOS deve usar launcher portatil baseado em `$HOME/Documents/Sistema Financeiro`, chamando `SistemaFinanceiro/SistemaFinanceiro` e nao caminhos absolutos da maquina de desenvolvimento.
- O launcher do app e `MacOS/Instalar Sistema Financeiro.command` devem ter permissao de execucao.
- Se o binario do launcher dentro do `.app` for substituido, assinaturas antigas em `Contents/_CodeSignature` devem ser removidas para evitar assinatura inconsistente.
- O instalador macOS deve copiar a aplicacao para `~/Documents/Sistema Financeiro`, excluindo `data/`, `tests/`, `docs/`, `__pycache__/`, `.DS_Store`, `launcher_distribuicao.c` e `Sistema Financeiro.app/`.
- O instalador macOS deve instalar `Sistema Financeiro.app` em `/Applications` e pedir permissao administrativa via macOS quando necessario.
- O instalador Windows deve manter os dados locais fora do pacote e nao deve copiar dados de desenvolvimento.
- Builds PyInstaller devem ser gerados no sistema operacional alvo; o build Windows deve ser feito em Windows, nao em macOS.
- A URL padrao do app distribuido deve ser `http://sistema-financeiro.localhost:8010` quando suportada pela plataforma.
- O backend deve aceitar `http://sistema-financeiro.localhost:8010` e `https://sistema-financeiro.net:8030`.
- A configuracao do servidor Linux deve usar `APP_URL=https://sistema-financeiro.net:8030`, backend interno em `127.0.0.1:8010` e nginx em `8030 ssl`.
- Hosts/origens permitidos do servidor devem cobrir dominio e IP: `sistema-financeiro.net`, `sistema-financeiro.net:8030`, `192.168.1.212`, `192.168.1.212:8030`, e origens HTTP/HTTPS correspondentes.
- A porta padrao deve ser `8010`; conflito de porta deve ser tratado como orientacao operacional no README de instalacao de cada plataforma.
- O modo local deve manter `APP_HOST=127.0.0.1`.
- O modo rede deve usar `APP_HOST=0.0.0.0`, detectar o IP local da maquina e preencher `APP_URL`, `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`.
- `APP_ALLOWED_HOSTS` aceita lista CSV; entradas sem porta tambem aceitam a porta configurada em `APP_PORT`.
- `APP_ALLOWED_ORIGINS` aceita lista CSV; entradas sem esquema assumem `http://` e entradas sem porta assumem `APP_PORT`.
- O modo rede deve ser documentado como apropriado apenas para redes confiaveis; acesso remoto deve usar reverse-proxy com HTTPS.
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
- Dado o pacote Windows gerado por GitHub Actions, quando inspecionado, entao o runtime principal e `Aplicativo/SistemaFinanceiro/SistemaFinanceiro.exe` e nao `Aplicativo/app.py`.
- Dado o launcher Windows local, quando inspecionado, entao ele executa `SistemaFinanceiro.exe` e nao `python app.py`.
- Dado o pacote macOS instalado, quando o usuario executa `Abrir Sistema Financeiro na Rede.command`, entao o app sobe em `0.0.0.0`, mostra uma URL com IP local e permite acesso de outros dispositivos da mesma rede.
- Dado o pacote Windows instalado, quando o usuario executa o atalho `Sistema Financeiro Rede`, entao o app sobe em `0.0.0.0`, abre uma URL com IP local e permite acesso de outros dispositivos da mesma rede.
- Dado um cliente macOS/Linux, quando `configurar_mac.sh` e executado, entao `192.168.1.212 sistema-financeiro.net` fica presente em `/etc/hosts`.
- Dado um cliente Windows, quando `configurar_windows.ps1` e executado como Administrador, entao `192.168.1.212 sistema-financeiro.net` fica presente no arquivo `hosts` do Windows.
- Dado o servidor Linux configurado conforme `README-deploy.md`, quando acessado via `https://sistema-financeiro.net:8030`, entao as validacoes de Host e Origin aceitam a requisicao.
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

- `1.7` — 2026-07-27 — Pacote Windows gerado por GitHub Actions passa a ser montado em staging limpo com runtime PyInstaller, sem arvore fonte e com launchers apontando para `SistemaFinanceiro.exe`.
- `1.6` — 2026-07-06 — Inclusao de servidor Linux em `sistema-financeiro.net:8030`, scripts de hosts para clientes e regras padrao de Host/Origin.
- `1.5` — 2026-07-04 — Normalizacao de hosts/origens permitidos documentada para modo rede e launchers LAN.
- `1.4` — 2026-07-04 — Pacotes passam a documentar e entregar launchers separados para modo local e modo rede/LAN.
- `1.3` — 2026-07-02 — Pacote macOS passa a usar runtime PyInstaller; build Windows PyInstaller documentado como dependente de ambiente Windows.
- `1.2` — 2026-07-02 — Pacotes finais passam a excluir `docs/` para reduzir superficie de engenharia reversa e entregar somente runtime e instrucoes de instalacao.
- `1.1` — 2026-07-01 — Spec atualizada para refletir pacotes por plataforma em `MacOS/` e `Windows/`.
- `1.0` — 2026-06-30 — Spec criada para documentar regras de geracao, limpeza, validacao e instalacao do pacote macOS.

## Relacionados

- [[sdd]]
- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[requisitos]]
