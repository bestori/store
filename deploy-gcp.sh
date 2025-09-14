#!/bin/bash

# 🚀 Solel Bone Store - GCP Cloud Run Deployment Script
# This script handles Cloud Run deployment with Firebase integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="solel-bone"
SERVICE_NAME="solel-bone-store"
REGION="us-central1"
LOG_FILE="/tmp/deploy-gcp-$(date +%Y%m%d-%H%M%S).log"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${PURPLE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

# Check if gcloud is installed and authenticated
check_gcloud() {
    log "Checking gcloud CLI..."
    
    if ! command -v gcloud &> /dev/null; then
        error "❌ gcloud CLI not found! Install it from https://cloud.google.com/sdk/docs/install"
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        error "❌ Not authenticated with gcloud! Run: gcloud auth login"
    fi
    
    success "✅ gcloud CLI is ready"
}

# Get current project
get_project() {
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    
    if [ -z "$PROJECT_ID" ]; then
        error "❌ No project set! Run: gcloud config set project YOUR_PROJECT_ID"
    fi
    
    log "Using GCP Project: $PROJECT_ID"
}

# Validate environment
validate_environment() {
    log "Validating deployment environment..."
    
    # Check required files
    if [ ! -f "requirements.txt" ]; then
        error "❌ requirements.txt not found!"
    fi
    
    if [ ! -f "Dockerfile" ]; then
        error "❌ Dockerfile not found!"
    fi
    
    if [ ! -f "run.py" ]; then
        error "❌ run.py not found!"
    fi
    
    # Check for Firebase credentials
    if [ ! -f "firebase-credentials.json" ]; then
        warning "⚠️  firebase-credentials.json not found. Make sure to set it as a secret in Cloud Run."
    fi
    
    success "✅ Environment validation passed"
}

# Build and push container
build_and_push() {
    log "Building and pushing container..."
    
    # Configure Docker to use gcloud as a credential helper
    gcloud auth configure-docker
    
    # Build the container
    log "Building container image..."
    docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .
    
    # Push to Container Registry
    log "Pushing to Container Registry..."
    docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest
    
    success "✅ Container built and pushed successfully"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    log "Deploying to Cloud Run..."
    
    # Deploy the service
    gcloud run deploy $SERVICE_NAME \
        --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 0 \
        --port 8080 \
        --set-env-vars "FLASK_ENV=production,FLASK_DEBUG=false" \
        --set-secrets "FIREBASE_CREDENTIALS=firebase-credentials:latest" \
        --execution-environment gen2
    
    success "✅ Deployed to Cloud Run successfully"
}

# Get service URL
get_service_url() {
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
    
    if [ -n "$SERVICE_URL" ]; then
        success "🌐 Service URL: $SERVICE_URL"
        info "📊 Monitor logs: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME' --limit 50"
    else
        warning "⚠️  Could not retrieve service URL"
    fi
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    
    if [ -n "$SERVICE_URL" ]; then
        # Wait a moment for the service to be ready
        sleep 10
        
        # Test the service
        if curl -s "$SERVICE_URL" > /dev/null; then
            success "✅ Service is responding"
        else
            warning "⚠️  Service test unclear - check logs"
        fi
    else
        warning "⚠️  Cannot test - no service URL available"
    fi
}

# Setup Firebase secrets (if needed)
setup_firebase_secrets() {
    log "Setting up Firebase secrets..."
    
    if [ -f "firebase-credentials.json" ]; then
        # Create secret if it doesn't exist
        if ! gcloud secrets describe firebase-credentials >/dev/null 2>&1; then
            gcloud secrets create firebase-credentials --data-file=firebase-credentials.json
            success "✅ Firebase credentials secret created"
        else
            # Update existing secret
            gcloud secrets versions add firebase-credentials --data-file=firebase-credentials.json
            success "✅ Firebase credentials secret updated"
        fi
    else
        warning "⚠️  firebase-credentials.json not found - skipping secret setup"
    fi
}

# Migrate products to Firestore
migrate_products() {
    log "Running product migration to Firestore..."
    
    # Check if migration script exists
    if [ ! -f "migrate_to_firestore.py" ]; then
        warning "⚠️  migrate_to_firestore.py not found - skipping migration"
        return 0
    fi
    
    # Check if we have Excel files
    if [ ! -d "data/excel_files" ] || [ -z "$(ls -A data/excel_files 2>/dev/null)" ]; then
        warning "⚠️  No Excel files found in data/excel_files/ - skipping migration"
        return 0
    fi
    
    # Run migration with skip-existing flag to prevent duplicates
    log "Migrating products (skip existing to prevent duplicates)..."
    if python3 migrate_to_firestore.py --skip-existing --no-backup --verbose; then
        success "✅ Product migration completed successfully"
    else
        warning "⚠️  Product migration had issues - check logs"
    fi
}

# Main deployment function
deploy() {
    log "🚀 Starting Solel Bone Store Cloud Run deployment..."
    
    check_gcloud
    get_project
    validate_environment
    setup_firebase_secrets
    migrate_products
    build_and_push
    deploy_to_cloud_run
    get_service_url
    test_deployment
    
    success "🎉 Deployment completed successfully!"
    info "📊 Deployment log saved to: $LOG_FILE"
    info "🔍 View logs: gcloud logging read 'resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME' --limit 50"
    info "🔧 Manage service: gcloud run services describe $SERVICE_NAME --region=$REGION"
}

# Command line argument handling
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build")
        check_gcloud
        get_project
        validate_environment
        build_and_push
        ;;
    "migrate")
        check_gcloud
        get_project
        setup_firebase_secrets
        migrate_products
        ;;
    "test")
        get_project
        get_service_url
        test_deployment
        ;;
    *)
        echo "Usage: $0 {deploy|build|migrate|test}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full Cloud Run deployment with migration (default)"
        echo "  build   - Build and push container only"
        echo "  migrate - Run product migration to Firestore only"
        echo "  test    - Test current deployment"
        exit 1
        ;;
esac
