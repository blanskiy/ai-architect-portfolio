#!/bin/bash
# Build and push Docker image for ML model

set -e

# Configuration
REGISTRY="${REGISTRY:-myregistry.azurecr.io}"
IMAGE_NAME="${IMAGE_NAME:-ml-model}"
TAG="${TAG:-latest}"
DOCKERFILE="${DOCKERFILE:-Dockerfile}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building ML Model Docker Image${NC}"
echo "Registry: $REGISTRY"
echo "Image: $IMAGE_NAME"
echo "Tag: $TAG"
echo ""

# Navigate to docker directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../docker"

# Build image
echo -e "${YELLOW}Building image...${NC}"
docker build \
    -t "$IMAGE_NAME:$TAG" \
    -f "$DOCKERFILE" \
    ..

# Tag for registry
FULL_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"
echo -e "${YELLOW}Tagging as $FULL_IMAGE${NC}"
docker tag "$IMAGE_NAME:$TAG" "$FULL_IMAGE"

# Push to registry
if [ "$PUSH" = "true" ]; then
    echo -e "${YELLOW}Pushing to registry...${NC}"
    docker push "$FULL_IMAGE"
    echo -e "${GREEN}Pushed: $FULL_IMAGE${NC}"
fi

# Print summary
echo ""
echo -e "${GREEN}Build complete!${NC}"
echo "Local image: $IMAGE_NAME:$TAG"
echo "Registry image: $FULL_IMAGE"
echo ""
echo "To push to registry:"
echo "  PUSH=true ./build.sh"
echo ""
echo "To run locally:"
echo "  docker run -p 8080:8080 $IMAGE_NAME:$TAG"
