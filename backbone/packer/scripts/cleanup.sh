#!/bin/sh -eux
export DEBIAN_FRONTEND=noninteractive

# Remove open-vm-tools
apt-get -y purge open-vm-tools

# Remove git and vim 
apt-get -y purge git vim-common

# Remove snapd
apt-get -y purge snapd
rm -rf /var/cache/snapd/
rm -rf /snap

# Remove cloud init
apt-get -y purge cloud-init
rm -rf /etc/cloud/
rm -rf /var/lib/cloud/

# Delete all Linux headers
dpkg --list \
  | awk '{ print $2 }' \
  | grep 'linux-headers' \
  | xargs apt-get -y purge

# Remove specific Linux kernels, such as linux-image-3.11.0-15-generic but
# keeps the current kernel and does not touch the virtual packages,
# e.g. 'linux-image-generic', etc.
dpkg --list \
    | awk '{ print $2 }' \
    | grep 'linux-image-.*-generic' \
    | grep -v `uname -r` \
    | xargs apt-get -y purge

# Delete Linux source
dpkg --list \
    | awk '{ print $2 }' \
    | grep linux-source \
    | xargs apt-get -y purge

# Delete development packages
dpkg --list \
    | awk '{ print $2 }' \
    | grep -- '-dev$' \
    | xargs apt-get -y purge

# delete docs packages
dpkg --list \
    | awk '{ print $2 }' \
    | grep -- '-doc$' \
    | xargs apt-get -y purge

# Delete X11 libraries
apt-get -y purge libx11-data xauth libxmuu1 libxcb1 libx11-6 libxext6

# Delete obsolete networking
apt-get -y purge ppp pppconfig pppoeconf

# Delete oddities
apt-get -y purge popularity-contest installation-report command-not-found friendly-recovery bash-completion fonts-ubuntu-font-family-console laptop-detect

# Exlude the files we don't need w/o uninstalling linux-firmware
echo "==> Setup dpkg excludes for linux-firmware"
cat <<_EOF_ | cat >> /etc/dpkg/dpkg.cfg.d/excludes
#BENTO-BEGIN
path-exclude=/lib/firmware/*
path-exclude=/usr/share/doc/linux-firmware/*
#BENTO-END
_EOF_

# Delete the massive firmware packages
rm -rf /lib/firmware/*
rm -rf /usr/share/doc/linux-firmware/*

# Clean up orphaned packages with deborphan
apt-get -y install deborphan
while [ -n "$(deborphan --guess-all --libdevel)" ]
do
    deborphan --guess-all --libdevel | xargs apt-get -y purge
done
apt-get -y purge deborphan dialog

apt-get -y autoremove
apt-get -y autoclean
apt-get -y clean

# Remove docs
rm -rf /usr/share/doc/*

# Remove man pages
rm -rf /usr/share/man/*

# Remove cache files
find /var/cache -type f -exec rm -rf {} \;

# Remove APT files"
find /var/lib/apt -type f | xargs rm -f

# truncate any logs that have built up during the install
find /var/log -type f -exec truncate --size=0 {} \;

# Blank netplan machine-id (DUID) so machines get unique ID generated on boot.
truncate -s 0 /etc/machine-id

# remove the contents of /tmp and /var/tmp
rm -rf /tmp/* /var/tmp/*

# clear the history so our install isn't there
export HISTSIZE=0
rm -f /root/.wget-hsts

# Remove unused blocks
/sbin/fstrim -v /
