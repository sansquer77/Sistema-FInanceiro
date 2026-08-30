---
tipo: spec
area: migracao-dados
status: implementado
versao: 1.1
atualizado: 2026-08-30
relacionados:
  - "[[../arquitetura]]"
  - "[[importacao-dados]]"
  - "[[../adr/0003-sqlite-fonte-de-verdade]]"
  - "[[../adr/0012-fundacao-v2-contrato-e-migracao-de-dados]]"
tags: [spec, "area/migracao-dados", "status/implementado"]
aliases: ["Migração do banco para a v2", "Banco v2"]
---

# Migração do banco para a v2

> [!info] Status
> **implementado** · área: `migracao-dados` · atualizado em 2026-08-30 · relacionados: [[../arquitetura]], [[importacao-dados]], [[../adr/0003-sqlite-fonte-de-verdade]], [[../adr/0012-fundacao-v2-contrato-e-migracao-de-dados]]

## Problema

O usuário que abre a linha v2 pode possuir anos de dados em um `data/finance.db` criado e evoluído pela linha 1.x. A v2 precisa adotar um baseline explícito de schema sem perder dados, quebrar rotinas externas de backup que esperam o nome `finance.db` ou executar em toda abertura a cadeia histórica de compatibilizações.

## Usuário

Usuário existente que atualiza o aplicativo para a linha v2 e usuário novo que inicia a v2 sem banco anterior.

## Jornada

1. O usuário abre o aplicativo normalmente.
2. O app identifica se `finance.db` não existe, já usa o schema v2 ou ainda é legado.
3. Em uma instalação nova, o app cria `finance.db` diretamente no baseline v2.
4. Diante de um banco legado, o app prepara e valida um novo banco antes de trocar qualquer nome definitivo.
5. Após sucesso integral, o banco legado passa a se chamar `finance-v1.bkp` e o banco v2 assume `finance.db`.
6. Nas aberturas posteriores, o app reconhece o schema v2 e não repete a compatibilização da linha 1.x.

## Dados

- `data/finance.db`: banco ativo; mantém o nome esperado pelo app e por rotinas externas de backup.
- `data/finance-v1.bkp`: cópia integral e não sobrescrita do banco legado anterior à migração.
- `PRAGMA user_version`: versão inteira e monotônica do schema; o baseline inicial da linha v2 usa `20000`.
- arquivos temporários de migração: permanecem no mesmo diretório do banco para permitir promoção por renomeação no mesmo volume e são removidos após sucesso ou falha tratada.

## Regras

- Banco ausente cria um `finance.db` novo, íntegro e marcado como schema v2.
- Banco com `user_version = 20000` abre sem executar compatibilizações da linha 1.x.
- Banco existente com `user_version = 0` é tratado como legado 1.x.
- A identificação da versão deve funcionar com banco WAL em caminhos que contenham espaços, inclusive o diretório de homologação da v2.
- Versão de schema maior ou diferente das versões suportadas bloqueia a abertura com erro explícito, sem alterar arquivos.
- A normalização do legado ocorre em cópia de trabalho; o arquivo original não recebe `ALTER TABLE`, backfill ou outra transformação lógica.
- O candidato v2 é produzido em arquivo separado e validado antes da promoção.
- A validação exige `PRAGMA integrity_check = ok`, ausência de violações em `PRAGMA foreign_key_check` e igualdade das contagens de todas as tabelas de usuário entre a cópia normalizada e o candidato.
- `finance-v1.bkp` nunca é sobrescrito.
- A promoção só ocorre depois das validações e tenta restaurar `finance.db` se a segunda renomeação falhar.
- Falha anterior à promoção preserva `finance.db` legado no nome original.
- Abertura posterior à migração mantém `finance.db` como banco ativo e `finance-v1.bkp` como recuperação legada.
- Segredos persistidos em `secure_configs` são copiados somente como payload criptografado.
- Arquivos runtime externos ao SQLite, inclusive chave mestra e arquivos `.enc` legados, não são movidos pelo migrador.

## API e dados

- Não cria rota HTTP.
- O fluxo ocorre antes de o servidor começar a aceitar requisições.
- `financeiro/database.py` passa a separar inicialização pública, construção/normalização do schema e validação/promoção do banco.
- O schema funcional inicial da v2 permanece equivalente ao schema final da versão 1.x; melhorias estruturais adicionais exigem specs e migrações v2 próprias.

## Critérios de aceite

1. Dado diretório de dados sem banco, quando o app inicializa, então cria `finance.db` com `user_version = 20000`.
2. Dado banco v2 válido, quando o app inicializa novamente, então não executa o caminho de compatibilidade legado.
3. Dado `finance.db` legado válido, quando o app inicializa, então preserva o arquivo original como `finance-v1.bkp`.
4. Dado migração legada concluída, quando os arquivos são inspecionados, então o banco ativo v2 mantém o nome `finance.db`.
5. Dado tabelas e dados no banco legado, quando a migração termina, então todas as tabelas de usuário mantêm as mesmas contagens após a normalização prevista.
6. Dado banco legado com segredo criptografado, quando migrado, então o payload armazenado permanece idêntico e não é exposto em logs.
7. Dado falha de integridade ou chave estrangeira no candidato, quando a validação ocorre, então a promoção é recusada e o `finance.db` original permanece no lugar.
8. Dado `finance-v1.bkp` preexistente e `finance.db` ainda legado, quando o app inicializa, então a migração é bloqueada sem sobrescrever nenhum dos dois arquivos.
9. Dado schema desconhecido ou posterior ao suportado, quando o app inicializa, então a abertura é bloqueada sem modificar o banco.
10. Dado migração bem-sucedida, quando o app abre novamente, então não cria outro backup nem repete a migração.
11. Dado falha durante a promoção após renomear o legado, quando a restauração é possível, então o nome `finance.db` volta a apontar para o banco legado.
12. Dado banco SQLite em modo WAL dentro de caminho com espaços, quando o app identifica o schema, então a inicialização prossegue sem erro de abertura por URI.

## Fora de escopo

- Alterar regras financeiras ou payloads da API durante a migração.
- Excluir automaticamente `finance-v1.bkp`.
- Migrar Open Finance ou Consolidação Familiar antes da implementação das respectivas specs.
- Fazer limpeza definitiva de colunas ou remodelagem de entidades na mesma entrega.
- Oferecer tela de progresso nesta primeira versão do migrador.

## Plano de implementação

- [x] Passo 1 — separar detecção da versão, criação do baseline e compatibilidade legada em `financeiro/database.py`. Fecha: critérios 1, 2 e 9.
- [x] Passo 2 — criar cópia de trabalho, candidato compacto, validações e promoção com backup. Fecha: critérios 3, 4, 5, 6, 7, 8 e 11.
- [x] Passo 3 — garantir idempotência nas reaberturas e preservação de arquivos externos. Fecha: critérios 10 e regras de segurança.
- [x] Passo 4 — adicionar testes automatizados usando apenas diretórios e bancos temporários. Fecha: critérios 1 a 12.

## Changelog

- `1.1` — 2026-08-30 — Corrigida a leitura de `user_version` em bancos WAL localizados em caminhos com espaços, como a pasta de homologação v2.0.
- `1.0` — 2026-08-30 — Implementado o baseline de schema `20000`, a detecção automática na abertura, a migração por cópia normalizada/compactada, as validações e a promoção recuperável com `finance-v1.bkp`.
- `0.1` — 2026-08-30 — Especificado o migrador automático da linha 1.x para o baseline v2, com backup `finance-v1.bkp`, manutenção do nome ativo `finance.db`, validação e promoção recuperável.

## Relacionados

- [[../arquitetura]]
- [[importacao-dados]]
- [[../adr/0003-sqlite-fonte-de-verdade]]
- [[../adr/0012-fundacao-v2-contrato-e-migracao-de-dados]]
