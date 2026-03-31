FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y && \
    apt install -y wget ca-certificates g++-aarch64-linux-gnu g++-arm-linux-gnueabi python3-dev python3 python3-pip gcc g++ clang --no-install-recommends

ARG GO_VERSION=1.24.3
RUN ARCH=$(dpkg --print-architecture) && \
    case "$ARCH" in \
        amd64) GOARCH=amd64 ;; \
        arm64) GOARCH=arm64 ;; \
        armhf) GOARCH=armv6l ;; \
        *) echo "unsupported architecture: $ARCH" && exit 1 ;; \
    esac && \
    wget -q https://go.dev/dl/go${GO_VERSION}.linux-${GOARCH}.tar.gz -O /tmp/go.tar.gz && \
    rm -rf /usr/local/go && \
    tar -C /usr/local -xzf /tmp/go.tar.gz && \
    rm /tmp/go.tar.gz

RUN apt install -y llvm
WORKDIR /app

RUN apt install git make -y
RUN apt install -y bpfcc-tools


RUN apt install -y --no-install-recommends \
      clang llvm libbpf-dev libelf-dev zlib1g-dev \
      make git wget ca-certificates gcc g++ pkg-config \
      linux-headers-generic python3 python3-pip curl && \
    rm -rf /var/lib/apt/lists/*

COPY . .

ENV PATH="/usr/local/go/bin:${PATH}"
RUN go mod download


RUN go generate && go build -o mariadb_io_monitor .
CMD ["ls", "-lh", "mariadb_io_monitor"]