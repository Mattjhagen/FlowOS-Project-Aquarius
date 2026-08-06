# FlowOS ISO Builder
# Builds a bootable ISO that boots directly into the FlowOS CLI.
#
# Usage (from repo root):
#   docker build -f iso/Dockerfile -t flowos-builder .
#   docker run --rm --privileged -v $(pwd)/dist:/output flowos-builder

FROM alpine:3.21

# Build tools
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

# Add librsvg + DejaVu fonts for splash PNG generation
RUN apk add --no-cache librsvg font-dejavu

# Copy the entire FlowOS repo into the build context
COPY . /src/

# Generate GRUB splash PNG from SVG
RUN rsvg-convert -w 1920 -h 1080 /src/iso/grub/splash.svg -o /build/splash.png

# Make all scripts executable
RUN chmod +x /src/iso/scripts/*.sh /src/iso/initramfs/init

# Run build stages
RUN sh /src/iso/scripts/build-rootfs.sh
RUN sh /src/iso/scripts/build-initramfs.sh
RUN sh /src/iso/scripts/create-iso.sh

# Default command: copy ISO to output mount
CMD ["sh", "-c", "cp /build/flowos.iso /output/flowos.iso && echo 'ISO ready at dist/flowos.iso'"]
