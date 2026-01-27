#!/bin/bash
# Run the OpenAI SDK test both locally and in Docker to compare results

echo "======================================================================="
echo "INTERNAL LLM SANITY CHECK - Local vs Docker Comparison"
echo "======================================================================="

# Test 1: Local execution
echo ""
echo "🏠 TEST 1: Running locally (host machine)..."
echo "-----------------------------------------------------------------------"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CHAPTER_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$CHAPTER_DIR"
python3 scripts/test_openai_sdk_direct.py
LOCAL_EXIT_CODE=$?

echo ""
echo ""
echo "======================================================================="
echo ""

# Test 2: Docker execution
echo "🐳 TEST 2: Running inside Docker container..."
echo "-----------------------------------------------------------------------"

# Check if container is running
if ! docker ps | grep -q agentic_streamlit_app_ch00; then
    echo "⚠️  Container agentic_streamlit_app_ch00 is not running"
    echo "   Starting containers..."
    bash start-chapter-resources.sh &
    DOCKER_PID=$!
    sleep 15  # Give containers time to start
fi

# Run test inside Docker
docker exec agentic_streamlit_app_ch00 python /app/scripts/test_openai_sdk_direct.py
DOCKER_EXIT_CODE=$?

echo ""
echo ""
echo "======================================================================="
echo "COMPARISON SUMMARY"
echo "======================================================================="
echo "Local Test:  $([ $LOCAL_EXIT_CODE -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') (exit code: $LOCAL_EXIT_CODE)"
echo "Docker Test: $([ $DOCKER_EXIT_CODE -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL') (exit code: $DOCKER_EXIT_CODE)"
echo "======================================================================="

if [ $LOCAL_EXIT_CODE -eq 0 ] && [ $DOCKER_EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS: Both environments work correctly!"
    exit 0
elif [ $LOCAL_EXIT_CODE -eq 0 ] && [ $DOCKER_EXIT_CODE -ne 0 ]; then
    echo "⚠️  DIAGNOSIS: Local works but Docker fails"
    echo "   → This indicates an IP whitelisting / network issue"
    echo "   → Docker containers have different IPs than your host machine"
    echo "   → Contact internal API admins to whitelist Docker network IPs"
    exit 1
else
    echo "❌ FAILURE: Check configuration and credentials"
    exit 1
fi
