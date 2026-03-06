FROM ubuntu:20.04

# Pre requisites
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y && \
    apt install -y wget ca-certificates g++-aarch64-linux-gnu g++-arm-linux-gnueabi python3-dev python3 python3-pip gcc g++ clang --no-install-recommends

# Install golang 1.24.3
RUN wget https://go.dev/dl/go1.24.3.linux-amd64.tar.gz  -O /go1.24.3.linux-amd64.tar.gz
RUN rm -rf /usr/local/go && tar -C /usr/local -xzf /go1.24.3.linux-amd64.tar.gz

# Install twine
RUN pip3 install -U pip setuptools wheel
RUN pip3 install twine

ENV PATH=$PATH:/usr/local/go/bin
ENV CGO_ENABLED=1
ENV TWINE_USERNAME=__token__