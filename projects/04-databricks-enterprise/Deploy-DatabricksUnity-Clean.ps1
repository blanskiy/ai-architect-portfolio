# ============================================================
# Databricks Unity Catalog - Managed Identity Deployment
# PowerShell Version - Clean (No Special Characters)
# ============================================================

# Stop on any error
$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Databricks Unity Catalog with Managed Identity" -ForegroundColor Cyan
Write-Host "PowerShell Deployment Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Configuration
# ============================================================
$RG_NAME = "ml-portfolio-rg"
$STORAGE_ACCOUNT = "azlancedb"
$CONTAINER_NAME = "lakehouse"
$DATABRICKS_WORKSPACE = "databricks-unity-ml"
$CONNECTOR_NAME = "unity-catalog-connector"
$LOCATION = "westus2"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group:      $RG_NAME"
Write-Host "  Storage Account:     $STORAGE_ACCOUNT"
Write-Host "  Container:           $CONTAINER_NAME"
Write-Host "  Databricks Name:     $DATABRICKS_WORKSPACE"
Write-Host "  Region:              $LOCATION"
Write-Host ""
Write-Host "Press Enter to continue or Ctrl+C to cancel..." -ForegroundColor Yellow
$null = Read-Host

# ============================================================
# Step 1: Login to Azure
# ============================================================
Write-Host ""
Write-Host "Step 1: Azure Login" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

try {
    $account = az account show 2>$null | ConvertFrom-Json
    if ($account) {
        Write-Host "[OK] Already logged in as: $($account.user.name)" -ForegroundColor Green
    }
} catch {
    Write-Host "Logging in to Azure..." -ForegroundColor Yellow
    az login
}

Write-Host "[OK] Logged in to Azure" -ForegroundColor Green

# ============================================================
# Step 2: Get Subscription
# ============================================================
Write-Host ""
Write-Host "Step 2: Verify Subscription" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

$SUBSCRIPTION_ID = az account show --query id -o tsv
$SUBSCRIPTION_NAME = az account show --query name -o tsv
Write-Host "Using subscription: $SUBSCRIPTION_NAME ($SUBSCRIPTION_ID)" -ForegroundColor Green

# ============================================================
# Step 3: Create Container
# ============================================================
Write-Host ""
Write-Host "Step 3: Create Container in ADLS" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

try {
    az storage container create --name $CONTAINER_NAME --account-name $STORAGE_ACCOUNT --auth-mode login --only-show-errors 2>$null
    Write-Host "[OK] Container created: $CONTAINER_NAME" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Container may already exist" -ForegroundColor Yellow
}

# ============================================================
# Step 4: Create Databricks Workspace
# ============================================================
Write-Host ""
Write-Host "Step 4: Create Databricks Workspace (Premium Tier)" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"
Write-Host "This may take 5-10 minutes..." -ForegroundColor Yellow

try {
    az databricks workspace create --resource-group $RG_NAME --name $DATABRICKS_WORKSPACE --location $LOCATION --sku premium --managed-resource-group "databricks-rg-$DATABRICKS_WORKSPACE" --only-show-errors 2>$null
    Write-Host "[OK] Databricks workspace created" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Workspace may already exist" -ForegroundColor Yellow
}

# Get workspace URL
$WORKSPACE_URL = az databricks workspace show --resource-group $RG_NAME --name $DATABRICKS_WORKSPACE --query workspaceUrl -o tsv

Write-Host "[OK] Databricks workspace ready" -ForegroundColor Green
Write-Host "     URL: https://$WORKSPACE_URL" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANT: Save this URL!" -ForegroundColor Magenta

# ============================================================
# Step 5: Enable Managed Identity
# ============================================================
Write-Host ""
Write-Host "Step 5: Enable Managed Identity on Databricks" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

az databricks workspace update --resource-group $RG_NAME --name $DATABRICKS_WORKSPACE --set identity.type=SystemAssigned --only-show-errors 2>$null

$PRINCIPAL_ID = az databricks workspace show --resource-group $RG_NAME --name $DATABRICKS_WORKSPACE --query identity.principalId -o tsv

Write-Host "[OK] Managed Identity enabled" -ForegroundColor Green
Write-Host "     Principal ID: $PRINCIPAL_ID" -ForegroundColor Yellow
Write-Host ""
Write-Host "IMPORTANT: Save this Principal ID!" -ForegroundColor Magenta

# ============================================================
# Step 6: Grant Storage Access
# ============================================================
Write-Host ""
Write-Host "Step 6: Grant Storage Access" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

$STORAGE_ID = az storage account show --name $STORAGE_ACCOUNT --resource-group $RG_NAME --query id -o tsv

try {
    az role assignment create --assignee $PRINCIPAL_ID --role "Storage Blob Data Contributor" --scope $STORAGE_ID --only-show-errors 2>$null
    Write-Host "[OK] Storage access granted to Databricks managed identity" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Role may already be assigned" -ForegroundColor Yellow
}

# ============================================================
# Step 7: Create Access Connector
# ============================================================
Write-Host ""
Write-Host "Step 7: Create Unity Catalog Access Connector" -ForegroundColor Cyan
Write-Host "------------------------------------------------------------"

try {
    az databricks access-connector create --resource-group $RG_NAME --name $CONNECTOR_NAME --location $LOCATION --identity-type SystemAssigned --only-show-errors 2>$null
    Write-Host "[OK] Access Connector created" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Access connector may already exist" -ForegroundColor Yellow
}

$CONNECTOR_PRINCIPAL_ID = az databricks access-connector show --resource-group $RG_NAME --name $CONNECTOR_NAME --query identity.principalId -o tsv
$CONNECTOR_ID = az databricks access-connector show --resource-group $RG_NAME --name $CONNECTOR_NAME --query id -o tsv

Write-Host "     Connector ID: $CONNECTOR_ID" -ForegroundColor Yellow
Write-Host "     Principal ID: $CONNECTOR_PRINCIPAL_ID" -ForegroundColor Yellow

try {
    az role assignment create --assignee $CONNECTOR_PRINCIPAL_ID --role "Storage Blob Data Contributor" --scope $STORAGE_ID --only-show-errors 2>$null
    Write-Host "[OK] Storage access granted to Access Connector" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Role may already be assigned" -ForegroundColor Yellow
}

# ============================================================
# Step 8: Get Tenant ID
# ============================================================
$TENANT_ID = az account show --query tenantId -o tsv

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "DEPLOYMENT COMPLETE!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Save these values:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Databricks Workspace URL:" -ForegroundColor Cyan
Write-Host "  https://$WORKSPACE_URL"
Write-Host ""
Write-Host "Storage Configuration:" -ForegroundColor Cyan
Write-Host "  Account: $STORAGE_ACCOUNT"
Write-Host "  Container: $CONTAINER_NAME"
Write-Host "  Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/"
Write-Host ""
Write-Host "Managed Identity:" -ForegroundColor Cyan
Write-Host "  Workspace Principal ID: $PRINCIPAL_ID"
Write-Host "  Connector Principal ID: $CONNECTOR_PRINCIPAL_ID"
Write-Host "  Tenant ID: $TENANT_ID"
Write-Host ""
Write-Host "Access Connector:" -ForegroundColor Cyan
Write-Host "  Resource ID: $CONNECTOR_ID"
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open Databricks workspace:" -ForegroundColor Yellow
Write-Host "   https://$WORKSPACE_URL"
Write-Host ""
Write-Host "2. Create Unity Catalog Metastore (in Account Console):" -ForegroundColor Yellow
Write-Host "   - Go to Account Console > Data > Metastores"
Write-Host "   - Click 'Create Metastore'"
Write-Host "   - Name: primary-metastore"
Write-Host "   - Region: $LOCATION"
Write-Host "   - Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/metastore"
Write-Host "   - Access Connector: $CONNECTOR_NAME"
Write-Host ""
Write-Host "3. Create Cluster with this Spark config:" -ForegroundColor Yellow
Write-Host "   spark.databricks.unity_catalog.enabled true"
Write-Host "   spark.hadoop.fs.azure.account.auth.type.${STORAGE_ACCOUNT}.dfs.core.windows.net OAuth"
Write-Host "   spark.hadoop.fs.azure.account.oauth.provider.type.${STORAGE_ACCOUNT}.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider"
Write-Host "   spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID"
Write-Host ""
Write-Host "4. Run the Unity Catalog setup SQL" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. Upload and run the RAG demo notebook" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# Save configuration to file
# ============================================================
$configPath = "deployment_config.txt"
$configContent = @"
Databricks Unity Catalog Deployment Configuration
Generated: $(Get-Date)

Workspace URL: https://$WORKSPACE_URL
Resource Group: $RG_NAME
Storage Account: $STORAGE_ACCOUNT
Container: $CONTAINER_NAME
Location: $LOCATION

Workspace Principal ID: $PRINCIPAL_ID
Connector Principal ID: $CONNECTOR_PRINCIPAL_ID
Connector Resource ID: $CONNECTOR_ID
Tenant ID: $TENANT_ID

Storage Path: abfss://${CONTAINER_NAME}@${STORAGE_ACCOUNT}.dfs.core.windows.net/

Spark Configuration:
spark.databricks.unity_catalog.enabled true
spark.hadoop.fs.azure.account.auth.type.${STORAGE_ACCOUNT}.dfs.core.windows.net OAuth
spark.hadoop.fs.azure.account.oauth.provider.type.${STORAGE_ACCOUNT}.dfs.core.windows.net org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider
spark.hadoop.fs.azure.account.oauth2.msi.tenant $TENANT_ID
"@

$configContent | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "[OK] Configuration saved to: $configPath" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
