# Cerina Protocol Foundry - Deployment Guide

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Production Deployment](#production-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Monitoring & Logging](#monitoring--logging)
7. [Security Considerations](#security-considerations)

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key or Anthropic API key

### Backend Setup

```bash
# Navigate to project root
cd cerina-protocol-foundry

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
nano .env

# Initialize database
python -c "from backend.models.database import init_db; init_db()"

# Run backend server
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access Points
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Redoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Set your API keys
export OPENAI_API_KEY=your-key-here
# OR
export ANTHROPIC_API_KEY=your-key-here
export LLM_PROVIDER=anthropic

# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Including MCP Server

```bash
# Start with MCP server profile
docker-compose --profile mcp up -d
```

### Building Individual Images

```bash
# Build backend image
docker build -f Dockerfile.backend -t cerina-backend .

# Build frontend image
docker build -f frontend/Dockerfile -t cerina-frontend ./frontend
```

---

## Production Deployment

### 1. Server Requirements

- **Minimum**: 2 vCPU, 4GB RAM, 20GB storage
- **Recommended**: 4 vCPU, 8GB RAM, 50GB storage
- OS: Ubuntu 22.04 LTS or similar

### 2. PostgreSQL Setup

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql <<EOF
CREATE USER cerina WITH PASSWORD 'your-secure-password';
CREATE DATABASE cerina_foundry OWNER cerina;
GRANT ALL PRIVILEGES ON DATABASE cerina_foundry TO cerina;
EOF
```

### 3. Application Setup

```bash
# Clone repository
git clone <your-repo-url> /opt/cerina-foundry
cd /opt/cerina-foundry

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Configure environment
cp .env.example .env
# Edit with production values

# Initialize database
python -c "from backend.models.database import init_db; init_db()"
```

### 4. Systemd Service

Create `/etc/systemd/system/cerina-backend.service`:

```ini
[Unit]
Description=Cerina Protocol Foundry Backend
After=network.target postgresql.service

[Service]
User=cerina
Group=cerina
WorkingDirectory=/opt/cerina-foundry
Environment="PATH=/opt/cerina-foundry/venv/bin"
EnvironmentFile=/opt/cerina-foundry/.env
ExecStart=/opt/cerina-foundry/venv/bin/gunicorn backend.api.main:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile /var/log/cerina/access.log \
    --error-logfile /var/log/cerina/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Create log directory
sudo mkdir -p /var/log/cerina
sudo chown cerina:cerina /var/log/cerina

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cerina-backend
sudo systemctl start cerina-backend
```

### 5. Nginx Reverse Proxy

Create `/etc/nginx/sites-available/cerina`:

```nginx
upstream cerina_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # Frontend static files
    root /opt/cerina-foundry/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://cerina_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://cerina_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Static asset caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/cerina /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. SSL Certificate

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `postgresql://user:pass@localhost/db` |
| `LLM_PROVIDER` | LLM provider (openai/anthropic) | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `MAX_ITERATIONS` | `5` | Max agent iterations |
| `MIN_SAFETY_SCORE` | `7.0` | Safety threshold |
| `MIN_CLINICAL_SCORE` | `6.0` | Clinical threshold |
| `MIN_EMPATHY_SCORE` | `6.0` | Empathy threshold |
| `CORS_ORIGINS` | `[]` | Allowed CORS origins |

---

## Database Setup

### SQLite (Development)

SQLite is used by default for development:

```bash
DATABASE_URL=sqlite:///./cerina_foundry.db
```

### PostgreSQL (Production)

1. **Create database:**
```sql
CREATE DATABASE cerina_foundry;
CREATE USER cerina WITH ENCRYPTED PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE cerina_foundry TO cerina;
```

2. **Connection string:**
```bash
DATABASE_URL=postgresql://cerina:your-password@localhost:5432/cerina_foundry
```

3. **Run migrations:**
```bash
# If using Alembic
alembic upgrade head
```

### Backup

```bash
# PostgreSQL backup
pg_dump -U cerina cerina_foundry > backup_$(date +%Y%m%d).sql

# Restore
psql -U cerina cerina_foundry < backup_20231201.sql
```

---

## Monitoring & Logging

### Log Files

- Backend: `/var/log/cerina/access.log`, `/var/log/cerina/error.log`
- Nginx: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`

### Health Endpoints

- Backend health: `GET /api/v1/health`
- WebSocket: `ws://host/ws/`

### Prometheus Metrics (Optional)

Add to `requirements.txt`:
```
prometheus-fastapi-instrumentator
```

Then in `main.py`:
```python
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

Access metrics at `/metrics`

---

## Security Considerations

### 1. API Keys
- Never commit API keys to version control
- Use environment variables or secrets manager
- Rotate keys regularly

### 2. Database
- Use strong passwords
- Enable SSL for database connections
- Regular backups

### 3. Network
- Use HTTPS everywhere
- Configure firewall (ufw)
- Rate limit API endpoints

### 4. Application
- Keep dependencies updated
- Enable CORS only for trusted origins
- Validate all user inputs

### Firewall Setup

```bash
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check DATABASE_URL
   - Verify PostgreSQL is running
   - Check user permissions

2. **LLM API errors**
   - Verify API key is valid
   - Check rate limits
   - Ensure sufficient credits

3. **WebSocket not connecting**
   - Check Nginx WebSocket config
   - Verify proxy headers
   - Check firewall rules

### Logs

```bash
# Backend logs
journalctl -u cerina-backend -f

# Nginx logs
tail -f /var/log/nginx/error.log

# Docker logs
docker-compose logs -f backend
```
