# Self-signed TLS certs (MVP)

Generate dev certs (one-time):

```bash
mkcert -install
mkcert -cert-file astoka.local.pem -key-file astoka.local.key \
  astoka.local "*.astoka.local"
```

Add to `/etc/hosts`:

```
127.0.0.1 astoka.local flower.astoka.local minio.astoka.local
```

Faza 2: jeśli ekspozycja zewnętrzna — Let's Encrypt via Traefik ACME (NFR-SEC-05).

`*.pem` and `*.key` files are gitignored.
