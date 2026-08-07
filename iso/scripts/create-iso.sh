#!/bin/sh
# Runs INSIDE Docker. Assembles the final bootable ISO.
set -e

ISO_ROOT=/build/iso
OUT=/build/flowos.iso

echo "==> Assembling ISO structure..."
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

# GRUB splash background
if [ -f /build/splash.png ]; then
    cp /build/splash.png "$ISO_ROOT/boot/grub/splash.png"
    echo "==> Splash: $(du -sh $ISO_ROOT/boot/grub/splash.png | cut -f1)"
fi

# GRUB unicode font (needed for gfxterm)
mkdir -p "$ISO_ROOT/boot/grub/fonts"
UNICODE_PF2=$(find /usr/share/grub /usr/lib/grub -name "unicode.pf2" 2>/dev/null | head -1)
if [ -n "$UNICODE_PF2" ]; then
    cp "$UNICODE_PF2" "$ISO_ROOT/boot/grub/fonts/unicode.pf2"
    echo "==> Font: $UNICODE_PF2"
fi

# Squashfs rootfs
echo "==> Creating squashfs rootfs (this takes a while)..."
mksquashfs /build/rootfs "$ISO_ROOT/flowos/rootfs.squashfs" \
    -comp xz -Xbcj x86 -b 1M \
    -no-progress \
    -e /build/rootfs/proc \
    -e /build/rootfs/sys \
    -e /build/rootfs/dev \
    -e /build/rootfs/tmp
echo "==> Squashfs: $(du -sh $ISO_ROOT/flowos/rootfs.squashfs | cut -f1)"

# GRUB BIOS boot image (embed USB keyboard + search so it never drops to rescue)
echo "==> Installing GRUB..."
grub-mkimage \
    -O i386-pc \
    -o "$ISO_ROOT/boot/grub/core.img" \
    -p "/boot/grub" \
    biosdisk iso9660 normal search search_fs_file search_fs_uuid search_label \
    linux echo gzio part_msdos part_gpt fat ext2 ls reboot halt \
    usb usb_keyboard uhci ohci ehci at_keyboard

# GRUB EFI image
grub-mkimage \
    -O x86_64-efi \
    -o "$ISO_ROOT/EFI/BOOT/BOOTX64.EFI" \
    -p "/boot/grub" \
    iso9660 normal search search_fs_file search_fs_uuid search_label \
    linux echo gzio part_msdos part_gpt fat ext2 ls reboot halt \
    usb usb_keyboard uhci ohci ehci at_keyboard

# Create EFI boot image
dd if=/dev/zero of="$ISO_ROOT/boot/grub/efi.img" bs=1M count=4
mkfs.vfat "$ISO_ROOT/boot/grub/efi.img"
mmd -i "$ISO_ROOT/boot/grub/efi.img" ::/EFI ::/EFI/BOOT
mcopy -i "$ISO_ROOT/boot/grub/efi.img" "$ISO_ROOT/EFI/BOOT/BOOTX64.EFI" ::/EFI/BOOT/

# GRUB modules
mkdir -p "$ISO_ROOT/boot/grub/i386-pc"
cp /usr/lib/grub/i386-pc/*.mod "$ISO_ROOT/boot/grub/i386-pc/" 2>/dev/null || true
mkdir -p "$ISO_ROOT/boot/grub/x86_64-efi"
cp /usr/lib/grub/x86_64-efi/*.mod "$ISO_ROOT/boot/grub/x86_64-efi/" 2>/dev/null || true
cp /usr/lib/grub/x86_64-efi/*.lst "$ISO_ROOT/boot/grub/x86_64-efi/" 2>/dev/null || true

# Build ISO with xorriso (BIOS + UEFI hybrid)
echo "==> Building ISO with xorriso..."
xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "FLOWOS" \
    -eltorito-boot boot/grub/core.img \
    -no-emul-boot \
    -boot-load-size 4 \
    -boot-info-table \
    --grub2-boot-info \
    --grub2-mbr /usr/lib/grub/i386-pc/boot_hybrid.img \
    -eltorito-alt-boot \
    -e boot/grub/efi.img \
    -no-emul-boot \
    -isohybrid-gpt-basdat \
    -output "$OUT" \
    "$ISO_ROOT"

echo ""
echo "=========================================="
echo "  FlowOS ISO built successfully!"
echo "  Output: $OUT"
echo "  Size:   $(du -sh $OUT | cut -f1)"
echo "=========================================="
echo ""
echo "  Write to USB:"
echo "  Linux:  sudo dd if=flowos.iso of=/dev/sdX bs=4M status=progress"
echo "  Mac:    Use Balena Etcher — https://etcher.balena.io"
echo "  Win:    Use Rufus — https://rufus.ie"
