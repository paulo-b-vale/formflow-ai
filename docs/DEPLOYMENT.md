# 🚀 FormFlow AI - Deployment Guide

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Options](#deployment-options)
  - [Docker Compose (Recommended)](#docker-compose-recommended)
  - [Manual Deployment](#manual-deployment)
  - [Cloud Deployment](#cloud-deployment)
- [Production Configuration](#production-configuration)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)
- [Scaling](#scaling)

---

## Overview

FormFlow AI can be deployed in multiple ways depending on your infrastructure needs:

1. **Docker Compose**: Single-server deployment (recommended for small to medium workloads)
2. **Kubernetes**: Multi-server orchestration (recommended for large-scale production)
3. **Cloud Platforms**: Managed services (AWS, GCP, Azure)
4. **Manual**: Traditional server deployment

---

## Prerequisites

### Hardware Requirements

**Minimum (Development)**:
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD

**Recommended (Production)**:
- CPU: 4-8 cores
- RAM: 16GB
- Storage: 100GB SSD
- Network: 100 Mbps+

### Software Requirements

- **Operating System**: Linux (Ubuntu 22.04 LTS recommended) or macOS
- **Docker**: 24.0+ and Docker Compose 2.0+
- **Python**: 3.11+ (if manual deployment)
- **Node.js**: 18+ (if manual deployment)
- **MongoDB**: 7.0+
- **Redis**: 7.2+

### External Services

Required API keys:
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
- OpenAI API key (optional, [Get one here](https://platform.openai.com/api-keys))

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/formflow-ai.git
cd formflow-ai
```

### 2. Environment Variables

Copy and configure the environment file:

```bash
cp .env.example .env
nano .env  # or use your favorite editor
```

**Critical Variables to Configure**:

```env
# Database
MONGODB_URL=mongodb://mongodb:27017  # For Docker, or your MongoDB URI
DATABASE_NAME=formflow_ai

# Redis
REDIS_URL=redis://redis:6379/0

# AI Models (REQUIRED - Get your own keys!)
GEMINI_API_KEY=your_actual_gemini_api_key_here
OPENAI_API_KEY=your_actual_openai_key_here  # Optional

# Security (CHANGE THESE!)
SECRET_KEY=your-super-secret-key-min-32-chars-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# S3 Storage
S3_BUCKET_NAME=formflow-uploads
S3_ACCESS_KEY=your_s3_access_key
S3_SECRET_KEY=your_s3_secret_key
S3_ENDPOINT_URL=http://minio:9000  # For Docker, or your S3 URL

# CORS (Production URLs)
ALLOWED_ORIGINS=["https://your-domain.com","https://www.your-domain.com"]

# Email (Optional, for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# App Settings
ENVIRONMENT=production  # development | staging | production
LOG_LEVEL=INFO  # DEBUG | INFO | WARNING | ERROR
```

---

## Deployment Options

### Docker Compose (Recommended)

#### Development Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

Services started:
- Backend API: `http://localhost:8002`
- Frontend: `http://localhost:3000`
- MongoDB: `localhost:27017`
- Redis: `localhost:6379`
- MinIO: `http://localhost:9001` (admin: minioadmin/minioadmin)

#### Production Deployment

Use the production compose file:

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
```

**Create Production Compose File**:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    restart: always
    ports:
      - "8002:8002"
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - mongodb
      - redis
      - minio
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        - NEXT_PUBLIC_API_URL=https://api.your-domain.com
    restart: always
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production

  mongodb:
    image: mongo:7.0
    restart: always
    volumes:
      - mongodb_data:/data/db
      - ./mongodb-init:/docker-entrypoint-initdb.d
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASSWORD}
      - MONGO_INITDB_DATABASE=formflow_ai
    command: --wiredTigerCacheSizeGB 2

  redis:
    image: redis:7.2-alpine
    restart: always
    volumes:
      - redis_data:/data
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

  minio:
    image: minio/minio:latest
    restart: always
    volumes:
      - minio_data:/data
    environment:
      - MINIO_ROOT_USER=${S3_ACCESS_KEY}
      - MINIO_ROOT_PASSWORD=${S3_SECRET_KEY}
    command: server /data --console-address ":9001"

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - backend
      - frontend

volumes:
  mongodb_data:
  redis_data:
  minio_data:
```

#### Create Nginx Configuration

```nginx
# nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8002;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name your-domain.com www.your-domain.com;
        return 301 https://$server_name$request_uri;
    }

    # Main HTTPS server
    server {
        listen 443 ssl http2;
        server_name your-domain.com www.your-domain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API requests
        location /api/ {
            proxy_pass http://backend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts for AI processing
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Frontend
        location / {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # WebSocket support (future)
        location /ws/ {
            proxy_pass http://backend/ws/;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```

#### SSL Certificate Setup

**Option 1: Let's Encrypt (Recommended)**

```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal (already set up by certbot)
sudo certbot renew --dry-run

# Copy certificates to project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./ssl/
```

**Option 2: Self-Signed (Development Only)**

```bash
mkdir ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/privkey.pem \
  -out ssl/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

---

### Manual Deployment

#### Backend Setup

```bash
# Install Python dependencies
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations/setup
python create_admin_user.py
python add_performance_indexes.py

# Start backend (development)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Start backend (production with Gunicorn)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8002 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
```

**Systemd Service** (`/etc/systemd/system/formflow-backend.service`):

```ini
[Unit]
Description=FormFlow AI Backend
After=network.target mongodb.service redis.service

[Service]
Type=notify
User=formflow
WorkingDirectory=/opt/formflow-ai
Environment="PATH=/opt/formflow-ai/venv/bin"
ExecStart=/opt/formflow-ai/venv/bin/gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8002 \
  --timeout 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable formflow-backend
sudo systemctl start formflow-backend
sudo systemctl status formflow-backend
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

# Start production server
npm start

# Or use PM2 for process management
npm install -g pm2
pm2 start npm --name "formflow-frontend" -- start
pm2 save
pm2 startup
```

---

### Cloud Deployment

#### AWS Deployment

**Architecture**:
```
Route 53 → CloudFront → ALB → ECS/Fargate
                               ├─ Backend containers
                               └─ Frontend containers

DocumentDB (MongoDB) | ElastiCache (Redis) | S3
```

**Steps**:

1. **Create VPC and Subnets**

```bash
# Using AWS CLI
aws ec2 create-vpc --cidr-block 10.0.0.0/16
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24
```

2. **Setup Managed Services**

```bash
# DocumentDB (MongoDB-compatible)
aws docdb create-db-cluster \
  --db-cluster-identifier formflow-db \
  --engine docdb \
  --master-username admin \
  --master-user-password YourPassword123

# ElastiCache (Redis)
aws elasticache create-cache-cluster \
  --cache-cluster-id formflow-cache \
  --engine redis \
  --cache-node-type cache.t3.micro \
  --num-cache-nodes 1
```

3. **Push Docker Images to ECR**

```bash
# Authenticate
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

# Create repositories
aws ecr create-repository --repository-name formflow-backend
aws ecr create-repository --repository-name formflow-frontend

# Build and push
docker build -t formflow-backend .
docker tag formflow-backend:latest YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/formflow-backend:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/formflow-backend:latest
```

4. **Deploy to ECS/Fargate**

Create `task-definition.json`:

```json
{
  "family": "formflow-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/formflow-backend:latest",
      "portMappings": [
        {
          "containerPort": 8002,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "MONGODB_URL", "value": "mongodb://formflow-db.cluster-xxx.docdb.amazonaws.com:27017"},
        {"name": "REDIS_URL", "value": "redis://formflow-cache.xxx.cache.amazonaws.com:6379"}
      ],
      "secrets": [
        {"name": "SECRET_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:formflow/secret-key"},
        {"name": "GEMINI_API_KEY", "valueFrom": "arn:aws:secretsmanager:us-east-1:xxx:secret:formflow/gemini-key"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/formflow-backend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create ECS service
aws ecs create-service \
  --cluster formflow-cluster \
  --service-name formflow-backend \
  --task-definition formflow-backend \
  --desired-count 2 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=backend,containerPort=8002
```

#### Google Cloud Platform (GCP)

```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/formflow-backend

# Deploy to Cloud Run
gcloud run deploy formflow-backend \
  --image gcr.io/PROJECT_ID/formflow-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production \
  --set-secrets GEMINI_API_KEY=formflow-gemini-key:latest

# Deploy frontend
gcloud run deploy formflow-frontend \
  --image gcr.io/PROJECT_ID/formflow-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Azure

```bash
# Create Container Registry
az acr create --resource-group formflow-rg --name formflowregistry --sku Basic

# Build and push
az acr build --registry formflowregistry --image formflow-backend:latest .

# Create Container Instances
az container create \
  --resource-group formflow-rg \
  --name formflow-backend \
  --image formflowregistry.azurecr.io/formflow-backend:latest \
  --cpu 2 --memory 4 \
  --registry-login-server formflowregistry.azurecr.io \
  --registry-username formflowregistry \
  --registry-password PASSWORD \
  --dns-name-label formflow-api \
  --ports 8002 \
  --environment-variables \
    ENVIRONMENT=production \
    MONGODB_URL=mongodb://... \
  --secure-environment-variables \
    SECRET_KEY=your-secret-key \
    GEMINI_API_KEY=your-gemini-key
```

---

## Production Configuration

### 1. Create Admin User

```bash
# Run the admin creation script
python create_admin_user.py

# Or manually via API
curl -X POST "https://your-domain.com/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@your-company.com",
    "password": "SecureAdminPass123!",
    "full_name": "System Administrator",
    "role": "admin"
  }'
```

### 2. Database Indexing

```bash
# Apply performance indexes
python add_performance_indexes.py
```

This creates indexes on:
- `users.email` (unique)
- `form_templates.category`
- `form_responses.user_id`, `form_responses.submitted_at`
- `conversation_logs.session_id`, `conversation_logs.user_id`

### 3. Backup Strategy

**MongoDB Backup**:

```bash
# Create backup script
cat > /opt/formflow/backup-mongodb.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mongodb"
mkdir -p $BACKUP_DIR

mongodump \
  --uri="mongodb://admin:password@localhost:27017" \
  --db=formflow_ai \
  --out=$BACKUP_DIR/backup_$DATE

# Compress
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/backup_$DATE
rm -rf $BACKUP_DIR/backup_$DATE

# Keep only last 7 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/formflow/backup-mongodb.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/formflow/backup-mongodb.sh") | crontab -
```

**Redis Backup** (automatic via RDB):

```bash
# redis.conf
save 900 1       # Save if 1 key changed in 15 min
save 300 10      # Save if 10 keys changed in 5 min
save 60 10000    # Save if 10000 keys changed in 1 min

dir /var/lib/redis
dbfilename dump.rdb
```

### 4. Log Management

**Log Rotation** (`/etc/logrotate.d/formflow`):

```
/var/log/formflow/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 formflow formflow
    sharedscripts
    postrotate
        systemctl reload formflow-backend
    endscript
}
```

### 5. Environment Variables Validation

```bash
# Validate all required env vars are set
python -c "
import os
required_vars = [
    'MONGODB_URL', 'REDIS_URL', 'SECRET_KEY',
    'GEMINI_API_KEY', 'S3_BUCKET_NAME'
]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    print(f'Missing environment variables: {missing}')
    exit(1)
print('All required environment variables are set!')
"
```

---

## Monitoring & Maintenance

### Health Checks

**Backend Health Endpoint**:

```python
# app/main.py
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "mongodb": await check_mongodb(),
            "redis": await check_redis(),
            "minio": await check_minio()
        }
    }
```

Test:
```bash
curl http://localhost:8002/health
```

### Monitoring Tools

**Option 1: Prometheus + Grafana**

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus_data:
  grafana_data:
```

**Option 2: Cloud Monitoring**

- AWS CloudWatch
- GCP Cloud Monitoring
- Azure Monitor
- Datadog
- New Relic

### Application Metrics

Track these metrics:
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (%)
- Active users
- LLM API latency
- Token usage
- Cache hit rate

---

## Troubleshooting

### Common Issues

**1. Backend won't start**

```bash
# Check logs
docker-compose logs backend

# Common causes:
# - Missing environment variables
# - Database connection failed
# - Port already in use

# Solutions:
docker-compose down
docker-compose up -d
```

**2. MongoDB connection error**

```bash
# Test connection
docker exec -it mongodb mongo --eval "db.adminCommand('ping')"

# Check MongoDB logs
docker logs mongodb

# Recreate container
docker-compose down mongodb
docker volume rm formflow_mongodb_data  # WARNING: Deletes data!
docker-compose up -d mongodb
```

**3. Redis connection issues**

```bash
# Test Redis
docker exec -it redis redis-cli ping

# Should return: PONG

# Clear Redis cache
docker exec -it redis redis-cli FLUSHALL
```

**4. Frontend can't reach backend**

```bash
# Check CORS settings in .env
ALLOWED_ORIGINS=["http://localhost:3000"]

# Check network connectivity
docker network inspect formflow_default
```

**5. High memory usage**

```bash
# Check container stats
docker stats

# Limit container memory
docker-compose.yml:
services:
  backend:
    mem_limit: 2g
```

---

## Scaling

### Horizontal Scaling

**Load Balancer Setup** (Nginx):

```nginx
upstream backend_servers {
    least_conn;  # Load balancing method
    server backend1:8002 weight=1 max_fails=3 fail_timeout=30s;
    server backend2:8002 weight=1 max_fails=3 fail_timeout=30s;
    server backend3:8002 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    location /api/ {
        proxy_pass http://backend_servers/;
    }
}
```

### Database Scaling

**MongoDB Replica Set**:

```yaml
# docker-compose.replica.yml
services:
  mongodb-primary:
    image: mongo:7.0
    command: mongod --replSet rs0 --bind_ip_all

  mongodb-secondary1:
    image: mongo:7.0
    command: mongod --replSet rs0 --bind_ip_all

  mongodb-secondary2:
    image: mongo:7.0
    command: mongod --replSet rs0 --bind_ip_all
```

Initialize:
```javascript
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "mongodb-primary:27017" },
    { _id: 1, host: "mongodb-secondary1:27017" },
    { _id: 2, host: "mongodb-secondary2:27017" }
  ]
})
```

**Redis Cluster**:

```bash
# Create Redis cluster
docker run -d --name redis-cluster -p 6379-6384:6379-6384 \
  redis:7.2 redis-cluster --cluster-enabled yes
```

### Auto-Scaling (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: formflow-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: formflow-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use strong database passwords
- [ ] Enable SSL/TLS (HTTPS)
- [ ] Configure firewall rules
- [ ] Limit CORS origins
- [ ] Enable rate limiting
- [ ] Keep dependencies updated
- [ ] Implement backup strategy
- [ ] Set up monitoring alerts
- [ ] Use environment secrets manager (AWS Secrets Manager, etc.)
- [ ] Disable debug mode in production
- [ ] Implement DDoS protection
- [ ] Regular security audits

---

## Post-Deployment

### 1. Verify Deployment

```bash
# Health check
curl https://your-domain.com/api/health

# Test API
curl -X POST https://your-domain.com/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@your-company.com&password=YourPassword"

# Check frontend
curl https://your-domain.com
```

### 2. Performance Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Load test
ab -n 1000 -c 10 https://your-domain.com/api/health

# Or use wrk
wrk -t12 -c400 -d30s https://your-domain.com/api/health
```

### 3. Set Up Alerts

Configure alerts for:
- API downtime
- High error rates (>5%)
- Slow response times (>2s)
- High CPU/memory usage (>80%)
- Database connection issues
- Disk space low (<20%)

---

## Support

For deployment assistance:
- 📧 **Email**: devops@formflow-ai.com
- 💬 **Discord**: [Join our server](https://discord.gg/formflow)
- 📖 **Documentation**: [Full docs](https://docs.formflow-ai.com)

---

**Last Updated**: January 2025

**Deployment successfully completed? Star the repo and share your feedback!**
