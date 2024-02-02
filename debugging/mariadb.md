Generate coredump on the affected MariaDB server.

```sh
pgrep mariadbd | xargs gcore
```

This will create a `core.<x>` where `<x>` is the pid of MariaDB proces. The core file is likely to be `~5G` in size. Compress it.

```sh
gzip core.<x>
```

Compressed `core.<x>.gz` should be around `~5OM.

---

Build the MariaDB debug container.

```sh
docker build -t mariadb-debug:10.6 -f mariadb.Dockerfile .
```

This has the latest MariaDB 10.6 with all the debug symbols necessary to generate a useful stacktrace.

---

Copy the coredump locally for debugging.

```
scp -C -oProxyCommand="ssh -o 'ForwardAgent yes' frappe@frappe.cloud 'ssh-add && nc %h %p'" root@m<y>-mumbai.frappe.cloud:/root/core.<x>.gz .
```

Extract the compressed core file.

```sh
gzip -d core.<x>.gz
```

You'll get the `core.<x>` file back. Generate complete stacktrace.

```sh
docker run -v ./core.<x>:/core -v --rm -it mariadb-debug:10.6 gdb --batch --eval-command="set print frame-arguments all" --eval-command="thread apply all bt full" /usr/sbin/mariadbd /core > stack.txt
```

or launch gdb.

```sh
docker run -v ./core.<x>:/core -v --rm -it mariadb-debug:10.6 gdb /usr/sbin/mariadbd /core
```
