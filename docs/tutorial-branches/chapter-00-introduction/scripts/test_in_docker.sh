#!/bin/bash
# Debug script to test internal LLM from inside Docker container

echo "======================================================================="
echo "Docker Container Internal LLM Sanity Check"
echo "======================================================================="

# Check if container is running
if ! docker ps | grep -q agentic_streamlit_app_ch00; then
    echo "❌ Container agentic_streamlit_app_ch00 is not running"
    exit 1
fi

echo ""
echo "📋 Environment variables in container:"
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY:0:8}..."'
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_BASE_URL=$INTERNAL_LLM_BASE_URL"'
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_MODEL=$INTERNAL_LLM_MODEL"'
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_EMBEDDING_MODEL=$INTERNAL_LLM_EMBEDDING_MODEL"'

echo ""
echo "📋 Container network info:"
docker exec agentic_streamlit_app_ch00 hostname -i

echo ""
echo "======================================================================="
echo "Test 1: Simple Python OpenAI SDK test (inline)"
echo "======================================================================="

# Create and run a simple Python test inline
docker exec agentic_streamlit_app_ch00 python3 -c "
import os
import openai

api_key = os.getenv('INTERNAL_LLM_API_KEY')
base_url = os.getenv('INTERNAL_LLM_BASE_URL')
model = os.getenv('INTERNAL_LLM_MODEL')

print(f'API Key: {api_key[:8]}...{api_key[-4:]}' if api_key else 'No API key')
print(f'Base URL: {base_url}')
print(f'Model: {model}')

if not api_key:
    print('❌ INTERNAL_LLM_API_KEY not set in container')
    exit(1)

print('')
print('Initializing OpenAI client...')
client = openai.OpenAI(api_key=api_key, base_url=base_url)

print('Making chat completion request...')
try:
    response = client.chat.completions.create(
        model=model,
        messages=[{'role': 'user', 'content': 'Say hello'}],
        max_tokens=10
    )
    print('✅ SUCCESS!')
    print(f'Response: {response.choices[0].message.content}')
except openai.PermissionDeniedError as e:
    print(f'❌ 403 Permission Denied: {e}')
    print('This indicates IP whitelisting issue or invalid credentials')
    exit(1)
except Exception as e:
    print(f'❌ Error: {type(e).__name__}: {e}')
    exit(1)
"

DOCKER_TEST_EXIT=$?

echo ""
echo "======================================================================="
echo "Test 2: curl test to endpoint"
echo "======================================================================="

docker exec agentic_streamlit_app_ch00 sh -c '
API_KEY=$INTERNAL_LLM_API_KEY
BASE_URL=$INTERNAL_LLM_BASE_URL
MODEL=$INTERNAL_LLM_MODEL

echo "Testing: $BASE_URL/chat/completions"
echo ""

curl -s -w "\nHTTP Status: %{http_code}\n" \
  -X POST "$BASE_URL/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$MODEL\",
    \"messages\": [{\"role\": \"user\", \"content\": \"test\"}],
    \"max_tokens\": 10
  }"
'

echo ""
echo "======================================================================="
echo "SUMMARY"
echo "======================================================================="

if [ $DOCKER_TEST_EXIT -eq 0 ]; then
    echo "✅ Docker container can successfully connect to internal LLM"
    echo "   The issue is NOT an IP whitelisting problem"
else
    echo "❌ Docker container cannot connect to internal LLM"
    echo "   Possible causes:"
    echo "   1. Environment variables not properly loaded in container"
    echo "   2. IP whitelisting (Docker container IP blocked)"
    echo "   3. Network connectivity issue"
fi

exit $DOCKER_TEST_EXIT
