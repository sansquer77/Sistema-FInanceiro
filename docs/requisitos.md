# Requisitos

## Objetivo

Manter um sistema financeiro local, privado e simples para controlar contas, saldos, lancamentos e classificacoes financeiras em SQLite, com interface web servida pelo proprio app Python.

## Escopo atual implementado

- Autenticacao local com cadastro, login, logout e sessao por cookie HTTP-only.
- Alteracao de email, alteracao de senha e exclusao da conta do usuario autenticado.
- Recuperacao de senha por codigo temporario enviado por email SMTP configurado localmente.
- Cadastro, edicao, listagem, arquivamento e restauracao de contas-correntes.
- Controle de saldo atual por conta, atualizado por receitas, despesas e transferencias.
- Cadastro, edicao, listagem e exclusao controlada de categorias, subcategorias e tags.
- Lancamentos manuais dos tipos receita, despesa e transferencia.
- Vinculo de cada lancamento a uma categoria, subcategoria opcional e uma ou mais tags.
- Exclusao de lancamentos com reversao do impacto no saldo.
- Importacao de lancamentos exportados do Organizze em `.xls` ou `.csv`.
- Interface web estatica em `web/`, sem dependencias externas de frontend.

## Fora do escopo atual

- Cartoes de credito, faturas, fechamento, vencimento e pagamento de fatura.
- Relatorios analiticos completos por periodo, categoria, conta ou tag.
- Recorrencia, parcelamento, lancamentos previstos e conciliacao bancaria.
- Open Finance, sincronizacao em nuvem ou integracoes bancarias automaticas.
- Multiusuario em rede; o uso esperado e local.

## Regras funcionais

- Toda operacao de dados financeiros exige usuario autenticado.
- Dados financeiros pertencem ao usuario autenticado e nao podem ser acessados por outro usuario.
- Contas arquivadas nao aparecem na lista principal, mas podem ser restauradas.
- A moeda de uma conta com lancamentos ativos nao pode ser alterada.
- Receitas aumentam o saldo da conta de origem.
- Despesas reduzem o saldo da conta de origem.
- Transferencias reduzem o saldo da conta de origem e aumentam o saldo da conta de destino.
- Transferencias exigem contas diferentes e com a mesma moeda.
- Cada lancamento exige descricao, data valida, valor maior que zero, conta, categoria e ao menos uma tag.
- Categorias, subcategorias e tags em uso por lancamentos nao podem ser excluidas.
- Importacoes podem criar categorias, subcategorias e tags inexistentes para o usuario autenticado.
- Linhas importadas com situacao diferente de `Pago` sao ignoradas e reportadas.

## Regras de seguranca

- Senhas sao armazenadas com PBKDF2-HMAC-SHA256 e salt por senha.
- Tokens de recuperacao sao armazenados como hash e expiram em 15 minutos.
- Ao redefinir a senha, sessoes ativas do usuario sao encerradas.
- A configuracao SMTP fica criptografada em `data/email_config.enc`.
- A chave local fica em `data/email_config.key` ou na variavel `SISTEMA_FINANCEIRO_CONFIG_KEY`.
- Arquivos de runtime em `data/` nao devem ser versionados.
- Upload de importacao e limitado a 5 MB.
- Identificadores recebidos pela API devem ser validados contra o usuario autenticado.

## Requisitos nao funcionais

- O app deve rodar localmente com Python 3 e bibliotecas padrao.
- O frontend deve continuar simples, responsivo e sem build step.
- Valores monetarios devem ser persistidos em centavos.
- O banco SQLite deve ser criado automaticamente em `data/finance.db`.
- Mudancas de schema devem ser idempotentes para preservar bancos locais existentes.
- Mensagens de erro devem ser claras para o usuario e nao expor detalhes internos.

## Criterios de aceite gerais

- Um usuario novo consegue criar conta, categoria/tag e lancamento sem configuracao externa.
- A lista de contas reflete imediatamente o impacto dos lancamentos.
- A importacao informa total lido, importado, ignorado e motivos de rejeicao.
- A documentacao de arquitetura deve ser atualizada quando endpoints, tabelas ou fluxos centrais mudarem.
