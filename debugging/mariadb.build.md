# Guide to Building and Hosting MariaDB Ubuntu Packages

We are building MariaDB 10.6.16 with some changes for Ubuntu 20.04

We need to build this on Ubuntu 20.04 itself. But to host the repository we need a newer release. We will use 23.10 and build MariaDB inside a container.

We'll use [Reprepro](https://wikitech.wikimedia.org/wiki/Reprepro) to create a Ubuntu repository. Older releases of reprepro do not work well with ddeb packages (debug symbols).

At the end, we'll have our MariaDB 10.6.16+ packages for Ubuntu 20.04 hosted on packages.frappe.cloud.

---

## Build Ubuntu Packages

### Prepare Build Container

1. Create `frappe` user and install docker from https://docs.docker.com/engine/install/ubuntu/

2. Use `mariadb.build.Dockerfile` to create our build container

```sh
docker build -t mariadb-build:10.6 .
```

References:
https://mariadb.com/kb/en/building-mariadb-on-ubuntu/
https://mariadb.com/kb/en/Build_Environment_Setup_for_Linux/

---

### Clone MariaDB

```sh
git clone --branch mariadb-10.6.16 https://github.com/MariaDB/server.git /home/frappe/mariadb/server
```

Fetch git submodules

```
cd server
git clean -dffx
git reset --hard HEAD
git submodule update --init --recursive
```

Cherry-pick interesting changes

```sh
git cherry-pick bb511def1d316ffbdd815f2fc99d0a5813671814
```

References:

- https://jira.mariadb.org/browse/MDEV-32371

- https://github.com/MariaDB/server/pull/2866
- https://github.com/MariaDB/server/commit/bb511def1d316ffbdd815f2fc99d0a5813671814

---

### Build Ubuntu Packages

Run the build inside a container. We'll have the packages placed in `/home/frappe/mariadb`

```sh
docker run --rm -v /home/frappe/mariadb:/mariadb -w /mariadb/server -it mariadb-build:10.6 bash ./debian/autobake.sh
```

Tip: Temporarily resize this server to allocate as many CPU cores as you can. More the cores the faster the build.

References: https://mariadb.com/kb/en/building-mariadb-on-ubuntu/

---

## Host Ubuntu Repository

### Setup OpenPGP

We need to [sign the packages with OpenPGP](https://ubuntu.com/server/docs/third-party-apt-repositories)

1. Create a OpenPGP key for `Frappe Developers <developers@frappe.io>`. This is an interactive step. Refer frappe.io/app/frappe-asset for Paasphrase.

```sh
gpg --full-gen-key
```

Once completed we should have something like

```sh
$ gpg --list-secret-key --with-subkey-fingerprint
/home/frappe/.gnupg/pubring.kbx
-------------------------------
sec   rsa4096 2024-01-29 [SC]
      2AADEF02BE446B0FA3B0AC3DF38C274AC216D014
uid           [ultimate] Frappe Developers <developers@frappe.io>
```

Export the public key in the repository directory

```sh
mkdir -p /home/frappe/repository
gpg --armor --output /home/frappe/repository/frappe.gpg.key --export-options export-minimal --export 2AADEF02BE446B0FA3B0AC3DF38C274AC216D014
```

### Setup Reprepro

Create the directory structure that looks like our urls (https://packages.frappe.cloud/mariadb/10.6)

Reprepro needs two config files `conf/distributions` and `conf/options`

```sh
mkdir -p /home/frappe/repository/mariadb/10.6/conf
```

```sh
echo "Origin: MariaDB
Label: MariaDB
Codename: focal
Architectures: amd64 source
Components: main
DDebComponents: main
Limit: 3
Description: MariaDB Repository
SignWith: 2AADEF02BE446B0FA3B0AC3DF38C274AC216D014" > /home/frappe/repository/mariadb/10.6/conf/distributions
```

```sh
echo "verbose
basedir /home/frappe/repository/mariadb/10.6
ask-passphrase" > /home/frappe/repository/mariadb/10.6/conf/options
```

The tree structure should now look like

```sh
$ tree /home/frappe/repository/
/home/frappe/repository/
├── frappe.gpg.key
└── mariadb
    └── 10.6
        └── conf
            ├── distributions
            └── options

4 directories, 3 files
```

Download and install a newer reprepro release

```sh
curl -skO "http://ftp.debian.org/debian/pool/main/r/reprepro/reprepro_5.4.3-1_amd64.deb"
apt-get install -y --no-install-recommends "./reprepro_5.4.3-1_amd64.deb"
```

### Prepare the repository

Build the repository from the `.changes` file in `/home/frappe/mariadb`

```sh
reprepro -Vb /home/frappe/repository/mariadb/10.6 --ignore=wrongsourceversion include focal /home/frappe/mariadb/*.changes
```

References:

- https://mariadb.com/kb/en/Creating_a_Debian_Repository/
- https://wiki.debian.org/DebianRepository/SetupWithReprepro
- https://github.com/MariaDB/buildbot/blob/dev/utils.py#L221

### Publish the repository with NGINX

```sh
apt install nginx
usermod -aG frappe www-data
```

```nginx
echo "server {
    listen 80;
    server_name packages.frappe.cloud;

    location / {
        root /home/frappe/repository;
        autoindex on;
    }

    location ~ /(.*)/conf {
        deny all;
    }

    location ~ /(.*)/db {
        deny all;
    }
}" > /home/frappe/nginx.conf
```

```sh
ln -s /home/frappe/nginx.conf /etc/nginx/conf.d/packages.frappe.cloud.conf
```

Setup TLS for `packages.frappe.cloud`

```sh
snap install --classic certbot
certbot --nginx --agree-tos --email developers@frappe.io --domains packages.frappe.cloud
```

### Install patched MariaDB

Fetch OpenPGP key

```sh
wget -O - https://packages.frappe.cloud/frappe.gpg.key | apt-key add -
```

Setup repository and install as usual

```sh
echo "deb https://packages.frappe.cloud/mariadb/10.6 focal main" > /etc/apt/sources.list.d/mariadb.list"
apt update
apt install mariadb-server
```

For debug symbols fetch from `main/debug`

```sh
echo "deb https://packages.frappe.cloud/mariadb/10.6 focal main main/debug" > /etc/apt/sources.list.d/mariadb.list"
apt update
apt install mariadb-server mariadb-server-core-10.6-dbgsym
```
