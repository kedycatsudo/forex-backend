# Task 10 — Database Exposure Lockdown

## Goal
Ensure the database is **not reachable from the public internet**.

## Policy
1. Database must bind only to:
   - localhost (`127.0.0.1`) when app and DB are on same host, or
   - private interface/VPC IP when DB is on separate private host.
2. No public firewall allow rules for DB ports:
   - PostgreSQL: `5432/tcp`
   - MySQL: `3306/tcp`
3. If DB is separate from app, traffic must go over private network/VPC only.
4. Never expose DB credentials or admin ports publicly.
5. Access for operators must use SSH tunnel / bastion / VPN, not open DB port.

---

## Deployment patterns

### A) App + DB on same droplet (single host)
- DB bind address: `127.0.0.1`
- UFW:
  - deny incoming by default
  - allow only `80/443` (+ restricted SSH)
  - deny `5432` / `3306`

### B) App and DB on separate hosts
- DB bind address: private IP only (e.g. `10.x.x.x`)
- DB firewall/security group:
  - allow DB port **only from app private IP/security group**
  - deny all public sources

---

## PostgreSQL template

### postgresql.conf
```conf
# /etc/postgresql/<version>/main/postgresql.conf
listen_addresses = '127.0.0.1'   # single-host pattern
# or private IP for VPC pattern, e.g.:
# listen_addresses = '10.10.0.5'
port = 5432
```

### pg_hba.conf
```conf
# /etc/postgresql/<version>/main/pg_hba.conf

# local unix socket
local   all             all                                     scram-sha-256

# localhost only (single-host)
host    all             all             127.0.0.1/32            scram-sha-256

# VPC example (only app subnet)
# host  all             all             10.10.0.0/24            scram-sha-256
```

### restart
```bash
sudo systemctl restart postgresql
```

---

## MySQL template

### mysqld.cnf
```conf
# /etc/mysql/mysql.conf.d/mysqld.cnf
bind-address = 127.0.0.1   # single-host pattern
# or private IP for VPC pattern
mysqlx-bind-address = 127.0.0.1
port = 3306
```

### restart
```bash
sudo systemctl restart mysql
```

---

## UFW template
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSH restricted to admin IP
sudo ufw allow from <ADMIN_PUBLIC_IP> to any port 22 proto tcp
sudo ufw deny 22/tcp

# DB ports denied publicly
sudo ufw deny 5432/tcp
sudo ufw deny 3306/tcp
```

---

## Verification checklist

### On DB host
```bash
# PostgreSQL listening sockets
sudo ss -ltnp | grep 5432

# MySQL listening sockets
sudo ss -ltnp | grep 3306

# UFW rules
sudo ufw status verbose
```

Expected:
- DB listens on `127.0.0.1:<port>` or private IP only
- No `0.0.0.0:<port>` or `[::]:<port>` for DB
- No public allow rule for DB port

### External test (from internet host)
```bash
nc -vz <DB_PUBLIC_IP> 5432
nc -vz <DB_PUBLIC_IP> 3306
```

Expected: connection refused/timed out.

---

## App connection examples

### single-host
```env
DATABASE_URL=postgresql+asyncpg://app_user:***@127.0.0.1:5432/app_db
```

### private VPC host
```env
DATABASE_URL=postgresql+asyncpg://app_user:***@10.10.0.5:5432/app_db
```

---

## Rollout notes
- Apply first in staging.
- Keep one active SSH session before firewall changes.
- Backup DB configs before editing.
- Record final network diagram (app IP/subnet -> DB private IP/subnet).