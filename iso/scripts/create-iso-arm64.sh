#!/bin/sh
# Runs INSIDE Docker. Assembles the ARM64 bootable ISO (UEFI only — no BIOS).
set -e

ISO_ROOT=/build/iso
OUT=/build/flowos.iso

echo "==> Assembling ARM64 ISO structure..."
mkdir -p "$ISO_ROOT/boot/grub" "$ISO_ROOT/flowos" "$ISO_ROOT/EFI/BOOT"

# Kernel
VMLINUZ=$(find /boot -name 'vmlinuz*' | head -1)
if [ -z "$VMLINUZ" ]; then
    echo "ERROR: No kernel found in /boot"
    ls /boot
    exit 1
fi
cp "$VMLINUZ" "$ISO_ROOT/boot/vmlinuz"
echo "==> Kernel: $VMLINUZ -> /boot/vmlinuz"

# Initramfs
cp /build/initrd.img "$ISO_ROOT/boot/initrd.img"
echo "==> Initramfs: $(du -sh /build/initrd.img | cut -f1)"

# GRUB config
cp /src/iso/grub/grub.cfg "$ISO_ROOT/boot/grub/grub.cfg"

# GRUB splash + font
if [ -f /build/splash.png ]; then
    cp /build/splash.png "$ISO_ROOT/boot/grub/splash.png"
    echo "==> Splash: $(du -sh $ISO_ROOT/boot/grub/splash.png | cut -f1)"
fi
mkdir -p "$ISO_ROOT/boot/grub/fonts"
UNICODE_PF2=$(find /usr/share/grub /usr/lib/grub -name "unicode.pf2" 2>/dev/null | head -1)
[ -n "$UNICODE_PF2" ] && cp "$UNICODE_PF2" "$ISO_ROOT/boot/grub/fonts/unicode.pf2"

# Squashfs rootfs (ARM BCJ filter instead of x86)
echo "==> Creating squashfs rootfs (this takes a while)..."
mksquashfs /build/rootfs "$ISO_ROOT/flowos/rootfs.squashfs" \
    -comp xz -Xbcj arm -b 1M \
    -no-progress \
    -e /build/rootfs/proc \
    -e /build/rootfs/sys \
    -e /build/rootfs/dev \
    -e /build/rootfs/tmp
echo "==> Squashfs: $(du -sh $ISO_ROOT/flowos/rootfs.squashfs | cut -f1)"

# GRUB EFI image for ARM64
echo "==> Installing GRUB (arm64-efi)..."
grub-mkimage \
    -O arm64-efi \
    -o "$ISO_ROOT/EFI/BOOT/BOOTAA64.EFI" \
    -p "/boot/grub" \
    iso9660 normal search search_fs_file linux echo \
    gzio part_msdos part_gpt fat ext2 ls reboot halt

# EFI boot image
dd if=/dev/zero of="$ISO_ROOT/boot/grub/efi.img" bs=1M count=4
mkfs.vfat "$ISO_ROOT/boot/grub/efi.img"
mmd -i "$ISO_ROOT/boot/grub/efi.img" ::/EFI ::/EFI/BOOT
mcopy -i "$ISO_ROOT/boot/grub/efi.img" "$ISO_ROOT/EFI/BOOT/BOOTAA64.EFI" ::/EFI/BOOT/

# GRUB modules
mkdir -p "$ISO_ROOT/boot/grub/arm64-efi"
cp /usr/lib/grub/arm64-efi/*.mod "$ISO_ROOT/boot/grub/arm64-efi/" 2>/dev/null || true
cp /usr/lib/grub/arm64-efi/*.lst "$ISO_ROOT/boot/grub/arm64-efi/" 2>/dev/null || true

# Build ISO — EFI only (ARM64 has no BIOS/legacy boot)
echo "==> Building ISO with xorriso..."
xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "FLOWOS_ARM64" \
    -eltorito-alt-boot \
    -e boot/grub/efi.img \
    -no-emul-boot \
    -isohybrid-gpt-basdat \
    -output "$OUT" \
    "$ISO_ROOT"

echo ""
echo "=========================================="
echo "  FlowOS ARM64 ISO built successfully!"
echo "  Output: $OUT"
echo "  Size:   $(du -sh $OUT | cut -f1)"
echo "=========================================="
echo ""
echo "  Test in UTM on Apple Silicon:"
echo "  New VM → Virtualize → Linux → select this ISO"
echo "  Set RAM to 2048MB+ for best performance"
