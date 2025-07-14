# 📊 JOTA News System - Monitoring & Dashboards Documentation

## 🎯 **Overview**

The JOTA News System includes a comprehensive monitoring stack with Prometheus metrics collection and Grafana dashboards. This documentation covers the current state of the monitoring system after cleanup and optimization.

## 🏗️ **Architecture**

### **Monitoring Stack Components**
- **Prometheus**: Metrics collection and storage (`http://localhost:9090`)
- **Grafana**: Dashboard visualization (`http://localhost:3000`)
- **Django Metrics**: Custom application metrics via django-prometheus
- **Infrastructure Exporters**: Redis, RabbitMQ, PostgreSQL, Nginx exporters

### **Data Flow**
```
Django App → Prometheus Endpoints → Prometheus Server → Grafana Dashboards
Infrastructure Services → Exporters → Prometheus Server → Grafana Dashboards
```

## 📈 **Working Metrics**

### **✅ Confirmed Working Metrics**

#### **News System Metrics**
- `jota_news_articles_total{category, source, status}` - **22,000+ articles**
- `jota_webhooks_events_total{status}` - Webhook processing events
- `django_http_requests_total_by_method_total{method}` - **610+ HTTP requests**

#### **Infrastructure Metrics**
- `redis_connected_clients` - **8 active connections**
- `redis_memory_used_bytes` - Cache memory usage
- `rabbitmq_connections` - **4 message broker connections**
- `rabbitmq_queue_messages{queue}` - Queue depths and message counts
- `postgres_up` - Database availability
- `nginx_http_requests_total` - Web server metrics

#### **System Performance**
- `rate(django_http_requests_total_by_method_total[5m])` - Request rates
- `process_resident_memory_bytes` - Memory usage
- `process_cpu_seconds_total` - CPU utilization

## 🎛️ **Dashboard Organization**

### **Active Dashboards**

#### **1. System Overview (Primary)**
- **URL**: `/d/jota-system-overview`
- **Purpose**: Main dashboard with all working metrics
- **Panels**: 8 panels showing real system data
- **Metrics**: News articles, HTTP requests, Redis/RabbitMQ status

#### **2. Core Metrics**
- **URL**: `/d/jota-news-dashboard` 
- **Purpose**: Basic system health monitoring
- **Focus**: Core application metrics

#### **3. Complete Dashboard**
- **URL**: `/d/jota-news-complete`
- **Purpose**: Infrastructure performance monitoring
- **Focus**: System resources and performance

#### **4. Redis Dashboard**
- **URL**: `/d/redis-dashboard`
- **Purpose**: Cache performance monitoring
- **Metrics**: Connections, memory, hit ratios, operations

#### **5. RabbitMQ Dashboard**  
- **URL**: `/d/rabbitmq-dashboard`
- **Purpose**: Message broker monitoring
- **Metrics**: Connections, queues, throughput, consumers

### **Disabled Dashboards**
The following dashboards have been disabled due to non-functional metrics:
- `business-dashboard.json.disabled` - Business KPI metrics (not implemented)
- `celery-dashboard.json.disabled` - Task processing metrics (connection issues)
- `security-dashboard.json.disabled` - Security event metrics (not integrated)

## ⚙️ **Configuration**

### **Prometheus Configuration**
**File**: `/infrastructure/monitoring/prometheus.yml`

**Scrape Jobs**:
- `django` - Main application metrics (2s interval)
- `django-business` - Business metrics endpoint (2s interval) 
- `django-security` - Security metrics endpoint (2s interval)
- `django-celery` - Celery metrics endpoint (2s interval)
- `redis`, `rabbitmq`, `postgres`, `nginx` - Infrastructure (2s interval)

### **Grafana Configuration**
**Dashboards**: `/infrastructure/monitoring/grafana/dashboards/`
**Provisioning**: Automatic dashboard loading every 10 seconds
**Datasource**: Prometheus at `http://prometheus:9090`

## 🔧 **Maintenance & Troubleshooting**

### **Common Issues**

#### **Metrics Not Appearing**
1. Check Prometheus targets: `http://localhost:9090/targets`
2. Verify endpoint responses: `curl http://localhost:8000/metrics`
3. Check scrape intervals in `prometheus.yml`

#### **Dashboard Panels Empty**
1. Test queries in Grafana Explore
2. Verify metric names in Prometheus
3. Check time range (use "Last 15 minutes")

#### **Celery Metrics Timeout**
- Known issue: `/celery/metrics/` endpoint times out
- Status: Under investigation
- Workaround: Use infrastructure metrics for task monitoring

### **Maintenance Commands**

#### **Restart Monitoring Stack**
```bash
docker-compose restart prometheus grafana
```

#### **Generate Test Data**
```bash
python3 quick_metrics_generator.py
```

#### **Check System Health**
```bash
curl http://localhost:8000/health/
curl http://localhost:9090/-/healthy
curl http://localhost:3000/api/health
```

## 📊 **Metrics Implementation Status**

### **✅ Fully Implemented**
- News article tracking and categorization
- HTTP request monitoring
- Infrastructure monitoring (Redis, RabbitMQ, PostgreSQL)
- System resource monitoring

### **⚠️ Partially Implemented**
- Webhook event tracking (defined but needs more integration)
- Basic health monitoring

### **❌ Not Implemented**
- Task retry rate monitoring
- Notification delivery rate tracking
- Security event logging
- Failed login attempt tracking
- Rate limiting metrics

## 🚀 **Future Improvements**

### **Short Term**
1. Fix Celery metrics endpoint timeout
2. Implement notification delivery tracking
3. Add basic security event logging

### **Medium Term**
1. Integrate authentication monitoring
2. Implement proper rate limiting with metrics
3. Add business KPI calculations

### **Long Term**
1. Add alerting rules in Prometheus
2. Implement custom business metrics
3. Add performance baseline monitoring

## 🔐 **Access Information**

### **Grafana**
- **URL**: http://localhost:3000
- **Login**: admin / admin
- **Main Dashboard**: http://localhost:3000/d/jota-system-overview

### **Prometheus**
- **URL**: http://localhost:9090
- **Query UI**: http://localhost:9090/graph
- **Targets**: http://localhost:9090/targets

### **Metrics Endpoints**
- **Main**: http://localhost:8000/metrics
- **Business**: http://localhost:8000/business/metrics/
- **Security**: http://localhost:8000/security/metrics/
- **Celery**: http://localhost:8000/celery/metrics/ (timeout issues)

## 📝 **Change Log**

### **2025-07-14 - Dashboard Cleanup**
- Removed non-functional dashboard panels
- Created consolidated System Overview dashboard
- Disabled dashboards with fake metrics
- Updated documentation to reflect current state
- Fixed Prometheus configuration for optimal scraping

---

**Last Updated**: July 14, 2025
**Status**: ✅ Production Ready (for implemented features)
**Next Review**: Monitor Celery metrics implementation