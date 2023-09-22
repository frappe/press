#!/bin/bash

set -e

cd ~ || exit

sudo apt update && sudo apt install redis-server libcups2-dev

pip install frappe-bench
bench init --skip-assets --python "$(which python)" ~/frappe-bench --frappe-path https://github.com/adityahase/frappe --frappe-branch frappe-cloud

mysql --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
mysql --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

install_whktml() {
    wget -O /tmp/wkhtmltox.tar.xz https://github.com/frappe/wkhtmltopdf/raw/master/wkhtmltox-0.12.3_linux-generic-amd64.tar.xz
    tar -xf /tmp/wkhtmltox.tar.xz -C /tmp
    sudo mv /tmp/wkhtmltox/bin/wkhtmltopdf /usr/local/bin/wkhtmltopdf
    sudo chmod o+x /usr/local/bin/wkhtmltopdf
}
install_whktml &

cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app press "${GITHUB_WORKSPACE}"

bench setup requirements --dev

# workaround for dependency issue
bench pip install cryptography~=41.0.3
bench pip install filelock~=3.8.0
pip install pydantic==2.3.0
pip install pyOpenSSL~=23.2.0

bench start &> bench_start_logs.txt &
CI=Yes bench build --app frappe &
bench new-site --db-root-password root --admin-password admin test_site
bench --site test_site install-app press
bench set-config -g server_script_enabled 1
