#!/bin/bash
# Test internal LLM connection from inside Docker container

echo "============================================================"
echo "Testing Internal LLM Connection from Docker Container"
echo "============================================================"

# Check if container is running
if ! docker ps | grep -q agentic_streamlit_app_ch00; then
    echo "❌ Container agentic_streamlit_app_ch00 is not running"
    exit 1
fi

echo ""
echo "📋 Container Network Info:"
docker exec agentic_streamlit_app_ch00 hostname -i

echo ""
echo "📋 Environment Variables in Container:"
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY:0:8}..."'
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_BASE_URL=$INTERNAL_LLM_BASE_URL"'
docker exec agentic_streamlit_app_ch00 sh -c 'echo "INTERNAL_LLM_MODEL=$INTERNAL_LLM_MODEL"'

echo ""
echo "📋 Testing HTTP connection from container:"
docker exec agentic_streamlit_app_ch00 curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" \
  -H "Authorization: Bearer ${INTERNAL_LLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"o4-mini-project","messages":[{"role":"user","content":"test"}],"max_tokens":10}' \
  https://ai-incubator-api.pnnl.gov/chat/completions

echo ""
echo "============================================================"
