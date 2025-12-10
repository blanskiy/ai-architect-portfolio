# Security Guide - Credential Management
**Protecting Your Azure Credentials in Open Source Projects**

## 🔒 Overview

Your Azure credentials (storage keys, SAS tokens, API keys) are **sensitive** and should **NEVER** be committed to Git, especially in public/open-source repositories.

This project uses **environment variables** and **`.env` files** to keep credentials secure.

---

## ✅ What IS Committed to Git (Safe)

| File | Purpose | Contains Credentials? |
|------|---------|----------------------|
| `.env.example` | Template | ❌ No - just placeholders |
| `rag_config.py` | Code | ❌ No - reads from environment |
| `*.py` | Source code | ❌ No - uses environment variables |
| `*.md` | Documentation | ❌ No - instructions only |
| `.gitignore` | Security rules | ❌ No - prevents credential commits |

---

## ❌ What is NOT Committed to Git (Sensitive)

| File | Purpose | Why Not Committed |
|------|---------|-------------------|
| `.env` | Your actual credentials | ⚠️  **NEVER commit - in .gitignore** |
| `lancedb/` | Local vector database | Contains your data |
| `__pycache__/` | Python cache | Not needed in repo |

---

## 🛡️ How Security Works

### 1. **Environment Variables**

Credentials are stored as environment variables, not hardcoded:

```python
# ❌ BAD - Hardcoded credentials (DON'T DO THIS!)
account_name = "azlancedb"
sas_token = "sp=r&st=2025..."

# ✅ GOOD - Read from environment
account_name = os.getenv("AZURE_STORAGE_ACCOUNT")
sas_token = os.getenv("AZURE_STORAGE_SAS_TOKEN")
```

### 2. **`.env` File (Local Only)**

Your credentials are stored in `.env` file:
- Lives only on **your computer**
- Listed in `.gitignore`
- **Never** pushed to GitHub

```bash
# .env (YOUR LOCAL MACHINE ONLY)
AZURE_STORAGE_ACCOUNT=azlancedb
AZURE_STORAGE_SAS_TOKEN=sp=r&st=2025...
```

### 3. **`.env.example` (Safe Template)**

A template **without real credentials** that shows others what to set up:

```bash
# .env.example (SAFE TO COMMIT)
AZURE_STORAGE_ACCOUNT=your-storage-account-name
AZURE_STORAGE_SAS_TOKEN=your-sas-token-here
```

### 4. **`.gitignore` (Protection)**

Prevents accidental commits of sensitive files:

```gitignore
.env
lancedb/
*credentials*
*secrets*
```

---

## 🚀 Setup Instructions

### For You (Repository Owner)

**Already done! ✅**  
Your `.env` file is created with your Azure credentials.

```powershell
# Verify .env exists
Get-Content .env

# Should show your credentials (not in Git)
```

### For Others (Collaborators/Users)

If someone clones your repository:

1. **Copy the template:**
   ```powershell
   Copy-Item .env.example .env
   ```

2. **Fill in their own credentials:**
   ```powershell
   # Edit .env with their Azure credentials
   notepad .env
   ```

3. **Verify not committed:**
   ```powershell
   git status
   # .env should NOT appear in changes
   ```

---

## 🔍 Verification Checklist

### Before Committing to Git

Run these checks:

```powershell
# 1. Verify .env is in .gitignore
Get-Content .gitignore | Select-String ".env"
# Should show: .env

# 2. Verify .env is NOT tracked by Git
git status
# .env should NOT be listed

# 3. Search for hardcoded credentials in code
Get-ChildItem -Recurse -Include *.py | Select-String -Pattern "azlancedb|sp=r&st="
# Should return NOTHING (except in .env)

# 4. Double-check .env is ignored
git check-ignore .env
# Should return: .env
```

---

## 🚨 What If I Accidentally Commit Credentials?

### If you haven't pushed yet:

```powershell
# Remove from staging
git reset HEAD .env

# Remove from commit history
git commit --amend
```

### If you already pushed to GitHub:

**CRITICAL - Act immediately!**

1. **Revoke the credentials:**
   ```powershell
   # Delete the SAS token in Azure Portal
   # Generate a new one
   ```

2. **Remove from Git history:**
   ```powershell
   # Use BFG Repo Cleaner or git filter-branch
   # This is complex - see GitHub docs
   ```

3. **Update credentials:**
   ```powershell
   # Update .env with new credentials
   ```

**Prevention is key! Always verify before pushing!**

---

## 📊 Your Current Setup

### Storage Account Details

```
Account Name: azlancedb
Container: rag-container
Authentication: SAS Token
Permissions: Read-only (sp=r)
Expiration: 2027-01-01
IP Restriction: 67.164.71.224
```

### Security Features

✅ SAS token (not account key) - Limited permissions  
✅ Read-only access - Can't delete/modify  
✅ Expiration date - Token expires in 2027  
✅ IP restriction - Only works from your IP  
✅ Not in Git - Protected by .gitignore  

---

## 🎯 Best Practices

### DO ✅
- Use `.env` for local development
- Use `.env.example` as template
- Add `.env` to `.gitignore`
- Use environment variables in code
- Use SAS tokens (not account keys)
- Set expiration dates on tokens
- Restrict IP addresses when possible

### DON'T ❌
- Hardcode credentials in code
- Commit `.env` to Git
- Share credentials in chat/email
- Use account keys (too much access)
- Create tokens without expiration
- Give write permissions unless needed

---

## 🔐 Additional Security Layers

### 1. Use Azure Key Vault (Production)

For production deployments:

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://myvault.vault.azure.net/", credential=credential)
sas_token = client.get_secret("storage-sas-token").value
```

### 2. Use Managed Identity

For Azure-hosted applications:

```python
from azure.identity import ManagedIdentityCredential

credential = ManagedIdentityCredential()
# No credentials needed - Azure handles authentication
```

### 3. Rotate Credentials Regularly

```powershell
# Generate new SAS token every 90 days
az storage container generate-sas \
  --account-name azlancedb \
  --name rag-container \
  --permissions r \
  --expiry $(date -d "+90 days" +%Y-%m-%dT%H:%MZ)
```

---

## 📚 Resources

- [Azure Storage Security](https://learn.microsoft.com/en-us/azure/storage/common/storage-security-guide)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [12-Factor App Config](https://12factor.net/config)
- [OWASP Secrets Management](https://owasp.org/www-community/vulnerabilities/Secrets_Management)

---

## ✅ Summary

Your credentials are secure because:

1. ✅ Stored in `.env` (not committed to Git)
2. ✅ `.env` is in `.gitignore`
3. ✅ Code uses environment variables
4. ✅ SAS token has limited permissions
5. ✅ Token expires in 2027
6. ✅ IP-restricted access

**You can safely commit your code to GitHub!** 🚀

---

**Questions?** Check if `.env` is in your `.gitignore` before every commit!
