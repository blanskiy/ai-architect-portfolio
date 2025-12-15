#!/bin/bash
# ============================================================
# Databricks Unity Catalog - Managed Identity Deployment
# Quick Start Script
# ============================================================

set -e  # Exit on error

echo "============================================================"
echo "Databricks Unity Catalog with Managed Identity"
echo "Quick Deployment Script"
echo "============================================================"
echo ""

# ============================================================
# Configuration - Update these values
# ============================================================
RG_NAME="ml-portfolio-rg"
STORAGE_ACCOUNT="azlancedb"
CONTAINER_NAME="databricks-data"
DATABRICKS_WORKSPACE="databricks-unity-ml"
CONNECTOR_NAME="unity-catalog-connector"
LOCATION="eastus"  # Change to your preferred region

echo "Configuration:"
echo "  Resource Group:      $RG_NAME"
echo "  Storage Account:     $STORAGE_ACCOUNT"
echo "  Container:           $CONTAINER_NAME"
echo "  Databricks Name:     $DATABRICKS_WORKSPACE"
echo "  Region:              $LOCATION"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."

# ============================================================
# Step 1: Login to Azure
# ============================================================
echo ""
echo "Step 1: Azure Login"
echo "------------------------------------------------------------"
az login
echo "✅ Logged in to Azure"

# ============================================================
# Step 2: Set Subscription (if you have multiple)
# ============================================================
echo ""
echo "Step 2: Select Subscription"
echo "------------------------------------------------------------"
# az account list --output table
# read -p "Enter subscription ID (or press Enter to use current): " SUB_ID
# if [ ! -z "$SUB_ID" ]; then
#     az account set --subscription $SUB_ID
# fi
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo "Using subscription: $SUBSCRIPTION_ID"

# ============================================================
# Step 3: Create Databricks Container
# ============================================================
echo ""
echo "Step 3: Create Container in ADLS"
echo "------------------------------------------------------------"
az storage container create \
    --name $CONTAINER_NAME \
    --account-name $STORAGE_ACCOUNT \
    --auth-mode login \
    || echo "Container may already exist"

echo "✅ Container created/verified: $CONTAINER_NAME"

# ============================================================
# Step 4: Create Databricks Workspace
# ============================================================
echo ""
echo "Step 4: Create Databricks Workspace (Premium Tier)"
echo "------------------------------------------------------------"
echo "This may take 5-10 minutes..."

az databricks workspace create \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --location $LOCATION \
    --sku premium \
    --managed-resource-group "databricks-rg-$DATABRICKS_WORKSPACE" \
    || echo "Workspace may already exist"

# Get workspace URL
WORKSPACE_URL=$(az databricks workspace show \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --query workspaceUrl -o tsv)

echo "✅ Databricks workspace ready"
echo "   URL: https://$WORKSPACE_URL"
echo "   Save this URL!"

# ============================================================
# Step 5: Enable System-Assigned Managed Identity
# ============================================================
echo ""
echo "Step 5: Enable Managed Identity on Databricks"
echo "------------------------------------------------------------"
az databricks workspace update \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --set identity.type=SystemAssigned

# Get the Managed Identity Principal ID
PRINCIPAL_ID=$(az databricks workspace show \
    --resource-group $RG_NAME \
    --name $DATABRICKS_WORKSPACE \
    --query identity.principalId -o tsv)

echo "✅ Managed Identity enabled"
echo "   Principal ID: $PRINCIPAL_ID"
echo "   Save this Principal ID!"

# ============================================================
# Step 6: Grant Storage Access to Databricks Managed Identity
# ============================================================
echo ""
echo "Step 6: Grant Storage Access"
echo "------------------------------------------------------------"

# Get storage account resource ID
STORAGE_ID=$(az storage account show \
    --name $STORAGE_ACCOUNT \
    --resource-group $RG_NAME \
    --query id -o tsv)

# Grant Storage Blob Data Contributor role
az role assignment create \
    --assignee $PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope $STORAGE_ID \
    || echo "Role may already be assigned"

echo "✅ Storage access granted to Databricks managed identity"

# ============================================================
# Step 7: Create Access Connector for Unity Catalog
# ============================================================
echo ""
echo "Step 7: Create Unity Catalog Access Connector"
echo "------------------------------------------------------------"

az databricks access-connector create \
    --resource-group $RG_NAME \
    --name $CONNECTOR_NAME \
    --location $LOCATION \
    --identity-type SystemAssigned \
    || echo "Access connector may already exist"

# Get connector's managed identity
CONNECTOR_PRINCIPAL_ID=$(az databricks access-connector show \
    --resource-group $RG_NAME \
    --name $CONNECTOR_NAME \
    --query identity.principalId -o tsv)

# Get connector resource ID
CONNECTOR_ID=$(az databricks access-connector show \
    --resource-group $RG_NAME \
    --name $CONNECTOR_NAME \
    --query id -o tsv)

echo "✅ Access Connector created"
echo "   Connector ID: $CONNECTOR_ID"
echo "   Principal ID: $CONNECTOR_PRINCIPAL_ID"

# Grant storage access to connector
az role assignment create \
    --assignee $CONNECTOR_PRINCIPAL_ID \
    --role "Storage Blob Data Contributor" \
    --scope $STORAGE_ID \
    || echo "Role may already be assigned"

echo "✅ Storage access granted to Access Connector"

# ============================================================
# Step 8: Get Tenant ID for Spark Config
# ============================================================
TENANT_ID=$(az account show --query tenantId -o tsv)

# ============================================================
# Summary
# ============================================================
echo ""
echo "============================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "============================================================"
echo ""
echo "📝 Save these values:"
echo ""
echo "Databricks Workspace URL:"
echo "  https://$WORKSPACE_URL"
echo ""
echo "Storage Configuration:"
echo "  Account: $STORAGE_ACCOUNT"
echo "  Container: $CONTAINER_NAME"
echo "  Path: abfss://$CONTAINER_NAME@$STORAGE_ACCOUNT.dfs.core.windows.net/"
echo ""
echo "Managed Identity:"
echo "  Workspace Principal ID: $PRINCIPAL_ID"
echo "  Connector Principal ID: $CONNECTOR_PRINCIPAL_ID"
echo "  Tenant ID: $TENANT_ID"
echo ""
echo "Access Connector:"
echo "  Resource ID: $CONNECTOR_ID"
echo ""
echo "============================================================"
echo "🎯 NEXT STEPS:"
echo "============================================================"
echo ""
echo "1. Open Databricks workspace:"
echo "   https://$WORKSPACE_URL"
echo ""
echo "2. Create Unity Catalog Metastore (in Account Console):"
echo "   - Go to Account Console > Data > Metastores"
echo "   - Click 'Create Metastore'"
echo "   - Name: primary-metastore"
echo "   - Region: $LOCATION"
echo "   - Path: abfss://$CONTAINER_NAME@$STORAGE_ACCOUNT.dfs.core.windows.net/metastore"
echo "   - Access Connector: $CONNECTOR_NAME"
echo ""
echo "3. Create Cluster with this Spark config:"
echo "   spark.databricks.unity_catalog.enabled true"
echo "   spark.hadoop.fs.azure.account.auth.type.$STORAGE_ACCOUNT.dfs.core.windows.net OAuth"
echo "   spark.hadoop.fs.azure.account.oauth.provider.type.$STORAGE_ACCOUNT.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider"
echo "   spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID"
echo ""
echo "4. Run the Unity Catalog setup SQL"
echo ""
echo "5. Upload and run the RAG demo notebook"
echo ""
echo "============================================================"
echo ""

# Save configuration to file
cat > deployment_config.txt << EOF
Databricks Unity Catalog Deployment Configuration
Generated: $(date)

Workspace URL: https://$WORKSPACE_URL
Resource Group: $RG_NAME
Storage Account: $STORAGE_ACCOUNT
Container: $CONTAINER_NAME
Location: $LOCATION

Workspace Principal ID: $PRINCIPAL_ID
Connector Principal ID: $CONNECTOR_PRINCIPAL_ID
Connector Resource ID: $CONNECTOR_ID
Tenant ID: $TENANT_ID

Storage Path: abfss://$CONTAINER_NAME@$STORAGE_ACCOUNT.dfs.core.windows.net/

Spark Configuration:
spark.databricks.unity_catalog.enabled true
spark.hadoop.fs.azure.account.auth.type.$STORAGE_ACCOUNT.dfs.core.windows.net OAuth
spark.hadoop.fs.azure.account.oauth.provider.type.$STORAGE_ACCOUNT.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider
spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID
EOF

echo "Configuration saved to: deployment_config.txt"
echo ""
