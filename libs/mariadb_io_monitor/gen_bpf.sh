#!/usr/bin/env bash
set -e
arch=$(uname -m)
[ "$arch" = "x86_64" ] && target="x86" || target="arm64"
GOPACKAGE=main go run github.com/cilium/ebpf/cmd/bpf2go -cc clang io_trace ./bpf/io_trace.bpf.c -- -O2 -g -target bpf -D__TARGET_ARCH_${target} -I.
