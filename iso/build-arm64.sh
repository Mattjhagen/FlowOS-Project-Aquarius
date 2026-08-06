#!/usr/bin/env bash
# FlowOS ARM64 ISO Builder — for Apple Silicon (M1/M2/M3/M4)
# Test in UTM: New VM → Virtualize → Linux → select dist/flowos-arm64.iso
#
# Usage:
#   ./iso/build-arm64.sh              # build
#   ./iso/build-arm64.sh --no-cache   # force full rebuild

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$REPO_ROOT/dist"
IMAGE_NAME="flowos-builder-arm64"
ISO_NAME="flowos-arm64.iso"

echo ""
echo "  FlowOS ARM64 ISO Builder  (Apple Silicon)"
echo ""

if ! command -v docker &>/dev/null; then
    echo "Error: Docker is required."
    echo "  https://docs.docker.com/desktop/install/mac-install/"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo "Error: Docker daemon is not running. Start Docker Desktop and try again."
    exit 1
fi

mkdir -p "$DIST"

echo "==> Building Docker image (linux/arm64)..."
CACHE_FLAG=""
[ "$1" = "--no-cache" ] && CACHE_FLAG="--no-cache"

docker build \
    $CACHE_FLAG \
    --platform linux/arm64 \
    -f "$REPO_ROOT/iso/Dockerfile.arm64" \
    -t "$IMAGE_NAME" \
    "$REPO_ROOT"

echo "==> Extracting ISO..."
docker run \
    --rm \
    --privileged \
    -v "$DIST:/output" \
    "$IMAGE_NAME" \
    sh -c "cp /build/flowos.iso /output/flowos-arm64.iso"

ISO_PATH="$DIST/$ISO_NAME"
ISO_SIZE=$(du -sh "$ISO_PATH" 2>/dev/null | cut -f1 || echo "unknown")

echo ""
echo "=========================================="
echo "  Build complete!"
echo "  $ISO_PATH  ($ISO_SIZE)"
echo "=========================================="
echo ""
echo "  Test in UTM (Apple Silicon — native speed):"
echo "  1. Install UTM: https://mac.getutm.app"
echo "  2. New VM → Virtualize → Linux"
echo "  3. Boot ISO: $ISO_PATH"
echo "  4. RAM: 2048MB+"
echo ""
