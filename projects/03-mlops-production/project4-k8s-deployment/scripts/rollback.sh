#!/bin/bash
# Rollback ML model deployment

set -e

# Configuration
RELEASE_NAME="${RELEASE_NAME:-ml-model}"
NAMESPACE="${NAMESPACE:-ml-production}"
REVISION="${REVISION:-}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Rolling back ML Model Deployment${NC}"
echo "Release: $RELEASE_NAME"
echo "Namespace: $NAMESPACE"
echo ""

# Show deployment history
echo -e "${YELLOW}Deployment history:${NC}"
helm history "$RELEASE_NAME" -n "$NAMESPACE"
echo ""

# Determine revision to rollback to
if [ -z "$REVISION" ]; then
    echo -e "${YELLOW}No revision specified, rolling back to previous version${NC}"
    helm rollback "$RELEASE_NAME" -n "$NAMESPACE"
else
    echo -e "${YELLOW}Rolling back to revision $REVISION${NC}"
    helm rollback "$RELEASE_NAME" "$REVISION" -n "$NAMESPACE"
fi

# Wait for rollback to complete
echo ""
echo -e "${YELLOW}Waiting for rollback to complete...${NC}"
kubectl rollout status deployment/"$RELEASE_NAME-ml-model" -n "$NAMESPACE" --timeout=5m

# Show current status
echo ""
echo -e "${GREEN}Rollback complete!${NC}"
echo ""
echo "Current pods:"
kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=ml-model"

echo ""
echo "Current deployment history:"
helm history "$RELEASE_NAME" -n "$NAMESPACE" | tail -5

echo ""
echo -e "${GREEN}To rollback to a specific revision:${NC}"
echo "  REVISION=2 ./rollback.sh"
