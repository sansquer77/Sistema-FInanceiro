# Configuração de Rede — Sistema Financeiro

Por padrão, o Sistema Financeiro roda **100% local**, sem nenhuma configuração adicional. Este guia é só para quem quer ir além disso: acessar o app de outros dispositivos na mesma casa/escritório, ou publicá-lo em um servidor com domínio próprio.

## Escolha seu cenário

| Cenário | O que fazer |
|---|---|
| Só eu, neste computador | Nada a configurar — use o app normalmente. |
| Eu e mais pessoas na mesma rede Wi-Fi/cabo, cada um acessando o computador de quem está com o app aberto | [Uso em rede local (LAN)](#uso-em-rede-local-lan) |
| Rede local, mas centralizado em um servidor dedicado (ex.: um Ubuntu sempre ligado), com domínio próprio e HTTPS, sem depender do notebook de ninguém estar ligado | [Servidor Linux (avançado)](#servidor-linux-avançado) |

---

## Uso em rede local (LAN)

Cenário mais simples para várias pessoas da mesma casa acessarem o app pelo celular ou notebook: o app roda no computador de uma pessoa, e os demais dispositivos da rede acessam esse computador diretamente. Não precisa de servidor separado nem de domínio. Os pacotes de instalação já trazem um atalho pronto para isso — não é preciso mexer em variáveis de ambiente manualmente.

- **macOS**: execute `~/Documents/Sistema Financeiro/Abrir Sistema Financeiro na Rede.command`.
- **Windows**: abra o atalho `Sistema Financeiro Rede`.

Depois de iniciado nesse modo, descubra o IP do computador na rede local (ex.: `192.168.1.50`) e acesse de outro dispositivo pelo navegador:

```text
http://192.168.1.50:8010
```

> [!warning] Use apenas em rede confiável
> O modo rede local expõe a interface do app para qualquer dispositivo conectado à mesma rede Wi-Fi/cabo, sem HTTPS. Use somente em redes domésticas ou de escritório confiáveis — nunca em Wi-Fi público ou compartilhado. Ao iniciar nesse modo, o app mostra um alerta no terminal lembrando que a conexão é HTTP; isso é esperado para uso doméstico, mas se quiser HTTPS e um endereço fixo por domínio mesmo dentro da rede local, use o [servidor Linux](#servidor-linux-avançado) abaixo.

Se algum dispositivo não conseguir acessar pelo IP, confira se o firewall do computador está bloqueando a porta `8010` para conexões da rede local.

---

## Servidor Linux (avançado)

Continua sendo um cenário de **rede local** — a diferença é que, em vez do app depender do computador de uma pessoa estar ligado, ele roda de forma centralizada em uma máquina Linux dedicada (ex.: um mini PC ou servidor doméstico sempre ligado), acessível por um domínio próprio e HTTPS para qualquer dispositivo da rede, sem precisar saber o IP de ninguém.

Os exemplos abaixo usam como referência um servidor em `192.168.1.212`, acessado por `https://sistema-financeiro.net:8030` — ajuste domínio, IP e porta para o seu caso.

> [!note] Acesso fora da rede local
> Este guia cobre o servidor rodando dentro da rede local. Se você também quiser acessá-lo de fora de casa (pela internet), é preciso expor a porta do servidor no roteador (port forwarding) — o que está fora do escopo deste guia e exige atenção extra à segurança (HTTPS obrigatório, firewall, atualizações do servidor em dia).

### 1. Variáveis de ambiente do backend

| Variável | Uso |
|---|---|
| `APP_HOST` | Interface em que o backend escuta. Use `127.0.0.1` quando houver proxy reverso na frente (recomendado) e `0.0.0.0` apenas se for expor o backend diretamente, sem proxy. |
| `APP_PORT` | Porta interna do backend. Padrão: `8010`. |
| `APP_URL` | URL pública usada pelo app. Ex.: `https://sistema-financeiro.net:8030`. |
| `APP_ALLOWED_HOSTS` | Hosts aceitos no header `Host`, em CSV. Entradas sem porta também aceitam `APP_PORT`. |
| `APP_ALLOWED_ORIGINS` | Origens aceitas para requisições que alteram dados, em CSV. |
| `SISTEMA_FINANCEIRO_DATA_DIR` | Pasta dos dados locais. Opcional — só defina se quiser mudar o local padrão. |

URLs aceitas por padrão pelo backend (ajuste as variáveis acima para domínios, IPs ou portas diferentes destes):

- `http://sistema-financeiro.localhost:8010`
- `https://sistema-financeiro.net:8030`
- `http://sistema-financeiro.net:8030`
- `https://192.168.1.212:8030`
- `http://192.168.1.212:8030`

### 2. Serviço systemd

Salve como `/etc/systemd/system/sistema-financeiro.service` no servidor:

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

Ative e acompanhe os logs:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sistema-financeiro.service
sudo journalctl -u sistema-financeiro -f
```

### 3. Proxy reverso (nginx) com HTTPS

Salve como `/etc/nginx/sites-available/sistema-financeiro`:

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

### 4. Configurar os dispositivos clientes

Para os dispositivos acessarem pelo domínio (`sistema-financeiro.net`) em vez do IP puro, é preciso mapear o domínio para o IP do servidor em cada dispositivo — normalmente editando o arquivo `hosts` do sistema operacional.

**macOS e Linux** — o pacote macOS inclui um script pronto para isso:

```bash
chmod +x configurar_mac.sh
sudo ./configurar_mac.sh
```

**Windows** — o pacote Windows inclui `configurar_windows.ps1`:

1. Clique com o botão direito em `configurar_windows.ps1`.
2. Escolha **Executar com o PowerShell**.
3. Confirme a execução como Administrador.

Depois de configurado, acesse de qualquer dispositivo:

```text
https://sistema-financeiro.net:8030
```

> [!note] Certificado autoassinado
> Se o certificado SSL for autoassinado (comum em servidores domésticos), o navegador pede uma confirmação de segurança na primeira abertura de cada dispositivo. Isso é esperado — basta confirmar para prosseguir.

---

## Voltar ao modo local ou rede local

Os pacotes desktop continuam funcionando sem servidor a qualquer momento, mesmo depois de configurar o servidor Linux:

- macOS local: abra `Sistema Financeiro` na pasta Aplicativos.
- macOS rede local: execute `~/Documents/Sistema Financeiro/Abrir Sistema Financeiro na Rede.command`.
- Windows local: abra o atalho `Sistema Financeiro`.
- Windows rede local: abra o atalho `Sistema Financeiro Rede`.

## Solução de problemas

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Outro dispositivo não abre o app pelo IP na rede local | Firewall bloqueando a porta `8010` | Libere a porta `8010` para conexões da rede local no firewall do computador. |
| Navegador bloqueia o acesso pelo domínio no servidor Linux | `hosts` não configurado no dispositivo cliente | Rode `configurar_mac.sh` (macOS/Linux) ou `configurar_windows.ps1` (Windows) no dispositivo. |
| Aviso de certificado inválido no servidor Linux | Certificado autoassinado | Esperado em servidor doméstico — confirme a exceção de segurança no navegador, ou instale um certificado válido (ex.: Let's Encrypt) se preferir eliminar o aviso. |
| App não inicia após alterar variáveis de ambiente | `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS` sem o domínio ou IP usado | Confirme que a URL de acesso está listada em ambas as variáveis, com a porta quando aplicável. |
