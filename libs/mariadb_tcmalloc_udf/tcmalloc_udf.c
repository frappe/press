#define _GNU_SOURCE
#include <mysql.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <pthread.h>

typedef void (*fn_get_stats)(char *buf, int len);
typedef int  (*fn_get_num_prop)(const char *property, size_t *value);
typedef void (*fn_release_free)(void);
typedef void (*fn_release_bytes)(size_t n);

static fn_get_stats     tc_get_stats    = NULL;
static fn_get_num_prop  tc_get_num_prop = NULL;
static fn_release_free  tc_release_free = NULL;
static fn_release_bytes tc_rel_bytes    = NULL;

static pthread_once_t   tc_resolve_once = PTHREAD_ONCE_INIT;

static void resolve_tcmalloc_symbols(void)
{
    tc_get_stats    = (fn_get_stats)   dlsym(RTLD_DEFAULT, "MallocExtension_GetStats");
    tc_get_num_prop = (fn_get_num_prop)dlsym(RTLD_DEFAULT, "MallocExtension_GetNumericProperty");
    tc_release_free = (fn_release_free)dlsym(RTLD_DEFAULT, "MallocExtension_ReleaseFreeMemory");
    tc_rel_bytes    = (fn_release_bytes)dlsym(RTLD_DEFAULT, "MallocExtension_ReleaseToSystem");
}

static void ensure_resolved(void)
{
    pthread_once(&tc_resolve_once, resolve_tcmalloc_symbols);
}

#define REQUIRE_LD_SYMBOL(msg_buf, sym)                                              \
    do {                                                                       \
        if (!(sym)) {                                                          \
            strncpy((msg_buf),                                                 \
                    "tcmalloc not available - check LD_PRELOAD", 80);         \
            return 1;                                                          \
        }                                                                      \
    } while (0)

#define STATS_BUF_SIZE (64 * 1024)   // for tcmalloc output


/* =========================================================================
For every UDF function, MySQL looks for three C functions with specific signatures :
  x_init()    - called once when the function is first used; returns 0 on success
  x()         - called for each invocation of the function in a query
  x_deinit()  - called once when the server shuts down or the function is unloaded
* =========================================================================/

/* =========================================================================
* tcmalloc_stats() -> STRING
* Returns a human-readable string of tcmalloc stats, as produced by
* MallocExtension::GetStats().  This includes data for debugging.
* ========================================================================= */

my_bool tcmalloc_stats_init(UDF_INIT *initid, UDF_ARGS *args, char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_stats() takes no arguments", 80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_get_stats);

    initid->ptr = (char *)malloc(STATS_BUF_SIZE);
    if (!initid->ptr) {
        strncpy(message, "tcmalloc_stats: out of memory", 80);
        return 1;
    }
    initid->max_length  = STATS_BUF_SIZE;
    initid->maybe_null  = 0;
    initid->const_item  = 0;
    return 0;
}

char *tcmalloc_stats(UDF_INIT *initid,
                     UDF_ARGS *args     __attribute__((unused)),
                     char     *result   __attribute__((unused)),
                     unsigned long *length,
                     char *is_null, char *error)
{
    if (!tc_get_stats) { *is_null = 1; *error = 1; return NULL; }
    tc_get_stats(initid->ptr, STATS_BUF_SIZE);
    *length = (unsigned long)strnlen(initid->ptr, STATS_BUF_SIZE);
    return initid->ptr;
}

void tcmalloc_stats_deinit(UDF_INIT *initid)
{
    free(initid->ptr);
    initid->ptr = NULL;
}

/* =========================================================================
 * tcmalloc_allocated_bytes() -> BIGINT
 * Bytes currently allocated and in use by the application
 * (generic.current_allocated_bytes).
 * ========================================================================= */

my_bool tcmalloc_allocated_bytes_init(UDF_INIT *initid, UDF_ARGS *args,
                                      char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_allocated_bytes() takes no arguments", 80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_get_num_prop);
    initid->maybe_null = 0;
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_allocated_bytes(UDF_INIT *initid __attribute__((unused)),
                                   UDF_ARGS *args   __attribute__((unused)),
                                   char *is_null    __attribute__((unused)),
                                   char *error)
{
    size_t val = 0;
    if (!tc_get_num_prop ||
        !tc_get_num_prop("generic.current_allocated_bytes", &val)) {
        *error = 1;
        return 0;
    }
    return (long long)val;
}

/* =========================================================================
 * tcmalloc_heap_size() -> BIGINT
 * Total bytes obtained from the OS for the heap
 * (generic.heap_size).
 * ========================================================================= */

my_bool tcmalloc_heap_size_init(UDF_INIT *initid, UDF_ARGS *args, char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_heap_size() takes no arguments", 80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_get_num_prop);
    initid->maybe_null = 0;
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_heap_size(UDF_INIT *initid __attribute__((unused)),
                             UDF_ARGS *args   __attribute__((unused)),
                             char *is_null    __attribute__((unused)),
                             char *error)
{
    size_t val = 0;
    if (!tc_get_num_prop ||
        !tc_get_num_prop("generic.heap_size", &val)) {
        *error = 1;
        return 0;
    }
    return (long long)val;
}

/* =========================================================================
 * tcmalloc_free_bytes() -> BIGINT
 * Total bytes held free inside tcmalloc across all cache tiers:
 *   pageheap_free  + central_cache_free + transfer_cache_free
 *                  + thread_cache_free
 *
 * This is memory tcmalloc owns but has not yet returned to the OS and is
 * not currently handed out to the application.
 * ========================================================================= */

my_bool tcmalloc_free_bytes_init(UDF_INIT *initid, UDF_ARGS *args, char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_free_bytes() takes no arguments", 80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_get_num_prop);
    initid->maybe_null = 0;
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_free_bytes(UDF_INIT *initid __attribute__((unused)),
                              UDF_ARGS *args   __attribute__((unused)),
                              char *is_null    __attribute__((unused)),
                              char *error)
{
    size_t pageheap = 0, central = 0, transfer = 0, thread = 0;

    if (!tc_get_num_prop) { *error = 1; return 0; }

    /* Ignore individual return values – unavailable properties stay 0. */
    tc_get_num_prop("tcmalloc.pageheap_free_bytes",      &pageheap);
    tc_get_num_prop("tcmalloc.central_cache_free_bytes", &central);
    tc_get_num_prop("tcmalloc.transfer_cache_free_bytes",&transfer);
    tc_get_num_prop("tcmalloc.thread_cache_free_bytes",  &thread);

    return (long long)(pageheap + central + transfer + thread);
}

/* =========================================================================
 * tcmalloc_property(name VARCHAR) -> BIGINT
 * Generic accessor for any MallocExtension numeric property.
 * Returns NULL if the property name is unknown.
 *
 * Useful property names:
 *   generic.current_allocated_bytes
 *   generic.heap_size
 *   tcmalloc.pageheap_free_bytes
 *   tcmalloc.pageheap_unmapped_bytes
 *   tcmalloc.slack_bytes
 *   tcmalloc.central_cache_free_bytes
 *   tcmalloc.transfer_cache_free_bytes
 *   tcmalloc.thread_cache_free_bytes
 *   tcmalloc.max_total_thread_cache_bytes
 *   tcmalloc.current_total_thread_cache_bytes
 *   tcmalloc.aggressive_memory_decommit
 * ========================================================================= */

my_bool tcmalloc_property_init(UDF_INIT *initid, UDF_ARGS *args, char *message)
{
    ensure_resolved();
    if (args->arg_count != 1 || args->arg_type[0] != STRING_RESULT) {
        strncpy(message,
                "tcmalloc_property(name STRING) requires one string argument",
                80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_get_num_prop);
    initid->maybe_null = 1;   /* NULL when the property name is unknown */
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_property(UDF_INIT *initid __attribute__((unused)),
                            UDF_ARGS *args,
                            char *is_null, char *error __attribute__((unused)))
{
    size_t val  = 0;
    char  *name = args->args[0];

    if (!name || !tc_get_num_prop) { *is_null = 1; return 0; }
    if (!tc_get_num_prop(name, &val)) { *is_null = 1; return 0; }
    return (long long)val;
}

/* =========================================================================
 * tcmalloc_release_memory() -> BIGINT
 * Calls MallocExtension_ReleaseFreeMemory() to return all free pages in the
 * page heap back to the OS.
 *
 * Returns the number of bytes released (pageheap_free_bytes before the call
 * minus pageheap_free_bytes after the call).  This is an approximation
 * because other threads may allocate/free concurrently.
 * ========================================================================= */

my_bool tcmalloc_release_memory_init(UDF_INIT *initid, UDF_ARGS *args,
                                     char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_release_memory() takes no arguments", 80);
        return 1;
    }
    REQUIRE_LD_SYMBOL(message, tc_release_free);
    initid->maybe_null = 0;
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_release_memory(UDF_INIT *initid __attribute__((unused)),
                                  UDF_ARGS *args   __attribute__((unused)),
                                  char *is_null    __attribute__((unused)),
                                  char *error)
{
    size_t free_before = 0, unmapped_before = 0;
    size_t free_after  = 0, unmapped_after  = 0;

    if (!tc_release_free) { *error = 1; return 0; }

    if (tc_get_num_prop) {
        tc_get_num_prop("tcmalloc.pageheap_free_bytes",     &free_before);
        tc_get_num_prop("tcmalloc.pageheap_unmapped_bytes", &unmapped_before);
    }

    tc_release_free();

    if (tc_get_num_prop) {
        tc_get_num_prop("tcmalloc.pageheap_free_bytes",     &free_after);
        tc_get_num_prop("tcmalloc.pageheap_unmapped_bytes", &unmapped_after);
    }

    /*
     * Report bytes actually decommitted to the OS:
     * = free pages that moved to unmapped state
     * = increase in unmapped + decrease in free
     * (both should be equal; use the larger for safety)
     */
    size_t by_unmapped = unmapped_after > unmapped_before
                         ? unmapped_after - unmapped_before : 0;
    size_t by_free     = free_before > free_after
                         ? free_before - free_after : 0;
    return (long long)(by_unmapped > by_free ? by_unmapped : by_free);
}

/* =========================================================================
 * tcmalloc_available() -> BIGINT
 * Returns 1 if the tcmalloc allocator is active (i.e. its symbols were
 * resolved via LD_PRELOAD), 0 otherwise.  No side-effects.
 * ========================================================================= */

my_bool tcmalloc_available_init(UDF_INIT *initid, UDF_ARGS *args, char *message)
{
    ensure_resolved();
    if (args->arg_count != 0) {
        strncpy(message, "tcmalloc_available() takes no arguments", 80);
        return 1;
    }
    initid->maybe_null = 0;
    initid->const_item = 0;
    return 0;
}

long long tcmalloc_available(UDF_INIT *initid __attribute__((unused)),
                             UDF_ARGS *args   __attribute__((unused)),
                             char *is_null    __attribute__((unused)),
                             char *error      __attribute__((unused)))
{
    return (tc_get_stats != NULL) ? 1LL : 0LL;
}

void tcmalloc_available_deinit(UDF_INIT *initid __attribute__((unused))) {}
