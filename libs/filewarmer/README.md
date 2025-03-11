### filewarmer - File Warm Up Helper

This library will do nothing but try to read file blocks as fast as possible.

It's useful to initialize/pre-warm volumes.

### Installation

```bash
pip install filewarmer
```

### Usage

```python
from filewarmer import FWUP

fwup = FWUP()
fwup.warmup(
    ["/var/lib/mysql/abc_demo/tab@020Sales@020Invoice.ibd", "/var/lib/mysql/abc_demo/tab@020Sales@020Invoice.ibd"]
    method="io_uring",
    small_file_size_threshold=1024 * 1024,
    block_size_for_small_files=256 * 1024,
    block_size_for_large_files=256 * 1024,
    small_files_worker_count=1,
    large_files_worker_count=1,
)
```

**Notes -**

- Block size's unit is bytes.
- For io_uring, it's recommended to use Linux Kernel 5.1 or higher.
- For io_uring, use a single thread to submit the requests.

### Build + Publish

```bash
TWINE_PASSWORD=xxxxxx VERSION=0.0.10 ./build.sh
```

> In the `TWINE_PASSWORD` put the API key of the PyPi account.

### Why this library?

Once you create a new RBS volume from a snapshot, you will not get performance as expected. It's because AWS keep the Snapshot in S3 and when you try to access certain blocks of the volume, it will download the blocks from S3 to the EBS volume. This process is called "Lazy Loading".

But for our database physical restoration process, we need to pre-warm selected files for validation and copying to target directory. To make next process faster, we need to pre-warm the files beforehand.

The [AWS documentation](https://docs.aws.amazon.com/ebs/latest/userguide/ebs-initialize.html) suggests to use `dd` or `fio` to pre-warm the files. But both of them are not optimized for this purpose and we can get at max 25~40MB/s speed on a 3000IOPS 600MB/s disk. But with this library, we can get almost 90% of speed.

In the library, we also do batching of small files. In case of database, we have lot of small files and reading them and waiting for the io completion will take more time. So, we read them in batches.

In **io_uring**, we can submit multiple requests and wait for the completion of all of them.

Assume, small files are those <= 1MB.

In io_uring we are submitting 64 requests at a time.

1MB = 256KB \* 4

So, we can submit (64/4) = 16 small 1MB files i/o requests at a time.

This will reduce the overhead of submitting the requests and waiting for the io completion.

So, in case of io_uring, we should run only two threads to submit the requests.

- One for small files
- Another for large files

**Note** > We have also support for `psync` which is default in most of the io operation due to support in every Linux Kernel. For Linux Kernel 5.1 or higher, we should use `io_uring` which is faster than `psync`.

### License

Apache 2.0
