#!/bin/bash

# Build script for multi-architecture images using podman
# Supports both arm64/v8 and x86_64 architectures

set -e

IMAGE_NAME="telegramtastic"
REGISTRY="ghcr.io/shakataganai"
TAG="${1:-latest}"

echo "Building multi-architecture image: ${REGISTRY}/${IMAGE_NAME}:${TAG}"

# Create manifest list
podman manifest create "${REGISTRY}/${IMAGE_NAME}:${TAG}" || true

# Build for amd64
echo "Building for linux/amd64..."
podman build \
    --platform linux/amd64 \
    --tag "${REGISTRY}/${IMAGE_NAME}:${TAG}-amd64" \
    .

# Build for arm64
echo "Building for linux/arm64/v8..."
podman build \
    --platform linux/arm64/v8 \
    --tag "${REGISTRY}/${IMAGE_NAME}:${TAG}-arm64" \
    .

# Add images to manifest
podman manifest add "${REGISTRY}/${IMAGE_NAME}:${TAG}" "${REGISTRY}/${IMAGE_NAME}:${TAG}-amd64"
podman manifest add "${REGISTRY}/${IMAGE_NAME}:${TAG}" "${REGISTRY}/${IMAGE_NAME}:${TAG}-arm64"

# Push manifest and images
echo "Pushing multi-architecture manifest..."
podman manifest push "${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "Successfully built and pushed multi-architecture image: ${REGISTRY}/${IMAGE_NAME}:${TAG}"