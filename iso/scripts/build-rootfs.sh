#!/bin/sh
# Runs INSIDE Docker. Builds the Alpine rootfs with FlowOS pre-installed.
set -e

ROOTFS=/build/rootfs

echo "==> Creating Alpine rootfs..."
mkdir -p "$ROOTFS"

# Bootstrap Alpine into rootfs
apk add --no-cache --root "$ROOTFS" --initdb \
    alpine-base \
    python3 \
    py3-pip \
    py3-setuptools \
    git \
    bash \
    curl \
    wget \
    openssh-client \
    openssh-server \
    util-linux \
    procps \
    htop \
    ncurses \
    ca-certificates \
    tzdata \
    sudo \
    shadow \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    iproute2 \
    iputils \
    dhclient \
    wpa_supplicant \
    openssl \
    less \
    vim \
    nano

echo "==> Installing Python packages..."
chroot "$ROOTFS" pip3 install --break-system-packages --no-cache-dir \
    anthropic \
    rich \
    prompt_toolkit \
    psutil \
    fastapi \
    uvicorn

echo "==> Copying FlowOS source..."
mkdir -p "$ROOTFS/opt/flowos"
cp -r /src/flowos.py "$ROOTFS/opt/flowos/"
cp -r /src/tools.py "$ROOTFS/opt/flowos/"
cp -r /src/session.py "$ROOTFS/opt/flowos/"
cp -r /src/plugin_manager.py "$ROOTFS/opt/flowos/"
cp -r /src/plugins "$ROOTFS/opt/flowos/"
cp -r /src/gui "$ROOTFS/opt/flowos/"

echo "==> Configuring users..."
# Create flowos user (uid 1000)
chroot "$ROOTFS" sh -c "
    echo 'root:flowos' | chpasswd
    addgroup -S flowos 2>/dev/null || true
    adduser -D -s /bin/sh -G flowos -h /home/flowos flowos 2>/dev/null || true
    echo 'flowos ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
"
mkdir -p "$ROOTFS/home/flowos/.flowos"
chroot "$ROOTFS" chown -R flowos:flowos /home/flowos /opt/flowos

echo "==> Applying FlowOS overlay..."
cp -r /src/iso/overlay/. "$ROOTFS/"
chmod +x "$ROOTFS/usr/local/bin/flowos"
chmod +x "$ROOTFS/home/flowos/.profile"

echo "==> Configuring OpenRC services..."
chroot "$ROOTFS" sh -c "
    rc-update add devfs sysinit 2>/dev/null || true
    rc-update add dmesg sysinit 2>/dev/null || true
    rc-update add mdev sysinit 2>/dev/null || true
    rc-update add networking boot 2>/dev/null || true
    rc-update add hostname boot 2>/dev/null || true
    rc-update add local default 2>/dev/null || true
"

# Set hostname
echo "flowos" > "$ROOTFS/etc/hostname"

# Network: DHCP on boot
cat > "$ROOTFS/etc/network/interfaces" <<'EOF'
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
EOF

echo "==> Rootfs build complete."
du -sh "$ROOTFS"
