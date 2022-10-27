---
title: Local Infrastruture
---

# Local Infrastructure

Local infrastructure subsystem is a faster, cheaper and more flexible alternative to running virtual machines on a public cloud for development.

> Note: Local Insfrastructure is available for Linux hosts only. You're free to add Mac OS support by using Virtualbox.

## Prerequisites

#### Dependencies

- Packer - For building virtual machine images.
- Vagrant - Simplified CLI/API for managing virtual hosts.
    - vagrant-libvirt - For using KVM/Libvirt. Duh!
    - vagrant-hostmanager - For managing hosts file in guests and host machine.

- Libvirt/KVM - Virtualization provider.

### Installation
Dependencies can be installed with 

```bash
source env/bin/activate
python3 apps/press/backbone/setup.py
```
> Note: After this logout completely and login again to start with local infrastructure. Start a new shell session. if you're on a Non-GUI server.

### Building Base Images

To spawn virtual machines quickly, we'll create a ubuntu base image (as seen on DigitalOcean or other cloud providers). This image can later be used to spawn blank virtual machines in seconds.

This can be done with (`backbone` CLI is installed with `press` application)

```bash
source env/bin/activate
backbone hypervisor build
```

> Note: When running for the very first time this will download a ~500 MB ubuntu image.

See contents of `press/backbone/packer` directory for more details.

### Spawning Virtual Machines
There's no simple CLI for this at the moment. 

1. Create a Vagrant directory
```bash
mkdir scratch
cd scratch
ln -s ../apps/press/backbone/vagrant/Vagrantfile Vagrantfile
```

2. Start local cluster with the following command and provide sudo password when asked
```
vagrant up --no-parallel --provider=libvirt
```

You can destroy the machines with 
```
vagrant destroy -f
```
and spawn them again with `vagrant up` command.

Local machines have following names/ips by default

|Type               |Name       |Public IP  |Private IP | 
|-------------------|-----------|-----------|-----------|
|Proxy Server       |n1.fc.dev  |10.0.1.101 |10.1.1.101 |
|Frappe Server      |f1.fc.dev  |10.0.2.101 |10.1.2.101 |
|Database Server    |m1.fc.dev  |10.0.3.101 |10.1.3.101 |
|Database Server    |m2.fc.dev  |10.0.3.102 |10.1.3.102 |

### Accessing VMs

You can ssh into these machines using following commands

```bash
ssh root@n1.fc.dev
```
```bash
vagrant ssh n1
```
