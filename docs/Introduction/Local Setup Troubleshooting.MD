---
route: local-dev-setup-troubleshooting
allow_guest: 1
published: 1
---

1. Check if scheduler is enabled (bench doctor)
1. Ping Agent
2. Update Agent
3. Check if TLS Certificate is expired on Server (TLS Certificate doctype)
 - If expired, obtain a new one by calling \_obtain\_certificate
4. Run install_nginx on Server and Proxy Server