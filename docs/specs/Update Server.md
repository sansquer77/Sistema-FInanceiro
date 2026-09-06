---
tipo: spec
area: distribuicao
status: implementado
versao: 1.4
atualizado: 2026-09-06
relacionados:
  - "[[sdd]]"
  - "[[templates/spec-template|Template de spec]]"
  - "[[distribuição]]"
  - "[[arquitetura]]"
  - "[[seguranca-autenticacao]]"
tags: [spec, "area/distribuicao", deploy, servidor]
aliases: ["Update Server", "Atualizacao do Servidor", "Deploy do Servidor"]
---

# Update Server

> [!info] Status
> **implementado** · área: `distribuicao` · atualizado em 2026-09-06 · relacionados: [[sdd]], [[templates/spec-template|Template de spec]], [[distribuição]], [[arquitetura]], [[seguranca-autenticacao]]

## Problema

A atualização do servidor Linux precisa substituir a versão em produção de forma previsível, preservando os dados existentes e oferecendo rollback rápido caso a nova versão apresente falhas críticas.

## Usuário

Mantenedor responsável por atualizar a instância Linux do Sistema Financeiro em `sistema-financeiro.net`, com acesso SSH ao servidor `sansquer@192.168.1.212`.

## Jornada

1. O mantenedor promove para a pasta de homologação somente o código V2 já testado e validado localmente.
2. O `deploysf` sincroniza essa homologação com o staging Endor e aciona o script remoto via SSH.
3. O serviço é interrompido para liberar arquivos de código e evitar escrita concorrente.
4. A versão atual de `/opt/sistema-financeiro` é copiada para `/mnt/endor/Sistema Financeiro_backup`.
5. A nova versão disponível em `/mnt/endor/Sistema Financeiro` é aplicada em `/opt/sistema-financeiro`.
6. A propriedade dos arquivos volta para `sistema:sistema`.
7. O serviço é reiniciado e os logs são monitorados.
8. Em falha crítica, o backup é restaurado imediatamente.

## Dados

| Caminho | Tipo | Regra |
|---|---|---|
| `/opt/sistema-financeiro` | diretório | Pasta oficial de execução em produção. |
| `/mnt/endor/Sistema Financeiro` | diretório | Fonte da nova versão a publicar. Deve conter código validado antes do deploy. |
| `/mnt/endor/Sistema Financeiro_backup` | diretório | Backup substituível da versão anterior de produção. |
| `/opt/sistema-financeiro/data` | diretório | Dados de runtime. Deve ser preservado durante atualização de código. |
| `sistema-financeiro.service` | systemd service | Serviço Python da aplicação. |
| `/etc/ssl/private/sistema-financeiro.key` | arquivo | Chave privada do certificado local. Deve permanecer restrita ao servidor. |
| `/etc/ssl/certs/sistema-financeiro.crt` | arquivo | Certificado usado pelo nginx para `sistema-financeiro.net`. |

## Regras

- O deploy normal parte da homologação local validada e é acionado pelo alias `deploysf`; SSH manual permanece disponível para diagnóstico e rollback.
- O banco SQLite e demais arquivos de `data/` não devem ser alterados por este documento.
- Antes de copiar código novo, o serviço deve estar parado.
- O backup anterior em `/mnt/endor/Sistema Financeiro_backup` pode ser removido somente depois de confirmar que `/opt/sistema-financeiro` existe.
- O backup deve ser criado antes de qualquer alteração em `/opt/sistema-financeiro`.
- A atualização recomendada deve preservar `/opt/sistema-financeiro/data/`.
- A atualização remota deve preservar também `/opt/sistema-financeiro/secure/` e `/opt/sistema-financeiro/.venv/`, ainda que existam diretórios homônimos no staging.
- A cópia com `cp -r "/mnt/endor/Sistema Financeiro/"* /opt/sistema-financeiro/` é aceita como procedimento simples somente quando a origem não contém `data/` e quando não há necessidade de remover arquivos obsoletos.
- Para reduzir regressões, o procedimento recomendado usa `rsync` com `--delete` e exclusões explícitas de dados/runtime.
- O script macOS deve propagar falhas de `rsync`, SSH e atualização remota, anunciando sucesso somente depois de confirmar o serviço ativo.
- Se uma falha ocorrer depois da interrupção do serviço, o script remoto deve tentar iniciá-lo novamente antes de encerrar com erro.
- Após a cópia, `/opt/sistema-financeiro` deve pertencer a `sistema:sistema`.
- Após iniciar o serviço, os logs devem ser acompanhados até confirmar inicialização sem erro crítico.
- Rollback deve restaurar o backup inteiro e aplicar novamente `chown -R sistema:sistema`.
- Renovação de certificado SSL deve ser procedimento separado do deploy comum.

## API e dados

Não há rotas de API nem tabelas novas.

Serviços e arquivos operacionais afetados:

| Item | Ação |
|---|---|
| `sistema-financeiro.service` | parar, iniciar e monitorar. |
| `/opt/sistema-financeiro` | substituir código da aplicação. |
| `/mnt/endor/Sistema Financeiro_backup` | criar backup da versão anterior. |
| `/etc/ssl/private/sistema-financeiro.key` | renovar somente quando o certificado expirar. |
| `/etc/ssl/certs/sistema-financeiro.crt` | renovar e distribuir para clientes confiáveis quando necessário. |

## Procedimento

### 1. Conectar no servidor

Executar na máquina de administração:

```bash
ssh sansquer@192.168.1.212
```

### 2. Pré-validação no servidor

Executar no servidor antes de parar o serviço:

```bash
test -d /opt/sistema-financeiro
test -d "/mnt/endor/Sistema Financeiro"
sudo systemctl status sistema-financeiro.service --no-pager
```

Melhoria recomendada: validar sintaxe antes da troca, usando a nova versão em Endor:

```bash
cd "/mnt/endor/Sistema Financeiro"
python3 -m py_compile app.py financeiro/*.py
```

### 3. Interromper serviço e criar backup

Executar no servidor via SSH:

```bash
# A. Interrompe o serviço para liberar os arquivos
sudo systemctl stop sistema-financeiro.service

# B. Remove o backup anterior e gera uma nova cópia de segurança no Endor
sudo rm -rf "/mnt/endor/Sistema Financeiro_backup"
sudo cp -r /opt/sistema-financeiro "/mnt/endor/Sistema Financeiro_backup"
```

Validação recomendada do backup:

```bash
test -d "/mnt/endor/Sistema Financeiro_backup"
test -f "/mnt/endor/Sistema Financeiro_backup/app.py"
test -d "/mnt/endor/Sistema Financeiro_backup/financeiro"
test -d "/mnt/endor/Sistema Financeiro_backup/web"
```

### 4. Atualizar produção e ajustar permissões

Executar no servidor via SSH.

Procedimento simples informado:

```bash
# A. Copia o conteúdo novo do Endor para a pasta de produção em /opt
sudo cp -r "/mnt/endor/Sistema Financeiro/"* /opt/sistema-financeiro/

# B. Restabelece o usuário 'sistema' como proprietário para evitar erros de escrita
sudo chown -R sistema:sistema /opt/sistema-financeiro
```

Procedimento recomendado quando `rsync` estiver disponível:

```bash
sudo rsync -a --delete \
  --exclude 'data/' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude '.DS_Store' \
  --exclude 'server.log' \
  "/mnt/endor/Sistema Financeiro/" \
  /opt/sistema-financeiro/

sudo chown -R sistema:sistema /opt/sistema-financeiro
```

Motivo da melhoria: `rsync --delete` remove arquivos obsoletos que poderiam continuar ativos após o deploy, enquanto as exclusões preservam dados de runtime e evitam copiar caches/metadados.

### 5. Reiniciar serviço e validar status

Executar no servidor via SSH:

```bash
# A. Inicializa a nova versão do sistema
sudo systemctl start sistema-financeiro.service

# B. Monitora os logs em tempo real (Pressione Ctrl+C para sair)
sudo journalctl -u sistema-financeiro -f
```

Validações recomendadas em outra sessão SSH:

```bash
sudo systemctl status sistema-financeiro.service --no-pager
curl -kI https://sistema-financeiro.net:8030/
curl -kI https://192.168.1.212:8030/
```

### 6. Rollback em falha crítica

Caso o passo anterior aponte falhas críticas na nova versão, executar no servidor:

```bash
sudo systemctl stop sistema-financeiro.service
sudo rm -rf /opt/sistema-financeiro/*
sudo cp -r "/mnt/endor/Sistema Financeiro_backup/"* /opt/sistema-financeiro/
sudo chown -R sistema:sistema /opt/sistema-financeiro
sudo systemctl start sistema-financeiro.service
```

Validação pós-rollback:

```bash
sudo systemctl status sistema-financeiro.service --no-pager
sudo journalctl -u sistema-financeiro -n 100 --no-pager
```

## Certificado SSL

### Renovação ou geração

Se o certificado expirar, executar no servidor:

```bash
sudo openssl req -x509 -newkey rsa:2048 \
  -keyout /etc/ssl/private/sistema-financeiro.key \
  -out /etc/ssl/certs/sistema-financeiro.crt \
  -days 365 \
  -nodes \
  -subj "/CN=sistema-financeiro.net" \
  -addext "subjectAltName = DNS:sistema-financeiro.net"

sudo systemctl reload nginx
```

Melhoria recomendada: incluir também o IP no SAN quando clientes acessarem por IP:

```bash
sudo openssl req -x509 -newkey rsa:2048 \
  -keyout /etc/ssl/private/sistema-financeiro.key \
  -out /etc/ssl/certs/sistema-financeiro.crt \
  -days 365 \
  -nodes \
  -subj "/CN=sistema-financeiro.net" \
  -addext "subjectAltName = DNS:sistema-financeiro.net,IP:192.168.1.212"

sudo systemctl reload nginx
```

### Confiança do certificado no cliente

1. Copiar `/etc/ssl/certs/sistema-financeiro.crt` do servidor para a máquina cliente.
2. No macOS, abrir **Acesso às Chaves**.
3. Arrastar o arquivo para **Início de Sessão > Certificados**.
4. Dar duplo clique no certificado.
5. Abrir **Confiar**.
6. Alterar para **Sempre Confiar**.

## Critérios de aceite

- Dado o servidor conectado via SSH, quando a pré-validação é executada, então `/opt/sistema-financeiro` e `/mnt/endor/Sistema Financeiro` existem.
- Dado o serviço em execução, quando `sudo systemctl stop sistema-financeiro.service` é executado, então a aplicação deixa de atender antes da cópia.
- Dado o backup criado, quando inspecionado, então contém `app.py`, `financeiro/` e `web/`.
- Dado o procedimento recomendado com `rsync`, quando a atualização termina, então `/opt/sistema-financeiro/data/` permanece preservado.
- Dado que `data/`, `secure/` ou `.venv/` existam no staging, quando o deploy remoto é executado, então os diretórios homônimos da instalação permanecem inalterados.
- Dado erro depois de parar o serviço, quando o script remoto encerra, então ele tenta restabelecer o serviço e devolve falha ao chamador.
- Dado que a atualização remota terminou, quando `deploysf` anuncia sucesso, então o `systemd` confirmou `sistema-financeiro.service` ativo.
- Dado a nova versão copiada, quando `sudo chown -R sistema:sistema /opt/sistema-financeiro` é executado, então o usuário do serviço consegue escrever arquivos de runtime.
- Dado o serviço reiniciado, quando `journalctl -u sistema-financeiro -f` é monitorado, então não aparecem falhas críticas de inicialização.
- Dado falha crítica após deploy, quando o rollback é executado, então o backup volta para `/opt/sistema-financeiro` e o serviço inicia novamente.
- Dado certificado expirado, quando a renovação é executada, então o nginx recarrega sem reiniciar a aplicação Python.

## Fora de escopo

- Executar SSH automaticamente a partir desta spec.
- Alterar banco SQLite, logs, chaves SMTP ou dados de usuário.
- Criar pipeline CI/CD.
- Automatizar emissão de certificado por AC pública.
- Alterar configuração do nginx, exceto reload após renovação de certificado.

## Changelog

- `1.4` — 2026-09-06 — Removida a validação `sudo systemctl` duplicada no cliente; a confirmação permanece no script remoto autorizado e seu status é propagado pelo SSH.
- `1.3` — 2026-09-06 — Deploy macOS e remoto passam a compartilhar exclusões, usar sincronização limpa, propagar falhas e validar a recuperação/atividade do serviço.
- `1.2` — 2026-09-06 — Script remoto versionado em `adm/` passa a preservar explicitamente `data/`, `secure/` e `.venv/`, sem antecipar a remoção de arquivos obsoletos.
- `1.1` — 2026-09-06 — Registrado o fluxo real de promoção controlada entre repositório V2, homologação local, staging Endor e produção.
- `1.0` — 2026-07-07 — Spec criada para atualização manual do servidor, backup, deploy, rollback e renovação de certificado.

## Relacionados

- [[sdd]]
- [[templates/spec-template|Template de spec]]
- [[distribuição]]
- [[arquitetura]]
- [[seguranca-autenticacao]]
