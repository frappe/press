#!/bin/bash
set -euxo pipefail

function install_go() {
    unamearch=$(uname -m)
    if [[ $unamearch == x86_64* ]]; then
        arch="amd64"
    elif [[ $unamearch == arm* ]]; then
        arch="arm64"
    elif [[ $unamearch == aarch* ]]; then
        arch="arm64"
    else
        exit
    fi
    wget -q https://go.dev/dl/go$GOVERSION.linux-$arch.tar.gz -O /tmp/go.tar.gz
    tar -C /home/frappe/.local/ -xzf /tmp/go.tar.gz
    rm /tmp/go.tar.gz
    export PATH=$PATH:/home/frappe/.local/go/bin
}

function init_bench() {
    bench init --skip-redis-config-generation frappe-bench

    cd frappe-bench
    mkdir .clones
    mkdir .docker-builds

    bench set-mariadb-host mariadb
    bench set-redis-cache-host redis:6379
    bench set-redis-queue-host redis:6379
    bench set-redis-socketio-host redis:6379

    # https://github.com/asottile/dockerfile/issues/71
    # https://github.com/asottile/setuptools-golang/issues/65#issuecomment-891090060
    export GO111MODULE=off
    if [[ -z "$PRESSBRANCH" ]]; then
        bench get-app $PRESSREPO
    else
        bench get-app $PRESSREPO --branch=$PRESSBRANCH
    fi

    bench new-site press.localhost \
        --force \
        --mariadb-root-password $MYSQL_ROOT_PASSWORD \
        --admin-password $BENCH_ADMIN_PASSWORD \
        --no-mariadb-socket

    bench --site press.localhost install-app press
    bench --site press.localhost set-config developer_mode $BENCH_DEVELOPER_MODE
    bench --site press.localhost set-config mute_emails $BENCH_MUTE_EMAILS
    bench --site press.localhost clear-cache

    bench use press.localhost
}

mkdir -p /home/frappe/.certbot
mkdir -p /home/frappe/.certbot/webroot

sudo apt update
sudo apt install -y certbot
python3 -m pip install certbot-dns-route53

install_go
# if [[ ! -x "$(command -v go)" ]]; then
#     install_go
# fi

if [[ ! -e /home/frappe/.local/wait-for-it.sh ]]; then
    wget -q https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh -O /home/frappe/.local/wait-for-it.sh
    chmod +x /home/frappe/.local/wait-for-it.sh
fi

/home/frappe/.local/wait-for-it.sh mariadb:3306
/home/frappe/.local/wait-for-it.sh redis:6379

if [[ -d "/home/frappe/benches/frappe-bench" ]]; then
    echo "Bench already exists, skipping init"
    cd /home/frappe/benches/frappe-bench
else
    echo "Creating new bench..."
    mkdir -p /home/frappe/benches
    cd /home/frappe/benches

    init_bench
fi

exec bench start
