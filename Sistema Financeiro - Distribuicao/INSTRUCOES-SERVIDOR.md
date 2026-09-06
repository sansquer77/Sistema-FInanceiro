# Sistema Financeiro — Configuração de servidor Linux

Este guia é destinado a usuários avançados que desejam manter uma instalação central do Sistema Financeiro em um servidor Linux sempre ligado. Os demais dispositivos acessam o app pelo navegador; o banco SQLite permanece no servidor.

> Esta configuração exige familiaridade com Linux, terminal, permissões, DNS e HTTPS. Antes de expor o app fora de uma rede confiável, avalie firewall, certificado público, atualizações do sistema e controles adicionais de acesso.

## 1. Arquitetura recomendada

```text
Navegador
  → HTTPS :443 (ou outra porta escolhida)
  → Nginx
  → HTTP 127.0.0.1:8010
  → Sistema Financeiro
  → SQLite em /var/lib/sistema-financeiro/data/finance.db
```

O backend deve escutar somente em `127.0.0.1`. O Nginx é a única camada exposta à rede e encerra a conexão TLS.

## 2. Preparar o servidor

Os exemplos usam o usuário de serviço `sistema-financeiro` e podem ser adaptados ao Linux utilizado.

```bash
sudo useradd --system --home /var/lib/sistema-financeiro \
  --create-home --shell /usr/sbin/nologin sistema-financeiro

sudo mkdir -p \
  /opt/sistema-financeiro \
  /var/lib/sistema-financeiro/data \
  /etc/sistema-financeiro

sudo chown -R sistema-financeiro:sistema-financeiro \
  /opt/sistema-financeiro \
  /var/lib/sistema-financeiro \
  /etc/sistema-financeiro

sudo chmod 700 /var/lib/sistema-financeiro /etc/sistema-financeiro
```

Instale os componentes operacionais:

```bash
sudo apt update
sudo apt install -y nginx rsync ca-certificates
```

O pacote Linux já contém o runtime da aplicação; Python não precisa ser instalado para executá-lo.

## 3. Enviar o runtime ao servidor

Extraia o pacote `Linux Ubuntu - X.Y.Z.zip`. A pasta que contém o executável é `Linux/Aplicativo/SistemaFinanceiro`.

### A partir de macOS ou Linux

Substitua `USUARIO_SSH` e `SERVIDOR`:

```bash
rsync -av --delete \
  "Linux/Aplicativo/SistemaFinanceiro/" \
  USUARIO_SSH@SERVIDOR:/tmp/sistema-financeiro-runtime/
```

### A partir do Windows (PowerShell)

Com o cliente OpenSSH instalado:

```powershell
scp -r ".\Linux\Aplicativo\SistemaFinanceiro" `
  "USUARIO_SSH@SERVIDOR:/tmp/sistema-financeiro-runtime"
```

### Instalar no servidor

```bash
ssh USUARIO_SSH@SERVIDOR

sudo rsync -a --delete \
  /tmp/sistema-financeiro-runtime/ \
  /opt/sistema-financeiro/

sudo chown -R sistema-financeiro:sistema-financeiro /opt/sistema-financeiro
sudo chmod 755 /opt/sistema-financeiro/SistemaFinanceiro
```

Dados, chaves e backups ficam fora de `/opt/sistema-financeiro`; assim, uma atualização do runtime não os remove.

## 4. Configurar o systemd

Crie `/etc/systemd/system/sistema-financeiro.service`:

```ini
[Unit]
Description=Sistema Financeiro
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=sistema-financeiro
Group=sistema-financeiro
WorkingDirectory=/opt/sistema-financeiro

Environment=APP_HOST=127.0.0.1
Environment=APP_PORT=8010
Environment=APP_URL=https://financas.exemplo.com
Environment=APP_ALLOWED_HOSTS=financas.exemplo.com
Environment=APP_ALLOWED_ORIGINS=https://financas.exemplo.com
Environment=SISTEMA_FINANCEIRO_DATA_DIR=/var/lib/sistema-financeiro/data
Environment=SISTEMA_FINANCEIRO_CONFIG_KEY_PATH=/etc/sistema-financeiro/config.key

ExecStart=/opt/sistema-financeiro/SistemaFinanceiro
Restart=on-failure
RestartSec=5s

# Endurecimento compatível com escrita apenas nos diretórios de runtime.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/sistema-financeiro /etc/sistema-financeiro

[Install]
WantedBy=multi-user.target
```

Troque `financas.exemplo.com` pelo domínio real. Se usar uma porta externa diferente de `443`, inclua-a em `APP_URL`, `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`.

Ative o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro.service
sudo systemctl status sistema-financeiro.service --no-pager
```

Na primeira inicialização, o app cria o banco e a estrutura necessária no diretório de dados configurado.

## 5. Configurar Nginx e HTTPS

Crie `/etc/nginx/sites-available/sistema-financeiro`:

```nginx
server {
    listen 443 ssl;
    server_name financas.exemplo.com;

    ssl_certificate /CAMINHO/DO/CERTIFICADO.crt;
    ssl_certificate_key /CAMINHO/DA/CHAVE.key;
    ssl_protocols TLSv1.2 TLSv1.3;

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

Use um certificado emitido por uma autoridade confiável sempre que o servidor puder ser acessado pela internet. Para uma rede estritamente privada, uma autoridade interna também pode ser usada, desde que seu certificado seja instalado nos clientes.

```bash
sudo ln -s /etc/nginx/sites-available/sistema-financeiro \
  /etc/nginx/sites-enabled/sistema-financeiro
sudo nginx -t
sudo systemctl reload nginx
```

Libere somente a porta HTTPS no firewall. Não exponha a porta interna `8010`:

```bash
sudo ufw allow 443/tcp
sudo ufw status
```

## 6. Atualizar com segurança

Antes de substituir o runtime:

1. gere e valide um backup `.sfbackup` pelo próprio app;
2. mantenha uma cópia operacional do runtime anterior;
3. envie a versão nova para um diretório temporário;
4. pare o serviço somente depois de validar a nova origem;
5. substitua `/opt/sistema-financeiro` com `rsync --delete`;
6. reinicie e confirme o estado `active`.

Exemplo no servidor:

```bash
test -x /tmp/sistema-financeiro-runtime/SistemaFinanceiro
sudo systemctl stop sistema-financeiro.service

sudo mkdir -p /opt/sistema-financeiro-rollback
sudo rsync -a --delete \
  /opt/sistema-financeiro/ \
  /opt/sistema-financeiro-rollback/

sudo rsync -a --delete \
  /tmp/sistema-financeiro-runtime/ \
  /opt/sistema-financeiro/

sudo chown -R sistema-financeiro:sistema-financeiro /opt/sistema-financeiro
sudo systemctl start sistema-financeiro.service
sudo systemctl is-active --quiet sistema-financeiro.service
```

Em falha, restaure `/opt/sistema-financeiro-rollback/` e reinicie o serviço. O rollback do runtime não substitui o backup dos dados.

## 7. Verificação e diagnóstico

```bash
sudo systemctl status sistema-financeiro.service --no-pager
sudo journalctl -u sistema-financeiro -n 100 --no-pager
sudo nginx -t
curl -I https://financas.exemplo.com/
```

| Sintoma | Verificação |
|---|---|
| Nginx retorna `502 Bad Gateway` | Confirme o serviço e se o backend escuta em `127.0.0.1:8010`. |
| App retorna `403` em alterações | Revise domínio e porta em `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`. |
| Banco não pode ser criado | Confirme a propriedade de `/var/lib/sistema-financeiro/data`. |
| Backup não grava no destino | O usuário `sistema-financeiro` precisa escrever no diretório configurado. |
| Serviço encerra imediatamente | Consulte `journalctl` e confirme arquitetura/compatibilidade do pacote Linux. |

## Limites deste guia

Este documento não automatiza DNS público, emissão de certificados, abertura de portas no roteador, VPN, monitoramento externo ou recuperação de desastre. Esses itens dependem da infraestrutura e do nível de exposição escolhido pelo operador.
