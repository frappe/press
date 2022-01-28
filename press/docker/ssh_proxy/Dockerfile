# syntax = docker/dockerfile:experimental
FROM ubuntu:20.04

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND noninteractive

# Install essential packages
RUN --mount=type=cache,target=/var/cache/apt apt-get update \
  && apt-get install --yes --no-install-suggests --no-install-recommends \
  openssh-server \
  && rm -rf /var/lib/apt/lists/* \
  `#stage-pre-essentials`

RUN mkdir /run/sshd

EXPOSE 22
VOLUME ["/home", "/etc"]
CMD ["/usr/sbin/sshd", "-D", "-e"]
