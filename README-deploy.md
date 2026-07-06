# Deploy — Sistema Financeiro

Este guia cobre tres formas de uso:

- app local no proprio computador;
- app local exposto para a rede local;
- servidor Linux em `192.168.1.212`, acessado por `https://sistema-financeiro.net:8030`.

## URLs suportadas

O backend aceita por padrao:

- `http://sistema-financeiro.localhost:8010`
- `https://sistema-financeiro.net:8030`
- `http://sistema-financeiro.net:8030`
- `https://192.168.1.212:8030`
- `http://192.168.1.212:8030`

Para outros dominios, IPs ou portas, ajuste `APP_URL`, `APP_ALLOWED_HOSTS` e `APP_ALLOWED_ORIGINS`.

## Variaveis de ambiente

| Variavel | Uso |
|---|---|
| `APP_HOST` | Interface em que o backend escuta. Use `127.0.0.1` atras de proxy e `0.0.0.0` para expor diretamente na LAN. |
| `APP_PORT` | Porta interna do backend. Padrao: `8010`. |
| `APP_URL` | URL publica usada pelo app. Ex.: `https://sistema-financeiro.net:8030`. |
| `APP_ALLOWED_HOSTS` | Hosts aceitos no header `Host`, em CSV. Entradas sem porta tambem aceitam `APP_PORT`. |
| `APP_ALLOWED_ORIGINS` | Origens aceitas para requisicoes mutaveis, em CSV. |
| `SISTEMA_FINANCEIRO_DATA_DIR` | Pasta dos dados locais. Opcional. |

## Servidor Linux

Salve estes arquivos no servidor Linux `192.168.1.212`.

### `/etc/systemd/system/sistema-financeiro.service`

```ini
[Unit]
Description=Sistema Financeiro
After=network.target

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

ExecStart=/usr/bin/python3 /opt/sistema-financeiro/app.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Ative:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro.service
sudo journalctl -u sistema-financeiro -f
```

### `/etc/nginx/sites-available/sistema-financeiro`

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

Ative:

```bash
sudo ln -sf /etc/nginx/sites-available/sistema-financeiro /etc/nginx/sites-enabled/sistema-financeiro
sudo nginx -t
sudo systemctl reload nginx
```

## Clientes MacOS e Linux

Para acessar o servidor pelo dominio, configure o arquivo `hosts`.

O pacote MacOS inclui `configurar_mac.sh`. Para usar:

```bash
chmod +x configurar_mac.sh
sudo ./configurar_mac.sh
```

Depois acesse:

```text
https://sistema-financeiro.net:8030
```

Se o certificado for autoassinado, o navegador pode pedir confirmacao de seguranca na primeira abertura.

## Clientes Windows

O pacote Windows inclui `configurar_windows.ps1`.

Como usar:

1. Clique com o botao direito em `configurar_windows.ps1`.
2. Escolha `Executar com o PowerShell`.
3. Confirme a execucao como Administrador.
4. Acesse `https://sistema-financeiro.net:8030`.

Se o certificado for autoassinado, o navegador pode pedir confirmacao de seguranca na primeira abertura.

## App local e rede local

Os pacotes desktop continuam podendo rodar sem servidor:

- MacOS local: abrir `Sistema Financeiro` em Aplicativos.
- MacOS rede local: executar `~/Documents/Sistema Financeiro/Abrir Sistema Financeiro na Rede.command`.
- Windows local: abrir o atalho `Sistema Financeiro`.
- Windows rede local: abrir o atalho `Sistema Financeiro Rede`.

Use modo rede local apenas em rede confiavel. Para acesso por dominio ou fora da maquina, prefira o servidor Linux com HTTPS.
