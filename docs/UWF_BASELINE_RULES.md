# Task 9 — UFW Baseline Rules

## Goal
Minimize inbound network exposure on the droplet.

## Baseline policy
1. Default deny incoming.
2. Default allow outgoing.
3. Allow only required public ports:
   - `80/tcp` (HTTP)
   - `443/tcp` (HTTPS)
4. Restrict SSH (`22/tcp`) to admin IP allowlist (preferred).
5. Deny direct public DB access:
   - `5432/tcp` (PostgreSQL)
   - `3306/tcp` (MySQL)

---

## Standard command template (Ubuntu/Debian)

> Replace `<ADMIN_PUBLIC_IP>` with your real public IP/CIDR.

```bash
# inspect current state
sudo ufw status verbose

# baseline defaults
sudo ufw default deny incoming
sudo ufw default allow outgoing

# web ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# SSH allowlist first (important)
sudo ufw allow from <ADMIN_PUBLIC_IP> to any port 22 proto tcp

# deny broad SSH access
sudo ufw deny 22/tcp

# deny public DB ports
sudo ufw deny 5432/tcp
sudo ufw deny 3306/tcp

# enable firewall
sudo ufw enable

# verify final rules
sudo ufw status numbered
```

---

## Optional: non-standard SSH port

If SSH runs on a custom port (example `2222`):

```bash
sudo ufw allow from <ADMIN_PUBLIC_IP> to any port 2222 proto tcp
sudo ufw deny 2222/tcp
```

And ensure SSH daemon config matches (`/etc/ssh/sshd_config`), then restart SSH service.

---

## Safety checklist (avoid lockout)
1. Keep current SSH session open.
2. Add allowlist SSH rule **before** deny rule.
3. Open a second terminal and confirm SSH access still works.
4. Only then close original session.

---

## Verification

### From droplet
```bash
sudo ufw status verbose
sudo ss -ltnp
```

### From external host
```bash
# web should be reachable
nc -vz <DROPLET_PUBLIC_IP> 80
nc -vz <DROPLET_PUBLIC_IP> 443

# DB should NOT be reachable
nc -vz <DROPLET_PUBLIC_IP> 5432
nc -vz <DROPLET_PUBLIC_IP> 3306
```

Expected:
- 80/443 reachable (if services active)
- 5432/3306 blocked
- SSH reachable only from allowlisted source IP(s)

---

## Rollback/adjustments
If you accidentally block needed access but still have SSH:
```bash
sudo ufw status numbered
sudo ufw delete <RULE_NUMBER>
```

If UFW must be temporarily disabled (last resort):
```bash
sudo ufw disable
```

---

## Evidence to capture (for deployment checklist)
- `sudo ufw status verbose` output
- `sudo ss -ltnp` output
- External connectivity test results
- Date/time + operator who applied rules