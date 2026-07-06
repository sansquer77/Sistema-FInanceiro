#!/bin/bash
set -e

IP="192.168.1.212"
DOMAIN="sistema-financeiro.net"
HOSTS_FILE="/etc/hosts"

echo "Configurando o dominio local no Mac/Linux..."

if ! grep -qE "^[[:space:]]*$IP[[:space:]]+$DOMAIN([[:space:]]|$)" "$HOSTS_FILE"; then
    echo -e "\n$IP\t$DOMAIN" | sudo tee -a "$HOSTS_FILE" > /dev/null
    echo "Dominio '$DOMAIN' adicionado ao /etc/hosts."
else
    echo "Dominio '$DOMAIN' ja esta configurado neste computador."
fi

echo "Acesse: https://$DOMAIN:8030"
