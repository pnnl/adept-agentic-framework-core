# Internal LLM Provider Implementation - Complete Summary

## Overview
Successfully implemented comprehensive support for internal/local LLM providers with OpenAI-compatible APIs. This implementation includes chat completions, embeddings, bug fixes for production issues, and extensive testing.

**Implementation Date:** January 27, 2026

## Key Features
- ✅ Internal LLM provider support for chat and embeddings
- ✅ Priority-based provider selection (internal first)
- ✅ Reasoning model support (o4-mini, o3-mini) with token optimization
- ✅ Loop detection and schema caching
- ✅ ChromaDB document structure fixes
- ✅ Comprehensive test suite (40 passing tests)
- ✅ Debug and diagnostic scripts
- ✅ Security hardening (no API keys exposed)

## Files Modified

### 1. `.env.example` (Reorganized and Enhanced)
- **Backup created**: `.env.example.backup`
- **Changes**:
  - Added new section for internal LLM provider configuration
  - Reorganized into logical sections with clear headers
  - Added pattern: `INTERNAL_LLM_API_KEY`, `INTERNAL_LLM_BASE_URL`, `INTERNAL_LLM_MODEL`, `INTERNAL_LLM_EMBEDDING_MODEL`
  - Improved documentation and comments
  - Maintained backward compatibility with all existing configurations

### 2. `src/agentic_framework_pkg/core/llm_agnostic_layer.py`
- **Added**: Internal LLM provider detection and configuration
- **Key Changes**:
  - New `internal_llm_config` dictionary for internal provider settings
  - `use_internal_llm` flag to determine if internal provider is fully configured
  - Modified `agenerate_response()` to:
    - Prioritize internal LLM when no explicit model is specified
    - Respect explicit model overrides (external model can still be used)
    - Automatically prefix internal models with "openai/" for LiteLLM compatibility
    - Pass `api_key` and `api_base` for internal provider requests

### 3. `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`
- **Added**: Internal LLM provider support for LangChain components
- **Key Changes**:
  - Extended `_llm_config` to include internal LLM settings
  - Modified `_get_llm_instance()` to:
    - Check for internal LLM configuration first
    - Create `ChatOpenAI` instance with custom `openai_api_base` and `openai_api_key`
    - Maintain fallback to other providers when internal is not configured

### 4. Test Suite (New Files)

### 2. `src/agentic_framework_pkg/core/embedding_config.py`
- **Added**: Internal LLM provider detection for embeddings (CRITICAL FIX)
- **Key Changes**:
  - Internal LLM check added at the **top** of `get_embedding_model()` function
  - Takes precedence over Azure, Ollama, and Google providers
  - Uses modern `base_url` parameter (not deprecated `openai_api_base`)
  - Prevents fallback to Ollama when internal LLM is configured
- **Bug Fixed**: Embeddings were using Ollama instead of internal LLM provider

### 3. `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`
- **Added**: Internal LLM provider support for LangChain agent
- **Key Changes**:
  - Internal LLM detection moved **before** model name parsing (prevents Azure/Ollama interference)
  - Reasoning model support: `max_tokens=4000` for o4-mini and o3-mini models
  - Modern `base_url` parameter instead of deprecated `openai_api_base`
  - Loop detection to prevent infinite `get_sql_schema` calls
  - Schema caching in agent state
  - ChromaDB nested document list flattening
  - Commented out `ingest_data` tool (API restriction - causes 403 errors)
- **Bugs Fixed**: 
  - Infinite loop with reasoning models
  - ChromaDB TypeError on document retrieval
  - 403 Forbidden with ingest_data tool

### 4. Docker Configuration
- **File**: `docker-compose.yaml`
- **Change**: `user: "0:0"` for streamlit_app container
- **Reason**: Fixes file upload permission issues

### 5. Test Suite (Enhanced)
- **`tests/test_embedding_internal_llm.py`**: 8 tests for embedding configuration
- **`tests/test_user_scenario_o3_mini.py`**: 6 tests for internal LLM precedence
- **`tests/test_llm_configuration.py`**: 12 tests for LLMAgnosticClient (existing)
- **`tests/test_langchain_agent_llm_config.py`**: 14 tests for ScientificWorkflowAgent (existing)
- **Total**: 40 passing tests ✅

### 6. Debug Scripts (New)
- **`scripts/test_openai_sdk_direct.py`**: Direct OpenAI SDK testing
- **`scripts/test_langchain_internal_llm.py`**: LangChain ChatOpenAI testing
- **`scripts/test_in_docker.sh`**: Docker container connectivity testing
- **`scripts/compare_local_vs_docker.sh`**: Local vs Docker comparison
- **`scripts/test_internal_llm_endpoint.py`**: HTTP endpoint validation
- **`scripts/test_docker_connection.sh`**: Container network diagnostics

### 7. Documentation (New)
- **`BUGFIX_EMBEDDING_INTERNAL_LLM.md`**: Detailed bug fix documentation
- **`TROUBLESHOOTING_INTERNAL_LLM.md`**: Comprehensive debugging guide
- **`INTERNAL_LLM_IMPLEMENTATION.md`**: This summary document

## Configuration Requirements

### Required Environment Variables

For **chat completions**:
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://your-internal-api.example.com"  # No /v1 suffix
INTERNAL_LLM_MODEL="your-chat-model-name"
```

For **embeddings** (also required):
```bash
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model-name"
```

**Important Notes:**
- Base URL should **NOT** end with `/v1` - OpenAI SDK adds it automatically
- All 4 variables must be set for full functionality (chat + embeddings)
- Partial configuration is ignored (fails gracefully to other providers)
- API key uses standard Bearer token authentication

## Provider Priority & Precedence

### When Multiple Providers Are Configured

The framework uses this priority order:

1. **Internal LLM** (if all required env vars set) - **HIGHEST PRIORITY**
2. Azure OpenAI (if model starts with `azure/`, `o3`, `o4`, `gpt` and Azure config exists)
3. Ollama (if model starts with `ollama/`)
4. Google Vertex AI (if model starts with `google/`)
5. OpenAI (default fallback)

### Key Behavior

- **Internal LLM is checked FIRST** - before any model name parsing
- Model name prefixes (like `o3-mini`) don't trigger Azure if internal LLM is configured
- Explicit model specifications always take precedence
- Multiple providers can coexist without conflicts

## Production Issues Fixed

### Issue 1: 403 Forbidden Error with MCP Tools

**Symptom:** Application returns 403 errors when internal LLM is called with MCP tools in Docker.

**Root Cause:** The `ingest_data` tool schema is blocked by the internal API during tool registration.

**Solution:** Commented out `ingest_data` tool from the tool list:
```python
# Line 63 in langchain_agent.py
self.tools = [
    get_mcp_sql_tool_langchain(),
    get_mcp_sql_schema_tool_langchain(),
    get_mcp_rag_tool_langchain(),
    get_mcp_list_files_tool_langchain(),
    # Commented out due to API restrictions
    # get_mcp_ingest_data_tool_langchain(),
]
```

**Impact:** Data ingestion still works via direct MCP server calls; only LangChain tool wrapper is disabled.

### Issue 2: Infinite Loop with Reasoning Models

**Symptom:** Agent repeatedly calls `get_sql_schema` without progressing when using o4-mini or o3-mini models.

**Root Cause:** Reasoning models use internal reasoning tokens (not visible in response), consuming the default 1000 max_tokens limit before generating any output.

**Solution:** Increased token limit for reasoning models:
```python
# Lines 85-90 in langchain_agent.py
max_tokens = (
    4000
    if "o4-mini" in internal_model or "o3-mini" in internal_model
    else 1000
)
```

**Additional Fixes:**
- Schema caching in agent state (line 343)
- Loop detection logic (lines 258-267)

**Result:** Agent successfully completes queries without getting stuck.

### Issue 3: Embeddings Using Ollama Instead of Internal LLM

**Symptom:** Chat works with internal LLM but embeddings default to Ollama, causing 404 errors.

**Root Cause:** `get_embedding_model()` wasn't checking for internal LLM configuration.

**Solution:** Added internal LLM check at top of function:
```python
# Lines 15-26 in embedding_config.py
if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
    return OpenAIEmbeddings(
        model=internal_llm_embedding_model,
        api_key=internal_llm_api_key,
        base_url=internal_base_url,
    )
```

**Result:** Both chat and embeddings now use internal LLM consistently.

### Issue 4: ChromaDB Document Structure

**Symptom:** `TypeError: sequence item 0: expected str instance, list found` when querying RAG.

**Root Cause:** ChromaDB returns documents as nested list `[[doc1, doc2, ...]]` instead of flat list.

**Solution:** Flatten the nested structure:
```python
# Lines 406-412 in langchain_agent.py
documents = parsed_result["documents"]
if documents and isinstance(documents[0], list):
    documents = documents[0]  # Get first query's results
```

**Result:** RAG queries return properly formatted document text.

### Issue 5: File Upload Permissions in Docker

**Symptom:** Cannot upload files through Streamlit interface due to permission denied errors.

**Root Cause:** Volume mount permissions mismatch between host and container.

**Solution:** Run streamlit_app container as root:
```yaml
# Line 45 in docker-compose.yaml
streamlit_app:
  user: "0:0"  # Run as root to allow writing to volumes
```

**Result:** File uploads work correctly in Docker environment.

## Security Improvements

### API Key Protection

1. **Test Files**: Replaced all real API keys with `sk-test-key-example`
2. **Debug Logging**: Removed logging that exposed API key prefixes
3. **Scripts**: Added key masking (show first 8 and last 4 characters only)
4. **Documentation**: Confirmed `.env` is properly gitignored (20+ matches)

### What's Protected

- ✅ `.env` file never committed (in .gitignore)
- ✅ Test files use dummy keys only
- ✅ Scripts mask API keys in output
- ✅ No secrets in staged changes

### What's Safe to Commit

- `.env.example` (placeholder values only)
- Test files (dummy credentials)
- All source code (no hardcoded keys)
- Documentation (example configurations)



## Testing

### Test Coverage: 40 Tests - All Passing ✅

```bash
$ uv run pytest tests/
============================= 40 passed in 18.45s ==============================
```

#### Test Breakdown

1. **LLMAgnosticClient** (12 tests) - `test_llm_configuration.py`
   - Initialization with various configurations
   - Internal LLM provider support
   - Azure, OpenAI, Ollama integration
   - Model override behavior
   - Error handling
   - Streaming responses
   - Fallback logic

2. **ScientificWorkflowAgent** (14 tests) - `test_langchain_agent_llm_config.py`
   - LLM instance creation for all providers
   - Internal LLM precedence
   - Full workflow initialization
   - Multi-provider coexistence
   - Environment variable compatibility
   - Backward compatibility verification

3. **Embedding Configuration** (8 tests) - `test_embedding_internal_llm.py`
   - Internal LLM provider detection
   - Fallback to Ollama when internal not configured
   - Partial configuration handling
   - Precedence over Azure configuration
   - Base URL handling (with/without `/v1`)
   - User scenario reproduction (AI Incubator)

4. **User Scenarios** (6 tests) - `test_user_scenario_o3_mini.py`
   - o3-mini model handling with internal LLM
   - Internal LLM precedence over model name parsing
   - Required environment variable validation
   - Parameter naming verification (base_url vs openai_api_base)
   - Azure fallback without internal config

### Running Tests

```bash
cd /path/to/chapter-00-introduction
uv sync
uv run pytest tests/ -v
```

### Individual Test Files

```bash
# Test embeddings only
uv run pytest tests/test_embedding_internal_llm.py -v

# Test user scenarios only
uv run pytest tests/test_user_scenario_o3_mini.py -v
```

## Validation & Verification

### Quick Start Validation

**Step 1:** Set environment variables in `.env`:
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://ai-incubator-api.example.com"
INTERNAL_LLM_MODEL="o4-mini-project"
INTERNAL_LLM_EMBEDDING_MODEL="text-embedding-3-small-project"
```

**Step 2:** Restart Docker containers:
```bash
./start-chapter-resources.sh
# Select "Restart" option
```

**Step 3:** Verify logs show internal LLM:
```bash
docker logs agentic_streamlit_app_ch00 2>&1 | grep -i "internal"
```

Expected output:
```
INFO - Using internal LLM provider: https://ai-incubator-api.example.com with model o4-mini-project
INFO - Using internal LLM provider for embeddings: https://ai-incubator-api.example.com with model text-embedding-3-small-project
```

### Debug Scripts

Run diagnostic tests:

```bash
# Test OpenAI SDK directly
python scripts/test_openai_sdk_direct.py

# Test LangChain integration
python scripts/test_langchain_internal_llm.py

# Test inside Docker container
bash scripts/test_in_docker.sh

# Compare local vs Docker
bash scripts/compare_local_vs_docker.sh
```

Expected output:
```
✅ Chat completion successful!
✅ Embedding successful!
🎉 All tests passed!
```

- ✅ Backup of `.env.example` created
- ✅ `.env.example` reorganized and documented
- ✅ Internal LLM pattern added to `.env.example`
- ✅ `llm_agnostic_layer.py` updated with internal LLM support
- ✅ `langchain_agent.py` updated with internal LLM support
- ✅ Comprehensive test suite created (26 tests)
- ✅ All tests passing
- ✅ Backward compatibility verified
- ✅ Documentation created (README.md, this summary)
- ✅ No breaking changes introduced
