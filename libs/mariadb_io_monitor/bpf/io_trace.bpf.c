#include "vmlinux.h"
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_tracing.h>
#include <bpf/bpf_core_read.h>

char LICENSE[] SEC("license") = "GPL";

// Kind of a boolean map to indicate whether to process events globally
struct
{
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, u32);
    __type(value, u8);
} global_processing_flag SEC(".maps");

// eBPF Map to hold the PIDs to be tracked
struct
{
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 256);
    __type(key, u32);
    __type(value, u8);
} pids SEC(".maps");

// Perf array to send events to user-space
struct
{
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
} events SEC(".maps");

// Structure of event data to be sent to user-space
struct event
{
    u32 pid;    // process id
    u32 tid;    // thread id
    u8 op;      // 'R' or 'W'
    u8 stage;   // 'E' for entry, 'X' for exit
    u8 _pad[6]; // align next u64
    u64 bytes;
    char comm[32];       // process name
    char directory[128]; // directory path
    char filename[128];  // file name
};

struct
{
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 16384);
    __type(key, u64);
    __type(value, u64);
} requests SEC(".maps");

// Function signatures
static __always_inline int is_global_processing_enabled();
static __always_inline int should_track_current_event(struct file *file);
static __always_inline void fill_event_details(struct event *ev, u8 op, u8 stage, size_t count, struct file *file);
static __always_inline void store_file_ptr_during_entry(struct file *file);
static __always_inline struct file *get_file_ptr_from_map(struct pt_regs *ctx);

// [ENTRY] Kprobes for Read and Write

SEC("kprobe/vfs_write")
int BPF_KPROBE(kprobe__vfs_write,
               struct file *file,
               const char *buf,
               size_t count,
               loff_t *pos)
{
    if (!file)
        return 0;

    if (!is_global_processing_enabled())
        return 0;

    if (!should_track_current_event(file))
        return 0;

    store_file_ptr_during_entry(file);

    struct event ev = {};
    fill_event_details(&ev, 'W', 'E', count, file);
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("kprobe/vfs_read")
int BPF_KPROBE(kprobe__vfs_read,
               struct file *file,
               char *buf,
               size_t count,
               loff_t *pos)
{
    if (!file)
        return 0;

    if (!is_global_processing_enabled())
        return 0;

    if (!should_track_current_event(file))
        return 0;

    /* store file pointer for the corresponding exit probe */
    store_file_ptr_during_entry(file);

    struct event ev = {};
    fill_event_details(&ev, 'R', 'E', count, file);
    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

// [EXIT] Kretprobes for Read and Write

SEC("kretprobe/vfs_write")
int BPF_KRETPROBE(kretprobe__vfs_write)
{
    if (!is_global_processing_enabled())
        return 0;

    s64 ret = (s64)PT_REGS_RC(ctx);
    struct file *file = get_file_ptr_from_map(ctx);
    if (!file)
        return 0;

    if (!should_track_current_event(file))
        return 0;

    struct event ev = {};
    fill_event_details(&ev, 'W', 'X', (size_t)ret, file);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

SEC("kretprobe/vfs_read")
int BPF_KRETPROBE(kretprobe__vfs_read)
{
    if (!is_global_processing_enabled())
        return 0;

    s64 ret = (s64)PT_REGS_RC(ctx);
    struct file *file = get_file_ptr_from_map(ctx);
    if (!file)
        return 0;

    if (!should_track_current_event(file))
        return 0;

    struct event ev = {};
    fill_event_details(&ev, 'R', 'X', (size_t)ret, file);

    bpf_perf_event_output(ctx, &events, BPF_F_CURRENT_CPU, &ev, sizeof(ev));
    return 0;
}

// Helper functions

static __always_inline int is_global_processing_enabled()
{
    u32 key = 0;
    u8 *val = bpf_map_lookup_elem(&global_processing_flag, &key);
    if (val && *val)
    {
        return 1;
    }
    return 0;
}

static __always_inline int should_track_current_event(struct file *file)
{
    u64 tg = bpf_get_current_pid_tgid();
    u32 pid = (u32)(tg >> 32);

    // Check pids in track list
    u8 *val = bpf_map_lookup_elem(&pids, &pid);
    if (val)
    {
        // Track only regular file operations
        unsigned long i_mode = BPF_CORE_READ(file, f_inode, i_mode);
        const unsigned long S_IFREG = 0100000UL;
        const unsigned long S_IFMT = 0170000UL;
        if ((i_mode & S_IFMT) != S_IFREG)
            return 0;

        // Allowed to track
        return 1;
    }

    return 0;
}

static __always_inline void store_file_ptr_during_entry(struct file *file)
{
    u64 key = bpf_get_current_pid_tgid();
    u64 file_ptr = (u64)(uintptr_t)file;
    bpf_map_update_elem(&requests, &key, &file_ptr, BPF_ANY);
}

static __always_inline struct file *get_file_ptr_from_map(struct pt_regs *ctx)
{
    s64 ret = (s64)PT_REGS_RC(ctx);
    u64 key = bpf_get_current_pid_tgid();

    // Check in requests map
    u64 *file_ptr_p = bpf_map_lookup_elem(&requests, &key);
    struct file *f = NULL;
    if (file_ptr_p)
    {
        f = (struct file *)(uintptr_t)(*file_ptr_p);
        // Cleanup
        bpf_map_delete_elem(&requests, &key);
    }

    return f;
}

static __always_inline void fill_event_details(struct event *ev, u8 op, u8 stage, size_t count, struct file *file)
{
    u64 tg = bpf_get_current_pid_tgid();
    // [ 63 .. 32 ][ 31 .. 0 ]
    //     TGID       TID
    ev->pid = (u32)(tg >> 32);
    ev->tid = (u32)tg;
    ev->op = op;
    ev->stage = stage;
    ev->bytes = count;
    ev->filename[0] = '\0';
    ev->directory[0] = '\0';
    ev->comm[0] = '\0';

    bpf_get_current_comm(&ev->comm, sizeof(ev->comm));

    // Read the filename
    struct dentry *d = BPF_CORE_READ(file, f_path.dentry);
    if (d)
    {
        const char *fname = (const char *)BPF_CORE_READ(d, d_name.name);
        if (fname)
        {
            long ret_fn = bpf_core_read_str(ev->filename, sizeof(ev->filename), fname);
            if (ret_fn < 0)
            {
                /* on failure leave filename empty */
                ev->filename[0] = '\0';
            }
        }

        // Read parent dentry's name into directory
        struct dentry *parent = BPF_CORE_READ(d, d_parent);
        if (parent)
        {
            const char *pname = (const char *)BPF_CORE_READ(parent, d_name.name);
            if (pname)
            {
                long ret_dir = bpf_core_read_str(ev->directory, sizeof(ev->directory), pname);
                if (ret_dir < 0)
                {
                    ev->directory[0] = '\0';
                }
            }
        }
    }
}
