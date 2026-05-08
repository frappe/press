# tcmalloc_udf

MariaDB UDF plugin that exposes tcmalloc internals as SQL functions. Requires tcmalloc to be loaded via `LD_PRELOAD` — functions return errors or 0 when it's not active.

## Functions

| Function | Returns | Description |
|---|---|---|
| `tcmalloc_available()` | INT | 1 if tcmalloc is active, 0 otherwise |
| `tcmalloc_stats()` | STRING | Full stats dump from `MallocExtension_GetStats` |
| `tcmalloc_allocated_bytes()` | BIGINT | Bytes currently in use by the application |
| `tcmalloc_heap_size()` | BIGINT | Total bytes obtained from the OS |
| `tcmalloc_free_bytes()` | BIGINT | Bytes held free inside tcmalloc (not returned to OS) |
| `tcmalloc_property(name)` | BIGINT | Any numeric property by name, NULL if unknown |
| `tcmalloc_release_memory()` | BIGINT | Releases free pages to OS, returns bytes released |

## Build

Requires Docker. Produces `.so` files for x86\_64 and aarch64, for MariaDB 10.4, 10.6, and 11.8.

```bash
./build.sh
# output in ./dist/
```

## Install

Copy the `.so` matching your MariaDB version and server architecture to the plugin directory:

```bash
# find the plugin directory
mariadb_config --plugindir

# copy
cp dist/tcmalloc_udf-mariadb10.6-x86_64.so /path/to/plugin/dir/tcmalloc_udf.so
```

Then register the functions in MariaDB:

```sql
CREATE FUNCTION IF NOT EXISTS tcmalloc_available    RETURNS INTEGER SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_stats        RETURNS STRING  SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_allocated_bytes RETURNS INTEGER SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_heap_size    RETURNS INTEGER SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_free_bytes   RETURNS INTEGER SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_property     RETURNS INTEGER SONAME 'tcmalloc_udf.so';
CREATE FUNCTION IF NOT EXISTS tcmalloc_release_memory RETURNS INTEGER SONAME 'tcmalloc_udf.so';
```

## Uninstall

```sql
DROP FUNCTION IF EXISTS tcmalloc_available;
DROP FUNCTION IF EXISTS tcmalloc_stats;
DROP FUNCTION IF EXISTS tcmalloc_allocated_bytes;
DROP FUNCTION IF EXISTS tcmalloc_heap_size;
DROP FUNCTION IF EXISTS tcmalloc_free_bytes;
DROP FUNCTION IF EXISTS tcmalloc_property;
DROP FUNCTION IF EXISTS tcmalloc_release_memory;
```
