#!/bin/bash
# Ensure we're in the same directory as the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Parse arguments
VERSION=""
PUSH=false

for arg in "$@"; do
  case $arg in
    --push)
      PUSH=true
      ;;
    *)
      VERSION="$arg"
      ;;
  esac
done

if [ -z "$VERSION" ]; then
  echo "Error: Version parameter is missing."
  echo "Usage: ./build_docker.sh <version> [--push]"
  echo "Example: ./build_docker.sh v1.0.9.6major28"
  echo "Example: ./build_docker.sh v1.0.9.6major28 --push"
  exit 1
fi

if [ "$PUSH" = true ]; then
  echo "Starting docker buildx process for platform linux/amd64,linux/arm64 (with push)..."
  docker buildx build --platform linux/amd64,linux/arm64 --build-arg PRODSYS_VERSION="$VERSION" -t "llsynit/produksjonssystem:$VERSION" --push .
else
  echo "Starting docker buildx process for platform linux/amd64,linux/arm64..."
  docker buildx build --platform linux/amd64,linux/arm64 --build-arg PRODSYS_VERSION="$VERSION" -t "llsynit/produksjonssystem:$VERSION" .
fi