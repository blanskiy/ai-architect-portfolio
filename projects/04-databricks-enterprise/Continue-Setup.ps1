# ============================================================
# Databricks Unity Catalog - Continuation Script
# Run this AFTER enabling Managed Identity in Azure Portal
# ============================================================

# Stop on any error
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Databricks Unity Catalog - Continuation Script" -ForegroundColor Cyan
Write-Host "Run this after enabling Managed Identity manually" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Configuration (from your deployment)
# ============================================================
$RG_NAME = "ml-portfolio-rg"
$STORAGE_ACCOUNT = "azlancedb"
$CONTAINER_NAME = "lakehouse"
$DATABRICKS_WORKSPACE = "databricks-unity-ml"
$CONNECTOR_NAME = "unity-catalog-connector"
$LOCATION = "westus2"
$WORKSPACE_URL = "adb-2503836992218403.3.azuredatabricks.net"
$SUBSCRIPTION_ID = "f145b6d6-938e-4be9-876d-eac04dbda8e2"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Workspace: $DATABRICKS_WORKSPACE"
Write-Host "  URL: https://$WORKSPACE_URL"
Write-Host ""

# ============================================================
# Get Managed Identity Principal ID
# ============================================================
Write-Host "Step 1: Get Managed Identity Information" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

Write-Host ""
Write-Host "Did you enable System-Assigned Managed Identity in Azure Portal?" -ForegroundColor Yellow
Write-Host "(Identity > System assigned > Status: On)"
Write-Host ""
$response = Read-Host "Enter Y to continue, or N to see instructions"

if ($response -ne "Y" -and $response -ne "y") {
    Write-Host ""
    Write-Host "INSTRUCTIONS:" -ForegroundColor Cyan
    Write-Host "1. Go to Azure Portal: https://portal.azure.com"
    Write-Host "2. Navigate to: Resource Groups > ml-portfolio-rg > databricks-unity-ml"
    Write-Host "3. Click 'Identity' in left menu"
    Write-Host "4. Under 'System assigned' tab, toggle Status to 'On'"
    Write-Host "5. Click 'Save'"
    Write-Host "6. Copy the 'Object (principal) ID' that appears"
    Write-Host "7. Run this script again"
    Write-Host ""
    exit
}

Write-Host ""
Write-Host "Enter the Principal ID from Azure Portal (Object ID):" -ForegroundColor Yellow
$PRINCIPAL_ID = Read-Host "Principal ID"

if (-not $PRINCIPAL_ID) {
    Write-Host "[ERROR] Principal ID is required" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Using Principal ID: $PRINCIPAL_ID" -ForegroundColor Green

# ============================================================
# Grant Storage Access to Workspace Identity
# ============================================================
Write-Host ""
Write-Host "Step 2: Grant Storage Access to Workspace" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

$STORAGE_ID = "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"

try {
    az role assignment create --assignee $PRINCIPAL_ID --role "Storage Blob Data Contributor" --scope $STORAGE_ID --only-show-errors 2>$null | Out-Null
    Write-Host "[OK] Storage access granted to workspace managed identity" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Role may already be assigned" -ForegroundColor Yellow
}

# ============================================================
# Create Access Connector
# ============================================================
Write-Host ""
Write-Host "Step 3: Create Unity Catalog Access Connector" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

try {
    $connector = az databricks access-connector show --resource-group $RG_NAME --name $CONNECTOR_NAME 2>$null | ConvertFrom-Json
    if ($connector) {
        Write-Host "[INFO] Access Connector already exists" -ForegroundColor Yellow
        $CONNECTOR_ID = $connector.id
        $CONNECTOR_PRINCIPAL_ID = $connector.identity.principalId
    } else {
        throw "Not found"
    }
} catch {
    Write-Host "Creating Access Connector..." -ForegroundColor Yellow
    $connector = az databricks access-connector create --resource-group $RG_NAME --name $CONNECTOR_NAME --location $LOCATION --identity-type SystemAssigned 2>$null | ConvertFrom-Json
    $CONNECTOR_ID = $connector.id
    $CONNECTOR_PRINCIPAL_ID = $connector.identity.principalId
    Write-Host "[OK] Access Connector created" -ForegroundColor Green
}

Write-Host "     Connector ID: $CONNECTOR_ID" -ForegroundColor Yellow
Write-Host "     Principal ID: $CONNECTOR_PRINCIPAL_ID" -ForegroundColor Yellow

# ============================================================
# Grant Storage Access to Connector
# ============================================================
Write-Host ""
Write-Host "Step 4: Grant Storage Access to Access Connector" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

try {
    az role assignment create --assignee $CONNECTOR_PRINCIPAL_ID --role "Storage Blob Data Contributor" --scope $STORAGE_ID --only-show-errors 2>$null | Out-Null
    Write-Host "[OK] Storage access granted to Access Connector" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Role may already be assigned" -ForegroundColor Yellow
}

# ============================================================
# Get Tenant ID
# ============================================================
$TENANT_ID = az account show --query tenantId -o tsv

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "SAVE THESE VALUES:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Databricks Workspace:" -ForegroundColor Cyan
Write-Host "  URL: https://$WORKSPACE_URL"
Write-Host ""
Write-Host "Storage Configuration:" -ForegroundColor Cyan
Write-Host "  Account: $STORAGE_ACCOUNT"
Write-Host "  Container: $CONTAINER_NAME"
Write-Host "  Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/"
Write-Host ""
Write-Host "Managed Identities:" -ForegroundColor Cyan
Write-Host "  Workspace Principal ID: $PRINCIPAL_ID"
Write-Host "  Connector Principal ID: $CONNECTOR_PRINCIPAL_ID"
Write-Host ""
Write-Host "Unity Catalog Access Connector:" -ForegroundColor Cyan
Write-Host "  Name: $CONNECTOR_NAME"
Write-Host "  Resource ID: $CONNECTOR_ID"
Write-Host ""
Write-Host "Azure Configuration:" -ForegroundColor Cyan
Write-Host "  Tenant ID: $TENANT_ID"
Write-Host "  Subscription: $SUBSCRIPTION_ID"
Write-Host "  Resource Group: $RG_NAME"
Write-Host "  Location: $LOCATION"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open Databricks workspace:" -ForegroundColor Yellow
Write-Host "   https://$WORKSPACE_URL"
Write-Host ""
Write-Host "2. Create Unity Catalog Metastore:" -ForegroundColor Yellow
Write-Host "   - Go to Account Console (click profile > Manage Account)"
Write-Host "   - Navigate to: Data > Metastores > Create Metastore"
Write-Host "   - Name: primary-metastore"
Write-Host "   - Region: West US 2"
Write-Host "   - ADLS Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/metastore"
Write-Host "   - Access Connector ID: $CONNECTOR_ID"
Write-Host ""
Write-Host "3. Assign Metastore to Workspace:" -ForegroundColor Yellow
Write-Host "   - In Account Console > Workspaces"
Write-Host "   - Find: $DATABRICKS_WORKSPACE"
Write-Host "   - Actions > Assign Metastore > primary-metastore"
Write-Host ""
Write-Host "4. Create Cluster with Spark Config:" -ForegroundColor Yellow
Write-Host "   spark.databricks.unity_catalog.enabled true"
Write-Host "   spark.hadoop.fs.azure.account.auth.type.${STORAGE_ACCOUNT}.dfs.core.windows.net OAuth"
Write-Host "   spark.hadoop.fs.azure.account.oauth.provider.type.${STORAGE_ACCOUNT}.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider"
Write-Host "   spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID"
Write-Host ""
Write-Host "5. Upload unity_catalog_setup.sql and run it"
Write-Host ""
Write-Host "6. Upload and run the RAG demo notebook"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Save configuration
# ============================================================
$configPath = "deployment_config.txt"
$configContent = @"
Databricks Unity Catalog Deployment Configuration
Generated: $(Get-Date)
========================================================

WORKSPACE INFORMATION:
  Workspace URL: https://$WORKSPACE_URL
  Unity Catalog Enabled: Yes

STORAGE CONFIGURATION:
  Storage Account: $STORAGE_ACCOUNT
  Container: $CONTAINER_NAME
  Storage Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/

MANAGED IDENTITIES:
  Workspace Principal ID: $PRINCIPAL_ID
  Connector Principal ID: $CONNECTOR_PRINCIPAL_ID
  Storage Access: Granted to Both

UNITY CATALOG ACCESS CONNECTOR:
  Name: $CONNECTOR_NAME
  Resource ID: $CONNECTOR_ID

AZURE CONFIGURATION:
  Resource Group: $RG_NAME
  Location: $LOCATION
  Subscription ID: $SUBSCRIPTION_ID
  Tenant ID: $TENANT_ID

SPARK CLUSTER CONFIGURATION:
Copy this into your cluster's Spark Config:
--------------------------------------------------------
spark.databricks.unity_catalog.enabled true
spark.hadoop.fs.azure.account.auth.type.${STORAGE_ACCOUNT}.dfs.core.windows.net OAuth
spark.hadoop.fs.azure.account.oauth.provider.type.${STORAGE_ACCOUNT}.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider
spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID
--------------------------------------------------------

METASTORE CONFIGURATION:
For Unity Catalog Metastore Creation:
  Name: primary-metastore
  Region: West US 2
  ADLS Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/metastore
  Access Connector ID: $CONNECTOR_ID

========================================================
"@

$configContent | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "[OK] Configuration saved to: $configPath" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
