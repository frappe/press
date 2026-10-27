# Build-only Press Server

Build-only Servers run the Press Agent on an isolated HTTPS listener and direct Docker SDK and BuildKit CLI traffic to one explicitly configured Unix socket. They are not eligible to host benches, sites, public Release Groups, or staging sites. They are selected only when explicitly assigned as the Release Group's build server; they are excluded from Press's automatic global build-server pool.

## Safety contract

- Provisioning uses `build_only.yml`, whose only role is `build_only_agent`. It does not include the standard `docker`, `nginx`, or general `agent` roles.
- The build-only playbook does not install, configure, or restart the host Docker daemon and does not write or reload host NGINX configuration.
- The Agent runs as the unprivileged `press-build` account. Its API exposes only authenticated health, image-build, build-job read, and build-job cancel operations.
- `DOCKER_HOST` must be an absolute dedicated Unix socket. The role and Agent reject the default Docker sockets, symlinks, socket aliases to the standard host Docker socket, non-socket paths, and a daemon whose reported data-root differs from the configured dedicated data-root. A failed check returns an error; there is no fallback to Docker defaults.
- The dedicated socket group must be neither `root` nor `docker`; the build account is added only to the socket's dedicated group.
- The Docker service name must use `albasar-build-*.service` or `press-build-*.service`. The role reads, but does not change, its effective CPU quota, memory limit, and I/O weight and fails if they do not match the Server record.
- Docker data must reside on a dedicated non-root mount whose capacity does not exceed the configured storage ceiling. The role verifies the mount and capacity; Press does not resize or reformat it.
- The Agent endpoint must be HTTPS on the Server's own DNS name and configured port. The certificate is checked for that hostname. Press's health check must succeed after setup.
- The Agent binds only to the configured IPv4 address in Tailscale's CGNAT range, and the playbook verifies that address is assigned to `tailscale0`. Wildcard, loopback, non-Tailnet, and unassigned addresses fail closed. The build-only endpoint does not bind a public interface or alter NGINX/firewall rules.
- The Agent repository is HTTPS-only and pinned to a full commit SHA. The Release Group must explicitly select this active build Server; it is never chosen by global load balancing.

## Required Server fields

Set `Build-only Server`, `Use For Build`, the dedicated `Build Docker Host` and `Build Docker Data Root`, the HTTPS endpoint and port, the exact `tailscale0` IPv4 bind address, and the isolated Docker systemd unit name. Set the CPU quota, memory limit, I/O weight, dedicated storage mount, and storage capacity to match the already-running isolated daemon and filesystem. Set the Agent repository URL and a reviewed full commit SHA. Keep `Public`, `Staging`, `Use For New Benches`, and `Use For New Sites` disabled.

The endpoint port must be reachable from Press over Tailnet and serve a valid certificate. Confirm the chosen port is free on the Tailnet address; the default is `9444` to avoid common existing listeners. This playbook does not change provider firewalls. A failed Press-to-Agent HTTPS check leaves the Server setup failed rather than switching to another endpoint or socket.

## Resource behavior

The Server values are assertions against the isolated Docker systemd service and the dedicated mounted filesystem. They are not silently applied by Press. If the host's isolated daemon does not already have those limits, configure and validate that daemon separately before running this playbook. Press does not change the Docker service's `ExecStart`, daemon configuration, cgroup parent, or data-root.

## Verification

Before registration is marked Active, the playbook checks the socket type and identity, daemon data-root, dedicated mount, filesystem capacity, systemd resource limits, TLS certificate hostname, and listener. Press then calls the configured Agent HTTPS endpoint and requires an authenticated `pong`. Only the build-only Agent endpoints are permitted after registration.
