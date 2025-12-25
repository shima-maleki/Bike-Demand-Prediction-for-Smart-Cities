```# Deployment Guide

Complete guide for deploying the Bike Demand Prediction system to production.

## 🎯 Deployment Options

1. **Docker Compose** (Recommended for small-scale)
2. **Kubernetes** (For large-scale, high availability)
3. **Cloud Platforms** (AWS, GCP, Azure)
4. **Serverless** (AWS Lambda, Cloud Run)

## 🐳 Docker Compose Deployment

### Production Setup

#### 1. Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 8GB+ RAM, 20GB+ storage
- Domain name (optional, for SSL)
- Production secrets ready

#### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities.git
cd Bike-Demand-Prediction-for-Smart-Cities

# Copy production environment template
cp .env.example .env.prod

# Edit production environment
nano .env.prod
```

Required environment variables:
```bash
# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=bike_demand

# API Keys
WEATHER_API_KEY=your_openweathermap_key

# Airflow
AIRFLOW_POSTGRES_PASSWORD=airflow_password
AIRFLOW_SECRET_KEY=generate_with_openssl_rand_hex_32

# Grafana
GRAFANA_ADMIN_PASSWORD=grafana_password

# GitHub Container Registry (for images)
GITHUB_REPOSITORY=shima-maleki/bike-demand-prediction-for-smart-cities
IMAGE_TAG=latest

# Environment
ENVIRONMENT=production
```

#### 3. Build Images

```bash
# Build all images
docker-compose -f docker-compose.prod.yml build

# Or pull from GitHub Container Registry
docker login ghcr.io
docker-compose -f docker-compose.prod.yml pull
```

#### 4. Initialize Database

```bash
# Start database only
docker-compose -f docker-compose.prod.yml up -d postgres

# Wait for database to be ready
sleep 30

# Initialize schema (if not auto-initialized)
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d bike_demand -f /docker-entrypoint-initdb.d/02-schema.sql
```

#### 5. Start All Services

```bash
# Start all services in detached mode
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### 6. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check dashboard
curl http://localhost:8501

# Check Airflow
curl http://localhost:8080/health

# Check Grafana
curl http://localhost:3000/api/health
```

### Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Dashboard | http://localhost:8501 | - |
| MLflow | http://localhost:5000 | - |
| Airflow | http://localhost:8080 | airflow/airflow |
| Grafana | http://localhost:3000 | admin/[GRAFANA_ADMIN_PASSWORD] |
| Prometheus | http://localhost:9090 | - |

### Scaling

Scale specific services:

```bash
# Scale API to 3 replicas
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Scale with resource limits
docker-compose -f docker-compose.prod.yml up -d --scale api=3 --scale dashboard=2
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Helm 3.0+ (optional)

### 1. Create Namespace

```bash
kubectl create namespace bike-demand
kubectl config set-context --current --namespace=bike-demand
```

### 2. Create Secrets

```bash
# Database credentials
kubectl create secret generic postgres-secret \
  --from-literal=password=your_postgres_password

# API keys
kubectl create secret generic api-keys \
  --from-literal=weather-api-key=your_weather_key

# Airflow secret
kubectl create secret generic airflow-secret \
  --from-literal=postgres-password=airflow_password \
  --from-literal=secret-key=$(openssl rand -hex 32)
```

### 3. Deploy PostgreSQL

```yaml
# k8s/postgres/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: POSTGRES_DB
          value: bike_demand
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

Apply:
```bash
kubectl apply -f k8s/postgres/
```

### 4. Deploy API

```bash
# k8s/api/deployment.yaml
kubectl apply -f k8s/api/
```

### 5. Deploy Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: bike-demand-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.bike-demand.example.com
    - dashboard.bike-demand.example.com
    secretName: bike-demand-tls
  rules:
  - host: api.bike-demand.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 8000
  - host: dashboard.bike-demand.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: dashboard
            port:
              number: 8501
```

## ☁️ Cloud Platform Deployment

### AWS Deployment

#### Using ECS (Elastic Container Service)

1. **Push Images to ECR**

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Tag and push images
docker tag bike-demand-api:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/bike-demand-api:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/bike-demand-api:latest
```

2. **Create ECS Task Definition**

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
```

3. **Create ECS Service**

```bash
aws ecs create-service \
  --cluster bike-demand-cluster \
  --service-name api \
  --task-definition bike-demand-api \
  --desired-count 2 \
  --launch-type FARGATE
```

#### Using EKS (Elastic Kubernetes Service)

```bash
# Create EKS cluster
eksctl create cluster \
  --name bike-demand \
  --region us-east-1 \
  --nodes 3 \
  --node-type t3.medium

# Deploy to EKS
kubectl apply -f k8s/
```

### GCP Deployment

#### Using Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/bike-demand-api

# Deploy to Cloud Run
gcloud run deploy bike-demand-api \
  --image gcr.io/PROJECT_ID/bike-demand-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=... \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10
```

### Azure Deployment

#### Using Container Instances

```bash
# Create resource group
az group create --name bike-demand-rg --location eastus

# Create container instances
az container create \
  --resource-group bike-demand-rg \
  --name bike-demand-api \
  --image ghcr.io/shima-maleki/bike-demand-api:latest \
  --cpu 2 \
  --memory 2 \
  --registry-login-server ghcr.io \
  --registry-username $GITHUB_USERNAME \
  --registry-password $GITHUB_TOKEN \
  --dns-name-label bike-demand-api \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="..." \
    MLFLOW_TRACKING_URI="..."
```

## 🔒 Security Best Practices

### 1. Secrets Management

**Never commit secrets to Git!**

Use secrets managers:
- **Docker**: Docker Secrets or environment files (`.env.prod`)
- **Kubernetes**: Kubernetes Secrets + Sealed Secrets
- **AWS**: AWS Secrets Manager or Parameter Store
- **GCP**: Secret Manager
- **Azure**: Key Vault

### 2. SSL/TLS Certificates

```bash
# Using Let's Encrypt with cert-manager (K8s)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f k8s/cert-manager/cluster-issuer.yaml
```

### 3. Network Security

- Use private networks for database
- Implement firewall rules
- Enable VPC peering (cloud platforms)
- Use security groups / network policies

### 4. Container Security

```bash
# Scan images for vulnerabilities
docker scan bike-demand-api:latest

# Use non-root users in Dockerfiles
USER nonroot

# Keep base images updated
FROM python:3.11-slim-bullseye
```

## 📊 Monitoring & Logging

### Prometheus + Grafana Setup

Already included in `docker-compose.prod.yml`

1. **Access Grafana**: http://localhost:3000
2. **Login**: admin / [GRAFANA_ADMIN_PASSWORD]
3. **Import Dashboards**:
   - API Performance Dashboard
   - Model Metrics Dashboard
   - System Health Dashboard

### Application Logging

Configure centralized logging:

**Using ELK Stack:**
```yaml
# docker-compose.prod.yml additions
  elasticsearch:
    image: elasticsearch:8.11.0
    environment:
      - discovery.type=single-node

  kibana:
    image: kibana:8.11.0
    depends_on:
      - elasticsearch

  logstash:
    image: logstash:8.11.0
    volumes:
      - ./infrastructure/logstash/logstash.conf:/usr/share/logstash/pipeline/logstash.conf
```

**Using Cloud-native:**
- AWS: CloudWatch Logs
- GCP: Cloud Logging
- Azure: Monitor

## 🔄 CI/CD Pipeline

### GitHub Actions (Automated)

Workflows already configured in `.github/workflows/`:
- `ci.yml` - Runs on PR and push
- `cd.yml` - Builds and deploys on main branch
- `model-training.yml` - Weekly model retraining

### Manual Deployment

```bash
# Tag a release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# GitHub Actions will automatically:
# 1. Build Docker images
# 2. Run tests
# 3. Push to ghcr.io
# 4. Deploy to staging
# 5. (Manual approval for production)
```

## 🔧 Maintenance

### Database Backups

```bash
# Automated daily backups
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres bike_demand | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip < backup_20250101.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres bike_demand
```

### Model Updates

```bash
# Retrain and register new model
docker-compose -f docker-compose.prod.yml exec api \
  python -c "from src.training.train_pipeline import train_model; train_model()"

# Reload API model (zero-downtime)
curl -X POST http://localhost:8000/monitoring/models/reload
```

### Zero-Downtime Updates

```bash
# Rolling update (Docker Swarm)
docker service update --image ghcr.io/.../api:v2.0.0 bike-demand-api

# Rolling update (Kubernetes)
kubectl set image deployment/api api=ghcr.io/.../api:v2.0.0
kubectl rollout status deployment/api
```

## 📈 Scaling Guidelines

### Horizontal Scaling

**API Service:**
- Start: 2 replicas
- Peak hours: 5-10 replicas
- Auto-scale based on CPU (>70%)

**Database:**
- Use read replicas for heavy read workloads
- Connection pooling (pgBouncer)

### Vertical Scaling

Resource recommendations:

| Service | CPU | Memory | Storage |
|---------|-----|--------|---------|
| API | 2 cores | 2GB | 10GB |
| Dashboard | 1 core | 1GB | 5GB |
| PostgreSQL | 4 cores | 8GB | 100GB+ |
| MLflow | 2 cores | 2GB | 50GB+ |
| Airflow | 2 cores | 4GB | 20GB |

## 🚨 Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check database is running
docker-compose -f docker-compose.prod.yml ps postgres

# Check logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify connection
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d bike_demand -c "SELECT 1"
```

**2. API Not Starting**
```bash
# Check API logs
docker-compose -f docker-compose.prod.yml logs api

# Common issues:
# - Missing environment variables
# - Database not ready
# - Model not found in MLflow
```

**3. Out of Memory**
```bash
# Check resource usage
docker stats

# Increase memory limits in docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 4G
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [MLflow Deployment](https://mlflow.org/docs/latest/deployment/index.html)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)

---

**Repository**: https://github.com/shima-maleki/Bike-Demand-Prediction-for-Smart-Cities

**Questions?** Open an issue on GitHub
