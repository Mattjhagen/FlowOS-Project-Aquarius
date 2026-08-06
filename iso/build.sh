#!/usr/bin/env bash
# FlowOS ISO Build Script
# Builds a bootable USB image using Docker (works on Mac and Linux).
#
# Requirements: Docker Desktop (Mac) or Docker Engine (Linux)
# Output: dist/flowos.iso
#
# Usage:
#   ./iso/build.sh              # build ISO
#   ./iso/build.sh --no-cache   # force full rebuild

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/dist"
IMAGE_NAME="flowos-builder"
ISO_NAME="flowos.iso"

echo ""
echo "  ███████╗██╗      ██████╗ ██╗    ██╗ ██████╗ ███████╗"
echo "  ██╔════╝██║     ██╔═══██╗██║    ██║██╔═══██╗██╔════╝"
echo "  █████╗  ██║     ██║   ██║██║ █╗ ██║██║   ██║███████╗"
echo "  ██╔══╝  ██║     ██║   ██║██║███╗██║██║   ██║╚════██║"
echo "  ██║     ███████╗╚██████╔╝╚███╔███╔╝╚██████╔╝███████║"
echo "  ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝  ╚═════╝ ╚══════╝"
echo "  ISO Builder"
echo ""

# Check Docker
if ! command -v docker &>/dev/null; then
    echo "Error: Docker is required."
    echo "  Mac:   https://docs.docker.com/desktop/install/mac-install/"
    echo "  Linux: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Error: Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi

mkdir -p "$DIST"

echo "==> Building Docker image..."
CACHE_FLAG=""
[ "$1" = "--no-cache" ] && CACHE_FLAG="--no-cache"

docker build \
    $CACHE_FLAG \
    --platform linux/amd64 \
    -f "$REPO_ROOT/iso/Dockerfile" \
    -t "$IMAGE_NAME" \
    "$REPO_ROOT"

echo "==> Extracting ISO..."
docker run \
    --rm \
    --privileged \
    -v "$DIST:/output" \
    "$IMAGE_NAME" \
    sh -c "cp /build/flowos.iso /output/flowos.iso"

ISO_PATH="$DIST/$ISO_NAME"
ISO_SIZE=$(du -sh "$ISO_PATH" 2>/dev/null | cut -f1 || echo "unknown")

echo ""
echo "=========================================="
echo "  Build complete!"
echo "  $ISO_PATH  ($ISO_SIZE)"
echo "=========================================="
echo ""
echo "  Flash to USB:"
echo ""
echo "  Etcher (Mac/Win/Linux — easiest):"
echo "    https://etcher.balena.io"
echo ""
echo "  Command line (Linux):"
echo "    sudo dd if=$ISO_PATH of=/dev/sdX bs=4M status=progress && sync"
echo ""
echo "  Command line (Mac):"
echo "    diskutil unmountDisk /dev/diskN"
echo "    sudo dd if=$ISO_PATH of=/dev/rdiskN bs=4m"
echo ""
