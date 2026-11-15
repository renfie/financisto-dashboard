# Caddy, HTTPS and reverse-proxy integration

**Language / Sprache:** **English** | [Deutsch](CADDY.de.md)

The Financisto Dashboard includes **Caddy** as its own Docker Compose service. Caddy handles internal HTTPS, forwards authorized requests to the Python application, and stores its locally issued TLS certificates across updates. You do not have to install Caddy separately.

## Network overview

```text
LAN browser ── HTTPS (default host port 8443) ── Caddy ── dashboard:8000
                                                       (private Docker network)

Optional Internet access:
Internet browser ── HTTPS + public certificate ── Nginx Proxy Manager
                                   └── private HTTPS ── Caddy ── dashboard:8000
```

Caddy connects to the dashboard on the internal Docker network. Its published host port is configured by `HTTPS_BIND_IP` and `HTTPS_PORT`. The default is `0.0.0.0:8443` on the host; restrict `HTTPS_BIND_IP` to a LAN or loopback address where practical. No application HTTP port needs to be exposed publicly.

## TLS certificates

The provided [Caddyfile](../Caddyfile) uses `tls internal`. This means the certificates between the LAN browser or an upstream proxy and Caddy are issued by a **local Caddy CA**. They are not publicly trusted certificates.

For direct LAN browser access, the local Caddy root CA must be installed in the client's trust store to avoid browser certificate warnings. Treat the CA root as trusted certificate authority material. The certificate directory is backed by `caddy/data/` on the host and must not be deleted. When testing or rotating certificates, distribute a newly trusted CA only after verifying its origin.

For Internet access behind **Nginx Proxy Manager (NPM)**, NPM should use its own publicly trusted TLS certificate on the external connection. The NPM → Caddy connection is a separate TLS hop: configure its upstream TLS trust and host/SNI settings correctly; do not assume the private Caddy CA is publicly trusted.

## Configuration in the existing .env

For a new installation, configure the values through the installer. The following values are examples, **not actual deployment values**:

```dotenv
SITE_HOST=finance.example.org
SITE_ADDRESSES=https://finance.example.org
HTTPS_BIND_IP=192.0.2.10
HTTPS_PORT=8443
TRUSTED_PROXY_IPS=127.0.0.1/32
```

- `SITE_HOST`: primary hostname, used for Caddy's default SNI.
- `SITE_ADDRESSES`: comma-separated HTTPS site addresses and aliases; must match the hosts accessed by users.
- `HTTPS_BIND_IP` / `HTTPS_PORT`: host interface and HTTPS port published by Docker.
- `TRUSTED_PROXY_IPS`: exact remote address/CIDR of a trusted upstream reverse proxy, **never a public-wide network such as `0.0.0.0/0`**. This helps prevent spoofed client IP addresses in access-control checks.

Do not commit a populated `.env` to the public repository.

## IP restrictions and optional public access

The application has an IP allowlist and an administrator-controlled public-access setting. **Public access should be enabled only after** HTTPS, accounts, 2FA, proxy trust and appropriate firewall rules have been configured and tested. The administrator setting in the web interface controls public access for current installations; older documentation mentioning `PUBLIC_ACCESS` as a switch describes an older initialization flow.

Do not expose the internal Caddy port directly to the Internet simply because the GitHub repository is public. Publishing source code does not publish or change the running server.

## Updates and preserving certificates

The [update.sh](../../update.sh) copies the updated program's `Caddyfile` and `compose.yaml`, but preserves the existing `.env`, including your hostnames and explicitly configured aliases, and does not delete:

- `caddy/data/` — CA keys and certificates
- `caddy/config/` — Caddy runtime configuration/state
- `secrets/`, `data/` and database backups

The updater creates a backup and migrates older Caddy host aliases into `SITE_ADDRESSES` if missing, then checks that the Caddy container is running. It is not intended to replace a manual TLS validity check from a browser or NPM.

**Never use `docker compose down -v` to perform an update.**

## Basic operations

From the installed project's directory, as the normal project user:

```bash
docker compose ps
docker compose logs --tail=80 caddy
docker compose config --quiet
```

After changing relevant values in your existing `.env`:

```bash
docker compose up -d --no-deps --force-recreate caddy
```

For installation and upgrade instructions, see [README.en.md](../README.en.md). See also [Security and public access](SECURITY_UPGRADE.md) (German).
