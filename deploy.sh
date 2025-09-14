#!/bin/bash

# 🚀 Cable Tray Store - Production Deployment Script
# This script handles complete production deployment with security checks

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
APP_USER="solelbone"
APP_DIR="/opt/${PROJECT_NAME}"
SERVICE_NAME="${PROJECT_NAME}"
BACKUP_DIR="/opt/backups/${PROJECT_NAME}"
LOG_FILE="/tmp/deploy-$(date +%Y%m%d-%H%M%S).log"

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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should NOT be run as root for security reasons. Run as regular user with sudo access."
    fi
}

# Validate environment
validate_environment() {
    log "Validating deployment environment..."
    
    # Check required files
    if [ ! -f ".env.production" ]; then
        error "❌ .env.production file not found! Create it following PRODUCTION_DEPLOYMENT.md"
    fi
    
    if [ ! -f "firebase-credentials-production.json" ]; then
        error "❌ Production Firebase credentials not found! Download from Firebase Console"
    fi
    
    if [ ! -f "requirements.txt" ]; then
        error "❌ requirements.txt not found!"
    fi
    
    # Check critical environment variables
    source .env.production
    
    if [ "$FLASK_ENV" != "production" ]; then
        error "❌ FLASK_ENV must be 'production' in .env.production"
    fi
    
    if [ "$FLASK_DEBUG" != "false" ]; then
        error "❌ FLASK_DEBUG must be 'false' in production"
    fi
    
    if [ "$MOCK_FIREBASE" != "false" ]; then
        error "❌ MOCK_FIREBASE must be 'false' in production"
    fi
    
    if [ ${#SECRET_KEY} -lt 32 ]; then
        error "❌ SECRET_KEY must be at least 32 characters long"
    fi
    
    success "✅ Environment validation passed"
}

# Security check
security_check() {
    log "Running security checks..."
    
    # Check file permissions
    chmod 600 .env.production
    chmod 600 firebase-credentials-production.json
    
    # Check for sensitive files in git
    if git ls-files --error-unmatch .env.production >/dev/null 2>&1; then
        error "❌ .env.production is tracked by git! Add to .gitignore"
    fi
    
    if git ls-files --error-unmatch firebase-credentials-production.json >/dev/null 2>&1; then
        error "❌ firebase-credentials-production.json is tracked by git! Add to .gitignore"
    fi
    
    success "✅ Security checks passed"
}

# Create system user
create_app_user() {
    log "Setting up application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        sudo useradd --system --shell /bin/bash --home-dir "$APP_DIR" --create-home "$APP_USER"
        info "Created system user: $APP_USER"
    else
        info "User $APP_USER already exists"
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."
    
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        nginx \
        supervisor \
        redis-server \
        certbot \
        python3-certbot-nginx \
        ufw
    
    success "✅ System dependencies installed"
}

# Setup application directory
setup_app_directory() {
    log "Setting up application directory..."
    
    # Create backup
    if [ -d "$APP_DIR" ]; then
        create_backup
    fi
    
    # Create app directory
    sudo mkdir -p "$APP_DIR"
    sudo mkdir -p "$APP_DIR/logs"
    sudo mkdir -p "$APP_DIR/data"
    
    # Copy application files
    sudo cp -r . "$APP_DIR/"
    sudo cp .env.production "$APP_DIR/.env"
    sudo cp firebase-credentials-production.json "$APP_DIR/firebase-credentials.json"
    
    # Set ownership
    sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    
    # Set permissions
    sudo chmod 755 "$APP_DIR"
    sudo chmod 600 "$APP_DIR/.env"
    sudo chmod 600 "$APP_DIR/firebase-credentials.json"
    
    success "✅ Application directory setup complete"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    sudo mkdir -p "$BACKUP_DIR"
    BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    if [ -d "$APP_DIR" ]; then
        sudo tar -czf "$BACKUP_DIR/$BACKUP_NAME" -C "$APP_DIR" .
        info "Backup created: $BACKUP_DIR/$BACKUP_NAME"
    fi
}

# Setup Python environment
setup_python_env() {
    log "Setting up Python environment..."
    
    cd "$APP_DIR"
    
    # Create virtual environment
    sudo -u "$APP_USER" python3 -m venv venv
    
    # Install dependencies
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r requirements.txt
    sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install gunicorn
    
    success "✅ Python environment setup complete"
}

# Configure Supervisor
configure_supervisor() {
    log "Configuring Supervisor..."
    
    sudo tee /etc/supervisor/conf.d/${SERVICE_NAME}.conf > /dev/null <<EOF
[program:${SERVICE_NAME}]
command=${APP_DIR}/venv/bin/gunicorn --bind unix:${APP_DIR}/${SERVICE_NAME}.sock --workers 4 --timeout 120 --max-requests 1000 --preload run:app
directory=${APP_DIR}
user=${APP_USER}
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=${APP_DIR}/logs/gunicorn.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
environment=LANG=en_US.UTF-8,LC_ALL=en_US.UTF-8
EOF
    
    sudo supervisorctl reread
    sudo supervisorctl update
    
    success "✅ Supervisor configuration complete"
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Get server name from user or use default
    read -p "Enter your domain name (e.g., yourdomain.com): " DOMAIN_NAME
    DOMAIN_NAME=${DOMAIN_NAME:-localhost}
    
    sudo tee /etc/nginx/sites-available/${SERVICE_NAME} > /dev/null <<EOF
upstream ${SERVICE_NAME} {
    server unix:${APP_DIR}/${SERVICE_NAME}.sock fail_timeout=0;
}

server {
    listen 80;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};
    
    # SSL Configuration (certificates will be added by certbot)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:; connect-src 'self';";
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private must-revalidate auth;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
    
    # Rate Limiting
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone \$binary_remote_addr zone=api:10m rate=100r/m;
    
    # Static files
    location /static/ {
        alias ${APP_DIR}/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Rate limit login attempts
    location /auth/login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://${SERVICE_NAME};
        include /etc/nginx/proxy_params;
    }
    
    # Rate limit API calls
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://${SERVICE_NAME};
        include /etc/nginx/proxy_params;
    }
    
    # Main application
    location / {
        proxy_pass http://${SERVICE_NAME};
        include /etc/nginx/proxy_params;
    }
    
    # Health check
    location /health {
        proxy_pass http://${SERVICE_NAME};
        include /etc/nginx/proxy_params;
        access_log off;
    }
}
EOF
    
    # Enable site
    sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx configuration
    sudo nginx -t
    
    success "✅ Nginx configuration complete"
}

# Setup SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    if [ "$DOMAIN_NAME" != "localhost" ]; then
        read -p "Setup SSL certificate with Let's Encrypt? (y/n): " SETUP_SSL
        if [ "$SETUP_SSL" = "y" ]; then
            sudo certbot --nginx -d "$DOMAIN_NAME" -d "www.$DOMAIN_NAME" --non-interactive --agree-tos --email "admin@$DOMAIN_NAME"
            success "✅ SSL certificate setup complete"
        else
            warning "⚠️  SSL certificate setup skipped"
        fi
    else
        warning "⚠️  SSL setup skipped for localhost"
    fi
}

# Configure firewall
configure_firewall() {
    log "Configuring firewall..."
    
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow ssh
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    
    # Enable firewall (non-interactive)
    echo "y" | sudo ufw enable
    
    success "✅ Firewall configuration complete"
}

# Test deployment
test_deployment() {
    log "Testing deployment..."
    
    # Start services
    sudo supervisorctl start ${SERVICE_NAME}
    sudo systemctl restart nginx
    
    # Wait for startup
    sleep 10
    
    # Test local connection
    if curl -s http://localhost > /dev/null; then
        success "✅ Local HTTP test passed"
    else
        error "❌ Local HTTP test failed"
    fi
    
    # Test application response
    if curl -s http://localhost | grep -q "Solel Bone Store"; then
        success "✅ Application response test passed"
    else
        warning "⚠️  Application response test unclear"
    fi
    
    success "✅ Deployment tests completed"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create log rotation
    sudo tee /etc/logrotate.d/${SERVICE_NAME} > /dev/null <<EOF
${APP_DIR}/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ${APP_USER} ${APP_USER}
    postrotate
        supervisorctl restart ${SERVICE_NAME}
    endscript
}
EOF
    
    # Create health check script
    sudo tee ${APP_DIR}/health_check.sh > /dev/null <<'EOF'
#!/bin/bash
APP_URL="http://localhost"
HEALTH_ENDPOINT="${APP_URL}/health"
LOG_FILE="/opt/solel-bone/logs/health_check.log"

if curl -s "${HEALTH_ENDPOINT}" > /dev/null 2>&1; then
    echo "[$(date)] Health check PASSED" >> "${LOG_FILE}"
    exit 0
else
    echo "[$(date)] Health check FAILED" >> "${LOG_FILE}"
    # Restart the service
    supervisorctl restart solel-bone
    exit 1
fi
EOF
    
    sudo chmod +x ${APP_DIR}/health_check.sh
    sudo chown ${APP_USER}:${APP_USER} ${APP_DIR}/health_check.sh
    
    # Add cron job for health checks
    echo "*/5 * * * * ${APP_DIR}/health_check.sh" | sudo -u ${APP_USER} crontab -
    
    success "✅ Monitoring setup complete"
}

# Rollback function
rollback() {
    log "Rolling back deployment..."
    
    # Find latest backup
    LATEST_BACKUP=$(sudo ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -n1)
    
    if [ -n "$LATEST_BACKUP" ]; then
        sudo supervisorctl stop ${SERVICE_NAME}
        sudo rm -rf ${APP_DIR}/*
        sudo tar -xzf "$LATEST_BACKUP" -C "$APP_DIR"
        sudo chown -R ${APP_USER}:${APP_USER} "$APP_DIR"
        sudo supervisorctl start ${SERVICE_NAME}
        success "✅ Rollback completed using backup: $(basename $LATEST_BACKUP)"
    else
        error "❌ No backup found for rollback"
    fi
}

# Main deployment function
deploy() {
    log "🚀 Starting Solel Bone Store production deployment..."
    
    check_root
    validate_environment
    security_check
    create_app_user
    install_system_deps
    setup_app_directory
    setup_python_env
    configure_supervisor
    configure_nginx
    setup_ssl
    configure_firewall
    test_deployment
    setup_monitoring
    
    success "🎉 Deployment completed successfully!"
    info "📊 Deployment log saved to: $LOG_FILE"
    info "📁 Application directory: $APP_DIR"
    info "📋 Service name: $SERVICE_NAME"
    info "🔍 Check logs: sudo tail -f $APP_DIR/logs/gunicorn.log"
    info "🔧 Control service: sudo supervisorctl {start|stop|restart} $SERVICE_NAME"
    info "🌐 Nginx config: /etc/nginx/sites-available/$SERVICE_NAME"
}

# Command line argument handling
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "rollback")
        rollback
        ;;
    "test")
        test_deployment
        ;;
    "backup")
        create_backup
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|test|backup}"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full production deployment (default)"
        echo "  rollback - Rollback to previous backup"
        echo "  test     - Test current deployment"
        echo "  backup   - Create manual backup"
        exit 1
        ;;
esac