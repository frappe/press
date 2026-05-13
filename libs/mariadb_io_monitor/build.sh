# !/bin/sh

set -e

# Install bpftool if not present
if ! command -v bpftool >/dev/null 2>&1; then
    echo "bpftool not found, installing..."
    sudo apt install linux-tools-common linux-headers-generic
fi

bpftool btf dump file /sys/kernel/btf/vmlinux format c  > bpf/vmlinux.h
docker build --network=host -t mariadb_io_monitor -f Dockerfile .
docker create --name mariadb_io_monitor_container mariadb_io_monitor
mkdir -p ./out
docker cp mariadb_io_monitor_container:/app/mariadb_io_monitor ./out/mariadb_io_monitor
docker rm mariadb_io_monitor_container
chmod +x ./out/mariadb_io_monitor
