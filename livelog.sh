#!/bin/bash

# 📊 Live Log Monitor for Solel Bone Store Production
# This script shows real-time logs from the Cloud Run service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
SERVICE_NAME="solel-bone-store"
REGION="us-central1"

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

# Check if gcloud is authenticated
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        error "❌ gcloud CLI not found! Install it from https://cloud.google.com/sdk/docs/install"
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        error "❌ Not authenticated with gcloud! Run: gcloud auth login"
    fi
    
    if [ -z "$PROJECT_ID" ]; then
        error "❌ No project set! Run: gcloud config set project YOUR_PROJECT_ID"
    fi
}

# Show service info
show_service_info() {
    log "📊 Live Log Monitor for Solel Bone Store"
    echo -e "${CYAN}===========================================${NC}"
    echo -e "${YELLOW}Project ID:${NC} $PROJECT_ID"
    echo -e "${YELLOW}Service:${NC} $SERVICE_NAME"
    echo -e "${YELLOW}Region:${NC} $REGION"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null || echo "Not found")
    echo -e "${YELLOW}URL:${NC} $SERVICE_URL"
    
    # Get latest revision
    REVISION=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.latestReadyRevisionName)" 2>/dev/null || echo "Not found")
    echo -e "${YELLOW}Latest Revision:${NC} $REVISION"
    
    echo -e "${CYAN}===========================================${NC}"
    echo ""
}

# Live logs function
show_live_logs() {
    log "🔴 Starting live log stream... (Press Ctrl+C to stop)"
    echo -e "${YELLOW}Tip: Use --limit to change number of lines (default: 50)${NC}"
    echo ""
    
    # Build the log filter
    FILTER="resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME"
    
    # Start streaming logs
    gcloud logging read "$FILTER" \
        --limit=${LOG_LIMIT:-50} \
        --format="table(timestamp,severity,textPayload:wrap=100)" \
        --follow \
        --project="$PROJECT_ID"
}

# Show recent errors
show_recent_errors() {
    log "🚨 Recent errors (last 10)..."
    
    FILTER="resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND severity>=ERROR"
    
    gcloud logging read "$FILTER" \
        --limit=10 \
        --format="table(timestamp,severity,textPayload:wrap=100)" \
        --project="$PROJECT_ID"
}

# Show service health
show_health() {
    log "💚 Service health check..."
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)" 2>/dev/null)
    
    if [ -n "$SERVICE_URL" ]; then
        if curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL" | grep -q "200"; then
            success "✅ Service is healthy and responding"
        else
            error "❌ Service is not responding properly"
        fi
        
        # Show last few access logs
        echo ""
        log "📈 Recent access patterns..."
        FILTER="resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME AND httpRequest.requestUrl!=\"\""
        
        gcloud logging read "$FILTER" \
            --limit=5 \
            --format="table(timestamp,httpRequest.requestMethod,httpRequest.requestUrl,httpRequest.status)" \
            --project="$PROJECT_ID"
    else
        error "❌ Could not get service URL"
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  live     - Show live log stream (default)"
    echo "  errors   - Show recent errors only"
    echo "  health   - Show service health and recent requests"
    echo "  info     - Show service information only"
    echo ""
    echo "Environment variables:"
    echo "  LOG_LIMIT - Number of log lines to show (default: 50)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Live logs"
    echo "  $0 live              # Live logs"
    echo "  $0 errors            # Recent errors"
    echo "  $0 health            # Health check"
    echo "  LOG_LIMIT=100 $0     # Show 100 lines"
}

# Main function
main() {
    check_gcloud
    
    case "${1:-live}" in
        "live")
            show_service_info
            show_live_logs
            ;;
        "errors")
            show_service_info
            show_recent_errors
            ;;
        "health")
            show_service_info
            show_health
            ;;
        "info")
            show_service_info
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

# Trap Ctrl+C for clean exit
trap 'echo -e "\n${YELLOW}Log monitoring stopped.${NC}"; exit 0' INT

# Run main function
main "$@"