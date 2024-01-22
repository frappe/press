# syntax = docker/dockerfile:experimental
FROM ubuntu:20.04

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

RUN --mount=type=cache,target=/var/cache/apt apt-get update \
    && apt-get install --yes --no-install-suggests --no-install-recommends \
    curl \
    software-properties-common \
    gnupg \
    debian-goodies \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -m 0755 -p /etc/apt/keyrings

# Install MariaDB 10.6 from the official repository.
RUN --mount=type=cache,target=/var/cache/apt curl -fsSL 'https://mariadb.org/mariadb_release_signing_key.pgp' | gpg --dearmor -o /etc/apt/keyrings/mariadb.gpg  \
    && echo "deb [signed-by=/etc/apt/keyrings/mariadb.gpg] https://mirror.rackspace.com/mariadb/repo/10.6/ubuntu focal main main/debug" | tee /etc/apt/sources.list.d/mariadb.list \
    && apt-get update \
    && apt-get install --yes --no-install-suggests --no-install-recommends \
    gdb \
    mariadb-server \
    mariadb-server-core-10.6-dbgsym \
    && rm -rf /var/lib/apt/lists/*

# Install debug symbols for libc and libstdc++.
RUN --mount=type=cache,target=/var/cache/apt echo "deb http://ddebs.ubuntu.com focal main restricted universe multiverse" | tee -a /etc/apt/sources.list.d/ddebs.list \ 
    && echo "deb http://ddebs.ubuntu.com focal-updates main restricted universe multiverse" | tee -a /etc/apt/sources.list.d/ddebs.list \ 
    && echo "deb http://ddebs.ubuntu.com focal-proposed main restricted universe multiverse" | tee -a /etc/apt/sources.list.d/ddebs.list \ 
    && apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F2EDC64DC5AEE1F6B9C621F0C8CAB6595FDFF622 \
    && apt-get update \
    && apt-get install --yes --no-install-suggests --no-install-recommends \
    libc6-dbg \
    libstdc++6-10-dbg \
    lib32stdc++6-10-dbg \
    libx32stdc++6-10-dbg \
    libstdc++6-dbgsym \
    && rm -rf /var/lib/apt/lists/*
