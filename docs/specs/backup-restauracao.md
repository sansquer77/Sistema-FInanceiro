---
tipo: spec
area: backup-restauracao
status: em-revisao
versao: 1.0
atualizado: 2026-09-05
relacionados:
  - "[[migracao-banco-v2]]"
  - "[[privacidade-valores]]"
  - "[[seguranca-autenticacao]]"
  - "[[../adr/0010-segredos-criptografados-sqlite]]"
  - "[[../adr/0018-backup-completo-criptografado]]"
  - "[[../arquitetura]]"
tags: [spec, "area/backup-restauracao", "status/em-revisao"]
aliases: ["Backup e Restauração"]
---

# Backup e Restauração

> [!info] Status
> **em revisão** · versão: `1.0` · área: `backup-restauracao` · atualizado em 2026-09-05 · relacionados: [[migracao-banco-v2]], [[privacidade-valores]], [[../adr/0018-backup-completo-criptografado]]

## Problema

O banco `finance.db` contém os dados financeiros, mas não é suficiente para uma recuperação completa. O app também depende de configurações criptografadas, da chave mestra local e de metadados necessários para validar a restauração. Uma cópia direta do SQLite pode ser inconsistente quando o banco está em uso e uma cópia sem a chave pode parecer válida, mas não recuperar as integrações.

O usuário precisa gerar um pacote completo, criptografado, validado e restaurável, salvar esse pacote em um diretório escolhido e configurar uma política recorrente sem depender de conhecimento técnico.

## Usuário

Usuário local que quer proteger seus dados contra falha do disco, perda do computador, erro operacional ou migração para outra instalação compatível.

## Jornada

1. O usuário acessa uma aba própria **Backup** em Preferências.
2. Seleciona um diretório de destino e define frequência, retenção e senha do pacote.
3. Confirma a senha e escolhe se ela pode ser lembrada de forma criptografada para permitir backups automáticos.
4. Gera um backup imediato ou aguarda a próxima abertura do app após o vencimento da política.
5. O app cria uma cópia online consistente do SQLite, reúne configurações e chave mestra, valida os arquivos e gera um pacote ZIP criptografado.
6. O usuário acompanha a data, resultado e localização do último backup.
7. Para restaurar, seleciona um pacote, informa a senha e executa uma validação preliminar antes de confirmar a substituição do ambiente ativo.

## Dados

- `backup_directory`: diretório escolhido pelo usuário; deve ser absoluto, gravável e não pode ser o próprio diretório `data/` ativo.
- `schedule_frequency`: `on_start`, `daily`, `weekly` ou `monthly`.
- `retention_count`: quantidade de pacotes válidos mantidos.
- `backup_password`: senha do pacote; nunca aparece em texto puro fora da memória da operação.
- `remember_password`: indica se a senha é armazenada criptografada em `secure_configs` para execução recorrente.
- `last_backup_at`: data/hora da última geração concluída.
- `last_backup_status`: `success`, `failed` ou `never_run`.
- `package_filename`: nome do pacote gerado, sem permitir caminho arbitrário vindo de dados financeiros.
- `manifest`: versão do app, versão do schema, data, arquivos, tamanhos, hashes e resultado do `integrity_check`.

## Regras

- O backup completo inclui o banco SQLite, a chave mestra local e as configurações criptografadas necessárias para recuperar o ambiente; nenhum desses arquivos é gravado fora do payload protegido.
- A cópia SQLite usa `Connection.backup` ou mecanismo equivalente de backup online; copiar somente `finance.db` não é o contrato de backup.
- O pacote é criado em arquivo temporário, validado e promovido por renomeação atômica; falha não substitui o último backup válido.
- Cada arquivo incluído tem hash SHA-256 registrado no manifesto protegido.
- O pacote é rejeitado na restauração se a senha estiver incorreta, se houver alteração de conteúdo, se o manifesto for incompatível ou se o SQLite falhar no `integrity_check`.
- A restauração ocorre primeiro em área temporária e nunca substitui o banco ativo sem confirmação explícita.
- Antes de substituir o ambiente ativo, o app cria uma cópia de segurança do estado atual.
- A senha pode ser lembrada somente criptografada pelo mecanismo de segredos existente; o app não oferece recuperação da senha esquecida.
- Trocar a senha protege os pacotes futuros e não recriptografa nem altera pacotes anteriores.
- O backup automático ocorre na abertura quando estiver vencido. Agendamento com o app fechado depende de integração posterior com o agendador do sistema operacional.
- A retenção remove apenas pacotes válidos excedentes, nunca o último pacote válido nem arquivos que não tenham sido confirmados como backups do app.
- O destino não pode apontar para `data/`, `secure/`, o diretório temporário de restauração ou uma subpasta do próprio pacote em criação.
- A política protege a instalação SQLite inteira, inclusive em servidor caseiro com poucos usuários concorrentes; ela nunca filtra o pacote pelo usuário autenticado.
- Somente o usuário ativo mais antigo pode configurar, executar manualmente ou restaurar backups. As demais contas consultam o estado sem obter o segredo e sem poder alterar o ambiente compartilhado.
- Duas criações ou restaurações não podem executar simultaneamente no mesmo processo.
- A promoção de uma restauração obtém acesso exclusivo à instalação: aguarda requisições já iniciadas e impede novas leituras ou escritas até concluir ou reverter, sem serializar o uso normal fora dessa janela.

## Segurança

- A senha do pacote é validada com confirmação e permanece apenas em memória durante a operação, salvo quando o usuário opta explicitamente por armazená-la criptografada para automação.
- O pacote não usa ZipCrypto nem a criptografia legada do `zipfile`; o container ZIP transporta um payload protegido por criptografia autenticada definida em [[../adr/0018-backup-completo-criptografado]].
- Logs e mensagens não exibem senha, chave mestra, caminho de arquivos sensíveis internos, conteúdo financeiro ou payload bruto.
- O app não envia backups para serviços externos nesta primeira versão.
- O usuário é alertado de que perder a senha e a chave mestra impede a recuperação do pacote.

## API e dados

- `backup_settings`: registro único por instalação com diretório, frequência, retenção, opção de lembrar senha, usuário configurador e estado da última execução.
- `secure_configs`: aceita `config_type = backup_password`; contém a senha somente quando a opção de lembrá-la estiver ativa.
- `GET /api/backup/settings`: retorna política e estado, nunca a senha.
- `PUT /api/backup/settings`: valida e salva política, senha e confirmação.
- `POST /api/backup/run`: gera um pacote imediato; aceita senha em memória quando ela não estiver lembrada.
- `POST /api/backup/validate`: valida pacote e senha em área temporária, sem alterar arquivos ativos, e devolve um token efêmero de confirmação.
- `POST /api/backup/restore`: consome o token efêmero e confirma a promoção; a resposta orienta reiniciar o app.

## Critérios de aceite

- Dado um diretório válido, quando o usuário gera um backup, então um pacote ZIP criptografado é criado sem interromper o uso normal do banco.
- Dado um banco em uso, quando o backup é gerado, então a cópia SQLite passa por uma operação online consistente.
- Dado um backup concluído, quando o manifesto é validado, então ele informa versão do app, schema, arquivos, hashes e resultado de integridade.
- Dado configurações criptografadas no ambiente, quando o backup é concluído, então a chave mestra e essas configurações estão dentro do payload protegido.
- Dado uma senha incorreta, quando o usuário tenta restaurar, então nenhum arquivo ativo é alterado.
- Dado um pacote adulterado, quando o usuário tenta restaurar, então a autenticação falha antes da persistência.
- Dado um backup válido, quando o usuário solicita restauração, então o app valida o pacote em área temporária antes de pedir confirmação de substituição.
- Dado um ambiente ativo antes da restauração, quando a substituição é confirmada, então o estado anterior é preservado em uma cópia recuperável.
- Dado o backup automático vencido, quando o usuário abre o app, então uma nova execução ocorre conforme frequência e retenção configuradas.
- Dado que a senha foi alterada, quando um novo backup é gerado, então os pacotes futuros usam a nova senha e os anteriores permanecem inalterados.
- Dado um pacote inválido entre versões retidas, quando a retenção é executada, então o app não remove o último pacote válido por engano.
- Dado um destino igual ao diretório ativo ou temporário, quando o usuário tenta salvá-lo, então a configuração é rejeitada.
- Dada uma instalação com múltiplos usuários, quando o backup é gerado, então todos integram a mesma cópia SQLite consistente e apenas o responsável da instalação pode administrar ou restaurar o pacote.
- Dada uma instalação compartilhada em uso, quando uma restauração é confirmada, então requisições em andamento terminam antes da promoção e novas requisições aguardam o término da restauração.

## Pendências

> [!question] Pendências

- [x] Confirmar se a senha será lembrada criptografada para backups automáticos ou exigida a cada execução: ambas as opções são suportadas; automação exige lembrança explícita.
- [x] Definir a biblioteca e o formato exato do payload criptografado nos runtimes macOS, Windows e Linux: `cryptography`, AES-256-GCM incremental e scrypt, conforme ADR-0018.
- [x] Definir política de senha mínima e mensagens para senha esquecida: mínimo de 12 caracteres e nenhuma recuperação.
- [x] Definir se o diretório será escolhido nativamente em cada plataforma ou informado como caminho validado: caminho absoluto validado nesta versão.
- [ ] Definir agendamento posterior com o sistema operacional quando o app estiver fechado.
- [x] Definir o contrato de restauração entre versões incompatíveis do schema: a versão inicial aceita somente o schema corrente.

## Fora de escopo

- Sincronização em nuvem ou envio automático para terceiros.
- Backup incremental ou deduplicação entre pacotes.
- Restauração seletiva de apenas uma conta, categoria ou módulo.
- Recuperação de senha por e-mail ou serviço externo.

## Plano de implementação

- [x] Passo 1 — Fechar formato, criptografia, senha e compatibilidade no ADR-0018. Fecha: critérios 1, 3, 4, 5, 6 e 10.
- [x] Passo 2 — Criar configuração idempotente em Preferências e validação de diretório/retenção. Fecha: critérios 9 e 12.
- [x] Passo 3 — Implementar cópia online, manifesto, hashes, pacote temporário e promoção atômica. Fecha: critérios 1, 2 e 3.
- [x] Passo 4 — Implementar restauração temporária, validação e salvaguarda do ambiente ativo. Fecha: critérios 5, 6, 7 e 8.
- [x] Passo 5 — Implementar execução recorrente na abertura e retenção segura. Fecha: critérios 9 e 11.
- [x] Passo 6 — Testar round-trip, adulteração, senha incorreta, falhas de disco e compatibilidade nos pacotes distribuídos. Round-trip e falhas estão automatizados; os workflows instalam `cryptography` nos três sistemas e o smoke test final ocorre na geração dos artefatos da release.

## Changelog

- `1.0` — 2026-09-05 — Implementação concluída e em revisão de distribuição: política global segura para ambiente multiusuário, backup online autenticado, restauração em duas fases com acesso exclusivo na promoção, salvaguarda, agendamento na abertura, retenção validada, interface e testes de falha/round-trip.
- `0.2` — 2026-09-05 — Iniciada a implementação; fechados formato, criptografia, senha, persistência, rotas, seleção por caminho absoluto e compatibilidade de schema.
- `0.1` — 2026-09-05 — Rascunho inicial do módulo completo de Backup e Restauração, com pacote ZIP criptografado, senha configurável em Preferências, validação, retenção e execução recorrente na abertura.

## Relacionados

- [[migracao-banco-v2]]
- [[privacidade-valores]]
- [[seguranca-autenticacao]]
- [[../adr/0010-segredos-criptografados-sqlite]]
- [[../adr/0018-backup-completo-criptografado]]
