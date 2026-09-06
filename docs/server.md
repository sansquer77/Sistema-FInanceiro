---
tipo: arquitetura
area: servidor
status: implementado
versao: 1.6
atualizado: 2026-09-06
relacionados:
  - "[[sdd]]"
  - "[[arquitetura]]"
  - "[[distribuição]]"
  - "[[specs/Update Server]]"
  - "[[specs/seguranca-autenticacao]]"
tags: [arquitetura, "area/servidor", deploy, nginx]
aliases: ["Servidor", "Server Setup", "Configuração do Servidor"]
---

# Configuração do Servidor

> [!info] Status
> **implementado** · área: `servidor` · atualizado em 2026-09-06 · relacionados: [[sdd]], [[arquitetura]], [[distribuição]], [[specs/Update Server]], [[specs/seguranca-autenticacao]]

Este documento descreve como instalar, configurar e manter o Sistema Financeiro rodando em um servidor Linux dedicado (`192.168.1.212`), acessível por `https://sistema-financeiro.net:8030`. Cobre variáveis de ambiente, systemd, Nginx com HTTPS, certificado SSL, configuração dos clientes e o processo `deploysf`.

Para o procedimento de atualização de versão em produção (backup, troca de código, rollback), veja [[specs/Update Server]].

---

## Visão geral da arquitetura de rede

```text
┌─────────────────────────┐
│  Dispositivo cliente    │
│  (navegador)            │
│  https://sistema-       │
│  financeiro.net:8030    │
└───────────┬─────────────┘
            │ TLS (porta 8030)
            ▼
┌─────────────────────────┐
│  Nginx (reverse proxy)  │
│  listen 8030 ssl        │
│  ssl_certificate *.crt  │
│  ssl_certificate_key    │
│  *.key                  │
└───────────┬─────────────┘
            │ HTTP (127.0.0.1:8010)
            ▼
┌─────────────────────────┐
│  Python backend         │
│  app.py                 │
│  ThreadingHTTPServer    │
│  HOST=127.0.0.1         │
│  PORT=8010              │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  SQLite                 │
│  data/finance.db        │
└─────────────────────────┘
```

O backend Python escuta apenas em `127.0.0.1:8010` (loopback) e nunca é exposto diretamente à rede. O Nginx termina TLS na porta `8030` e repassa as requisições ao backend via proxy reverso.

---

## 1. Pré-requisitos no servidor

| Requisito | Detalhes |
|---|---|
| Sistema operacional | Ubuntu Server (ou derivado Debian) |
| Python | 3.10+ (pacote `python3` do sistema) |
| Dependências Python | `python3-venv` e `cryptography==50.0.1` instalados em ambiente virtual dedicado |
| Nginx | Instalado via `apt install nginx` |
| OpenSSL | Para geração de certificado autoassinado |
| Usuário de serviço | `sistema:sistema` — dono de `/opt/sistema-financeiro` |
| Volume Endor | Montado em `/mnt/endor` para receber o código via `deploysf` |
| Acesso SSH | `sansquer@192.168.1.212` com `sudo` |

Criar o usuário de serviço (se ainda não existir):

```bash
sudo useradd -r -s /usr/sbin/nologin sistema
sudo mkdir -p /opt/sistema-financeiro
sudo chown -R sistema:sistema /opt/sistema-financeiro
```

### 1.1 Montar o volume Endor em `/mnt/endor`

Antes de configurar o `fstab`, identifique como o volume chega ao Linux:

```bash
findmnt -no SOURCE,FSTYPE,OPTIONS /mnt/endor
lsblk -f
```

Use **somente uma** das alternativas abaixo, conforme o resultado. Crie primeiro o ponto de montagem:

```bash
sudo mkdir -p /mnt/endor
```

#### Disco físico ou volume local

Localize o UUID com `lsblk -f` e acrescente ao `/etc/fstab`, substituindo os valores de exemplo:

```fstab
UUID=SEU-UUID /mnt/endor ext4 defaults,nofail 0 2
```

#### Compartilhamento SMB/CIFS

Instale o cliente e proteja as credenciais:

```bash
sudo apt update
sudo apt install -y cifs-utils
sudo install -m 600 /dev/null /root/.smbcredentials-endor
sudo nano /root/.smbcredentials-endor
```

Conteúdo do arquivo de credenciais:

```ini
username=USUARIO_DO_COMPARTILHAMENTO
password=SENHA_DO_COMPARTILHAMENTO
```

Entrada correspondente no `/etc/fstab`:

```fstab
//SERVIDOR/Endor /mnt/endor cifs credentials=/root/.smbcredentials-endor,vers=3.0,iocharset=utf8,_netdev,nofail,x-systemd.automount 0 0
```

#### Compartilhamento NFS

```bash
sudo apt update
sudo apt install -y nfs-common
```

Entrada correspondente no `/etc/fstab`:

```fstab
SERVIDOR:/CAMINHO/Endor /mnt/endor nfs defaults,_netdev,nofail,x-systemd.automount 0 0
```

Valide a configuração antes de depender dela:

```bash
sudo mount -a
findmnt /mnt/endor
test -d "/mnt/endor/Sistema Financeiro"
sudo -u sistema test -r "/mnt/endor/Sistema Financeiro/app.py"
sudo -u sistema test -w "/mnt/endor/Data_backup"
```

> [!important] Permissões do backup
> O usuário `sistema` precisa ler a origem de deploy e gravar em `/mnt/endor/Data_backup`. Em SMB/NFS, `chmod` local pode não bastar: as permissões também precisam ser concedidas no servidor do compartilhamento.

### 1.2 Primeira carga de código

O `deploysf` é um fluxo de **atualização**. No primeiro provisionamento, prepare a origem no Endor e inicialize explicitamente `/opt/sistema-financeiro`:

```bash
test -f "/mnt/endor/Sistema Financeiro/app.py"
test -d "/mnt/endor/Sistema Financeiro/financeiro"
test -d "/mnt/endor/Sistema Financeiro/web"

sudo mkdir -p /opt/sistema-financeiro
sudo rsync -a \
  --exclude 'data/' \
  --exclude 'secure/' \
  --exclude '.venv/' \
  --exclude '__pycache__/' \
  --exclude '.git/' \
  "/mnt/endor/Sistema Financeiro/" \
  /opt/sistema-financeiro/
sudo chown -R sistema:sistema /opt/sistema-financeiro
```

### 1.3 Dependências Python

O núcleo financeiro permanece majoritariamente na biblioteca padrão, mas backups `.sfbackup` exigem `cryptography`. No servidor fonte, use um ambiente virtual persistente e a mesma versão dos pacotes oficiais:

```bash
sudo apt update
sudo apt install -y python3 python3-venv
sudo -u sistema python3 -m venv /opt/sistema-financeiro/.venv
sudo -u sistema /opt/sistema-financeiro/.venv/bin/python -m pip install --upgrade pip
sudo -u sistema /opt/sistema-financeiro/.venv/bin/python -m pip install cryptography==50.0.1
sudo -u sistema /opt/sistema-financeiro/.venv/bin/python -c "import cryptography; print(cryptography.__version__)"
```

Não instale a dependência globalmente com `sudo pip`. O diretório `.venv/` deve ser preservado pelo deploy.

### 1.4 Primeira execução e diretório `data/`

Não é necessário criar o banco manualmente. Na primeira inicialização, o app cria `data/`, `data/finance.db`, aplica o schema corrente e configura o SQLite. A pré-condição é que `sistema:sistema` tenha permissão de escrita em `/opt/sistema-financeiro`:

```bash
sudo -u sistema test -w /opt/sistema-financeiro
```

Nunca copie um `data/` vazio por cima de uma instalação existente e nunca inclua `data/` na origem do deploy.

---

## 2. Variáveis de ambiente do backend

O backend lê as seguintes variáveis em tempo de inicialização (definidas no arquivo `.service` do systemd):

| Variável | Valor no servidor | Descrição |
|---|---|---|
| `APP_HOST` | `127.0.0.1` | Interface de escuta. Loopback porque o Nginx está na frente. |
| `APP_PORT` | `8010` | Porta interna do backend. |
| `APP_URL` | `https://sistema-financeiro.net:8030` | URL pública completa usada pelo app para gerar links, cookies e validações. |
| `APP_ALLOWED_HOSTS` | `sistema-financeiro.net,sistema-financeiro.net:8030,192.168.1.212,192.168.1.212:8030` | Hosts aceitos no header `Host` (CSV). Entradas sem porta também aceitam `APP_PORT`. |
| `APP_ALLOWED_ORIGINS` | `https://sistema-financeiro.net:8030,http://sistema-financeiro.net:8030,https://192.168.1.212:8030,http://192.168.1.212:8030` | Origens aceitas para requisições de mutação (CSV). |
| `SISTEMA_FINANCEIRO_CONFIG_KEY_PATH` | `/etc/sistema-financeiro/config.key` | Caminho persistente da chave mestra de segredos criptografados. |

> [!important] APP_HOST=127.0.0.1
> O backend nunca deve escutar em `0.0.0.0` no servidor — toda exposição à rede passa pelo Nginx com TLS. Usar `0.0.0.0` sem proxy reverso exporia o app em HTTP puro.

### Diretório da chave mestra

```bash
sudo mkdir -p /etc/sistema-financeiro
sudo chmod 700 /etc/sistema-financeiro
sudo chown sistema:sistema /etc/sistema-financeiro
```

Se a chave já existir em `secure/config.key` dentro do código, copie-a:

```bash
sudo cp /opt/sistema-financeiro/secure/config.key /etc/sistema-financeiro/config.key
sudo chmod 600 /etc/sistema-financeiro/config.key
sudo chown sistema:sistema /etc/sistema-financeiro/config.key
```

---

## 3. Serviço systemd

Criar o arquivo `/etc/systemd/system/sistema-financeiro.service`:

```ini
[Unit]
Description=Sistema Financeiro
Wants=network-online.target
After=network-online.target
RequiresMountsFor=/mnt/endor

[Service]
Type=simple
User=sistema
Group=sistema
WorkingDirectory=/opt/sistema-financeiro

Environment=APP_HOST=127.0.0.1
Environment=APP_PORT=8010
Environment=APP_URL=https://sistema-financeiro.net:8030
Environment=APP_ALLOWED_HOSTS=sistema-financeiro.net,sistema-financeiro.net:8030,192.168.1.212,192.168.1.212:8030
Environment=APP_ALLOWED_ORIGINS=https://sistema-financeiro.net:8030,http://sistema-financeiro.net:8030,https://192.168.1.212:8030,http://192.168.1.212:8030
Environment=SISTEMA_FINANCEIRO_CONFIG_KEY_PATH=/etc/sistema-financeiro/config.key

ExecStart=/opt/sistema-financeiro/.venv/bin/python /opt/sistema-financeiro/app.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Ativar e acompanhar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro.service
sudo journalctl -u sistema-financeiro -f
```

### Comandos operacionais do serviço

| Ação | Comando |
|---|---|
| Verificar status | `sudo systemctl status sistema-financeiro.service --no-pager` |
| Parar | `sudo systemctl stop sistema-financeiro.service` |
| Iniciar | `sudo systemctl start sistema-financeiro.service` |
| Reiniciar | `sudo systemctl restart sistema-financeiro.service` |
| Logs em tempo real | `sudo journalctl -u sistema-financeiro -f` |
| Últimas 100 linhas de log | `sudo journalctl -u sistema-financeiro -n 100 --no-pager` |

---

## 4. Nginx — proxy reverso com HTTPS

Criar o arquivo `/etc/nginx/sites-available/sistema-financeiro`:

```nginx
server {
    listen 8030 ssl;
    server_name sistema-financeiro.net 192.168.1.212;

    ssl_certificate /etc/ssl/certs/sistema-financeiro.crt;
    ssl_certificate_key /etc/ssl/private/sistema-financeiro.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:8010;

        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }
}
```

Ativar o site e testar a configuração:

```bash
sudo ln -sf /etc/nginx/sites-available/sistema-financeiro /etc/nginx/sites-enabled/sistema-financeiro
sudo nginx -t
sudo systemctl reload nginx
```

### Firewall

Com o backend restrito a `127.0.0.1:8010`, libere somente a porta HTTPS do Nginx. Para uma rede doméstica `192.168.1.0/24` usando UFW:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8030 proto tcp
sudo ufw status
```

Não libere `8010/tcp`: essa porta é interna entre Nginx e Python. Se o servidor precisar ser acessível fora da LAN, a regra de firewall e a exposição no roteador exigem uma avaliação de segurança própria.

### O que cada diretiva faz

| Diretiva | Propósito |
|---|---|
| `listen 8030 ssl` | Escuta na porta `8030` com TLS habilitado. |
| `server_name` | Aceita conexões pelo domínio e pelo IP direto. |
| `ssl_certificate` / `ssl_certificate_key` | Certificado e chave privada para o TLS. |
| `ssl_protocols` | Restringe a TLSv1.2 e TLSv1.3 (desabilita versões inseguras). |
| `proxy_pass` | Repassa para o backend Python em loopback. |
| `proxy_set_header Host $http_host` | Preserva o `Host` original para as validações do backend (`APP_ALLOWED_HOSTS`). |
| `proxy_set_header X-Forwarded-Proto` | Informa ao backend que o acesso externo é HTTPS. |
| `proxy_read_timeout 90` | Timeout generoso para operações longas (importações, backups). |

---

## 5. Certificado SSL

### Gerar certificado autoassinado

Para uso em rede local doméstica, um certificado autoassinado é suficiente:

```bash
sudo openssl req -x509 -newkey rsa:2048 \
  -keyout /etc/ssl/private/sistema-financeiro.key \
  -out /etc/ssl/certs/sistema-financeiro.crt \
  -days 365 \
  -nodes \
  -subj "/CN=sistema-financeiro.net" \
  -addext "subjectAltName = DNS:sistema-financeiro.net,IP:192.168.1.212"
```

Após gerar ou renovar, recarregar o Nginx:

```bash
sudo systemctl reload nginx
```

> [!note] Certificado autoassinado
> O navegador pedirá uma confirmação de segurança na primeira abertura de cada dispositivo cliente. Isso é esperado em servidores domésticos — basta confirmar para prosseguir.

### Confiar no certificado em um Mac cliente

1. Copiar `/etc/ssl/certs/sistema-financeiro.crt` do servidor para a máquina cliente.
2. Abrir **Acesso às Chaves** (Keychain Access).
3. Arrastar o arquivo para **Início de Sessão > Certificados**.
4. Dar duplo clique no certificado importado.
5. Abrir a seção **Confiar**.
6. Alterar para **Sempre Confiar**.

### Verificar validade do certificado

```bash
openssl x509 -in /etc/ssl/certs/sistema-financeiro.crt -noout -dates
```

---

## 6. Configuração dos dispositivos clientes

Para acessar o servidor pelo domínio `sistema-financeiro.net` em vez do IP puro, cada dispositivo precisa mapear o domínio para `192.168.1.212` no seu arquivo `hosts`.

### macOS / Linux

O pacote macOS inclui um script pronto:

```bash
chmod +x configurar_mac.sh
sudo ./configurar_mac.sh
```

Manualmente:

```bash
echo "192.168.1.212 sistema-financeiro.net" | sudo tee -a /etc/hosts
```

### Windows

O pacote Windows inclui `configurar_windows.ps1`:

1. Clique com o botão direito em `configurar_windows.ps1`.
2. Escolha **Executar com o PowerShell**.
3. Confirme a execução como Administrador.

Após configurado, acessar de qualquer dispositivo:

```text
https://sistema-financeiro.net:8030
```

---

## 7. deploysf — deploy do Mac para o servidor

O `deploysf` promove uma versão que já passou pela homologação local; o repositório de desenvolvimento não é enviado diretamente ao servidor.

```text
Repositório V2 (desenvolvimento)
  → /Users/sansquer/Documents/Sistema Financeiro (homologação validada)
  → /Volumes/Endor/Sistema Financeiro (staging operacional)
  → /mnt/endor/Sistema Financeiro (mesmo staging visto pelo Linux)
  → /opt/sistema-financeiro (produção)
```

Essa separação reduz o risco de promover um desenvolvimento ainda não validado e mantém no Endor uma origem operacional para reinstalação ou rollback simples.

### Onde está definido

| Item | Caminho |
|---|---|
| Alias | `~/.zshrc` → `alias deploysf='~/Scripts/deploy.sh'` |
| Script | `~/Scripts/deploy.sh` |
| Fonte versionada | `adm/deploy-macos.sh` |

### O que o script faz

```text
1. Verifica se /Volumes/Endor está montado (volume compartilhado com o servidor).
2. Sincroniza com rsync --delete a homologação local para /Volumes/Endor/Sistema Financeiro.
3. Conecta via SSH em sansquer@192.168.1.212 e executa
   sudo /opt/scripts/atualiza-financeiro.sh no servidor.
```

### Origem e destino

| Etapa | Origem | Destino |
|---|---|---|
| Sincronização local → Endor | `/Users/sansquer/Documents/Sistema Financeiro` | `/Volumes/Endor/Sistema Financeiro` |
| Atualização no servidor | `/mnt/endor/Sistema Financeiro` (mesmo volume visto pelo Linux) | `/opt/sistema-financeiro` |

### Script completo (`~/Scripts/deploy.sh`)

```bash
#!/bin/bash

SRC="/Users/sansquer/Documents/Sistema Financeiro"
DEST="/Volumes/Endor/Sistema Financeiro"

echo "Verificando se o volume do servidor (/Volumes/Endor) está montado..."
if [ ! -d "/Volumes/Endor" ]; then
    echo "Erro: O volume /Volumes/Endor não está montado. Abortando deploy."
    exit 1
fi

echo "Sincronizando arquivos do MacOS para o servidor..."
rsync -avh --progress --delete "$SRC/" "$DEST/"

if [ $? -ne 0 ]; then
    echo "Erro durante a cópia dos arquivos. Deploy cancelado."
    exit 1
fi

echo "Iniciando atualização no servidor..."
ssh sansquer@192.168.1.212 'sudo /opt/scripts/atualiza-financeiro.sh'

echo "Deploy concluído com sucesso!"
```

O script macOS versionado aplica `--delete` para retirar arquivos obsoletos do staging e exclui `data/`, `secure/`, ambientes virtuais, caches e artefatos de build. Com `set -Eeuo pipefail`, falhas de sincronização ou SSH interrompem o fluxo. A confirmação do serviço ocorre dentro do script remoto — o único comando autorizado por `sudo` — e seu status é propagado ao Mac pela mesma sessão SSH.

Para atualizar a cópia executada pelo alias sem alterar a rotina de uso:

```bash
cp "/Users/sansquer/Documents/GitHub/Sistema FInanceiro - v2.0/adm/deploy-macos.sh" \
  "$HOME/Scripts/deploy.sh"
chmod 755 "$HOME/Scripts/deploy.sh"
bash -n "$HOME/Scripts/deploy.sh"
```

### Script no servidor (`/opt/scripts/atualiza-financeiro.sh`)

Este script é executado remotamente via SSH pelo `deploysf`. Ele é responsável por:

1. Parar o serviço `sistema-financeiro.service`.
2. Copiar o conteúdo de `/mnt/endor/Sistema Financeiro` sobre `/opt/sistema-financeiro`.
3. Ajustar permissões para `sistema:sistema`.
4. Reiniciar o serviço.

Instale o script abaixo como `root`, sem permitir edição pelo usuário usado no SSH:

```bash
sudo mkdir -p /opt/scripts
sudo nano /opt/scripts/atualiza-financeiro.sh
```

O script vigente antes deste endurecimento foi conferido em 2026-09-06 com SHA-256 `3af76845c2a4a431c583645039f47234347171b7e23786de3f48004da10d28f5`. Sua substituição versionada está em `adm/atualiza-financeiro.sh` e preserva os diretórios de runtime sem ainda remover arquivos obsoletos.

Conteúdo a instalar no servidor:

```bash
sudo install -o root -g root -m 755 \
  "/mnt/endor/Sistema Financeiro/adm/atualiza-financeiro.sh" \
  /opt/scripts/atualiza-financeiro.sh
```

Confira as permissões e o conteúdo instalado:

```bash
sudo ls -l /opt/scripts/atualiza-financeiro.sh
sudo bash -n /opt/scripts/atualiza-financeiro.sh
```

O script versionado valida a origem antes de parar o serviço, mantém e valida o rollback operacional e usa `rsync --delete` com exclusões equivalentes às do Mac. `data/`, `secure/` e `.venv/` permanecem protegidos, enquanto código obsoleto é removido. Uma armadilha de erro tenta restabelecer o serviço quando uma falha ocorre depois da parada; a conclusão exige confirmação de atividade pelo `systemd`.

#### Atualização manual do script remoto

O `deploysf` atual publica `adm/atualiza-financeiro.sh` junto com o restante do código, mas não o instala automaticamente em `/opt/scripts/`. Portanto:

- a instalação abaixo deve ser feita uma vez para ativar a versão protegida;
- deve ser repetida sempre que `adm/atualiza-financeiro.sh` mudar;
- deploys comuns da aplicação continuam usando apenas o fluxo habitual de copiar para a homologação e executar `deploysf`.

Para evitar que o deploy anterior seja executado antes da proteção, a primeira instalação pode ser feita diretamente do Mac:

```bash
scp \
  "/Users/sansquer/Documents/GitHub/Sistema FInanceiro - v2.0/adm/atualiza-financeiro.sh" \
  sansquer@192.168.1.212:/tmp/atualiza-financeiro.sh

ssh sansquer@192.168.1.212
```

No servidor:

```bash
sudo bash -n /tmp/atualiza-financeiro.sh
sudo install -o root -g root -m 755 \
  /tmp/atualiza-financeiro.sh \
  /opt/scripts/atualiza-financeiro.sh
rm -f /tmp/atualiza-financeiro.sh
sudo grep -A4 "rsync -a" /opt/scripts/atualiza-financeiro.sh
```

Nas atualizações futuras do script, depois que a versão nova já estiver no Endor, também é possível usar o comando documentado acima com `sudo install` a partir de `/mnt/endor/Sistema Financeiro/adm/atualiza-financeiro.sh`.

Para o procedimento completo de atualização, backup e rollback, consulte [[specs/Update Server]].

### Como usar

Na máquina de desenvolvimento (macOS), basta executar:

```bash
deploysf
```

> [!warning] Pré-condições
> - O volume `/Volumes/Endor` deve estar montado (compartilhamento de rede com o servidor).
> - A chave SSH para `sansquer@192.168.1.212` deve estar configurada.
> - O código em `/Users/sansquer/Documents/Sistema Financeiro` deve ter sido promovido do repositório V2 somente depois dos testes e da validação funcional local.

### Autenticação SSH sem senha

Na máquina de desenvolvimento, crie uma chave exclusiva para deploy, se ainda não existir:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/sistema_financeiro_deploy -C "deploy sistema-financeiro"
ssh-copy-id -i ~/.ssh/sistema_financeiro_deploy.pub sansquer@192.168.1.212
```

Adicione ao `~/.ssh/config`:

```sshconfig
Host sistema-financeiro-server
  HostName 192.168.1.212
  User sansquer
  IdentityFile ~/.ssh/sistema_financeiro_deploy
  IdentitiesOnly yes
```

Teste antes de usar o alias:

```bash
ssh sistema-financeiro-server 'echo SSH OK'
```

Para o comando remoto não pedir senha de `sudo`, crie no servidor, com `sudo visudo -f /etc/sudoers.d/sistema-financeiro-deploy`:

```sudoers
sansquer ALL=(root) NOPASSWD: /opt/scripts/atualiza-financeiro.sh
```

Proteja e valide a regra:

```bash
sudo chmod 440 /etc/sudoers.d/sistema-financeiro-deploy
sudo visudo -cf /etc/sudoers.d/sistema-financeiro-deploy
```

O `deploy.sh` pode então usar:

```bash
ssh sistema-financeiro-server 'sudo /opt/scripts/atualiza-financeiro.sh'
```

---

## 8. Estrutura de diretórios no servidor

```text
/opt/sistema-financeiro/          ← pasta de produção
├── app.py                        ← entry point do backend
├── financeiro/                   ← núcleo Python (regras, banco, rotas)
├── web/                          ← frontend (HTML, CSS, JS, assets)
├── secure/                       ← config.key (alternativa ao /etc/)
├── adm/                          ← scripts administrativos
└── data/                         ← runtime (banco, logs) — nunca sobrescrito
    └── finance.db                ← banco SQLite

/mnt/endor/Sistema Financeiro/    ← nova versão (via deploysf)
/mnt/endor/Sistema Financeiro_backup/ ← backup da versão anterior

/etc/sistema-financeiro/
└── config.key                    ← chave mestra de segredos

/etc/systemd/system/
└── sistema-financeiro.service    ← unit file do systemd

/etc/nginx/sites-available/
└── sistema-financeiro            ← config do Nginx

/etc/ssl/certs/
└── sistema-financeiro.crt        ← certificado SSL

/etc/ssl/private/
└── sistema-financeiro.key        ← chave privada SSL

/opt/scripts/
└── atualiza-financeiro.sh        ← script de atualização chamado pelo deploysf
```

---

## 9. URLs aceitas pelo backend

O backend aceita por padrão as seguintes combinações de Host e Origin:

| URL | Contexto |
|---|---|
| `http://sistema-financeiro.localhost:8010` | Execução local no desktop (modo padrão). |
| `https://sistema-financeiro.net:8030` | Servidor via domínio (HTTPS pelo Nginx). |
| `http://sistema-financeiro.net:8030` | Fallback HTTP pelo domínio. |
| `https://192.168.1.212:8030` | Servidor via IP direto (HTTPS). |
| `http://192.168.1.212:8030` | Fallback HTTP pelo IP. |

> [!tip] Customização
> Para usar domínio, IP ou porta diferentes, ajuste `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS` no `.service` e reinicie o serviço.

---

## 10. Verificação pós-configuração

Executar no servidor para confirmar que tudo está operacional:

```bash
# Serviço Python
sudo systemctl status sistema-financeiro.service --no-pager

# Nginx
sudo nginx -t
sudo systemctl status nginx --no-pager

# Acesso pelo domínio
curl -kI https://sistema-financeiro.net:8030/

# Acesso pelo IP
curl -kI https://192.168.1.212:8030/

# Logs do app
sudo journalctl -u sistema-financeiro -n 20 --no-pager

# Validade do certificado
openssl x509 -in /etc/ssl/certs/sistema-financeiro.crt -noout -dates
```

---

## 11. Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| `deploysf` falha com "volume não montado" | `/Volumes/Endor` não está acessível no Mac | Montar o compartilhamento de rede com o servidor. |
| `deploysf` falha no SSH | Chave SSH não configurada ou servidor fora da rede | Verificar `ssh sansquer@192.168.1.212` manualmente. |
| `/mnt/endor` desaparece após reiniciar | Montagem não persistida ou rede indisponível no boot | Validar a entrada no `/etc/fstab`, `network-online.target` e `findmnt /mnt/endor`. |
| Backup rejeita `/mnt/endor/Data_backup` | Usuário `sistema` não consegue gravar no volume | Executar `sudo -u sistema test -w /mnt/endor/Data_backup` e corrigir permissões no disco ou servidor SMB/NFS. |
| `ModuleNotFoundError: cryptography` | Serviço usa o Python do sistema ou venv incompleto | Criar `.venv`, instalar `cryptography==50.0.1` e usar o Python da venv no `ExecStart`. |
| Serviço não inicia | Erro de sintaxe no código Python ou dependência faltando | `sudo journalctl -u sistema-financeiro -n 50 --no-pager` para ver o erro. |
| Nginx retorna 502 Bad Gateway | Backend não está rodando ou escutando na porta errada | Verificar que `sistema-financeiro.service` está ativo e `APP_PORT=8010`. |
| Navegador bloqueia acesso pelo domínio | `hosts` não configurado no dispositivo cliente | Rodar `configurar_mac.sh` (macOS/Linux) ou `configurar_windows.ps1` (Windows). |
| Aviso de certificado inválido | Certificado autoassinado | Esperado em servidor doméstico — confirmar exceção no navegador, ou instalar como confiável no Keychain. |
| App rejeita requisição (403) | `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS` sem a URL usada | Confirmar que domínio e porta estão listados em ambas as variáveis no `.service`. |
| Dados perdidos após atualização | `data/` sobrescrito pelo deploy | Garantir que `rsync --exclude 'data/'` está sendo usado; restaurar do backup em `/mnt/endor/Sistema Financeiro_backup`. |
| Certificado expirado | Validade de 365 dias atingida | Regenerar com `openssl` e recarregar Nginx (ver seção 5). |

---

## Changelog

- `1.6` — 2026-09-06 — Eliminada a segunda chamada privilegiada de validação no cliente; o script remoto confirma o serviço e devolve o resultado ao `deploysf`.
- `1.5` — 2026-09-06 — Scripts Mac e Linux passam a compartilhar exclusões, remover código obsoleto, propagar falhas e confirmar o serviço ativo; documentada a instalação da fonte versionada do `deploysf`.
- `1.4` — 2026-09-06 — Explicitada a instalação manual inicial e recorrente do script remoto versionado, sem alterar o fluxo cotidiano do `deploysf`.
- `1.3` — 2026-09-06 — Script remoto passa a ser versionado em `adm/` e preserva explicitamente `data/`, `secure/` e `.venv/` durante a promoção para produção.
- `1.2` — 2026-09-06 — Documentado o pipeline real repositório V2 → homologação → Endor → produção e substituído o modelo presumido pelo conteúdo e hash do script remoto vigente.
- `1.1` — 2026-09-06 — Fechadas as lacunas operacionais: montagem persistente do Endor para disco/SMB/NFS, bootstrap inicial, `data/` automático, venv com `cryptography`, firewall restrito à LAN, script completo de atualização e chave SSH dedicada com sudo limitado.
- `1.0` — 2026-09-06 — Documento criado consolidando a configuração do servidor Linux: variáveis de ambiente, systemd, Nginx com HTTPS, certificado SSL, configuração dos clientes e fluxo completo do `deploysf`.

## Relacionados

- [[sdd]]
- [[arquitetura]]
- [[distribuição]]
- [[specs/Update Server]]
- [[specs/seguranca-autenticacao]]
