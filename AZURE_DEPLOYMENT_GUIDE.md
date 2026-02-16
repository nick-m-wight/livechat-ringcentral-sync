# Azure CI/CD Deployment Guide

## 🎯 Overview

This guide walks you through setting up a CI/CD pipeline from GitHub to Azure using **Azure Container Apps** for minimal cost during learning/testing.

## 💰 Cost Estimates

### Development/Testing (recommended for learning)
- **Azure Container Apps**: $0-5/month (free tier)
- **PostgreSQL Flexible Server (Burstable B1ms)**: ~$12/month
- **Azure Cache for Redis (Basic C0)**: ~$16/month
- **GitHub Actions**: FREE
- **Total**: ~$15-30/month

### Cost Optimization Tips
1. **Stop resources when not in use**: Scale containers to zero
2. **Use development tiers**: PostgreSQL Burstable tier
3. **Testing hours only**: Run 2-3 hours/day = ~$2-3/month for compute
4. **Free alternatives**: Use Azure Container Apps free tier (180k vCPU-seconds/month)
5. **Redis alternative**: Use in-memory cache initially (free)

### Production (when ready)
- Container Apps: ~$30-50/month
- PostgreSQL: ~$50-100/month (production tier)
- Redis: ~$20-80/month
- Total: ~$100-200/month

## 🏗️ Architecture

```
GitHub Repository
    │
    ├─ Push/PR triggers GitHub Actions
    │
    ▼
GitHub Actions (CI/CD)
    │
    ├─ Build Docker images
    ├─ Run tests
    ├─ Push to Azure Container Registry
    │
    ▼
Azure Container Apps Environment
    │
    ├─ App Container (FastAPI)
    ├─ Celery Worker Container
    ├─ Celery Beat Container
    │
    ├─ → Azure Database for PostgreSQL
    └─ → Azure Cache for Redis
```

## 📋 Prerequisites

1. **Azure Account**
   - Sign up: https://azure.microsoft.com/free/
   - Free tier includes $200 credit for 30 days + free services for 12 months

2. **GitHub Account**
   - Your repository is already on GitHub

3. **Azure CLI** (install locally)
   ```bash
   # Windows
   winget install Microsoft.AzureCLI

   # Or download from: https://aka.ms/installazurecliwindows
   ```

4. **GitHub CLI** (optional but helpful)
   ```bash
   winget install GitHub.cli
   ```

## 🚀 Setup Steps

### Step 1: Azure Resource Setup

1. **Login to Azure**
   ```bash
   az login
   ```

2. **Set up variables**
   ```bash
   # Set these to your preferences
   RESOURCE_GROUP="livechat-sync-rg"
   LOCATION="eastus"  # or "westus2", "westeurope", etc.
   ACR_NAME="livechatsyncacr"  # must be globally unique, lowercase
   CONTAINERAPPS_ENV="livechat-sync-env"
   ```

3. **Create Resource Group**
   ```bash
   az group create \
     --name $RESOURCE_GROUP \
     --location $LOCATION
   ```

4. **Create Azure Container Registry**
   ```bash
   az acr create \
     --resource-group $RESOURCE_GROUP \
     --name $ACR_NAME \
     --sku Basic \
     --location $LOCATION
   ```

5. **Create PostgreSQL Database**
   ```bash
   # Create PostgreSQL Flexible Server (Burstable tier for cost savings)
   az postgres flexible-server create \
     --resource-group $RESOURCE_GROUP \
     --name livechat-sync-postgres \
     --location $LOCATION \
     --admin-user livechat_admin \
     --admin-password "YourSecurePassword123!" \
     --sku-name Standard_B1ms \
     --tier Burstable \
     --version 16 \
     --storage-size 32

   # Create database
   az postgres flexible-server db create \
     --resource-group $RESOURCE_GROUP \
     --server-name livechat-sync-postgres \
     --database-name livechat_sync

   # Allow Azure services access
   az postgres flexible-server firewall-rule create \
     --resource-group $RESOURCE_GROUP \
     --name livechat-sync-postgres \
     --rule-name AllowAzureServices \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0
   ```

6. **Create Azure Cache for Redis**
   ```bash
   az redis create \
     --resource-group $RESOURCE_GROUP \
     --name livechat-sync-redis \
     --location $LOCATION \
     --sku Basic \
     --vm-size C0
   ```

7. **Create Container Apps Environment**
   ```bash
   az containerapp env create \
     --name $CONTAINERAPPS_ENV \
     --resource-group $RESOURCE_GROUP \
     --location $LOCATION
   ```

### Step 2: GitHub Secrets Setup

1. **Get Azure credentials for GitHub Actions**
   ```bash
   # Create service principal for GitHub Actions
   az ad sp create-for-rbac \
     --name "github-actions-livechat-sync" \
     --role contributor \
     --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP \
     --sdk-auth
   ```

   Copy the entire JSON output.

2. **Get ACR credentials**
   ```bash
   # Enable admin user
   az acr update --name $ACR_NAME --admin-enabled true

   # Get credentials
   az acr credential show --name $ACR_NAME
   ```

3. **Get PostgreSQL connection string**
   ```bash
   echo "postgresql://livechat_admin:YourSecurePassword123!@livechat-sync-postgres.postgres.database.azure.com:5432/livechat_sync?sslmode=require"
   ```

4. **Get Redis connection string**
   ```bash
   az redis list-keys \
     --resource-group $RESOURCE_GROUP \
     --name livechat-sync-redis

   # Format: redis://:<PRIMARY_KEY>@livechat-sync-redis.redis.cache.windows.net:6380?ssl=True
   ```

5. **Add secrets to GitHub**

   Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

   Add these secrets:
   - `AZURE_CREDENTIALS`: (JSON from step 1)
   - `ACR_LOGIN_SERVER`: `<ACR_NAME>.azurecr.io`
   - `ACR_USERNAME`: (from step 2)
   - `ACR_PASSWORD`: (from step 2)
   - `DATABASE_URL`: (from step 3)
   - `REDIS_URL`: (from step 4)
   - `LIVECHAT_CLIENT_ID`: (your LiveChat credentials)
   - `LIVECHAT_CLIENT_SECRET`: (your LiveChat credentials)
   - `LIVECHAT_ACCESS_TOKEN`: (your LiveChat credentials)
   - `RINGCENTRAL_CLIENT_ID`: (your RingCentral credentials)
   - `RINGCENTRAL_CLIENT_SECRET`: (your RingCentral credentials)
   - `RINGCENTRAL_JWT_TOKEN`: (your RingCentral credentials)

### Step 3: Create GitHub Actions Workflow

Create `.github/workflows/azure-deploy.yml` in your repository (see file below).

### Step 4: Create Container Apps

After the workflow builds and pushes images, create the container apps:

```bash
# Get ACR credentials
ACR_SERVER="${ACR_NAME}.azurecr.io"

# Create main app container
az containerapp create \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
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
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url \
    LIVECHAT_CLIENT_ID=secretref:livechat-client-id \
    LIVECHAT_CLIENT_SECRET=secretref:livechat-client-secret \
  --secrets \
    database-url="$DATABASE_URL" \
    redis-url="$REDIS_URL" \
    livechat-client-id="$LIVECHAT_CLIENT_ID" \
    livechat-client-secret="$LIVECHAT_CLIENT_SECRET"

# Create Celery worker container
az containerapp create \
  --name livechat-sync-celery-worker \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image ${ACR_SERVER}/livechat-sync-app:latest \
  --command "celery" "-A" "app.core.celery_app" "worker" "--loglevel=info" \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url \
  --secrets \
    database-url="$DATABASE_URL" \
    redis-url="$REDIS_URL"

# Create Celery beat container (scheduler)
az containerapp create \
  --name livechat-sync-celery-beat \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINERAPPS_ENV \
  --image ${ACR_SERVER}/livechat-sync-app:latest \
  --command "celery" "-A" "app.core.celery_app" "beat" "--loglevel=info" \
  --registry-server $ACR_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --cpu 0.25 \
  --memory 0.5Gi \
  --min-replicas 0 \
  --max-replicas 1 \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url \
  --secrets \
    database-url="$DATABASE_URL" \
    redis-url="$REDIS_URL"
```

### Step 5: Verify Deployment

```bash
# Get app URL
az containerapp show \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv

# Test health endpoint
curl https://<your-app-url>/health
```

## 🔄 CI/CD Pipeline Workflow

1. **Developer pushes code** to `main` branch or creates PR
2. **GitHub Actions triggers**:
   - Checkout code
   - Build Docker image
   - Run tests (optional)
   - Push image to Azure Container Registry
   - Update Container Apps with new image
3. **Azure Container Apps**:
   - Pulls new image
   - Performs rolling update
   - Scales containers based on traffic

## 💾 Database Migrations

Run migrations after deployment:

```bash
# Execute migration in app container
az containerapp exec \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --command "alembic upgrade head"
```

Or add to startup command in Container App.

## 📊 Monitoring & Logs

```bash
# View app logs
az containerapp logs show \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --follow

# View Celery worker logs
az containerapp logs show \
  --name livechat-sync-celery-worker \
  --resource-group $RESOURCE_GROUP \
  --follow

# View metrics in Azure Portal
# Navigate to: Resource Group → Container App → Monitoring → Metrics
```

## 🛑 Stop/Start Services (Cost Savings)

```bash
# Scale to zero (stop billing for compute)
az containerapp update \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0 \
  --max-replicas 0

# Scale back up
az containerapp update \
  --name livechat-sync-app \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0 \
  --max-replicas 2

# Stop PostgreSQL (saves cost)
az postgres flexible-server stop \
  --resource-group $RESOURCE_GROUP \
  --name livechat-sync-postgres

# Start PostgreSQL
az postgres flexible-server start \
  --resource-group $RESOURCE_GROUP \
  --name livechat-sync-postgres
```

## 🧹 Cleanup (Delete Everything)

```bash
# Delete entire resource group (removes all resources)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

## 🔒 Security Best Practices

1. **Use Azure Key Vault** for secrets (more secure than container secrets)
2. **Enable managed identity** for Container Apps
3. **Restrict PostgreSQL firewall** to only Azure services
4. **Use private endpoints** for production
5. **Enable Azure Monitor** for alerting
6. **Rotate credentials** regularly

## 📚 Additional Resources

- [Azure Container Apps Docs](https://learn.microsoft.com/en-us/azure/container-apps/)
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [Azure PostgreSQL Flexible Server](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/)
- [Azure Cache for Redis](https://learn.microsoft.com/en-us/azure/azure-cache-for-redis/)

## 🆘 Troubleshooting

### Container fails to start
- Check logs: `az containerapp logs show --name <app-name> --resource-group $RESOURCE_GROUP`
- Verify environment variables and secrets
- Test Docker image locally first

### Database connection errors
- Verify firewall rules allow Azure services
- Check connection string format
- Ensure SSL mode is set (`?sslmode=require`)

### High costs
- Scale containers to zero when not testing
- Stop PostgreSQL server when not needed
- Use Burstable tier for PostgreSQL
- Monitor usage in Azure Cost Management

## 💡 Next Steps

1. Set up **Azure Application Insights** for monitoring
2. Configure **custom domain** and SSL certificate
3. Enable **auto-scaling** based on CPU/memory
4. Set up **staging environment** for testing
5. Configure **backup and disaster recovery**
