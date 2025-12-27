# Chapter 12: Production Deployment

## Overview

This chapter guides you through deploying the bike demand forecasting system to production environments.

**Estimated Time**: 2-3 hours

## Deployment Strategy

### Cloud Provider Comparison

| Provider | Best For | Monthly Cost | Ease of Setup |
|----------|----------|--------------|---------------|
| **AWS EC2** | Most flexible | $70-100 | Medium |
| **Google Cloud** | Simple setup | $80-110 | Easy |
| **Azure** | Enterprise | $90-120 | Medium |
| **DigitalOcean** | Simplest | $50-80 | Easiest |

**Recommendation for beginners**: Start with **Docker Compose on a single VM** (DigitalOcean or AWS EC2).

---

## Quick Deployment (Docker Compose on VM)

### Step 1: Provision Server

**Requirements:**
- 8GB RAM (minimum)
- 30GB SSD storage
- Ubuntu 22.04 LTS
- Open ports: 22, 80, 443, 8000, 8501

**DigitalOcean Droplet:**
```bash
# Create via web UI or CLI
doctl compute droplet create bike-demand \
  --region nyc1 \
  --size s-2vcpu-8gb \
  --image ubuntu-22-04-x64
```

**AWS EC2:**
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.large \
  --key-name your-key
```

### Step 2: Install Docker

```bash
# SSH into server
ssh root@your-server-ip

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify
docker --version
docker compose version
```

### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/your-username/Bike-Demand-Prediction-for-Smart-Cities.git
cd Bike-Demand-Prediction-for-Smart-Cities

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Start all services
cd infrastructure
docker compose up -d

# Initialize database
sleep 30
docker compose exec -T postgres psql -U postgres -d bike_demand_db < postgres/schema.sql

# Load data and train model
cd ..
docker compose -f infrastructure/docker-compose.yml run --rm api python scripts/backfill_historical_data.py
```

### Step 4: Setup Reverse Proxy (Nginx)

```bash
# Install Nginx
sudo apt install nginx

# Create config
sudo nano /etc/nginx/sites-available/bike-demand
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/bike-demand /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5: SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Security Hardening

### 1. Use Strong Passwords

```bash
# Generate secure password
openssl rand -base64 32

# Update .env
DB_PASSWORD=<strong-password-here>
```

### 2. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 3. Database Access Control

```sql
-- Create read-only user for API
CREATE USER api_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO api_user;
```

### 4. API Rate Limiting

Already implemented in FastAPI using `slowapi`.

---

## Monitoring Setup

### Prometheus Metrics

Metrics endpoint already available at `/metrics`

### Grafana Dashboard

```bash
# Add to docker-compose.yml
docker compose -f infrastructure/docker-compose.yml up -d grafana
```

Access at `http://your-domain:3000` (default credentials: admin/admin)

---

## Backup & Recovery

### Automated Daily Backups

```bash
# Create backup script
cat > /root/backup-db.sh << 'EOF'
#!/bin/bash
docker compose exec -T postgres pg_dump -U postgres bike_demand_db | gzip > /backups/db_$(date +%Y%m%d).sql.gz
find /backups -name "db_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /root/backup-db.sh

# Add to cron
echo "0 2 * * * /root/backup-db.sh" | crontab -
```

### Upload to Cloud Storage

```bash
# AWS S3
aws s3 sync /backups s3://your-backup-bucket/

# Google Cloud Storage
gsutil rsync -r /backups gs://your-backup-bucket/
```

---

## Cost Optimization

**Monthly Breakdown (AWS EC2 t3.large):**
- Compute: $60
- Storage: $3
- Network: $5-10
- **Total: ~$70/month**

**Cost Reduction:**
- Use spot instances for training jobs
- Auto-shutdown during off-hours
- Compress Docker images
- Use CDN for dashboard assets

---

## Production Checklist

- [ ] Server provisioned with adequate resources
- [ ] Docker and Docker Compose installed
- [ ] Application deployed and running
- [ ] Database initialized with schema
- [ ] Historical data loaded
- [ ] Models trained
- [ ] Nginx reverse proxy configured
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Automated backups enabled
- [ ] Monitoring dashboards accessible
- [ ] DNS configured
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Documentation updated

---

## Kubernetes Deployment (Advanced)

For teams needing auto-scaling and high availability, see `k8s/` directory for Kubernetes manifests.

**Benefits:**
- Auto-scaling based on load
- Zero-downtime deployments
- Self-healing (automatic restarts)

**Trade-offs:**
- More complex setup
- Higher operational overhead
- Increased cost (~$200/month minimum)

---

## Summary

You've successfully deployed a production ML system! Key achievements:

✅ Deployed to cloud infrastructure
✅ Configured SSL/HTTPS
✅ Implemented security best practices
✅ Setup monitoring and alerting
✅ Automated backups

**Next:** Monitor performance, iterate, and scale as needed.

---

**Questions?** Open a [GitHub Issue](https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities/issues)
