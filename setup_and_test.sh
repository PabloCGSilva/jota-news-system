#!/bin/bash
set -e

# JOTA News System - Automated Setup and Testing Script
# =====================================================
# This script provides one-command setup and testing for the JOTA News System

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="JOTA News System"
DEMO_URL="http://localhost:8000/demo/"
API_DOCS_URL="http://localhost:8000/api/docs/"
GRAFANA_URL="http://localhost:3000"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "INFO")
            echo -e "${BLUE}ℹ ${message}${NC}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ ${message}${NC}"
            ;;
        "ERROR")
            echo -e "${RED}✗ ${message}${NC}"
            ;;
        "HEADER")
            echo -e "\n${PURPLE}${CYAN}================================${NC}"
            echo -e "${PURPLE}${CYAN}  ${message}${NC}"
            echo -e "${PURPLE}${CYAN}================================${NC}\n"
            ;;
    esac
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1
    
    print_status "INFO" "Waiting for ${service_name} to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" >/dev/null 2>&1; then
            print_status "SUCCESS" "${service_name} is ready!"
            return 0
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            print_status "INFO" "Still waiting for ${service_name}... (${attempt}/${max_attempts})"
        fi
        
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_status "ERROR" "${service_name} failed to start within expected time"
    return 1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "HEADER" "Checking Prerequisites"
    
    # Check Docker
    if command_exists docker; then
        print_status "SUCCESS" "Docker is installed"
        if docker info >/dev/null 2>&1; then
            print_status "SUCCESS" "Docker daemon is running"
        else
            print_status "ERROR" "Docker daemon is not running. Please start Docker Desktop."
            exit 1
        fi
    else
        print_status "ERROR" "Docker is not installed. Please install Docker Desktop."
        exit 1
    fi
    
    # Check Docker Compose
    if command_exists docker-compose; then
        print_status "SUCCESS" "Docker Compose is installed"
    else
        print_status "ERROR" "Docker Compose is not installed."
        exit 1
    fi
    
    # Check Python (for test runner)
    if command_exists python3; then
        print_status "SUCCESS" "Python 3 is available"
    elif command_exists python; then
        print_status "WARNING" "Python found (assuming Python 3)"
    else
        print_status "WARNING" "Python not found. Some features may not work."
    fi
    
    # Check system memory (need at least 4GB for reliable operation)
    if command_exists free; then
        total_mem=$(free -m | awk 'NR==2{printf "%.0f", $2}')
        if [ "$total_mem" -lt 4000 ]; then
            print_status "WARNING" "Low memory detected: ${total_mem}MB. Recommended: 4GB+ for optimal performance"
        else
            print_status "SUCCESS" "Memory check passed: ${total_mem}MB available"
        fi
    fi
    
    # Check available disk space (need at least 2GB)
    if command_exists df; then
        available_space=$(df . | awk 'NR==2 {print $4}')
        if [ "$available_space" -lt 2000000 ]; then  # 2GB in KB
            print_status "WARNING" "Low disk space detected. Recommended: 2GB+ free space"
        else
            print_status "SUCCESS" "Disk space check passed"
        fi
    fi
    
    # Check critical ports
    critical_ports="8000 3000 5432 6379"
    port_conflicts=0
    
    for port in $critical_ports; do
        if command_exists lsof && lsof -i :$port >/dev/null 2>&1; then
            print_status "WARNING" "Port $port is already in use"
            port_conflicts=$((port_conflicts + 1))
        fi
    done
    
    if [ $port_conflicts -gt 2 ]; then
        print_status "ERROR" "Multiple port conflicts detected. Please stop other services or change ports."
        exit 1
    fi
}

# Function to setup environment
setup_environment() {
    print_status "HEADER" "Setting Up Environment"
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_status "INFO" "Creating .env file..."
        cat > .env << EOL
# Django Settings
SECRET_KEY=django-insecure-jota-news-dev-key-$(date +%s)
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,api

# Database
DATABASE_URL=postgresql://postgres:postgres@db:5432/jota_news

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# External Services (Optional)
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Email Settings (Console backend for demo)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Demo Mode - No external integrations required
DEMO_MODE=True
EOL
        print_status "SUCCESS" "Environment file created"
    else
        print_status "INFO" "Environment file already exists"
    fi
    
    # Make scripts executable
    chmod +x test_runner.py 2>/dev/null || true
    chmod +x setup.sh 2>/dev/null || true
}

# Function to start services
start_services() {
    print_status "HEADER" "Starting Services"
    
    # Pull latest images
    print_status "INFO" "Pulling Docker images..."
    docker-compose pull
    
    # Build and start services
    print_status "INFO" "Building and starting services..."
    docker-compose up -d --build
    
    # Wait for services to be ready
    wait_for_service "http://localhost:8000/health/" "Django API"
    wait_for_service "http://localhost:3000/api/health" "Grafana"
    
    # Run migrations
    print_status "INFO" "Running database migrations..."
    docker-compose exec -T api python manage.py migrate
    
    # Setup demo data for immediate use
    print_status "INFO" "Setting up demo data for out-of-the-box functionality..."
    docker-compose exec -T api python setup_demo_data.py 2>/dev/null || print_status "WARNING" "Could not create demo data automatically"
}

# Function to run comprehensive tests
run_tests() {
    print_status "HEADER" "Running Comprehensive Tests"
    
    # Check if Python test runner is available
    if [ -f "test_runner.py" ]; then
        print_status "INFO" "Running automated test suite..."
        if command_exists python3; then
            python3 test_runner.py --all
        elif command_exists python; then
            python test_runner.py --all
        else
            print_status "WARNING" "Python not available for automated tests"
        fi
    else
        print_status "INFO" "Running basic Docker tests..."
        
        # Run Django tests
        print_status "INFO" "Running Django unit tests..."
        docker-compose exec -T api pytest tests/unit/ -v --tb=short || print_status "WARNING" "Some unit tests failed"
        
        # Run integration tests
        print_status "INFO" "Running integration tests..."
        docker-compose exec -T api pytest tests/integration/ -v --tb=short || print_status "WARNING" "Some integration tests failed"
    fi
    
    # Test API endpoints
    print_status "INFO" "Testing API endpoints..."
    local endpoints=(
        "http://localhost:8000/health/"
        "http://localhost:8000/api/v1/news/categories/"
        "http://localhost:8000/metrics"
        "http://localhost:8000/celery/health/"
        "http://localhost:8000/business/health/"
        "http://localhost:8000/security/health/"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -s -f "$endpoint" >/dev/null; then
            print_status "SUCCESS" "✓ $(basename "$endpoint")"
        else
            print_status "WARNING" "⚠ $(basename "$endpoint") not responding"
        fi
    done
}

# Function to validate system is ready
validate_system_ready() {
    print_status "HEADER" "Final System Validation"
    
    local validation_failed=0
    
    # Test critical endpoints
    local critical_endpoints=(
        "http://localhost:8000/health/"
        "http://localhost:8000/api/"
        "http://localhost:3000/api/health"
    )
    
    for endpoint in "${critical_endpoints[@]}"; do
        if curl -s -f "$endpoint" >/dev/null 2>&1; then
            print_status "SUCCESS" "✓ $(basename "$endpoint") is responding"
        else
            print_status "ERROR" "✗ $(basename "$endpoint") is not responding"
            validation_failed=1
        fi
    done
    
    # Check database connectivity
    if docker-compose exec -T api python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('DB OK')" 2>/dev/null | grep -q "DB OK"; then
        print_status "SUCCESS" "✓ Database connectivity verified"
    else
        print_status "ERROR" "✗ Database connectivity failed"
        validation_failed=1
    fi
    
    # Check Redis connectivity
    if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
        print_status "SUCCESS" "✓ Redis connectivity verified"
    else
        print_status "ERROR" "✗ Redis connectivity failed"
        validation_failed=1
    fi
    
    if [ $validation_failed -eq 0 ]; then
        print_status "SUCCESS" "🎉 All systems are operational!"
        return 0
    else
        print_status "ERROR" "❌ System validation failed. Check logs above."
        return 1
    fi
}

# Function to display final information
show_final_info() {
    print_status "HEADER" "Setup Complete!"
    
    echo -e "${GREEN}🎉 ${PROJECT_NAME} is ready!${NC}\n"
    
    echo -e "${CYAN}📱 Access Points:${NC}"
    echo -e "  ${BLUE}🖥️  Demo Dashboard:${NC}     ${DEMO_URL}"
    echo -e "  ${BLUE}📚 API Documentation:${NC}   ${API_DOCS_URL}"
    echo -e "  ${BLUE}📊 Grafana Monitoring:${NC}  ${GRAFANA_URL} (admin/admin)"
    echo -e "  ${BLUE}🔧 Admin Panel:${NC}         http://localhost:8000/admin/ (admin/admin123)"
    echo -e "  ${BLUE}📈 Metrics:${NC}             http://localhost:8000/metrics/"
    
    echo -e "\n${CYAN}🚀 Quick Actions:${NC}"
    echo -e "  ${BLUE}Interactive Demo:${NC}       Visit ${DEMO_URL}"
    echo -e "  ${BLUE}Run All Tests:${NC}          ./test_runner.py --all"
    echo -e "  ${BLUE}Interactive Tests:${NC}      ./test_runner.py --demo"
    echo -e "  ${BLUE}Health Check:${NC}           ./test_runner.py --health"
    echo -e "  ${BLUE}Performance Test:${NC}       ./test_runner.py --performance"
    
    echo -e "\n${CYAN}🛠️  Management Commands:${NC}"
    echo -e "  ${BLUE}View Logs:${NC}              docker-compose logs -f api"
    echo -e "  ${BLUE}Django Shell:${NC}           docker-compose exec api python manage.py shell"
    echo -e "  ${BLUE}Run Migrations:${NC}         docker-compose exec api python manage.py migrate"
    echo -e "  ${BLUE}Create Superuser:${NC}       docker-compose exec api python manage.py createsuperuser"
    echo -e "  ${BLUE}Stop Services:${NC}          docker-compose down"
    echo -e "  ${BLUE}Restart Services:${NC}       docker-compose restart"
    
    echo -e "\n${CYAN}📋 Available Dashboards:${NC}"
    echo -e "  ${BLUE}• Complete System Overview${NC}"
    echo -e "  ${BLUE}• Celery Task Monitoring${NC}"
    echo -e "  ${BLUE}• Business Metrics${NC}"
    echo -e "  ${BLUE}• Security Monitoring${NC}"
    echo -e "  ${BLUE}• Redis Cache Metrics${NC}"
    
    echo -e "\n${GREEN}💡 Pro Tips:${NC}"
    echo -e "  ${YELLOW}• Use the demo dashboard for easy testing and exploration${NC}"
    echo -e "  ${YELLOW}• All monitoring metrics are available in Grafana${NC}"
    echo -e "  ${YELLOW}• The API documentation is interactive - try it out!${NC}"
    echo -e "  ${YELLOW}• Check logs with: docker-compose logs -f <service_name>${NC}"
    
    echo -e "\n${PURPLE}🎯 Next Steps:${NC}"
    echo -e "  1. ${CYAN}Visit the demo dashboard: ${DEMO_URL}${NC}"
    echo -e "  2. ${CYAN}Explore the API documentation: ${API_DOCS_URL}${NC}"
    echo -e "  3. ${CYAN}Check monitoring dashboards: ${GRAFANA_URL}${NC}"
    echo -e "  4. ${CYAN}Run comprehensive tests: ./test_runner.py --all${NC}"
}

# Function to handle cleanup on exit
cleanup() {
    if [ $? -ne 0 ]; then
        print_status "ERROR" "Setup failed. Check the logs above for details."
        echo -e "\n${YELLOW}Troubleshooting:${NC}"
        echo -e "  • Ensure Docker Desktop is running"
        echo -e "  • Check that ports 8000 and 3000 are available"
        echo -e "  • Try: docker-compose down && docker-compose up -d"
        echo -e "  • View logs: docker-compose logs"
    fi
}

# Set up trap for cleanup
trap cleanup EXIT

# Main execution
main() {
    echo -e "${PURPLE}${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║                    🗞️  JOTA NEWS SYSTEM                      ║"
    echo "║                                                              ║"
    echo "║              Automated Setup & Testing Script               ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}\n"
    
    # Parse command line arguments
    SKIP_TESTS=false
    QUICK_SETUP=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --quick)
                QUICK_SETUP=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --skip-tests    Skip running tests after setup"
                echo "  --quick         Quick setup (minimal checks)"
                echo "  --help          Show this help message"
                echo ""
                echo "This script will:"
                echo "  1. Check prerequisites (Docker, Docker Compose)"
                echo "  2. Set up environment variables"
                echo "  3. Start all services with Docker Compose"
                echo "  4. Run database migrations"
                echo "  5. Create sample data and superuser"
                echo "  6. Run comprehensive tests (unless --skip-tests)"
                echo "  7. Display access information"
                exit 0
                ;;
            *)
                print_status "ERROR" "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute setup steps
    if [ "$QUICK_SETUP" = false ]; then
        check_prerequisites
    fi
    
    setup_environment
    start_services
    
    if [ "$SKIP_TESTS" = false ]; then
        run_tests
    fi
    
    # Final system validation
    if validate_system_ready; then
        show_final_info
    else
        print_status "ERROR" "Setup completed but system validation failed."
        print_status "INFO" "Try running: docker-compose logs to check for errors"
        exit 1
    fi
}

# Run main function
main "$@"