# Internal LLM Provider - Quick Reference

## Configuration (Add to .env)

```bash
# Required: All three must be set for internal LLM to activate
INTERNAL_LLM_API_KEY="your-internal-api-key"
INTERNAL_LLM_BASE_URL="https://your-internal-llm.example.com/v1"
INTERNAL_LLM_MODEL="your-model-name"

# Optional: For embedding operations
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"
```

## When Internal LLM is Used

✅ **Used automatically when:**
- All 3 required env vars are set
- No explicit model is specified in code
- Purpose-specific model env var (e.g., `STREAMLIT_DEFAULT_MODEL`) is not set

❌ **NOT used when:**
- Any required env var is missing
- Explicit model is specified in code: `agenerate_response(messages, "generic", model="gpt-4")`
- Purpose-specific model is set and internal model doesn't match

## Testing Your Configuration

### Test 1: Verify Internal LLM is Detected
```bash
cd /path/to/chapter-00-introduction
uv run pytest tests/test_llm_configuration.py::TestLLMAgnosticClient::test_initialization_with_internal_llm_provider -v
```

### Test 2: Verify Internal LLM is Used
```bash
uv run pytest tests/test_llm_configuration.py::TestLLMAgnosticClient::test_agenerate_response_with_internal_llm -v
```

### Test 3: Run All Tests
```bash
uv run pytest tests/ -v
```
Expected: `26 passed`

## Troubleshooting

### Issue: Internal LLM not being used
**Check:**
1. All 3 required env vars are set: `INTERNAL_LLM_API_KEY`, `INTERNAL_LLM_BASE_URL`, `INTERNAL_LLM_MODEL`
2. Values don't contain quotes inside the value (only around it)
3. Base URL ends with `/v1` (OpenAI-compatible format)
4. No explicit model override in your code

**Debug:**
Look for log messages:
- ✅ Good: `Internal LLM provider configured: https://...`
- ✅ Good: `Using internal LLM model: your-model-name`
- ✅ Good: `Internal LLM request - model: openai/your-model-name, base_url: https://...`

### Issue: Tests failing
**Common causes:**
1. Missing `langchain-ollama` package
   - **Fix:** `uv sync --extra dev`
2. Import errors
   - **Fix:** Ensure you're in the chapter directory when running tests
3. Environment variable conflicts
   - **Fix:** Tests use isolated environments, but check for system-wide env vars

## Migration Guide

### From Azure OpenAI
**Before:**
```bash
AZURE_API_KEY="xyz"
AZURE_API_BASE="https://your-resource.openai.azure.com/"
AZURE_API_VERSION="2023-05-15"
DEFAULT_LLM_MODEL="gpt-4"
```

**After (using internal):**
```bash
# Keep Azure config for specific use cases
AZURE_API_KEY="xyz"
AZURE_API_BASE="https://your-resource.openai.azure.com/"
AZURE_API_VERSION="2023-05-15"

# Add internal LLM as default
INTERNAL_LLM_API_KEY="internal-key"
INTERNAL_LLM_BASE_URL="https://internal.company.com/v1"
INTERNAL_LLM_MODEL="company-model"
DEFAULT_LLM_MODEL="company-model"
```

### From Ollama
**Before:**
```bash
OLLAMA_API_BASE="http://localhost:11434"
DEFAULT_LLM_MODEL="ollama/mistral"
```

**After (using internal):**
```bash
# Keep Ollama for local dev
OLLAMA_API_BASE="http://localhost:11434"

# Add internal LLM for production
INTERNAL_LLM_API_KEY="internal-key"
INTERNAL_LLM_BASE_URL="https://internal.company.com/v1"
INTERNAL_LLM_MODEL="company-model"
DEFAULT_LLM_MODEL="company-model"
```

## Files Changed Summary

| File                                       | Change                                   | Impact                    |
| ------------------------------------------ | ---------------------------------------- | ------------------------- |
| `.env.example`                             | Reorganized + added internal LLM section | Configuration             |
| `llm_agnostic_layer.py`                    | Added internal LLM detection & usage     | LiteLLM integration       |
| `langchain_agent.py`                       | Added internal LLM support               | LangChain integration     |
| `tests/test_llm_configuration.py`          | NEW: 12 tests                            | Validates LiteLLM layer   |
| `tests/test_langchain_agent_llm_config.py` | NEW: 14 tests                            | Validates LangChain layer |
| `tests/conftest.py`                        | NEW: Path configuration                  | Test infrastructure       |
| `tests/README.md`                          | NEW: Testing documentation               | Developer guide           |

## API Compatibility

Your internal LLM endpoint must support OpenAI-compatible format:

**POST** `{BASE_URL}/chat/completions`

**Request:**
```json
{
  "model": "your-model-name",
  "messages": [
    {"role": "user", "content": "Hello"}
  ]
}
```

**Headers:**
```
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

**Response:** Standard OpenAI format with `choices[].message.content`

## Getting Help

1. **Check logs:** Set `LOGGING_LEVEL="DEBUG"` in .env
2. **Run tests:** Verify your setup with `uv run pytest tests/ -v`
3. **Review:** [INTERNAL_LLM_IMPLEMENTATION.md](INTERNAL_LLM_IMPLEMENTATION.md)
4. **Validate:** [tests/README.md](tests/README.md)
