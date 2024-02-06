# syntax = docker/dockerfile:experimental
FROM ubuntu:20.04

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

RUN --mount=type=cache,target=/var/cache/apt apt-get update \
    && apt-get install --yes --no-install-suggests --no-install-recommends \
    curl \
    software-properties-common \
    gnupg \
    devscripts \
    equivs \
    && rm -rf /var/lib/apt/lists/*

RUN sed -Ei 's/^# deb-src /deb-src /' /etc/apt/sources.list

RUN mkdir -m 0755 -p /etc/apt/keyrings

# Install MariaDB 10.6 from the official repository.
RUN --mount=type=cache,target=/var/cache/apt curl -fsSL 'https://mariadb.org/mariadb_release_signing_key.pgp' | gpg --dearmor -o /etc/apt/keyrings/mariadb.gpg  \
    && echo "deb [signed-by=/etc/apt/keyrings/mariadb.gpg] https://mirror.rackspace.com/mariadb/repo/10.6/ubuntu focal main" | tee -a /etc/apt/sources.list.d/mariadb.list \
    && echo "deb-src [signed-by=/etc/apt/keyrings/mariadb.gpg] https://mirror.rackspace.com/mariadb/repo/10.6/ubuntu focal main" | tee -a /etc/apt/sources.list.d/mariadb.list \
    && apt-get update \
    && apt-get --yes --no-install-suggests --no-install-recommends build-dep mariadb-server \
    && rm -rf /var/lib/apt/lists/*
