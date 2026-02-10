#!/bin/bash
# Comprehensive Test Suite for Podman Deployment
# Tests all chapters systematically with detailed validation

set -o pipefail

# Color codes
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
CYAN='\033[1;36m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Test results array
declare -a TEST_RESULTS

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This test suite requires sudo${NC}"
    echo "Run with: sudo ./test-podman-deployment.sh [chapter]"
    exit 1
fi

# Logging
TEST_LOG="test-results-$(date +%Y%m%d-%H%M%S).log"
exec > >(tee -a "$TEST_LOG") 2>&1

# Print header
print_header() {
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}  ADEPT Podman Deployment Test Suite${NC}"
    echo -e "${BLUE}  Date: $(date)${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

# Print test section header
print_section() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Test helper functions
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("PASS: $test_name")
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("FAIL: $test_name")
        return 1
    fi
}

run_test_with_output() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -n "Testing: $test_name... "

    local output
    output=$(eval "$test_command" 2>&1)
    local result=$?

    if [ $result -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("PASS: $test_name")
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        echo -e "${YELLOW}Output: $output${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("FAIL: $test_name - $output")
        return 1
    fi
}

skip_test() {
    local test_name="$1"
    local reason="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    SKIPPED_TESTS=$((SKIPPED_TESTS + 1))
    echo -e "Testing: $test_name... ${YELLOW}⊘ SKIP${NC} ($reason)"
    TEST_RESULTS+=("SKIP: $test_name - $reason")
}

# Test 1: Prerequisites
test_prerequisites() {
    print_section "Prerequisites Check"

    run_test "Podman installed" "command -v podman"
    run_test "Podman-compose installed" "command -v podman-compose"
    run_test "Python 3.9+ available" "python3 --version | grep -E 'Python 3\.(9|1[0-9])'"
    run_test "Podman service accessible" "podman ps"
    run_test "Registry configured" "grep -q 'docker.io' /root/.config/containers/registries.conf"
}

# Test 2: Environment setup
test_environment() {
    print_section "Environment Setup"

    run_test "Project root accessible" "[ -d '/data/workspace/adept-agentic-framework-core' ]"
    run_test "Podman virtual environment exists" "[ -d '/data/workspace/adept-agentic-framework-core/.venv-podman' ]"
    run_test "Bootstrap script exists" "[ -f '/data/workspace/adept-agentic-framework-core/bootstrap-podman-env.sh' ]"
    run_test "Registry config script exists" "[ -f '/data/workspace/adept-agentic-framework-core/configure-podman-registries.sh' ]"
}

# Test 3: Chapter-specific tests
test_chapter() {
    local chapter_num="$1"
    local chapter_name="$2"
    local chapter_path="$3"
    local expected_containers=("${@:4}")

    print_section "Chapter $chapter_num: $chapter_name"

    # Check chapter directory
    if [ ! -d "$chapter_path" ]; then
        skip_test "Chapter $chapter_num directory" "Not found: $chapter_path"
        return 1
    fi

    cd "$chapter_path" || return 1

    # Check required files
    run_test "docker-compose.yaml exists" "[ -f 'docker-compose.yaml' ]"
    run_test "docker-compose.podman.yaml exists" "[ -f 'docker-compose.podman.yaml' ]"
    run_test "start-chapter-resources-podman.sh exists" "[ -f 'start-chapter-resources-podman.sh' ]"
    run_test "start script is executable" "[ -x 'start-chapter-resources-podman.sh' ]"

    # Check overlay file syntax
    run_test "Podman overlay has valid YAML" "podman-compose -f docker-compose.yaml -f docker-compose.podman.yaml config > /dev/null"

    # Verify no SELinux labels in overlay
    if grep -E ':\s*[Zz]\s*$' docker-compose.podman.yaml > /dev/null 2>&1; then
        run_test "No SELinux labels in overlay" "false"
    else
        run_test "No SELinux labels in overlay" "true"
    fi

    # Check for fix_directory_permissions function
    run_test "Startup script has permission fix" "grep -q 'fix_directory_permissions' start-chapter-resources-podman.sh"

    # Check containers if chapter is running
    local containers_running=true
    for container in "${expected_containers[@]}"; do
        if ! podman ps --format "{{.Names}}" | grep -q "^${container}$"; then
            containers_running=false
            break
        fi
    done

    if [ "$containers_running" = true ]; then
        echo -e "${YELLOW}Chapter $chapter_num appears to be running. Testing active deployment...${NC}"

        # Test running containers
        for container in "${expected_containers[@]}"; do
            run_test "Container $container running" "podman ps --format '{{.Names}}' | grep -q '^${container}$'"

            # Check for critical errors in logs
            local log_errors=$(podman logs --tail 50 "$container" 2>&1 | grep -iE "(error|exception|failed|fatal|critical)" | grep -viE "(deprecation|warning)" | wc -l)
            if [ "$log_errors" -eq 0 ]; then
                run_test "Container $container has no critical errors" "true"
            else
                run_test "Container $container has no critical errors" "false"
            fi
        done

        # Test chapter-specific endpoints
        test_chapter_endpoints "$chapter_num"

        # Test chapter-specific configuration
        test_chapter_config "$chapter_num"

    else
        echo -e "${YELLOW}Chapter $chapter_num not running. Skipping runtime tests.${NC}"
        skip_test "Chapter $chapter_num runtime tests" "Containers not running"
    fi

    cd - > /dev/null
}

# Test chapter endpoints
test_chapter_endpoints() {
    local chapter_num="$1"

    case "$chapter_num" in
        0)
            run_test "Ollama API (11434)" "curl -sf --max-time 5 http://localhost:11434/api/tags > /dev/null"
            run_test "MCP Server (8080)" "curl -sf --max-time 5 http://localhost:8080/health > /dev/null"
            run_test "Streamlit SSL (8501)" "curl -sfk --max-time 5 https://localhost:8501 > /dev/null"
            run_test "JupyterLab (8888)" "curl -sf --max-time 5 http://localhost:8888 > /dev/null"
            ;;
        1)
            run_test "MCP Server (8080)" "curl -sf --max-time 5 http://localhost:8080/health > /dev/null"
            run_test "Streamlit (8501)" "curl -sf --max-time 5 http://localhost:8501 > /dev/null"
            ;;
        2)
            run_test "MCP Server (8080)" "curl -sf --max-time 5 http://localhost:8080/health > /dev/null"
            run_test "HPC MCP Server (8081)" "curl -sf --max-time 5 http://localhost:8081/health > /dev/null"
            run_test "Streamlit (8501)" "curl -sf --max-time 5 http://localhost:8501 > /dev/null"
            ;;
        3)
            run_test "MCP Server (8080)" "curl -sf --max-time 5 http://localhost:8080/health > /dev/null"
            run_test "HPC MCP Server (8081)" "curl -sf --max-time 5 http://localhost:8081/health > /dev/null"
            run_test "Sandbox MCP Server (8082)" "curl -sf --max-time 5 http://localhost:8082/health > /dev/null"
            run_test "Streamlit (8501)" "curl -sf --max-time 5 http://localhost:8501 > /dev/null"
            ;;
    esac
}

# Test chapter configuration
test_chapter_config() {
    local chapter_num="$1"
    local chapter_path="/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-0${chapter_num}-*"

    case "$chapter_num" in
        0)
            # Check DATABASE_URL configuration
            if [ -f ".env" ]; then
                local db_url=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2-)
                if echo "$db_url" | grep -q "sqlite"; then
                    run_test "DATABASE_URL uses SQLite (correct for Ch0)" "true"
                elif echo "$db_url" | grep -q "postgresql"; then
                    run_test "DATABASE_URL uses SQLite (correct for Ch0)" "false"
                    echo -e "${RED}  ERROR: Chapter 0 .env has PostgreSQL URL but should use SQLite${NC}"
                else
                    skip_test "DATABASE_URL configuration" "Not found or unrecognized"
                fi
            else
                skip_test "DATABASE_URL configuration" ".env file not found"
            fi

            # Check data directory permissions
            if [ -d "data" ]; then
                local perms=$(stat -c "%a" data 2>/dev/null || stat -f "%Lp" data 2>/dev/null)
                if [ "$perms" = "777" ] || [ "$perms" = "775" ]; then
                    run_test "Data directory has correct permissions" "true"
                else
                    run_test "Data directory has correct permissions" "false"
                    echo -e "${YELLOW}  WARNING: data/ permissions are $perms (expected 777)${NC}"
                fi
            fi
            ;;
    esac
}

# Test 4: Container networking
test_networking() {
    print_section "Container Networking"

    local networks=$(podman network ls --format "{{.Name}}" | grep -E "agentic_network|ch0[0-3]")

    if [ -z "$networks" ]; then
        skip_test "Container networking" "No agentic networks found"
        return
    fi

    for network in $networks; do
        run_test "Network $network exists" "podman network inspect $network > /dev/null"
    done
}

# Test 5: Image availability
test_images() {
    print_section "Container Images"

    local common_images=(
        "ollama/ollama:latest"
        "jupyter/scipy-notebook:latest"
    )

    for image in "${common_images[@]}"; do
        if podman images --format "{{.Repository}}:{{.Tag}}" | grep -q "$image"; then
            run_test "Image $image available" "true"
        else
            skip_test "Image $image" "Not pulled yet"
        fi
    done
}

# Main test execution
main() {
    print_header

    local test_chapter="$1"

    # Always run prerequisite tests
    test_prerequisites
    test_environment

    # Run chapter-specific tests
    if [ -z "$test_chapter" ] || [ "$test_chapter" = "all" ]; then
        # Test all chapters
        test_chapter 0 "Introduction" \
            "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-00-introduction" \
            "ollama_ch00" "agentic_mcp_server_ch00" "agentic_streamlit_app_ch00" "agentic_jupyterlab_ch00"

        test_chapter 1 "Main Architecture" \
            "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-01-main" \
            "agentic_mcp_server" "agentic_streamlit_app"

        test_chapter 2 "HPC MCP Server" \
            "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot" \
            "agentic_mcp_server" "agentic_streamlit_app" "agentic_hpc_mcp_server"

        test_chapter 3 "Sandbox and Multi-Agent" \
            "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent" \
            "agentic_mcp_server" "agentic_streamlit_app" "agentic_hpc_mcp_server" "agentic_sandbox_mcp_server"
    else
        # Test specific chapter
        case "$test_chapter" in
            0)
                test_chapter 0 "Introduction" \
                    "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-00-introduction" \
                    "ollama_ch00" "agentic_mcp_server_ch00" "agentic_streamlit_app_ch00" "agentic_jupyterlab_ch00"
                ;;
            1)
                test_chapter 1 "Main Architecture" \
                    "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-01-main" \
                    "agentic_mcp_server" "agentic_streamlit_app"
                ;;
            2)
                test_chapter 2 "HPC MCP Server" \
                    "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot" \
                    "agentic_mcp_server" "agentic_streamlit_app" "agentic_hpc_mcp_server"
                ;;
            3)
                test_chapter 3 "Sandbox and Multi-Agent" \
                    "/data/workspace/adept-agentic-framework-core/docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent" \
                    "agentic_mcp_server" "agentic_streamlit_app" "agentic_hpc_mcp_server" "agentic_sandbox_mcp_server"
                ;;
            *)
                echo -e "${RED}Invalid chapter: $test_chapter${NC}"
                echo "Usage: $0 [0|1|2|3|all]"
                exit 1
                ;;
        esac
    fi

    # Additional system tests
    test_networking
    test_images

    # Print summary
    print_section "Test Summary"
    echo ""
    echo -e "Total Tests:   ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed:        ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed:        ${RED}$FAILED_TESTS${NC}"
    echo -e "Skipped:       ${YELLOW}$SKIPPED_TESTS${NC}"
    echo ""

    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${RED}  FAILED TESTS:${NC}"
        echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        for result in "${TEST_RESULTS[@]}"; do
            if [[ $result == FAIL:* ]]; then
                echo -e "  ${RED}✗${NC} ${result#FAIL: }"
            fi
        done
        echo ""
    fi

    echo -e "Full test log saved to: ${CYAN}$TEST_LOG${NC}"
    echo ""

    # Exit with appropriate code
    if [ $FAILED_TESTS -gt 0 ]; then
        echo -e "${RED}TEST SUITE FAILED${NC}"
        exit 1
    else
        echo -e "${GREEN}TEST SUITE PASSED${NC}"
        exit 0
    fi
}

# Show usage if -h or --help
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "ADEPT Podman Deployment Test Suite"
    echo ""
    echo "Usage: sudo $0 [chapter]"
    echo ""
    echo "Arguments:"
    echo "  0       Test Chapter 0 only"
    echo "  1       Test Chapter 1 only"
    echo "  2       Test Chapter 2 only"
    echo "  3       Test Chapter 3 only"
    echo "  all     Test all chapters (default)"
    echo ""
    echo "Examples:"
    echo "  sudo ./test-podman-deployment.sh        # Test all"
    echo "  sudo ./test-podman-deployment.sh 0      # Test Chapter 0"
    echo "  sudo ./test-podman-deployment.sh 1      # Test Chapter 1"
    exit 0
fi

# Run main
main "$1"
