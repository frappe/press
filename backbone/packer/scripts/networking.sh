#!/bin/sh -eux

echo "Create netplan config for eth0"
cat <<EOF >/etc/netplan/01-netcfg.yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: true
EOF

# Disable Predictable Network Interface names and use eth0
sed -i 's/GRUB_CMDLINE_LINUX="\(.*\)"/GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0 \1"/g' /etc/default/grub
update-grub
