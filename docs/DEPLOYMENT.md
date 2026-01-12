# Deployment Guide

This guide covers deploying FlowForm AI to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Deploy Options](#quick-deploy-options)
- [Docker Deployment](#docker-deployment)
- [Environment Variables](#environment-variables)
- [Production Checklist](#production-checklist)
- [Monitoring & Observability](#monitoring--observability)

---

## Prerequisites

- Docker & Docker Compose (for containerized deployment)
- MongoDB Atlas account or self-hosted MongoDB 7.0+
- Redis Cloud or self-hosted Redis 7.0+
- Google Cloud account for Gemini API access

---

## Quick Deploy Options

### Railway (Recommended)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

1. Click the button above or go to [Railway](https://railway.app)
2. Connect your GitHub repository
3. Add the required environment variables (see below)
4. Railway will auto-detect the Dockerfile and deploy

### Render

1. Create a new **Web Service** on [Render](https://render.com)
2. Connect your repository
3. Set:
   - **Build Command**: `docker build -t flowform .`
   - **Start Command**: `docker run -p 8000:8000 flowform`
4. Add environment variables in the Render dashboard

### Vercel (Frontend Only)

For the Next.js frontend:

```bash
cd frontend
vercel deploy --prod
```

Set `NEXT_PUBLIC_API_URL` to your backend URL.

---

## Docker Deployment

### Build and Run Locally

```bash
# Build all services
docker-compose build

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### Production Docker Compose

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - MONGODB_URL=${MONGODB_URL}
      - REDIS_URL=${REDIS_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://app:8000
    ports:
      - "3000:3000"
    depends_on:
      - app
    restart: unless-stopped
```

Run with:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URL` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/flowform` |
| `REDIS_URL` | Redis connection string | `redis://default:pass@redis-cloud.com:6379` |
| `JWT_SECRET_KEY` | Secret for JWT signing (min 32 chars) | `your-super-secret-key-min-32-chars` |
| `GOOGLE_API_KEY` | Google Gemini API key | `AIza...` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_NAME` | MongoDB database name | `flowform_ai` |
| `ENVIRONMENT` | Environment name | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiry | `30` |

### Generate JWT Secret

```bash
openssl rand -hex 32
```

---

## Production Checklist

### Security

- [ ] Change `JWT_SECRET_KEY` to a strong, unique value
- [ ] Set `CORS_ORIGINS` to specific domains (not `*`)
- [ ] Enable HTTPS (use reverse proxy like nginx or Cloudflare)
- [ ] Review rate limiting configuration
- [ ] Run security scan: `bandit -r app/`

### Performance

- [ ] Ensure MongoDB indexes are created (automatic on startup)
- [ ] Configure Redis connection pooling
- [ ] Set appropriate `ACCESS_TOKEN_EXPIRE_MINUTES`
- [ ] Enable gzip compression in reverse proxy

### Monitoring

- [ ] Set up health check monitoring
- [ ] Configure log aggregation (e.g., Datadog, Logflare)
- [ ] Set up uptime monitoring (e.g., UptimeRobot)
- [ ] Configure alerting for `/ready` endpoint failures

### Backup

- [ ] Enable MongoDB automated backups (Atlas) or configure mongodump
- [ ] Document restore procedures

---

## Monitoring & Observability

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Basic liveness check |
| `GET /ready` | Readiness check (verifies DB and Redis) |
| `GET /metrics` | Basic metrics (uptime, version) |

### Log Format

In production (`ENVIRONMENT=production`), logs are output as JSON:

```json
{
  "timestamp": "2026-01-11T22:30:00.000Z",
  "level": "INFO",
  "logger": "flowform.main",
  "message": "→ POST /auth/login",
  "request_id": "abc123",
  "method": "POST",
  "path": "/auth/login",
  "duration_ms": 45.2,
  "status_code": 200
}
```

### Prometheus Integration (Optional)

The `/metrics` endpoint can be extended for Prometheus. Add:

```python
# In app/main.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency')
```

---

## Troubleshooting

### Common Issues

**MongoDB Connection Failed**
- Verify `MONGODB_URL` is correct
- Check network/firewall rules
- Ensure IP is whitelisted in MongoDB Atlas

**Redis Connection Failed**
- Verify `REDIS_URL` is correct
- Check if Redis requires authentication
- The app will continue without rate limiting if Redis is unavailable

**Frontend Can't Reach Backend**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS configuration
- Ensure both services are on the same network (Docker)

---

## Support

For issues, please open a GitHub issue or contact the maintainer.
