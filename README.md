## Press

![unittests](https://github.com/frappe/press/actions/workflows/main.yaml/badge.svg)


This is `press`, a Frappe custom app that runs Frappe Cloud. This app manages infrastructure, subscription, marketplace, SaaS and much more.

> press: "I have a brother, without which I cannot live, agent"

The other half of the Frappe Cloud infrastructure is [agent](https://github.com/frappe/agent). Which is a flask application that runs on every server in a typical cluster and carries out tasks on HTTP requests. Creating a new site, installing an app, updating a site, creating a bench and everything in between is just a request (`Agent Job`) away.

> Note that, this README is in a very early WIP state and only covers a tiny bit of FC. More to come!

## Typical FC Cluster

![FC Cluster Diagram](.github/images/fc-cluster.png)

## Prerequisites

- Frappe Bench (https://github.com/frappe/bench)
- Docker
- Certbot with route53 plugin
- AWS account (for route53 & S3)
- Digital Ocean account (for [container registry](https://www.digitalocean.com/products/container-registry))

## Local Setup

You can find a detailed walkthough for setting up a local FC cluster [here](https://frappecloud.com/docs/local-fc-setup).

## Some Core DocTypes

- Server
- Database Server
- Proxy Server
- Site
- Release Group
- Deploy Candidate
- Bench
- App
- App Source
- App Release
- TLS Certificate

## The Front-end

You can read more about the VueJS frontend for Frappe Cloud [here](./dashboard/README.md).

## Contributing

> Journey of a thousand PRs begins with a single typo fix!

You can contribute in many ways, some of which are:

1. Reporting Issues: If you find a bug, typo etc. Feel free to raise an issue and we will take it from there.

2. Feature PRs: You can start by creating an issue with a feature proposal, we can discuss whether we should go ahead with it or not.

3. Give us a star!

4. Documentation

#### License

[GNU Affero General Public License v3.0](https://github.com/frappe/press/blob/master/license.txt)
