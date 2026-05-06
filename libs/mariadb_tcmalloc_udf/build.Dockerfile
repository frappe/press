ARG MARIADB_VERSION=10.6
FROM ubuntu:20.04

ARG MARIADB_VERSION
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates git cmake make \
        gcc g++ bison libncurses5-dev libgnutls28-dev \
        gcc-aarch64-linux-gnu libc6-dev-arm64-cross && \
    rm -rf /var/lib/apt/lists/*

# Clone only the needed depth; cmake configure generates my_config.h
RUN git clone --depth 1 --branch ${MARIADB_VERSION} \
        https://github.com/MariaDB/server /mariadb-src

RUN cmake -S /mariadb-src -B /tmp/cmake-conf -DWITHOUT_SERVER=ON -Wno-dev && \
    cp /tmp/cmake-conf/include/*.h /mariadb-src/include/

WORKDIR /build
COPY tcmalloc_udf.c .

RUN set -eux; \
    INC="-I/mariadb-src/include"; \
    gcc -O2 -Wall -Wextra -fPIC ${INC} \
        -shared -o tcmalloc_udf-mariadb${MARIADB_VERSION}-x86_64.so \
        tcmalloc_udf.c -ldl; \
    aarch64-linux-gnu-gcc -O2 -Wall -Wextra -fPIC ${INC} \
        -shared -o tcmalloc_udf-mariadb${MARIADB_VERSION}-aarch64.so \
        tcmalloc_udf.c -ldl; \
    ls -lh /build/*.so

CMD cp /build/*.so /out/
