# MariaDB Table Usage

This tool reports usage statistics for InnoDB and MyISAM tables.

- For InnoDB, it parses table pages and segment nodes to calculate usage accurately.
- For MyISAM, it reads file stats.

The tool reports the following information per table :

- data_length : Size of table data (In case of InnoDB, it includes the primary index usage as well)
- index_length : Usage of secondary indexes (In case of MyISAM, size of `MYI` file)
- data_free : Deleted or uninitialized space (InnoDB only)

## Usage

```
from mariadb_table_usage import usage

data = usage("test_db")
```

## Why not rely on the database ?

To get the same information from the database, we usually run:

```sql
SELECT data_length, index_length, data_free
FROM information_schema.tables
WHERE table_schema = 'test_db'
```

This query can cause disk I/O issues on shared database servers, especially when many small databases exist on the same host.

Related issues and references:

- https://bugs.mysql.com/bug.php?id=19588
- https://dev.mysql.com/doc/refman/8.4/en/information-schema-optimization.html

Although MySQL and MariaDB have improved this over time, there are still some fundamental problems.

## Problems with information_schema approach

When MariaDB calculates table usage using information_schema.tables, it needs to open each table and inspect its metadata.

If a database has many tables (for example, hundreds or thousands), this creates a few issues:

- The database has a limited [table_open_cache](https://dev.mysql.com/doc/refman/8.4/en/table-cache.html). Opening many tables for metadata queries can evict entries from the cache, which affects both subsequent metadata queries and normal production queries.

- The database engine treats `information_schema` queries like regular queries and does not consider system-level disk I/O limits.

- Unlike normal queries, `information_schema` queries with dynamic column do not benefit much from the InnoDB buffer pool and often result in direct disk reads.

- MariaDB may use multiple threads to calculate usage, which can further increase disk I/O pressure.

For each InnoDB table, the engine typically needs to read at least:

- The FSP header page
- The clustered index root page
- Non-leaf segment node page

Each page is 16 KB, so even a single table requires multiple disk reads. When this is repeated across many tables, disk I/O can spike quickly.

Sometimes the query appears fast because the required pages are already cached. However, this cache can be cleared:

- periodically
- after DDL operations
- when more than 10% of a table is modified

When the cache is cleared, the same query can suddenly cause heavy disk I/O and impact the entire server.

### Frappe Cloud Scenario

In Frappe Cloud, shared servers host a large number of very small sites. At minimum, site migrations happen once a week, and these migrations usually modify a few tables in each site database.

After such operations, metadata caches are often invalidated (theoretically). If usage information is then queried sequentially for each site’s database, information_schema queries can trigger disk reads for every table across many databases. This can lead to a sudden and significant disk I/O spike and, in some cases, a temporary I/O freeze on the server.

## Approach of this tool

This tool reads table files directly instead of querying the database engine.

It limits disk reads to a configurable rate (default: 200 ops/sec). This ensures consistent IO pressure regardless of how fast the files can be read.

It also monitors CPU iowait and pauses or stops its work if a configured threshold is reached. This helps keep the database server responsive.

Concurrency can be controlled to limit parallel table scans. For InnoDB tables, each table scan typically reads a few pages (FSP header, clustered index root, segment nodes). Each page is 16 KB.

By combining rate limiting, iowait monitoring, and concurrency control, the tool focuses on stability rather than speed and avoids putting excessive load on the disk.

## Resources to Understand

The parser and library has been written based on this following resources

- InnoDB Internals PPT : https://speakerdeck.com/xy/innodb-internals
- Great blogs to learn about InnoDB file structures :
  - https://blog.jcole.us/2013/01/02/on-learning-innodb-a-journey-to-the-core/
  - https://blog.jcole.us/2013/01/03/the-basics-of-innodb-space-file-layout/
  - https://blog.jcole.us/2013/01/04/page-management-in-innodb-space-files/
  - https://blog.jcole.us/2013/01/07/the-physical-structure-of-innodb-index-pages/
- InnoDB Parser in Ruby for Learning : https://github.com/jeremycole/innodb_ruby/blob/main/bin/innodb_space
- MariaDB Source Code : https://github.com/MariaDB/server

The codebase also includes comments explaining the implementation and references to the corresponding C source code.
