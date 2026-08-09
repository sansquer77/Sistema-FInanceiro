# Sistema Financeiro - Distribuicao Windows

Este pacote instala uma copia limpa do Sistema Financeiro em um computador Windows.

## Requisitos

- Windows 10 ou superior.
- Porta local `8010` livre.

O pacote ja inclui o runtime executavel do app. Nao e necessario instalar Python no computador de destino.

## Como instalar

1. Descompacte o pacote.
2. Abra `Instalar Sistema Financeiro.bat`.
3. Se o Windows SmartScreen perguntar, escolha `Mais informacoes` e depois `Executar assim mesmo`.
4. Ao final, use o icone `Sistema Financeiro` criado na Area de Trabalho.

## Modulo 1 - Execucao local

Use este modo para rodar o sistema apenas neste computador Windows.

1. Abra `Sistema Financeiro` pela Area de Trabalho.
2. O app iniciara o servidor local e abrira o navegador em:

   `http://127.0.0.1:8010`

3. Clique em `Criar acesso` e cadastre o primeiro usuario.
4. Cadastre suas contas, cartoes, categorias e lancamentos.

## Modulo 2 - Execucao em rede

Existem dois cenarios de rede.

### Acessar o servidor Linux central

Use esta opcao quando o Sistema Financeiro estiver rodando no servidor `192.168.1.212`.

1. Clique com o botao direito em `configurar_windows.ps1`.
2. Escolha `Executar com o PowerShell`.
3. Confirme a execucao como Administrador.
4. Acesse no navegador:

   `https://sistema-financeiro.net:8030`

Se o certificado SSL for autoassinado, o navegador pode pedir confirmacao de seguranca no primeiro acesso.

### Expor este Windows para outros dispositivos da LAN

Use este modo quando outros computadores ou celulares da mesma rede Wi-Fi/LAN precisarem acessar o sistema.

1. Instale normalmente.
2. Abra o atalho `Sistema Financeiro Rede` criado na Area de Trabalho.
3. O app detectara o IP local do Windows e abrira uma URL parecida com:

   `http://192.168.1.25:8010`

4. Nos outros dispositivos, abra essa URL no navegador.

Observacoes:

- O Windows pode pedir permissao de firewall para permitir conexoes de entrada do Sistema Financeiro.
- Todos os dispositivos precisam estar na mesma rede.
- Use este modo apenas em rede confiavel. Para acesso fora da rede local, prefira reverse-proxy com HTTPS.

Este modo e diferente do servidor Linux: ele expoe o app instalado neste Windows para a LAN.

## O que o instalador faz

- Copia os arquivos do sistema para `%USERPROFILE%\Documents\Sistema Financeiro`.
- Cria os icones `Sistema Financeiro` e `Sistema Financeiro Rede` na Area de Trabalho.
- Nao leva nenhum banco de dados da maquina original.
- Cria um banco SQLite vazio no primeiro uso.
- Cria arquivos locais de configuracao apenas na maquina instalada.

## Dados nao incluidos

Este pacote nao inclui:

- `data\finance.db`
- `data\server.log`
- `secure\config.key`
- configuracoes SMTP criptografadas
- usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais

## Porta e URL

O app roda localmente em:

`http://127.0.0.1:8010`

Se outro processo estiver usando a porta `8010`, encerre esse processo antes de abrir o app.

No modo rede, a URL usa o IP local detectado do Windows, por exemplo:

`http://192.168.1.25:8010`

## Onde ficam os dados

Depois da instalacao, os dados locais ficam em:

`%USERPROFILE%\Documents\Sistema Financeiro\data\finance.db`

Para fazer backup, copie a pasta:

`%USERPROFILE%\Documents\Sistema Financeiro`

## Reinstalacao ou atualizacao

Rodar o instalador novamente atualiza os arquivos do app em:

`%USERPROFILE%\Documents\Sistema Financeiro`

O instalador nao copia banco de dados nem chaves locais do pacote. Se ja existir um banco local no Windows de destino, ele permanece na pasta `data\`; se ja existir `secure\config.key`, ele tambem e preservado.
