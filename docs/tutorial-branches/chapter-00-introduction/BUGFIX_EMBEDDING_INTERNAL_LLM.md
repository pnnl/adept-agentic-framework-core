# Bug Fix: Embeddings Using Ollama Instead of Internal LLM

## Issue Summary

When running Streamlit with internal LLM configuration, the system was:
- ✅ **Correctly using internal LLM for chat/completions**
- ❌ **Incorrectly using Ollama for embeddings** (causing 404 errors)

Additionally, there was a 403 Forbidden error on the internal LLM endpoint.

## Root Causes

### 1. Embedding Configuration Not Checking for Internal LLM
**File**: `src/agentic_framework_pkg/core/embedding_config.py`

The `get_embedding_model()` function was checking for Azure, Ollama, and Google configurations, but **not for internal LLM provider settings**.

Result: Even with `INTERNAL_LLM_EMBEDDING_MODEL` set, the system fell back to Ollama.

### 2. Missing `/v1` Suffix in Base URL
**File**: `.env`

OpenAI-compatible APIs expect the base URL to include the `/v1` path:
- ❌ Wrong: `https://ai-incubator-api.pnnl.gov`
- ✅ Correct: `https://ai-incubator-api.pnnl.gov/v1`

## Solution

### 1. Updated `embedding_config.py`
Added internal LLM provider detection at the **top of the function** (before other checks):

```python
def get_embedding_model() -> Embeddings:
    """Returns the llm instance to be used for embedding."""
    
    # Check for internal LLM provider first
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")
    
    if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
        logger.info(f"Using internal LLM provider for embeddings: {internal_llm_base_url} with model {internal_llm_embedding_model}")
        return OpenAIEmbeddings(
            model=internal_llm_embedding_model,
            openai_api_key=internal_llm_api_key,
            openai_api_base=internal_llm_base_url
        )
    
    # ... rest of existing logic for Azure, Ollama, etc.
```

### 2. Created Comprehensive Test Suite
**New File**: `tests/test_embedding_internal_llm.py`

Added 8 tests specifically for embedding configuration:
- ✅ Internal LLM provider detection
- ✅ Fallback to Ollama when internal not configured
- ✅ Partial configuration handling
- ✅ Precedence over Azure configuration
- ✅ Base URL with/without `/v1` suffix
- ✅ User scenario reproduction (AI Incubator)
- ✅ Error cases and edge conditions

### 3. Created Troubleshooting Guide
**New File**: `TROUBLESHOOTING_INTERNAL_LLM.md`

Comprehensive guide covering:
- 403 Forbidden error debugging
- Base URL configuration
- Environment variable verification
- Manual API endpoint testing
- Common mistakes and fixes

## Files Modified

| File                              | Change                       | Lines |
| --------------------------------- | ---------------------------- | ----- |
| `embedding_config.py`             | Added internal LLM detection | +13   |
| `test_embedding_internal_llm.py`  | NEW: 8 comprehensive tests   | +162  |
| `TROUBLESHOOTING_INTERNAL_LLM.md` | NEW: Debugging guide         | +235  |

## Test Results

### Before Fix
```
❌ Embeddings using Ollama (404 error)
❌ ResponseError: model "nomic-embed-text" not found
```

### After Fix
```bash
$ uv run pytest tests/ -v
============================= 34 passed in 15.69s ==============================
```

**Test Coverage:**
- 12 tests: LLMAgnosticClient (chat completions)
- 14 tests: ScientificWorkflowAgent (LangChain integration)
- **8 tests: Embedding configuration (NEW)** ✨

## Verification Steps

### 1. Check Environment Variables
Ensure your `.env` has:
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://ai-incubator-api.pnnl.gov/v1"  # Must end with /v1
INTERNAL_LLM_MODEL="o4-mini-birthright"
INTERNAL_LLM_EMBEDDING_MODEL="text-embedding-3-small-project"
```

### 2. Run Tests
```bash
cd /path/to/chapter-00-introduction
uv run pytest tests/test_embedding_internal_llm.py -v
```
Expected: **8 passed** ✅

### 3. Restart Docker Compose
```bash
./start-chapter-resources.sh
# Select "Restart" option
```

### 4. Check Logs
```bash
docker logs agentic_streamlit_app_ch00 2>&1 | grep -i "internal"
```
Expected logs:
```
INFO - Using internal LLM provider: https://ai-incubator-api.pnnl.gov/v1 with model o4-mini-birthright
INFO - Using internal LLM provider for embeddings: https://ai-incubator-api.pnnl.gov/v1 with model text-embedding-3-small-project
```

❌ Should **NOT** see:
```
ResponseError: model "nomic-embed-text" not found
ollama_ch00 | [GIN] ... | 404 | ... | POST "/api/embed"
```

## Resolving the 403 Forbidden Error

The 403 error indicates authentication or access issues with your internal LLM endpoint. Common causes:

### 1. Base URL Missing `/v1`
**Fix**: Update your `.env`:
```bash
INTERNAL_LLM_BASE_URL="https://ai-incubator-api.pnnl.gov/v1"
```

### 2. Invalid API Key
**Verify**:
```bash
curl -X POST "https://ai-incubator-api.pnnl.gov/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "o4-mini-birthright", "messages": [{"role": "user", "content": "test"}]}'
```

Expected: JSON response (not HTML 403 error)

### 3. IP Whitelisting
**Check**: Does the internal LLM require requests from specific IP ranges?

**Test from Docker container**:
```bash
docker exec -it agentic_streamlit_app_ch00 curl https://ai-incubator-api.pnnl.gov/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 4. Azure Application Gateway Restrictions
The error shows `Microsoft-Azure-Application-Gateway/v2`, indicating the endpoint is behind Azure's gateway. This may require:
- Specific authentication headers
- OAuth tokens instead of API keys
- Request format adjustments

**Contact your internal LLM provider** to verify the correct authentication method.

## Benefits of This Fix

1. **Consistent Provider Usage**: Chat and embeddings now both use the internal LLM when configured
2. **No Ollama Dependency**: System works without requiring Ollama for embeddings
3. **Priority Order**: Internal LLM > Azure > Ollama (logical precedence)
4. **Well-Tested**: 8 new tests ensure embedding configuration works correctly
5. **Better Debugging**: Comprehensive troubleshooting guide and clear log messages

## Next Steps

If you're still getting the 403 error:
1. Verify the `/v1` suffix in your base URL
2. Test the API endpoint with curl (see troubleshooting guide)
3. Contact your internal LLM provider for authentication requirements
4. Check if the endpoint requires OAuth instead of API keys
5. Review [TROUBLESHOOTING_INTERNAL_LLM.md](TROUBLESHOOTING_INTERNAL_LLM.md) for detailed debugging steps

## Related Documentation

- [INTERNAL_LLM_IMPLEMENTATION.md](INTERNAL_LLM_IMPLEMENTATION.md) - Original implementation
- [INTERNAL_LLM_QUICKSTART.md](INTERNAL_LLM_QUICKSTART.md) - Quick reference
- [TROUBLESHOOTING_INTERNAL_LLM.md](TROUBLESHOOTING_INTERNAL_LLM.md) - Debugging guide
- [tests/README.md](tests/README.md) - Test documentation
