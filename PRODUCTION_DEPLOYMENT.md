# 🚀 Production Deployment Guide

## ⚠️ CRITICAL SECURITY CHECKLIST

Before deploying to production, ensure ALL these items are completed:

### 1. Environment Configuration
- [ ] Set `FLASK_ENV=production` (NOT development)
- [ ] Set `FLASK_DEBUG=false`
- [ ] Generate strong `SECRET_KEY` (minimum 32 characters, cryptographically secure)
- [ ] Update `FIREBASE_PROJECT_ID` to your actual production Firebase project (solel-bone)
- [ ] Set `MOCK_FIREBASE=false` to use real Firebase
- [ ] Configure proper `LOG_LEVEL=INFO` or `ERROR`

### 2. Firebase Security
- [ ] Create production Firebase project with proper security rules
- [ ] Download production service account key
- [ ] Update `firebase-credentials.json` with production credentials
- [ ] Set Firebase security rules to restrict access appropriately
- [ ] Enable Firebase Authentication if needed

### 3. Web Server Configuration
- [ ] Use HTTPS only (no HTTP)
- [ ] Configure proper SSL certificates
- [ ] Set up reverse proxy (nginx/Apache) with security headers
- [ ] Configure rate limiting at web server level
- [ ] Set up proper firewall rules

### 4. Application Security
- [ ] CSRF protection is ENABLED (`WTF_CSRF_ENABLED=True`)
- [ ] All forms include CSRF tokens
- [ ] Secure session configuration
- [ ] Content Security Policy configured
- [ ] Security headers enabled

### 5. Infrastructure Security
- [ ] Database credentials secured
- [ ] Environment variables secured (not in code)
- [ ] Proper logging and monitoring
- [ ] Regular security updates
- [ ] Backup strategy implemented

## 🔧 Production Environment Variables

Create a `.env.production` file with these settings:

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=your-super-secure-secret-key-minimum-32-characters

# Firebase Configuration
FIREBASE_PROJECT_ID=solel-bone
FIREBASE_PRIVATE_KEY_ID=your-production-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR PRODUCTION PRIVATE KEY\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-production-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-production-client-id
GOOGLE_APPLICATION_CREDENTIALS=firebase-credentials-production.json

# Security Settings
MOCK_FIREBASE=false
WTF_CSRF_ENABLED=true

# Application Configuration
DEFAULT_LANGUAGE=hebrew
SESSION_TIMEOUT_HOURS=24

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/production.log

# Rate Limiting
RATELIMIT_STORAGE_URL=redis://localhost:6379
RATELIMIT_DEFAULT=1000 per hour
```

## 🚦 Deployment Commands

### For Docker:
```bash
# Build production image
docker build -t cable-tray-store:production .

# Run with production environment
docker run -d \
  --name cable-tray-store-prod \
  --env-file .env.production \
  -p 80:5000 \
  cable-tray-store:production
```

### For Traditional Server:
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export FLASK_ENV=production
export FLASK_DEBUG=false

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 run:app
```

## 🔒 Security Headers

Ensure your reverse proxy adds these security headers:

```nginx
# In your nginx configuration
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:;";
```

## 📊 Monitoring

Set up monitoring for:
- Application logs
- Error rates
- Response times
- Database performance
- Security events
- Resource usage

## 🔄 Updates

For production updates:
1. Test all changes in staging environment first
2. Create database backup before deployment
3. Deploy during low-traffic periods
4. Monitor application after deployment
5. Have rollback plan ready

## 🚨 NEVER DO THIS IN PRODUCTION:
- ❌ Use `FLASK_DEBUG=true`
- ❌ Use `MOCK_FIREBASE=true`
- ❌ Disable CSRF protection
- ❌ Use weak SECRET_KEY
- ❌ Expose debug information
- ❌ Use development Firebase credentials
- ❌ Skip HTTPS
- ❌ Use default passwords
- ❌ Expose internal file paths in errors

## ✅ Current Status

Your application is currently configured for:
- ✅ Development mode with CSRF disabled
- ✅ Mock Firebase for testing
- ✅ All security features ready for production
- ✅ Proper error handling
- ✅ Bilingual interface working
- ✅ 958 products loaded from Excel

**To deploy to production: Follow this checklist completely!**