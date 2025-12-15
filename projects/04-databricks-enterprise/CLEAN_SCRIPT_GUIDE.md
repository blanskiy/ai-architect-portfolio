# Fixed PowerShell Script - Quick Start

## Problem Fixed
The original script had encoding issues with emoji characters. This clean version removes all special characters and works perfectly on Windows.

---

## How to Use the Clean Script

### Step 1: Delete the Old Script
```powershell
# In your project directory
cd C:\Users\blans\source\repos\ai-architect-portfolio\projects\04-databricks-enterprise

# Delete the old script with encoding issues
Remove-Item .\Deploy-DatabricksUnity.ps1
```

### Step 2: Download and Use the Clean Script

Download `Deploy-DatabricksUnity-Clean.ps1` and copy it to your project folder.

### Step 3: Run the Clean Script

```powershell
# Make sure you're in the right directory
cd C:\Users\blans\source\repos\ai-architect-portfolio\projects\04-databricks-enterprise

# Run the clean script
.\Deploy-DatabricksUnity-Clean.ps1
```

---

## What the Clean Script Does

Same functionality, just without special characters:

1. Creates "lakehouse" container in azlancedb
2. Creates Databricks workspace in West US 2
3. Enables Managed Identity
4. Creates Access Connector
5. Grants all permissions
6. Saves configuration to deployment_config.txt

---

## Configuration

The script is pre-configured with your values:

```
Resource Group:    ml-portfolio-rg
Storage Account:   azlancedb
Container:         lakehouse
Location:          westus2 (West US 2)
Workspace:         databricks-unity-ml
Connector:         unity-catalog-connector
```

---

## Expected Output

When you run the script, you'll see:

```
============================================================
Databricks Unity Catalog with Managed Identity
PowerShell Deployment Script
============================================================

Configuration:
  Resource Group:      ml-portfolio-rg
  Storage Account:     azlancedb
  Container:           lakehouse
  Databricks Name:     databricks-unity-ml
  Region:              westus2

Press Enter to continue or Ctrl+C to cancel...

Step 1: Azure Login
------------------------------------------------------------
[OK] Already logged in as: your-email@domain.com
[OK] Logged in to Azure

Step 2: Verify Subscription
------------------------------------------------------------
Using subscription: Your Subscription Name (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

[... continues with each step ...]

============================================================
DEPLOYMENT COMPLETE!
============================================================

Save these values:

Databricks Workspace URL:
  https://adb-xxxxxxxxxxxxx.xx.azuredatabricks.net

[... complete configuration ...]

[OK] Configuration saved to: deployment_config.txt
```

---

## After Script Completes

You'll have:

1. **deployment_config.txt** - Contains all important values
2. **Container created** - "lakehouse" in azlancedb
3. **Databricks workspace** - Ready to use
4. **Access configured** - Managed Identity enabled

---

## Next Steps

1. Open the workspace URL (shown in output)
2. Create Unity Catalog metastore (in Databricks UI)
3. Create cluster with Spark config (from deployment_config.txt)
4. Follow DEPLOYMENT_CHECKLIST.md

---

## Troubleshooting

### If script shows warnings about existing resources:

This is normal! The script checks if resources exist and won't recreate them.

Example:
```
[WARN] Container may already exist
[WARN] Workspace may already exist
```

These are fine - the script continues.

### If script fails on a step:

The script stops on errors. You can:
1. Fix the issue
2. Run the script again
3. It will skip already-created resources

---

## Quick Commands

```powershell
# Navigate to project
cd C:\Users\blans\source\repos\ai-architect-portfolio\projects\04-databricks-enterprise

# Run clean script
.\Deploy-DatabricksUnity-Clean.ps1

# After completion, view saved config
notepad deployment_config.txt
```

---

## Time Required

- Script execution: ~15-20 minutes
- Workspace creation is the longest step (5-10 minutes)

---

## What Gets Created

In Azure (West US 2):
- Container: lakehouse
- Databricks workspace: databricks-unity-ml  
- Access Connector: unity-catalog-connector
- Managed identities: Enabled on both
- Role assignments: Storage Blob Data Contributor

In your project:
- deployment_config.txt (save this file!)

---

Ready to deploy! Run the clean script now.
