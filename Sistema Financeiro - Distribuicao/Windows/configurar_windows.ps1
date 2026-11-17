# Requer execucao como Administrador
$hostsPath = "$env:windir\System32\drivers\etc\hosts"
$ip = "192.168.1.212"
$domain = "sistema-financeiro.net"
$entry = "$ip`t$domain"

Write-Host "Configurando o dominio local no Windows..." -ForegroundColor Cyan

$content = Get-Content $hostsPath -ErrorAction Stop
$alreadyConfigured = $content | Where-Object { $_ -match "^\s*$([regex]::Escape($ip))\s+$([regex]::Escape($domain))(\s|$)" }

if (-not $alreadyConfigured) {
    try {
        Add-Content -Path $hostsPath -Value "`n$entry"
        Write-Host "Dominio '$domain' adicionado ao arquivo hosts." -ForegroundColor Green
    } catch {
        Write-Host "Erro: execute o PowerShell como Administrador." -ForegroundColor Red
    }
} else {
    Write-Host "O dominio '$domain' ja esta configurado neste computador." -ForegroundColor Yellow
}

Write-Host "Acesse: https://$domain`:8030"
Write-Host "Pressione qualquer tecla para sair..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
