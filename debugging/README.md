# debugging

Tools to find the cause of a MariaDB crash on a database server.

MariaDB in production has no debug symbols, so its stacktraces are not usable.
These Dockerfiles build the same MariaDB version with symbols. You load the
coredump from the server into the container and get a readable stacktrace.

- [mariadb.md](mariadb.md) — take a coredump and read the stacktrace
- [mariadb.build.md](mariadb.build.md) — build MariaDB from source with symbols
- `mariadb.Dockerfile` — MariaDB 10.6 with debug symbols
- `mariadb.build.Dockerfile` — the build environment for a source build

## Replica reads

A site with `read_from_replica` on sends some requests to the replica. If the
replica is behind, the user sees data that is not there yet.

- `scan-replica-reads.sh` — list the endpoints that read from the replica, and
  the custom app code that changes the read path. Read only. Run it from the
  bench directory of the server.
