# debugging

Tools to find the cause of a MariaDB crash on a database server.

MariaDB in production has no debug symbols, so its stacktraces are not usable.
These Dockerfiles build the same MariaDB version with symbols. You load the
coredump from the server into the container and get a readable stacktrace.

- [mariadb.md](mariadb.md) — take a coredump and read the stacktrace
- [mariadb.build.md](mariadb.build.md) — build MariaDB from source with symbols
- `mariadb.Dockerfile` — MariaDB 10.6 with debug symbols
- `mariadb.build.Dockerfile` — the build environment for a source build
