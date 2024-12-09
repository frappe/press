# Explaining Choices

Most commits/comments already explain the decisions. Just putting them here for sanity.

## Mounts

Going forward the data (mostly machine-independent directories) will be kept on a separate volume.

For the migration we

1. Shut down the machine
2. Start a new machine (with a new ARM image)
3. Attach the root volume from the old machine to the new machine
4. Do some mount magic so all services find data where they expect it to be

### AWS Quirks

1. We can't attach a volume at boot. The VM must be in the Running state.
2. You can't rely on device_name provided during run_instance.
3. The device will have an alias that looks something like "/dev/disk/by-id/...<volume-id>..."

### Bind Mounts

Instead of directly mounting the volume to the target mount point, we

1. Mount the volume to /opt/volumes/<mariadb/docker>/
2. Bind mount the relative location from this path. /opt/volumes/mariadb/a/b/c to /a/b/c

This gives us the ability to

1. Have two different mounts (/etc/mysql and /var/lib/mysql)
2. Use the same old volumes as-is without any custom mounting scheme.

### Mount Dependency

We don't want MariaDB / Docker to start unless the data volume is mounted correctly.
Add a systemd mount dependency (BindsTo) so the services start if and only if the data volume is mounted.

Note: We define the dependency only on the bind mount. /opt/volumes... is left out as convenience.

### Relabeling

The base images are configured to mount partitions labeled UEFI and cloudimg-rootfs

1. We change these labels so the new machine doesn't accidentally boot from these
2. We update fstab so the old machine can still boot with the modified labels

Note: EFI partitions have a dirty bit set on them. fatlabel messes this up. We need to run fsck to fix this.

### UUID

When we spawn a new machine from the base image, all volumes get their own volume-id. If we rely on volume-id to determine the data volume then we'll have to do some extra work after the first boot. (To tell the machine about the volume)

When we format the data volume we get a new UUID. This UUID remains the same (since it's part of the data itself) across boots (unless we reformat the volume). This is the easiest way to recognize a volume in fstab.

During the migration, we need to do the extra step of updating fstab to use the old UUID (from the old root volume).

We could have modified the UUID of the old root volume (so we don't need to do any work after the migration). But

1. e2label needs a freshly checked disk (fsck)
2. fsck needs an unmounted partition. We can't unmount the root partition.

## Misc

### Hardcoded values

This is only going to be used for app and db servers.

- App servers will have /home/frappe/benches stored on the the data volume
- DB servers will have /var/lib/mysql and /etc/mysql stored on the data volume

### Wait for ping + cloud init

During the first boot we

1. Delete old host keys (to avoid collisions between multiple hosts)
2. Update SSH config
3. Restart SSHD

During this restart, for a short period, we can't start a new SSH session. (Sometimes we get lucky).
To avoid this. Explicitly wait for cloud-init to finish (and then check if sshd is running).

---

## TODO

#### Disk Usage Alerts

We'll need to add alerts for the modified mount points (old alerts rely on /)

#### Disk Resize

Resize logic resizes the first volume listed in the volumes table.

1. This ordering isn't guaranteed to be [root, data]
2. We need a way to specify exactly which volume we need to resize
