#!/bin/bash

# 🚀 Build, Push, and Deploy Script for Solel Bone Store
# This script builds the Docker image, pushes it, and deploys to Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="solel-bone"
SERVICE_NAME="solel-bone-store"
REGION="europe-west1"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

info() {
    echo -e "${PURPLE}[INFO] $1${NC}"
}

# Main deployment function
main() {
    log "🚀 Starting Build, Push, and Deploy for Solel Bone Store"
    
    # Generate unique image tag
    IMAGE_TAG="deploy-$TIMESTAMP"
    IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME:$IMAGE_TAG"
    
    info "Using image tag: $IMAGE_TAG"
    info "Full image name: $IMAGE_NAME"
    
    # Step 1: Build Docker image
    log "🔨 Building Docker image..."
    docker build -t "$IMAGE_NAME" .
    success "✅ Docker image built successfully"
    
    # Step 2: Push to Container Registry
    log "📤 Pushing image to Container Registry..."
    docker push "$IMAGE_NAME"
    success "✅ Image pushed to registry"
    
    # Step 3: Deploy to Cloud Run
    log "☁️ Deploying to Cloud Run..."
    gcloud run deploy $SERVICE_NAME \
        --image "$IMAGE_NAME" \
        --region $REGION \
        --platform managed \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --port 8080 \
        --set-env-vars "FLASK_ENV=production,FLASK_DEBUG=false,DEPLOYMENT_VERSION=$TIMESTAMP" \
        --set-secrets "FIREBASE_CREDENTIALS=firebase-credentials:latest" \
        --execution-environment gen2
    
    success "✅ Deployment completed"
    
    # Step 4: Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    if [ -n "$SERVICE_URL" ]; then
        success "🌐 Service URL: $SERVICE_URL"
        
        # Step 5: Test the deployment
        log "🧪 Testing deployment..."
        sleep 10
        
        if curl -s "$SERVICE_URL" > /dev/null; then
            success "✅ Service is responding"
            
            # Test search functionality
            log "🔍 Testing search functionality..."
            SEARCH_RESULT=$(curl -s -L "$SERVICE_URL/search?q=100" | grep -o "נמצאו [0-9]*" | head -1)
            if [ -n "$SEARCH_RESULT" ]; then
                success "🎉 Search test result: $SEARCH_RESULT"
            else
                error "❌ Search test failed - no results found"
            fi
        else
            error "❌ Service is not responding"
        fi
    else
        error "❌ Could not retrieve service URL"
    fi
    
    success "🎉 Build, Push, and Deploy completed successfully!"
    info "📊 Image: $IMAGE_NAME"
    info "🌐 URL: $SERVICE_URL"
    info "🔍 Test search: curl -s '$SERVICE_URL/search?q=100'"
}

# Run main function
main "$@"