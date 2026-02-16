#!/bin/bash
# Azure Setup Script for LiveChat-RingCentral Sync
# This script creates all necessary Azure resources for deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Azure Setup for LiveChat-RingCentral Sync            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if logged in to Azure
echo -e "${YELLOW}→ Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    echo -e "${RED}✗ Not logged in to Azure${NC}"
    echo "Please run: az login"
    exit 1
fi

SUBSCRIPTION_STATE=$(az account show --query state -o tsv)
if [ "$SUBSCRIPTION_STATE" != "Enabled" ]; then
    echo -e "${RED}✗ Your Azure subscription is disabled or expired${NC}"
    echo "Please enable your subscription in the Azure Portal: https://portal.azure.com"
    exit 1
fi

echo -e "${GREEN}✓ Azure login verified${NC}"
echo ""

# Configuration
echo -e "${YELLOW}→ Setting up configuration...${NC}"
RESOURCE_GROUP="livechat-sync-rg"
LOCATION="eastus"  # Change if you prefer another region
TIMESTAMP=$(date +%s)
ACR_NAME="livechatsync${TIMESTAMP}"
POSTGRES_NAME="livechat-postgres-${TIMESTAMP}"
REDIS_NAME="livechat-redis-${TIMESTAMP}"
CONTAINERAPPS_ENV="livechat-sync-env"
POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)

echo -e "${GREEN}Configuration:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  Container Registry: $ACR_NAME"
echo "  PostgreSQL Server: $POSTGRES_NAME"
echo "  Redis Cache: $REDIS_NAME"
echo ""

# Create credentials file
CREDENTIALS_FILE=".azure-credentials.txt"
echo "# Azure Credentials - KEEP THIS FILE SECURE!" > $CREDENTIALS_FILE
echo "# Generated on $(date)" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

# Create resource group
echo -e "${YELLOW}→ Creating resource group...${NC}"
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

echo -e "${GREEN}✓ Resource group created${NC}"

# Create container registry
echo -e "${YELLOW}→ Creating Azure Container Registry (this may take a few minutes)...${NC}"
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --location $LOCATION \
    --admin-enabled true \
    --output none

echo -e "${GREEN}✓ Container Registry created${NC}"

# Get ACR credentials
echo -e "${YELLOW}→ Getting ACR credentials...${NC}"
ACR_SERVER="${ACR_NAME}.azurecr.io"
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

echo "ACR_LOGIN_SERVER=$ACR_SERVER" >> $CREDENTIALS_FILE
echo "ACR_USERNAME=$ACR_USERNAME" >> $CREDENTIALS_FILE
echo "ACR_PASSWORD=$ACR_PASSWORD" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

echo -e "${GREEN}✓ ACR credentials saved${NC}"

# Create PostgreSQL
echo -e "${YELLOW}→ Creating PostgreSQL Flexible Server (this may take 5-10 minutes)...${NC}"
az postgres flexible-server create \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_NAME \
    --location $LOCATION \
    --admin-user livechat_admin \
    --admin-password "$POSTGRES_PASSWORD" \
    --sku-name Standard_B1ms \
    --tier Burstable \
    --version 16 \
    --storage-size 32 \
    --public-access 0.0.0.0-255.255.255.255 \
    --yes \
    --output none

echo -e "${GREEN}✓ PostgreSQL server created${NC}"

# Create database
echo -e "${YELLOW}→ Creating database...${NC}"
az postgres flexible-server db create \
    --resource-group $RESOURCE_GROUP \
    --server-name $POSTGRES_NAME \
    --database-name livechat_sync \
    --output none

echo -e "${GREEN}✓ Database created${NC}"

# Get PostgreSQL connection details
POSTGRES_HOST=$(az postgres flexible-server show \
    --resource-group $RESOURCE_GROUP \
    --name $POSTGRES_NAME \
    --query fullyQualifiedDomainName -o tsv)

DATABASE_URL="postgresql://livechat_admin:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/livechat_sync?sslmode=require"

echo "DATABASE_URL=$DATABASE_URL" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

echo -e "${GREEN}✓ Database connection string saved${NC}"

# Create Redis
echo -e "${YELLOW}→ Creating Azure Cache for Redis (this may take 5-10 minutes)...${NC}"
az redis create \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --location $LOCATION \
    --sku Basic \
    --vm-size C0 \
    --output none

echo -e "${GREEN}✓ Redis cache created${NC}"

# Get Redis credentials
echo -e "${YELLOW}→ Getting Redis credentials...${NC}"
REDIS_HOST=$(az redis show \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --query hostName -o tsv)

REDIS_KEY=$(az redis list-keys \
    --resource-group $RESOURCE_GROUP \
    --name $REDIS_NAME \
    --query primaryKey -o tsv)

REDIS_URL="rediss://:${REDIS_KEY}@${REDIS_HOST}:6380"

echo "REDIS_URL=$REDIS_URL" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

echo -e "${GREEN}✓ Redis credentials saved${NC}"

# Create Container Apps Environment
echo -e "${YELLOW}→ Creating Container Apps Environment...${NC}"
az containerapp env create \
    --name $CONTAINERAPPS_ENV \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --output none

echo -e "${GREEN}✓ Container Apps Environment created${NC}"

# Create service principal for GitHub Actions
echo -e "${YELLOW}→ Creating service principal for GitHub Actions...${NC}"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
GITHUB_SP=$(az ad sp create-for-rbac \
    --name "github-actions-livechat-sync-${TIMESTAMP}" \
    --role contributor \
    --scopes /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP} \
    --sdk-auth)

echo "AZURE_CREDENTIALS<<EOF" >> $CREDENTIALS_FILE
echo "$GITHUB_SP" >> $CREDENTIALS_FILE
echo "EOF" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

echo -e "${GREEN}✓ Service principal created${NC}"

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✓ Setup Complete!                                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Resources created:${NC}"
echo "  ✓ Resource Group: $RESOURCE_GROUP"
echo "  ✓ Container Registry: $ACR_SERVER"
echo "  ✓ PostgreSQL Server: $POSTGRES_HOST"
echo "  ✓ Redis Cache: $REDIS_HOST"
echo "  ✓ Container Apps Environment: $CONTAINERAPPS_ENV"
echo "  ✓ Service Principal for GitHub Actions"
echo ""
echo -e "${YELLOW}Important files created:${NC}"
echo "  📄 $CREDENTIALS_FILE - Contains all credentials (KEEP SECURE!)"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "  1. Review credentials: cat $CREDENTIALS_FILE"
echo "  2. Add secrets to GitHub (see QUICKSTART_AZURE.md)"
echo "  3. Update .github/workflows/azure-deploy.yml with:"
echo "     ACR_NAME: $ACR_NAME"
echo "     RESOURCE_GROUP: $RESOURCE_GROUP"
echo "  4. Push to GitHub to trigger deployment"
echo ""
echo -e "${YELLOW}Cost saving tip:${NC}"
echo "  Stop PostgreSQL when not testing:"
echo "  az postgres flexible-server stop --name $POSTGRES_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
