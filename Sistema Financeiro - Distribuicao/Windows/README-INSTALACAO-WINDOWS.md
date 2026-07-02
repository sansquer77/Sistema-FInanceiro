# Sistema Financeiro - Distribuicao Windows

Este pacote instala uma copia limpa do Sistema Financeiro em um computador Windows.

## Requisitos

- Windows 10 ou superior.
- Python 3 instalado e disponivel no PATH.
- Porta local `8010` livre.

Se o Python nao estiver instalado, baixe em:

`https://www.python.org/downloads/windows/`

Durante a instalacao do Python, marque a opcao:

`Add python.exe to PATH`

## Como instalar

1. Descompacte o pacote.
2. Abra `Instalar Sistema Financeiro.bat`.
3. Se o Windows SmartScreen perguntar, escolha `Mais informacoes` e depois `Executar assim mesmo`.
4. Ao final, use o icone `Sistema Financeiro` criado na Area de Trabalho.

## Primeiro uso

1. Abra `Sistema Financeiro` pela Area de Trabalho.
2. O app iniciara o servidor local e abrira o navegador em:

   `http://127.0.0.1:8010`

3. Clique em `Criar acesso` e cadastre o primeiro usuario.
4. Cadastre suas contas, cartoes, categorias e lancamentos.

## O que o instalador faz

- Copia os arquivos do sistema para `%USERPROFILE%\Documents\Sistema Financeiro`.
- Cria o icone `Sistema Financeiro` na Area de Trabalho.
- Nao leva nenhum banco de dados da maquina original.
- Cria um banco SQLite vazio no primeiro uso.
- Cria arquivos locais de configuracao apenas na maquina instalada.

## Dados nao incluidos

Este pacote nao inclui:

- `data\finance.db`
- `data\server.log`
- configuracoes SMTP criptografadas
- usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais

## Porta e URL local

O app roda localmente em:

`http://127.0.0.1:8010`

Se outro processo estiver usando a porta `8010`, encerre esse processo antes de abrir o app.

## Onde ficam os dados

Depois da instalacao, os dados locais ficam em:

`%USERPROFILE%\Documents\Sistema Financeiro\data\finance.db`

Para fazer backup, copie a pasta:

`%USERPROFILE%\Documents\Sistema Financeiro`

## Reinstalacao ou atualizacao

Rodar o instalador novamente atualiza os arquivos do app em:

`%USERPROFILE%\Documents\Sistema Financeiro`

O instalador nao copia banco de dados do pacote. Se ja existir um banco local no Windows de destino, ele permanece na pasta `data\`.
