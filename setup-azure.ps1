# Azure Setup Script for LiveChat-RingCentral Sync (PowerShell)
# This script creates all necessary Azure resources for deployment

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Blue
Write-Host "║  Azure Setup for LiveChat-RingCentral Sync            ║" -ForegroundColor Blue
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Blue
Write-Host ""

# Check if logged in to Azure
Write-Host "→ Checking Azure login..." -ForegroundColor Yellow
try {
    $account = az account show --output json | ConvertFrom-Json
    if ($account.state -ne "Enabled") {
        Write-Host "✗ Your Azure subscription is disabled or expired" -ForegroundColor Red
        Write-Host "Please enable your subscription in the Azure Portal: https://portal.azure.com" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Azure login verified" -ForegroundColor Green
} catch {
    Write-Host "✗ Not logged in to Azure" -ForegroundColor Red
    Write-Host "Please run: az login" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Configuration
Write-Host "→ Setting up configuration..." -ForegroundColor Yellow
$RESOURCE_GROUP = "livechat-sync-rg"
$LOCATION = "eastus"  # Change if you prefer another region
$TIMESTAMP = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$ACR_NAME = "livechatsync$TIMESTAMP"
$POSTGRES_NAME = "livechat-postgres-$TIMESTAMP"
$REDIS_NAME = "livechat-redis-$TIMESTAMP"
$CONTAINERAPPS_ENV = "livechat-sync-env"

# Generate secure password
$POSTGRES_PASSWORD = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 20 | ForEach-Object {[char]$_})

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  Resource Group: $RESOURCE_GROUP"
Write-Host "  Location: $LOCATION"
Write-Host "  Container Registry: $ACR_NAME"
Write-Host "  PostgreSQL Server: $POSTGRES_NAME"
Write-Host "  Redis Cache: $REDIS_NAME"
Write-Host ""

# Create credentials file
$CREDENTIALS_FILE = ".azure-credentials.txt"
"# Azure Credentials - KEEP THIS FILE SECURE!" | Out-File -FilePath $CREDENTIALS_FILE -Encoding utf8
"# Generated on $(Get-Date)" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8

# Create resource group
Write-Host "→ Creating resource group..." -ForegroundColor Yellow
az group create `
    --name $RESOURCE_GROUP `
    --location $LOCATION `
    --output none
Write-Host "✓ Resource group created" -ForegroundColor Green

# Create container registry
Write-Host "→ Creating Azure Container Registry (this may take a few minutes)..." -ForegroundColor Yellow
az acr create `
    --resource-group $RESOURCE_GROUP `
    --name $ACR_NAME `
    --sku Basic `
    --location $LOCATION `
    --admin-enabled true `
    --output none
Write-Host "✓ Container Registry created" -ForegroundColor Green

# Get ACR credentials
Write-Host "→ Getting ACR credentials..." -ForegroundColor Yellow
$ACR_SERVER = "$ACR_NAME.azurecr.io"
$ACR_CREDS = az acr credential show --name $ACR_NAME --output json | ConvertFrom-Json
$ACR_USERNAME = $ACR_CREDS.username
$ACR_PASSWORD = $ACR_CREDS.passwords[0].value

"ACR_LOGIN_SERVER=$ACR_SERVER" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"ACR_USERNAME=$ACR_USERNAME" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"ACR_PASSWORD=$ACR_PASSWORD" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
Write-Host "✓ ACR credentials saved" -ForegroundColor Green

# Create PostgreSQL
Write-Host "→ Creating PostgreSQL Flexible Server (this may take 5-10 minutes)..." -ForegroundColor Yellow
az postgres flexible-server create `
    --resource-group $RESOURCE_GROUP `
    --name $POSTGRES_NAME `
    --location $LOCATION `
    --admin-user livechat_admin `
    --admin-password $POSTGRES_PASSWORD `
    --sku-name Standard_B1ms `
    --tier Burstable `
    --version 16 `
    --storage-size 32 `
    --public-access 0.0.0.0-255.255.255.255 `
    --yes `
    --output none
Write-Host "✓ PostgreSQL server created" -ForegroundColor Green

# Create database
Write-Host "→ Creating database..." -ForegroundColor Yellow
az postgres flexible-server db create `
    --resource-group $RESOURCE_GROUP `
    --server-name $POSTGRES_NAME `
    --database-name livechat_sync `
    --output none
Write-Host "✓ Database created" -ForegroundColor Green

# Get PostgreSQL connection details
$POSTGRES_INFO = az postgres flexible-server show `
    --resource-group $RESOURCE_GROUP `
    --name $POSTGRES_NAME `
    --output json | ConvertFrom-Json
$POSTGRES_HOST = $POSTGRES_INFO.fullyQualifiedDomainName
$DATABASE_URL = "postgresql://livechat_admin:$POSTGRES_PASSWORD@$POSTGRES_HOST:5432/livechat_sync?sslmode=require"

"DATABASE_URL=$DATABASE_URL" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
Write-Host "✓ Database connection string saved" -ForegroundColor Green

# Create Redis
Write-Host "→ Creating Azure Cache for Redis (this may take 5-10 minutes)..." -ForegroundColor Yellow
az redis create `
    --resource-group $RESOURCE_GROUP `
    --name $REDIS_NAME `
    --location $LOCATION `
    --sku Basic `
    --vm-size C0 `
    --output none
Write-Host "✓ Redis cache created" -ForegroundColor Green

# Get Redis credentials
Write-Host "→ Getting Redis credentials..." -ForegroundColor Yellow
$REDIS_INFO = az redis show `
    --resource-group $RESOURCE_GROUP `
    --name $REDIS_NAME `
    --output json | ConvertFrom-Json
$REDIS_HOST = $REDIS_INFO.hostName

$REDIS_KEYS = az redis list-keys `
    --resource-group $RESOURCE_GROUP `
    --name $REDIS_NAME `
    --output json | ConvertFrom-Json
$REDIS_KEY = $REDIS_KEYS.primaryKey
$REDIS_URL = "rediss://:$REDIS_KEY@$REDIS_HOST:6380"

"REDIS_URL=$REDIS_URL" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
Write-Host "✓ Redis credentials saved" -ForegroundColor Green

# Create Container Apps Environment
Write-Host "→ Creating Container Apps Environment..." -ForegroundColor Yellow
az containerapp env create `
    --name $CONTAINERAPPS_ENV `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --output none
Write-Host "✓ Container Apps Environment created" -ForegroundColor Green

# Create service principal for GitHub Actions
Write-Host "→ Creating service principal for GitHub Actions..." -ForegroundColor Yellow
$SUBSCRIPTION_ID = (az account show --output json | ConvertFrom-Json).id
$GITHUB_SP = az ad sp create-for-rbac `
    --name "github-actions-livechat-sync-$TIMESTAMP" `
    --role contributor `
    --scopes "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP" `
    --sdk-auth

"AZURE_CREDENTIALS<<EOF" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
$GITHUB_SP | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"EOF" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
"" | Out-File -FilePath $CREDENTIALS_FILE -Append -Encoding utf8
Write-Host "✓ Service principal created" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✓ Setup Complete!                                     ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Resources created:" -ForegroundColor Blue
Write-Host "  ✓ Resource Group: $RESOURCE_GROUP"
Write-Host "  ✓ Container Registry: $ACR_SERVER"
Write-Host "  ✓ PostgreSQL Server: $POSTGRES_HOST"
Write-Host "  ✓ Redis Cache: $REDIS_HOST"
Write-Host "  ✓ Container Apps Environment: $CONTAINERAPPS_ENV"
Write-Host "  ✓ Service Principal for GitHub Actions"
Write-Host ""
Write-Host "Important files created:" -ForegroundColor Yellow
Write-Host "  📄 $CREDENTIALS_FILE - Contains all credentials (KEEP SECURE!)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Blue
Write-Host "  1. Review credentials: Get-Content $CREDENTIALS_FILE"
Write-Host "  2. Add secrets to GitHub (see QUICKSTART_AZURE.md)"
Write-Host "  3. Update .github/workflows/azure-deploy.yml with:"
Write-Host "     ACR_NAME: $ACR_NAME"
Write-Host "     RESOURCE_GROUP: $RESOURCE_GROUP"
Write-Host "  4. Push to GitHub to trigger deployment"
Write-Host ""
Write-Host "Cost saving tip:" -ForegroundColor Yellow
Write-Host "  Stop PostgreSQL when not testing:"
Write-Host "  az postgres flexible-server stop --name $POSTGRES_NAME --resource-group $RESOURCE_GROUP"
Write-Host ""
Write-Host "Setup complete! 🎉" -ForegroundColor Green
Write-Host ""
Write-Host "View your credentials now? (Y/N)" -ForegroundColor Yellow
$response = Read-Host
if ($response -eq 'Y' -or $response -eq 'y') {
    Get-Content $CREDENTIALS_FILE
}
