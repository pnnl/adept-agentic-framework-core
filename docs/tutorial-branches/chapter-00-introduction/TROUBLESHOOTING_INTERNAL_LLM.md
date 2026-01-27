# Troubleshooting Internal LLM Configuration

## Issue: 403 Forbidden Error

### Symptoms
```
openai.PermissionDeniedError: <html>
<head><title>403 Forbidden</title></head>
<body>
<center><h1>403 Forbidden</h1></center>
<hr><center>Microsoft-Azure-Application-Gateway/v2</center>
</body>
</html>
```

### Root Causes & Solutions

#### 1. Missing `/v1` suffix in base URL
**Problem**: OpenAI-compatible APIs expect the base URL to end with `/v1`

**Check your .env:**
```bash
# ❌ WRONG
INTERNAL_LLM_BASE_URL="https://ai-incubator-api.pnnl.gov"

# ✅ CORRECT
INTERNAL_LLM_BASE_URL="https://ai-incubator-api.pnnl.gov/v1"
```

**Fix**: Add `/v1` to the end of your `INTERNAL_LLM_BASE_URL`

#### 2. Incorrect API Key Format
**Problem**: API key may need specific prefix or format

**Check:**
- Does your API key start with the expected prefix (e.g., `sk-`)?
- Is the key properly copied without extra spaces or newlines?
- Has the key been regenerated and you're using an old one?

#### 3. Missing Authentication Headers
**Problem**: The endpoint may require additional headers beyond the API key

**Check if your internal LLM requires:**
- Custom authentication headers
- OAuth tokens instead of API keys
- Specific user-agent strings

#### 4. Network/Proxy Issues
**Problem**: Request is being blocked by firewall or proxy

**Check:**
- Can you access the URL from the Docker container?
  ```bash
  docker exec -it agentic_streamlit_app_ch00 curl https://ai-incubator-api.pnnl.gov/v1/models
  ```
- Is there a corporate proxy that needs configuration?
- Are there IP whitelisting requirements?

## Issue: Embeddings Using Ollama Instead of Internal LLM

### Symptoms
```
ResponseError: model "nomic-embed-text" not found, try pulling it first (status code: 404)
ollama_ch00 | [GIN] 2026/01/27 - 05:32:03 | 404 |   15.377167ms |      172.18.0.4 | POST     "/api/embed"
```

### Root Cause
The embedding configuration wasn't checking for internal LLM provider settings.

### Solution (Already Fixed)
Updated `embedding_config.py` to check for internal LLM configuration first:
```python
# Check for internal LLM provider first
internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
    return OpenAIEmbeddings(
        model=internal_llm_embedding_model,
        openai_api_key=internal_llm_api_key,
        openai_api_base=internal_llm_base_url
    )
```

### Verification
Run the test to confirm embeddings use internal LLM:
```bash
cd /path/to/chapter-00-introduction
uv run pytest tests/test_embedding_internal_llm.py::TestInternalLLMEmbeddingIntegration::test_user_scenario_ai_incubator -v
```

Expected: `PASSED` ✅

## Required Environment Variables

For **both chat and embeddings** to use your internal LLM, you must set:

```bash
# Required for chat/completion
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://your-endpoint.com/v1"  # Must end with /v1
INTERNAL_LLM_MODEL="your-chat-model-name"

# Required for embeddings
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model-name"
```

## Debugging Steps

### 1. Check Environment Variables Are Loaded
```bash
docker exec -it agentic_streamlit_app_ch00 env | grep INTERNAL_LLM
```

Expected output:
```
INTERNAL_LLM_API_KEY=sk-...
INTERNAL_LLM_BASE_URL=https://ai-incubator-api.pnnl.gov/v1
INTERNAL_LLM_MODEL=o4-mini-birthright
INTERNAL_LLM_EMBEDDING_MODEL=text-embedding-3-small-project
```

### 2. Check Logs for Internal LLM Detection
```bash
docker logs agentic_streamlit_app_ch00 2>&1 | grep -i "internal"
```

Expected logs:
```
INFO - Using internal LLM provider: https://ai-incubator-api.pnnl.gov/v1 with model o4-mini-birthright
INFO - Using internal LLM provider for embeddings: https://ai-incubator-api.pnnl.gov/v1 with model text-embedding-3-small-project
```

❌ **If you see Ollama logs instead:**
```
ResponseError: model "nomic-embed-text" not found
```
→ Your internal LLM config is incomplete or not being loaded

### 3. Test API Endpoint Manually
```bash
curl -X POST "https://ai-incubator-api.pnnl.gov/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "o4-mini-birthright",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

Expected: JSON response with chat completion
If 403: Check API key, authentication method, or whitelist requirements

### 4. Test Embedding Endpoint
```bash
curl -X POST "https://ai-incubator-api.pnnl.gov/v1/embeddings" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "text-embedding-3-small-project",
    "input": "test"
  }'
```

Expected: JSON response with embedding vector
If 403/404: Model name may be incorrect or not available

### 5. Verify Docker Compose Restart
After changing `.env`:
```bash
./start-chapter-resources.sh
# Select "Restart" or "Down then Up"
```

OR:
```bash
docker compose down
docker compose up --build -d
```

## Common Mistakes

### ❌ Wrong Model Names
```bash
# If you get "model not found" errors, verify exact model names
INTERNAL_LLM_MODEL="o4-mini"  # ❌ Wrong
INTERNAL_LLM_MODEL="o4-mini-birthright"  # ✅ Correct
```

### ❌ Missing Quotes in .env
```bash
# .env files don't need quotes for simple values, but include them for complex ones
INTERNAL_LLM_API_KEY=sk-your-api-key-here  # ✅ OK
INTERNAL_LLM_API_KEY="sk-your-api-key-here"  # ✅ Also OK
```

### ❌ Using Model Prefixes
```bash
# Don't add provider prefixes to internal models
INTERNAL_LLM_MODEL="openai/o4-mini-birthright"  # ❌ Wrong
INTERNAL_LLM_MODEL="o4-mini-birthright"  # ✅ Correct
```

## Validation Checklist

- [ ] `INTERNAL_LLM_BASE_URL` ends with `/v1`
- [ ] All 4 internal LLM env vars are set (API_KEY, BASE_URL, MODEL, EMBEDDING_MODEL)
- [ ] No trailing spaces or newlines in env var values
- [ ] API key is valid and not expired
- [ ] Model names match exactly what the API expects
- [ ] Docker containers restarted after .env changes
- [ ] Logs show "Using internal LLM provider" messages
- [ ] No Ollama errors in logs
- [ ] Test suite passes: `uv run pytest tests/test_embedding_internal_llm.py -v`

## Getting Help

If issues persist:
1. Run full test suite: `uv run pytest tests/ -v`
2. Check logs: `docker logs agentic_streamlit_app_ch00 2>&1 | less`
3. Verify API access: Use curl to test endpoints directly
4. Review [INTERNAL_LLM_QUICKSTART.md](INTERNAL_LLM_QUICKSTART.md)
