# Sistema Financeiro - Distribuicao

Este pacote instala uma copia limpa do Sistema Financeiro em outro Mac.

## Requisitos

- macOS com Python 3 disponivel pelo sistema.
- Permissao para instalar um app em `/Applications`.
- Porta local `8010` livre.

## Como instalar

1. Descompacte o arquivo `.zip`.
2. Abra `Instalar Sistema Financeiro.command`.
3. Se o macOS bloquear a abertura, clique com o botao direito no arquivo, escolha `Abrir` e confirme.
4. Se o macOS pedir senha, informe a senha do usuario do Mac para permitir a copia do icone para `/Applications`.
5. Ao final, abra `Sistema Financeiro` pela pasta Aplicativos.

## Primeiro uso

1. Abra `Sistema Financeiro` em Aplicativos.
2. O app iniciara o servidor local e abrira:

   `http://sistema-financeiro.localhost:8010`

3. Clique em `Criar acesso` e cadastre o primeiro usuario.
4. Cadastre suas contas, cartoes, categorias e lancamentos.

## Recuperacao de senha por email

O pacote nao inclui nenhuma credencial de email.

Para ativar `Esqueci minha senha`:

1. Entre no app.
2. Abra `Preferencias`.
3. Em `Recuperacao por email`, escolha:
   - `Gmail`
   - `Outlook / Microsoft`
   - ou `Manual`
4. Para Gmail ou Outlook/Microsoft, informe apenas:
   - email remetente
   - senha de app
5. Salve a configuracao.

O app preenche automaticamente servidor SMTP, porta e STARTTLS para Gmail e Outlook/Microsoft.

## O que o instalador faz

- Copia os arquivos do sistema para `~/Documents/Sistema Financeiro`.
- Instala o icone `Sistema Financeiro.app` em `/Applications`.
- Nao leva nenhum banco de dados da maquina original.
- Cria um banco SQLite vazio no primeiro uso.
- Cria arquivos locais de configuracao apenas na maquina instalada.

## Dados nao incluidos

Este pacote nao inclui:

- `data/finance.db`
- `data/server.log`
- configuracoes SMTP criptografadas
- usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais

## Porta e URL local

O app roda localmente em:

`http://sistema-financeiro.localhost:8010`

Se outro processo estiver usando a porta `8010`, encerre esse processo antes de abrir o app.

## Onde ficam os dados

Depois da instalacao, os dados locais ficam em:

`~/Documents/Sistema Financeiro/data/finance.db`

Para fazer backup, copie a pasta:

`~/Documents/Sistema Financeiro`

## Reinstalacao ou atualizacao

Rodar o instalador novamente atualiza os arquivos do app em:

`~/Documents/Sistema Financeiro`

O instalador nao copia banco de dados do pacote. Se ja existir um banco local no Mac de destino, ele permanece na pasta `data/`.
