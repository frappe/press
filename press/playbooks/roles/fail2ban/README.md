# fail2ban

This role installs Fail2Ban with one jail, `sshd`. The jail bans an IP address for 1 hour after 5 failed SSH logins in 10 minutes. Repeat offenders get longer bans.

The jail uses `mode = aggressive`, so connections that close before authentication also count as failures. Scanners cause most of these, and they fill the `MaxStartups` slots of `sshd`.

## Ignore list

The play needs `fail2ban_ignore_ips`. It fails when the value is empty, so that a play never bans Press. `press.security.fail2ban.ignore_ips()` makes the value. It contains:

- the private networks `10.0.0.0/8`, `172.16.0.0/12` and `192.168.0.0/16`
- the public IP address of each Proxy Server that is not archived
- the IP address of each Bastion Server that is not archived
- the IP addresses in **Press Settings > Infrastructure > SSH > Fail2Ban Ignore IPs**

Add the egress IP addresses of the Press host to that field before you run the play.

## Servers

The setup playbook of each server type includes this role. To install or update the jail on an existing server, use **Setup Fail2ban** on the server form. **Remove Fail2ban** stops and removes the package.

## Press host

Press does not manage the host it runs on. To install the jail on the Press host:

1. Print the ignore list:

   ```bash
   bench --site <site> execute press.security.fail2ban.ignore_ips
   ```

2. Run the play against the Press host. Use the SSH port of the host for `ansible_port`:

   ```bash
   ansible-playbook -i '<press-host-ip>,' -u root \
     -e ansible_port=22 \
     -e "fail2ban_ignore_ips='<output of step 1>'" \
     apps/press/press/playbooks/fail2ban.yml
   ```

3. Make sure that the jail is active:

   ```bash
   sudo fail2ban-client status sshd
   ```
