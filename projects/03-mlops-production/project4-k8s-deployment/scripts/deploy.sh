#!/bin/bash
# Deploy ML model to Kubernetes using Helm

set -e

# Configuration
RELEASE_NAME="${RELEASE_NAME:-ml-model}"
NAMESPACE="${NAMESPACE:-ml-production}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
CHART_PATH="${CHART_PATH:-./helm/ml-model}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Deploying ML Model to Kubernetes${NC}"
echo "Release: $RELEASE_NAME"
echo "Namespace: $NAMESPACE"
echo "Environment: $ENVIRONMENT"
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Create namespace if it doesn't exist
echo -e "${YELLOW}Creating namespace if needed...${NC}"
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Select values file based on environment
VALUES_FILE="$CHART_PATH/values-$ENVIRONMENT.yaml"
if [ ! -f "$VALUES_FILE" ]; then
    echo -e "${RED}Values file not found: $VALUES_FILE${NC}"
    exit 1
fi

echo -e "${YELLOW}Using values file: $VALUES_FILE${NC}"

# Check if release exists
if helm status "$RELEASE_NAME" -n "$NAMESPACE" &> /dev/null; then
    echo -e "${YELLOW}Upgrading existing release...${NC}"
    ACTION="upgrade"
else
    echo -e "${YELLOW}Installing new release...${NC}"
    ACTION="install"
fi

# Deploy with Helm
helm $ACTION "$RELEASE_NAME" "$CHART_PATH" \
    --namespace "$NAMESPACE" \
    --values "$CHART_PATH/values.yaml" \
    --values "$VALUES_FILE" \
    --wait \
    --timeout 5m

# Check deployment status
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Checking status..."
kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/name=ml-model"
echo ""
kubectl get svc -n "$NAMESPACE" -l "app.kubernetes.io/name=ml-model"
echo ""
kubectl get hpa -n "$NAMESPACE" -l "app.kubernetes.io/name=ml-model"

echo ""
echo -e "${GREEN}Useful commands:${NC}"
echo "  kubectl logs -f deployment/$RELEASE_NAME-ml-model -n $NAMESPACE"
echo "  kubectl port-forward svc/$RELEASE_NAME-ml-model 8080:80 -n $NAMESPACE"
echo "  helm history $RELEASE_NAME -n $NAMESPACE"
