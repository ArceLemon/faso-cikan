#!/bin/sh
# Prépare la configuration de Synapse puis passe la main au script officiel de l'image.
set -eu

python /conf/rendre_config.py /conf/homeserver.yaml /data/homeserver.yaml
cp /conf/log.config /data/log.config
chown 991:991 /data /data/homeserver.yaml /data/log.config

if [ ! -f /data/signing.key ]; then
    gosu 991:991 python -m synapse.app.homeserver \
        --config-path /data/homeserver.yaml --generate-keys
fi

# En local, Caddy signe ses certificats avec sa propre autorité. Synapse doit
# l'approuver pour joindre Keycloak en HTTPS par son adresse publique.
CA_LOCALE=/caddy/caddy/pki/authorities/local/root.crt
for _ in $(seq 1 30); do
    [ -f "$CA_LOCALE" ] && break
    sleep 2
done
if [ -f "$CA_LOCALE" ]; then
    cat /etc/ssl/certs/ca-certificates.crt "$CA_LOCALE" > /data/ca-approuvees.crt
    export SSL_CERT_FILE=/data/ca-approuvees.crt
fi

exec /start.py
