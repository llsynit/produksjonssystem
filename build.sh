#!/usr/bin/env bash
# Purpose: Builds and pushes a multi-platform Docker image for this module.
# Usage:   ./build.sh <version-tag>    (e.g. ./build.sh v0.1.0)
# Note:    Requires Docker buildx. IMAGE_PREFIX, PLATFORMS, and DOCKERFILE
#          can be overridden via environment variables.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Bruk: $0 <versjon>    (f.eks. $0 v0.1.0)" >&2
  exit 1
fi

# Variables
TAG="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_NAME="$(basename "$SCRIPT_DIR")"
IMAGE_PREFIX="${IMAGE_PREFIX:-llsynit}"
IMAGE="${IMAGE_PREFIX}/${MODULE_NAME}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
DOCKERFILE="${DOCKERFILE:-${SCRIPT_DIR}/Dockerfile}"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "Fant ikke Dockerfile: $DOCKERFILE" >&2
  exit 2
fi

echo "==> Bygger ${IMAGE}:${TAG} (+ latest) for ${PLATFORMS}"
# Setup: Ensures a buildx builder exists and is active. Errors suppressed
#        intentionally — create fails if already exists, use fails if already active.
docker buildx create --use --name multi >/dev/null 2>&1 || docker buildx use multi >/dev/null 2>&1 || true

docker buildx build \
  --platform "$PLATFORMS" \
  -t "${IMAGE}:${TAG}" \
  -t "${IMAGE}:test-latest" \
  -f "$DOCKERFILE" \
  "$SCRIPT_DIR" --push # Push to registry immediately on successful build

echo "✅ Pushet:"
echo "   - ${IMAGE}:${TAG}"
echo "   - ${IMAGE}:test-latest"
