# Sistema Financeiro - Distribuicao Linux Ubuntu

Este pacote instala uma copia limpa do Sistema Financeiro em um computador Linux Ubuntu.

## Requisitos

- Ubuntu ou distribuicao Linux compativel.
- Permissao para executar scripts `.sh`.
- Porta local `8010` livre.

O pacote ja inclui o runtime executavel do app. Nao e necessario instalar Python no computador de destino.

## Como instalar

1. Extraia este pacote.
2. Abra um Terminal na pasta extraida.
3. Execute:

   ```bash
   chmod +x Aplicativo/*.sh
   ```

## Modulo 1 - Execucao local

Use este modo para rodar o sistema apenas neste computador.

1. No Terminal, entre na pasta `Aplicativo`.
2. Execute:

   ```bash
   ./Abrir\ Sistema\ Financeiro.sh
   ```

3. Acesse no navegador:

   `http://127.0.0.1:8010`

4. Clique em `Criar acesso` e cadastre o primeiro usuario.

## Modulo 2 - Execucao em rede

Existem dois cenarios de rede.

### Acessar o servidor Linux central

Use esta opcao quando o Sistema Financeiro estiver rodando no servidor `192.168.1.212`.

Acesse diretamente:

`https://sistema-financeiro.net:8030`

Se necessario, adicione no `/etc/hosts`:

```text
192.168.1.212 sistema-financeiro.net
```

### Expor este Linux para outros dispositivos da LAN

Este pacote nao abre automaticamente o servidor local em `0.0.0.0`.
Para uso compartilhado, prefira o servidor Linux central com HTTPS.

## Dados nao incluidos

Este pacote nao inclui banco SQLite, logs, credenciais SMTP, chaves locais, usuarios, contas, cartoes, lancamentos, categorias, tags ou posicoes pessoais.

## Onde ficam os dados

Por padrao, o runtime cria os dados na pasta local do executavel:

`Aplicativo/SistemaFinanceiro/data/finance.db`
