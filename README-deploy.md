# Deploy — Sistema Financeiro

Este documento descreve passos práticos para executar o `Sistema Financeiro` em um servidor Linux com `systemd` e `nginx` (reverse-proxy). Também mostra exemplos de variáveis de ambiente usadas pela aplicação.

## Variáveis de ambiente úteis
- `APP_HOST` — interface que o backend vai escutar (padrão: `127.0.0.1`).
- `APP_PORT` — porta do backend (padrão: `8010`).
- `APP_URL` — URL pública do serviço (ex.: `http://meu-servidor.local:8010`). Usada em cookies e geração de links.
- `APP_ALLOWED_HOSTS` — hosts adicionais permitidos (CSV), ex.: `10.0.1.5,meu-servidor.local`.
- `APP_ALLOWED_ORIGINS` — origens adicionais permitidas (CSV), ex.: `http://10.0.1.5:8010`.
- `EXPOSE_LAN` — usado pelos launchers locais para detectar IP e expor na LAN (`1` para ativar).
- `SISTEMA_FINANCEIRO_DATA_DIR` — (opcional) caminho para dados; por padrão o app usa `./data` relativo ao diretório de execução.

Defina essas variáveis no ambiente do serviço `systemd` ou no script de inicialização do contêiner.

## Recomendações gerais
- Execute a aplicação em um ambiente isolado (virtualenv ou usuário dedicado).
- Rode a aplicação por trás de um reverse-proxy (nginx/Caddy) que faça TLS e terminates HTTPS.
- Mantenha `APP_HOST=127.0.0.1` quando usar reverse-proxy; quando quiser expor diretamente na LAN defina `APP_HOST=0.0.0.0` e configure `APP_ALLOWED_*` apropriadamente.

## Exemplo de unit `systemd`
Crie `/etc/systemd/system/sistema-financeiro.service` (ajuste paths/usuário conforme sua máquina):

```
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
Environment=APP_URL=http://sistema-financeiro.local:8010
Environment=APP_ALLOWED_HOSTS=127.0.0.1
Environment=APP_ALLOWED_ORIGINS=http://sistema-financeiro.local:8010
ExecStart=/usr/bin/python3 /opt/sistema-financeiro/app.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Comandos úteis:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro.service
sudo journalctl -u sistema-financeiro -f
```

Se precisar expor à LAN sem proxy, ajuste `Environment=APP_HOST=0.0.0.0` e adicione os hosts/origens apropriados em `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS`.

## Exemplo de configuração `nginx` (reverse-proxy)
Arquivo de site em `/etc/nginx/sites-available/sistema-financeiro`:

```
server {
    listen 80;
    server_name sistema-financeiro.local;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }
}
```

Ative e recarregue:

```bash
sudo ln -s /etc/nginx/sites-available/sistema-financeiro /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Para TLS com Certbot (Let's Encrypt):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d sistema-financeiro.local
```

Após TLS, ajuste `APP_URL` para `https://sistema-financeiro.local` no serviço `systemd`.

## Executar localmente (desenvolvimento)

Exemplo simples sem launcher:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt   # se houver
APP_HOST=127.0.0.1 APP_PORT=8010 APP_URL=http://127.0.0.1:8010 python3 app.py
```

Se usar o launcher incluído, defina `EXPOSE_LAN=1` para virar o comportamento de exposição da rede local (os launchers tentarão detectar o IP e preencher `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS`).

## Segurança e notas finais
- Sempre prefira colocar o app atrás de um proxy com TLS para evitar expor cookies/sessões em texto plano.
- Verifique `APP_URL` e `APP_ALLOWED_*` ao mover o serviço para outra máquina ou domínio.
- Garanta permissões adequadas na pasta `data/` (usuário do serviço deve possuir os arquivos).

## Problemas comuns
- Se o navegador reportar erro de origem (`Origin not allowed`), adicione a origem exata a `APP_ALLOWED_ORIGINS` (inclua esquema e porta).
- Se `Host` for rejeitado, adicione `host:port` a `APP_ALLOWED_HOSTS`.

---
Arquivo criado automaticamente pelo assistente de desenvolvimento.
