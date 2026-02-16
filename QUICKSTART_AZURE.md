# Azure CI/CD Quick Start Guide

## 🚀 Get Up and Running in 30 Minutes

This guide gets you from zero to deployed with minimal fuss.

## Prerequisites Checklist

- [ ] Azure account (sign up at https://azure.microsoft.com/free/)
- [ ] Azure CLI installed (`winget install Microsoft.AzureCLI`)
- [ ] GitHub repository (you already have this!)
- [ ] 30 minutes of time

## Step-by-Step Setup

### Step 1: Install Azure CLI (5 minutes)

```bash
# Windows
winget install Microsoft.AzureCLI

# Restart your terminal, then verify
az --version
```

### Step 2: Login to Azure (2 minutes)

```bash
# Login (opens browser)
az login

# Verify you're logged in
az account show

# Set subscription if you have multiple
az account list --output table
az account set --subscription "YOUR_SUBSCRIPTION_NAME"
```

### Step 3: Run Setup Script (10 minutes)

Copy and paste this entire block into your terminal:

```bash
# Set your configuration
RESOURCE_GROUP="livechat-sync-rg"
LOCATION="eastus"  # Change if you prefer another region
ACR_NAME="livechatsync$(date +%s)"  # Adds timestamp for uniqueness
POSTGRES_PASSWORD="$(openssl rand -base64 32)"  # Generates secure password

echo "Creating resources..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Container Registry: $ACR_NAME"
echo "PostgreSQL Password: $POSTGRES_PASSWORD"
echo ""
echo "SAVE THIS PASSWORD: $POSTGRES_PASSWORD"
echo ""

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create container registry
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --location $LOCATION \
  --admin-enabled true

# Create PostgreSQL
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name livechat-sync-postgres-$(date +%s) \
  --location $LOCATION \
  --admin-user livechat_admin \
  --admin-password "$POSTGRES_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --public-access 0.0.0.0

# Create database
POSTGRES_SERVER=$(az postgres flexible-server list \
  --resource-group $RESOURCE_GROUP \
  --query "[0].name" -o tsv)

az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER \
  --database-name livechat_sync

# Create Redis
az redis create \
  --resource-group $RESOURCE_GROUP \
  --name livechat-sync-redis-$(date +%s) \
  --location $LOCATION \
  --sku Basic \
  --vm-size C0

# Create Container Apps Environment
az containerapp env create \
  --name livechat-sync-env \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

echo "✅ Resources created!"
echo ""
echo "Next: Get your credentials..."
```

### Step 4: Get Credentials (5 minutes)

```bash
# Get Azure credentials for GitHub Actions
echo "1. AZURE_CREDENTIALS:"
az ad sp create-for-rbac \
  --name "github-actions-livechat-sync" \
  --role contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP \
  --sdk-auth

echo ""
echo "2. ACR Credentials:"
ACR_NAME=$(az acr list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
az acr credential show --name $ACR_NAME

echo ""
echo "3. Database URL:"
POSTGRES_SERVER=$(az postgres flexible-server list \
  --resource-group $RESOURCE_GROUP \
  --query "[0].fullyQualifiedDomainName" -o tsv)
echo "postgresql://livechat_admin:$POSTGRES_PASSWORD@$POSTGRES_SERVER:5432/livechat_sync?sslmode=require"

echo ""
echo "4. Redis URL:"
REDIS_NAME=$(az redis list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
REDIS_KEY=$(az redis list-keys \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query primaryKey -o tsv)
REDIS_HOST=$(az redis show \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --query hostName -o tsv)
echo "rediss://:$REDIS_KEY@$REDIS_HOST:6380"

echo ""
echo "✅ Copy these credentials to GitHub Secrets!"
```

### Step 5: Add GitHub Secrets (5 minutes)

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each:

| Secret Name | Value | Where to get it |
|-------------|-------|-----------------|
| `AZURE_CREDENTIALS` | Full JSON output | From Step 4, section 1 |
| `ACR_LOGIN_SERVER` | `<name>.azurecr.io` | From Step 4, section 2 |
| `ACR_USERNAME` | Username | From Step 4, section 2 |
| `ACR_PASSWORD` | Password | From Step 4, section 2 |
| `DATABASE_URL` | Full connection string | From Step 4, section 3 |
| `REDIS_URL` | Full Redis URL | From Step 4, section 4 |

Also add your API credentials:
- `LIVECHAT_CLIENT_ID`
- `LIVECHAT_CLIENT_SECRET`
- `LIVECHAT_ACCESS_TOKEN`
- `LIVECHAT_WEBHOOK_SECRET`
- `RINGCENTRAL_CLIENT_ID`
- `RINGCENTRAL_CLIENT_SECRET`
- `RINGCENTRAL_JWT_TOKEN`
- `RINGCENTRAL_WEBHOOK_SECRET`

### Step 6: Update Workflow File (2 minutes)

Edit `.github/workflows/azure-deploy.yml` and update these values:

```yaml
env:
  ACR_NAME: <YOUR_ACR_NAME>  # From Step 3
  RESOURCE_GROUP: livechat-sync-rg
```

### Step 7: Push and Deploy (5 minutes)

```bash
# Add all files
git add .github/workflows/azure-deploy.yml

# Commit
git commit -m "Add Azure CI/CD pipeline"

# Push to trigger deployment
git push origin main
```

Go to GitHub → Actions tab to watch the deployment!

### Step 8: Create Container Apps (3 minutes)

After the workflow completes, create the container apps:

```bash
# Get values
RESOURCE_GROUP="livechat-sync-rg"
ACR_NAME=$(az acr list --resource-group $RESOURCE_GROUP --query "[0].name" -o tsv)
ACR_SERVER="${ACR_NAME}.azurecr.io"
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Get database and redis URLs from Step 4
# Set them as environment variables:
DATABASE_URL="<YOUR_DATABASE_URL>"
REDIS_URL="<YOUR_REDIS_URL>"

# Create main app
az containerapp create \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --environment livechat-sync-env \
  --image ${ACR_SERVER}/livechat-sync-app:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --cpu 0.5 \
  --memory 1.0Gi \
  --min-replicas 0 \
  --max-replicas 2 \
  --secrets \
    database-url="$DATABASE_URL" \
    redis-url="$REDIS_URL" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url

# Get app URL
az containerapp show \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv

echo "✅ Deployment complete!"
echo "Visit your app at the URL above!"
```

## 🎉 You're Done!

Your app is now deployed with CI/CD! Every push to `main` will automatically deploy.

## 📱 Access Your App

```bash
# Get your app URL
APP_URL=$(az containerapp show \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg \
  --query properties.configuration.ingress.fqdn \
  -o tsv)

echo "Health Check: https://$APP_URL/health"
echo "Dashboard: https://$APP_URL/demo/"
echo "API Docs: https://$APP_URL/docs"
```

## 💡 Next Steps

### Test Your Deployment
```bash
curl https://$APP_URL/health
# Should return: {"status":"healthy","database":"connected"}
```

### View Logs
```bash
az containerapp logs show \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg \
  --follow
```

### Add Celery Workers (Optional)
```bash
# Create worker container
az containerapp create \
  --name livechat-sync-celery-worker \
  --resource-group livechat-sync-rg \
  --environment livechat-sync-env \
  --image ${ACR_SERVER}/livechat-sync-app:latest \
  --command "celery" "-A" "app.core.celery_app" "worker" "--loglevel=info" \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --secrets \
    database-url="$DATABASE_URL" \
    redis-url="$REDIS_URL" \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url
```

## 💰 Cost Monitoring

```bash
# Check current costs
az consumption usage list \
  --start-date $(date -d '30 days ago' +%Y-%m-%d) \
  --end-date $(date +%Y-%m-%d) \
  --output table

# Set up budget alert (optional)
az consumption budget create \
  --budget-name livechat-sync-budget \
  --amount 50 \
  --time-grain Monthly \
  --category Cost
```

## 🛑 Stop Everything (Save Money)

```bash
# Scale to zero
az containerapp update \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg \
  --min-replicas 0 \
  --max-replicas 0

# Stop PostgreSQL
POSTGRES_SERVER=$(az postgres flexible-server list \
  --resource-group livechat-sync-rg \
  --query "[0].name" -o tsv)

az postgres flexible-server stop \
  --resource-group livechat-sync-rg \
  --name $POSTGRES_SERVER
```

## 🧹 Delete Everything

```bash
# Remove all resources (stops all billing)
az group delete --name livechat-sync-rg --yes --no-wait
```

## 🆘 Troubleshooting

### "Resource already exists" error
- ACR names must be globally unique
- Add a timestamp or random number: `livechatsync$(date +%s)`

### "Insufficient permissions" error
- Make sure you're logged in: `az login`
- Check your subscription: `az account show`

### "Container failed to start"
- Check logs: `az containerapp logs show --name livechat-sync-app --resource-group livechat-sync-rg`
- Verify environment variables are set correctly
- Test the Docker image locally first

### GitHub Actions failing
- Verify all secrets are added correctly
- Check that ACR credentials are correct
- Look at the Actions logs for specific errors

## 📚 Useful Commands

```bash
# View all resources
az resource list --resource-group livechat-sync-rg --output table

# View container app status
az containerapp show \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg

# View recent deployments
az containerapp revision list \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg \
  --output table

# Restart container
az containerapp revision restart \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg

# Execute command in container
az containerapp exec \
  --name livechat-sync-app \
  --resource-group livechat-sync-rg \
  --command "alembic upgrade head"
```

## 🎓 What You've Learned

- ✅ Created Azure resources using CLI
- ✅ Set up Azure Container Registry
- ✅ Configured PostgreSQL and Redis
- ✅ Created a CI/CD pipeline with GitHub Actions
- ✅ Deployed a multi-container application
- ✅ Learned cost management strategies

## 📞 Need Help?

- Azure Documentation: https://learn.microsoft.com/azure/
- GitHub Actions: https://docs.github.com/actions
- Container Apps: https://learn.microsoft.com/azure/container-apps/

---

**You did it!** 🎉 Your app is now deployed with automatic CI/CD from GitHub to Azure!
