# Task 11 — Reverse Proxy / TLS Sanity

## Goal
Provide secure edge transport and reliable request correlation.

## Required outcomes
1. Enforce HTTP -> HTTPS redirect.
2. Use modern TLS (TLS 1.2/1.3, strong ciphers).
3. Forward trusted proxy headers correctly.
4. Preserve or inject request ID header (`X-Request-ID`).

---

## Nginx reference configuration

> Replace:
> - `api.example.com` with your domain
> - cert paths with your actual certificate files
> - upstream `127.0.0.1:8000` if app port differs

```nginx
# /etc/nginx/sites-available/api.example.com.conf

# Upstream app
upstream app_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# 1) HTTP listener: force HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name api.example.com;

    return 301 https://$host$request_uri;
}

# 2) HTTPS listener
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.example.com;

    # TLS certs (Let's Encrypt example)
    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # 3) Modern TLS baseline
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Good default curves
    ssl_ecdh_curve X25519:secp384r1;

    # OCSP stapling (optional but recommended when resolver is configured)
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 1.1.1.1 1.0.0.1 valid=300s ipv6=off;
    resolver_timeout 5s;

    # HSTS (enable only when fully HTTPS in production)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Pass through existing X-Request-ID if provided; otherwise use nginx request id
    map $http_x_request_id $req_id {
        default $http_x_request_id;
        ""      $request_id;
    }

    location / {
        proxy_http_version 1.1;
        proxy_pass http://app_backend;

        # 4) Trusted forwarding headers
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;

        # 5) Request correlation
        proxy_set_header X-Request-ID $req_id;
        add_header X-Request-ID $req_id always;

        # Timeouts
        proxy_connect_timeout 10s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## App-side trust notes (FastAPI/Uvicorn)
If running behind Nginx, ensure forwarded headers are trusted appropriately:

- Use Uvicorn proxy headers support:
  - `--proxy-headers`
  - and a safe `--forwarded-allow-ips` value (e.g. `127.0.0.1` when Nginx is local)

Example:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
```

If using Gunicorn+Uvicorn workers, set equivalent forwarded/proxy options in service config.

---

## Validation checklist

### A) HTTP redirects to HTTPS
```bash
curl -I http://api.example.com/health/live
```
Expect:
- `301` or `308`
- `Location: https://api.example.com/...`

### B) HTTPS works with valid cert
```bash
curl -I https://api.example.com/health/live
```
Expect:
- `200`
- valid certificate chain (no TLS errors)

### C) TLS protocol/cipher sanity
```bash
openssl s_client -connect api.example.com:443 -tls1_2 </dev/null
openssl s_client -connect api.example.com:443 -tls1_3 </dev/null
```
Expect successful handshakes for TLS1.2/1.3 only.

### D) Request ID propagation
```bash
curl -i https://api.example.com/health/live -H "X-Request-ID: demo-123"
```
Expect response header:
- `X-Request-ID: demo-123` (preserved)  
or nginx-generated value when not provided.

### E) Forwarded proto correctness
Hit an endpoint/log that records scheme and verify app sees `https`, not `http`.

---

## Hardening notes
1. Keep app bound to localhost/private interface, not public 0.0.0.0 unless required by architecture.
2. Keep TLS cert auto-renew (certbot timer or Caddy automatic TLS).
3. Reload Nginx after changes:
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```
4. Re-check firewall (only 80/443 + restricted SSH).

---

## Evidence to capture
- Nginx site config in repo/docs
- `curl -I` redirect proof
- `curl -i` showing `X-Request-ID`
- `openssl s_client` outputs (or screenshot/log)
- date/time + operator notes