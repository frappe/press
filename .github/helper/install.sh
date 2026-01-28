#!/bin/bash

set -e

cd ~ || exit

pip install frappe-bench
bench init --skip-assets --python "$(which python)" ~/frappe-bench --frappe-path https://github.com/balamurali27/frappe --frappe-branch fc-ci

mysql --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL character_set_server = 'utf8mb4'"
mysql --host 127.0.0.1 --port 3306 -u root -proot -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'"

cd ~/frappe-bench || exit

sed -i 's/watch:/# watch:/g' Procfile
sed -i 's/schedule:/# schedule:/g' Procfile
sed -i 's/socketio:/# socketio:/g' Procfile
sed -i 's/redis_socketio:/# redis_socketio:/g' Procfile

bench get-app press "${GITHUB_WORKSPACE}"

bench setup requirements --dev

export CI=Yes
bench new-site --mariadb-user-host-login-scope='%' --db-root-password root --admin-password admin test_site
bench --site test_site install-app press
bench set-config -g server_script_enabled 1
bench set-config -g http_port 8000
