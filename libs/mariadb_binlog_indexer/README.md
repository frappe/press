## MariaDB Binlog Indexer

This tool helps to index mariadb binlogs and store them in compact format to query faster.

### File Format

- **DuckDB** - Store all the metadata of binlogs.
- **Parquet** - Store the actual queries.

### DB Schema

```
┌─────────────┬─────────────┬─────────┬─────────┬─────────┬─────────┐
│ column_name │ column_type │  null   │   key   │ default │  extra  │
│   varchar   │   varchar   │ varchar │ varchar │ varchar │ varchar │
├─────────────┼─────────────┼─────────┼─────────┼─────────┼─────────┤
│ binlog      │ VARCHAR     │ YES     │ NULL    │ NULL    │ NULL    │
│ db_name     │ VARCHAR     │ YES     │ NULL    │ NULL    │ NULL    │
│ table_name  │ VARCHAR     │ YES     │ NULL    │ NULL    │ NULL    │
│ timestamp   │ INTEGER     │ YES     │ NULL    │ NULL    │ NULL    │
│ type        │ VARCHAR     │ YES     │ NULL    │ NULL    │ NULL    │
│ row_id      │ INTEGER     │ YES     │ NULL    │ NULL    │ NULL    │
│ event_size  │ INTEGER     │ YES     │ NULL    │ NULL    │ NULL    │
└─────────────┴─────────────┴─────────┴─────────┴─────────┴─────────┘
```

### Usage

Before starting up please note down,

- All the timestamps are in seconds UTC
- Available query types are `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `OTHER`

Also, check the python docstrings for more details.

#### Initialize Indexer

```python
from mariadb_binlog_indexer import Indexer

indexer = Indexer(
    base_path="<path to store indexer related files>",
    db_name="metadata.db", # The name of the database to store metadata
)
```

#### Index New Binlog

```python
indexer.add(
    binlog_path="<path to binlog>",
    batch_size=10000, # The batch size to insert binlog in duckdb
)
```

#### Remove Indexes of Binlog

```python
indexer.remove(
    binlog_path="<path to binlog>",
)
```

#### Generate Timeline

This function will provide a summary of binlog event in a given time range. It will split the time range into 30 parts and provide event related information for each part.

```python
indexer.get_timeline(
    start_timestamp=1746534427, # The start timestamp in seconds UTC
    end_timestamp=1756534427, # The end timestamp in seconds UTC,
    type="INSERT", # Optional
    database="test_db", # Optional
)
```

#### Get Row Ids

This function will help to get the row ids of each binlog based on our request.
The purpose of this function is to help finding required row ids beforehand to implement pagination on the other end.

Only reason of doing this is to reduce the search in the parquet files.

```python
indexer.get_row_ids(
    start_timestamp=1746534427, # The start timestamp in seconds UTC
    end_timestamp=1756534427, # The end timestamp in seconds UTC,
    type="INSERT", # Optional
    database="test_db", # Optional
    table="test_table", # Optional
    search_str="test", # Optional
)
```

#### Get Queries from Parquet Files

This function will help to get the queries from parquet files.

```python
indexer.get_queries(
    row_ids={
        "binlog_1": [101, 102, 103],
        "binlog_2": [104, 105, 106],
    },
    database="test_db", # Optional
)
```

You need to provide database name as filtering purpose only.
