#!/bin/bash

# JOTA News System Deployment Script
# Usage: ./scripts/deploy.sh [environment] [version]

set -e

# Configuration
ENVIRONMENTS=("staging" "production")
DOCKER_REGISTRY="ghcr.io"
IMAGE_NAME="jota-news-api"
AWS_REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if required tools are installed
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    command -v kubectl >/dev/null 2>&1 || { log_error "kubectl is required but not installed. Aborting."; exit 1; }
    
    # Check if we're in the right directory
    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found. Please run from project root."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

validate_environment() {
    local env=$1
    
    if [[ ! " ${ENVIRONMENTS[@]} " =~ " ${env} " ]]; then
        log_error "Invalid environment: $env"
        log_info "Valid environments: ${ENVIRONMENTS[*]}"
        exit 1
    fi
}

run_tests() {
    log_info "Running test suite..."
    
    # Start test services
    docker-compose -f docker-compose.ci.yml up -d db-test redis-test
    
    # Wait for services to be ready
    sleep 10
    
    # Run tests
    if docker-compose -f docker-compose.ci.yml run --rm api-test; then
        log_success "All tests passed"
    else
        log_error "Tests failed. Deployment aborted."
        docker-compose -f docker-compose.ci.yml down
        exit 1
    fi
    
    # Cleanup test services
    docker-compose -f docker-compose.ci.yml down
}

build_and_push() {
    local env=$1
    local version=$2
    
    log_info "Building and pushing Docker image for $env..."
    
    # Build image
    docker build -f services/api/Dockerfile.multistage \
        --target production \
        -t $DOCKER_REGISTRY/$IMAGE_NAME:$version \
        -t $DOCKER_REGISTRY/$IMAGE_NAME:$env \
        -t $DOCKER_REGISTRY/$IMAGE_NAME:latest \
        services/api/
    
    # Push to registry
    docker push $DOCKER_REGISTRY/$IMAGE_NAME:$version
    docker push $DOCKER_REGISTRY/$IMAGE_NAME:$env
    
    if [ "$env" == "production" ]; then
        docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest
    fi
    
    log_success "Image built and pushed successfully"
}

deploy_to_ecs() {
    local env=$1
    local version=$2
    
    log_info "Deploying to ECS $env..."
    
    # Update ECS service
    aws ecs update-service \
        --cluster jota-news-$env \
        --service jota-news-api-$env \
        --force-new-deployment \
        --region $AWS_REGION
    
    # Wait for deployment to complete
    log_info "Waiting for deployment to complete..."
    aws ecs wait services-stable \
        --cluster jota-news-$env \
        --services jota-news-api-$env \
        --region $AWS_REGION
    
    log_success "ECS deployment completed"
}

deploy_to_k8s() {
    local env=$1
    local version=$2
    
    log_info "Deploying to Kubernetes $env..."
    
    # Update deployment image
    kubectl set image deployment/jota-news-api \
        jota-news-api=$DOCKER_REGISTRY/$IMAGE_NAME:$version \
        -n jota-news-$env
    
    # Wait for rollout to complete
    kubectl rollout status deployment/jota-news-api -n jota-news-$env
    
    log_success "Kubernetes deployment completed"
}

run_health_checks() {
    local env=$1
    
    log_info "Running health checks for $env..."
    
    # Define health check URL based on environment
    if [ "$env" == "staging" ]; then
        HEALTH_URL="https://staging-api.jota.news/health/"
    else
        HEALTH_URL="https://api.jota.news/health/"
    fi
    
    # Wait for service to be ready
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$HEALTH_URL" > /dev/null; then
            log_success "Health check passed"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Health checks failed after $max_attempts attempts"
    return 1
}

run_smoke_tests() {
    local env=$1
    
    log_info "Running smoke tests for $env..."
    
    # Define API base URL
    if [ "$env" == "staging" ]; then
        API_BASE_URL="https://staging-api.jota.news"
    else
        API_BASE_URL="https://api.jota.news"
    fi
    
    # Test critical endpoints
    endpoints=(
        "/health/"
        "/api/v1/"
        "/api/v1/news/articles/"
        "/api/v1/news/categories/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "$API_BASE_URL$endpoint" > /dev/null; then
            log_success "✓ $endpoint"
        else
            log_error "✗ $endpoint"
            return 1
        fi
    done
    
    log_success "All smoke tests passed"
}

rollback() {
    local env=$1
    
    log_warning "Rolling back deployment for $env..."
    
    # Rollback ECS deployment
    if command -v aws >/dev/null 2>&1; then
        aws ecs update-service \
            --cluster jota-news-$env \
            --service jota-news-api-$env \
            --force-new-deployment \
            --region $AWS_REGION
    fi
    
    # Rollback Kubernetes deployment
    if command -v kubectl >/dev/null 2>&1; then
        kubectl rollout undo deployment/jota-news-api -n jota-news-$env
    fi
    
    log_success "Rollback completed"
}

notify_deployment() {
    local env=$1
    local version=$2
    local status=$3
    
    # Send notification to Slack (if webhook URL is set)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color
        local emoji
        
        if [ "$status" == "success" ]; then
            color="good"
            emoji="✅"
        else
            color="danger"
            emoji="❌"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"text\": \"$emoji JOTA News System deployment to $env $status\",
                    \"fields\": [
                        {\"title\": \"Environment\", \"value\": \"$env\", \"short\": true},
                        {\"title\": \"Version\", \"value\": \"$version\", \"short\": true},
                        {\"title\": \"Status\", \"value\": \"$status\", \"short\": true}
                    ]
                }]
            }" \
            $SLACK_WEBHOOK_URL
    fi
}

main() {
    local env=${1:-staging}
    local version=${2:-$(git rev-parse --short HEAD)}
    
    log_info "Starting deployment to $env with version $version"
    
    # Validate inputs
    validate_environment $env
    check_prerequisites
    
    # Pre-deployment steps
    if [ "$env" == "production" ]; then
        log_warning "Deploying to PRODUCTION environment"
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi
    
    # Run tests
    run_tests
    
    # Build and push
    build_and_push $env $version
    
    # Deploy
    if command -v aws >/dev/null 2>&1; then
        deploy_to_ecs $env $version
    fi
    
    if command -v kubectl >/dev/null 2>&1; then
        deploy_to_k8s $env $version
    fi
    
    # Post-deployment verification
    if run_health_checks $env && run_smoke_tests $env; then
        log_success "Deployment to $env completed successfully!"
        notify_deployment $env $version "success"
    else
        log_error "Deployment verification failed"
        rollback $env
        notify_deployment $env $version "failed"
        exit 1
    fi
}

# Help function
show_help() {
    cat << EOF
JOTA News System Deployment Script

Usage: $0 [environment] [version]

Arguments:
    environment    Target environment (staging|production) [default: staging]
    version        Version tag [default: current git commit]

Options:
    -h, --help     Show this help message

Examples:
    $0                          # Deploy to staging with current commit
    $0 staging                  # Deploy to staging with current commit
    $0 production v1.2.3        # Deploy v1.2.3 to production
    $0 staging feature-branch   # Deploy feature branch to staging

Environment Variables:
    SLACK_WEBHOOK_URL          Slack webhook for notifications
    AWS_PROFILE               AWS profile to use
    DOCKER_REGISTRY           Docker registry URL

EOF
}

# Parse command line arguments
case $1 in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac