#!/bin/sh
# Runs INSIDE Docker. Creates a minimal initramfs with busybox.
set -e

INITRD_DIR=/build/initramfs
OUT=/build/initrd.img

echo "==> Building initramfs..."
mkdir -p "$INITRD_DIR"/{bin,sbin,lib,lib/modules,proc,sys,dev,mnt/{iso,squash,root,overlay}}

# Copy busybox and create symlinks
cp /bin/busybox "$INITRD_DIR/bin/"
chroot "$INITRD_DIR" /bin/busybox --install -s /bin 2>/dev/null || \
    "$INITRD_DIR/bin/busybox" --install -s "$INITRD_DIR/bin"

# Copy kernel modules for squashfs + overlay + iso9660
KVER=$(ls /lib/modules/ | head -1)
if [ -n "$KVER" ]; then
    mkdir -p "$INITRD_DIR/lib/modules/$KVER"
    for mod in squashfs overlay loop iso9660 sr_mod cdrom; do
        find /lib/modules/"$KVER" -name "${mod}.ko*" 2>/dev/null | while read f; do
            cp "$f" "$INITRD_DIR/lib/modules/$KVER/"
        done
    done
fi

# Copy switch_root (may be in util-linux)
for bin in switch_root mdev; do
    which $bin 2>/dev/null && cp $(which $bin) "$INITRD_DIR/sbin/" || true
done

# Copy init script
cp /src/iso/initramfs/init "$INITRD_DIR/init"
chmod +x "$INITRD_DIR/init"

echo "==> Packing initramfs..."
(cd "$INITRD_DIR" && find . | cpio -oH newc | gzip -9 > "$OUT")
echo "==> initramfs: $(du -sh $OUT | cut -f1)"
