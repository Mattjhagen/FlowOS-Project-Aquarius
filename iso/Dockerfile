# FlowOS ISO Builder
# Builds a bootable ISO that boots directly into the FlowOS CLI.
#
# Usage (from repo root):
#   docker build -f iso/Dockerfile -t flowos-builder .
#   docker run --rm --privileged -v $(pwd)/dist:/output flowos-builder

FROM alpine:3.21

# Build tools + splash deps in one layer to minimise image size
RUN apk add --no-cache \
    squashfs-tools \
    xorriso \
    grub \
    grub-bios \
    grub-efi \
    mtools \
    dosfstools \
    cpio \
    gzip \
    busybox-static \
    linux-lts \
    linux-lts-dev \
    python3 \
    py3-pip \
    bash \
    curl \
    wget \
    findutils \
    coreutils

# Create build workspace
RUN mkdir -p /build /output /src

# Copy the entire FlowOS repo into the build context
COPY . /src/

# Copy pre-built splash PNG if present (optional — grub.cfg falls back gracefully)
RUN [ -f /src/iso/grub/splash.png ] && cp /src/iso/grub/splash.png /build/splash.png || true

# Make all scripts executable
RUN chmod +x /src/iso/scripts/*.sh /src/iso/initramfs/init

# Run build stages
RUN sh /src/iso/scripts/build-rootfs.sh
RUN sh /src/iso/scripts/build-initramfs.sh
RUN sh /src/iso/scripts/create-iso.sh

# Default command: copy ISO to output mount
CMD ["sh", "-c", "cp /build/flowos.iso /output/flowos.iso && echo 'ISO ready at dist/flowos.iso'"]
