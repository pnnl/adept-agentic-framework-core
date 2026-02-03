# Internal LLM Implementation Plan - Chapter 03

**Date:** February 3, 2026  
**Status:** 📋 Planning Phase - Awaiting Approval  
**Target Chapter:** chapter-03-llm-sandbox-and-multi-agent

---

## Executive Summary

This document outlines the plan to implement internal/local LLM provider support for Chapter 03, following the proven patterns established in Chapter 00 and Chapter 01. Chapter 03 introduces additional complexity with **multi-agent orchestration**, **sandbox code execution**, and **multiple MCP servers**, requiring careful consideration of LLM configuration across all components.

### Key Differences from Chapter 01
- **3 MCP Servers**: Main, HPC, and Sandbox servers (vs. 1 in Chapter 01)
- **Multi-Agent System**: Planner, Supervisor, and Worker agents all need LLM configuration
- **No `embedding_config.py`**: Embeddings are handled directly in `csv_rag_tool.py` via `LLMAgnosticClient`
- **More Complex Tool Ecosystem**: 30+ tools across multiple servers

---

## 1. Current State Analysis

### 1.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit App                             │
│                  (Uses ScientificWorkflowAgent)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
        ┌───────▼───────┐       ┌────────▼────────┐
        │  Main MCP     │       │  HPC MCP        │
        │  Server       │       │  Server         │
        │  (Port 8080)  │       │  (Port 8081)    │
        └───────┬───────┘       └─────────────────┘
                │
        ┌───────▼───────┐
        │  Sandbox MCP  │
        │  Server       │
        │  (Port 8082)  │
        └───────────────┘
```

### 1.2 Files Requiring Changes

Based on Chapter 00/01 patterns, the following files need modification:

#### Configuration Files
- ✅ **MISSING**: `.env.example` (needs to be created from Chapter 01 template)
- ✅ **EXISTS**: `docker-compose.yaml` (needs internal LLM env vars)
- ✅ **EXISTS**: `docker-compose-hpc.yaml` (optional, if HPC uses LLMs)

#### Core Python Files
- ✅ **EXISTS**: `src/agentic_framework_pkg/core/llm_agnostic_layer.py`
  - Already has LiteLLM integration
  - **Needs**: Internal LLM detection logic (lines 150-200)
  
- ❌ **MISSING**: `src/agentic_framework_pkg/core/embedding_config.py`
  - Chapter 03 doesn't have this file
  - Embeddings are handled in `csv_rag_tool.py` directly
  - **Action**: Verify `LLMAgnosticClient.acreate_embedding()` supports internal LLM

- ✅ **EXISTS**: `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`
  - **Needs**: Internal LLM initialization in `__init__()` (before line 70)

#### Multi-Agent Files (NEW in Chapter 03)
- ✅ **EXISTS**: `src/agentic_framework_pkg/mcp_server/tools/multi_agent_tool.py`
  - Creates Planner, Supervisor, and Worker agents
  - **Needs**: Internal LLM support in:
    - `create_planner_agent()` (line 143)
    - `create_worker_agent()` (line 62)
    - All calls to `_llm_agnostic_client_instance.get_langchain_chat_model()`

#### Tool Files
- ✅ **EXISTS**: `src/agentic_framework_pkg/mcp_server/tools/csv_rag_tool.py`
  - Uses `LLMAgnosticClient` for embeddings (line 32)
  - **Verify**: Embedding calls respect internal LLM configuration

### 1.3 Embedding Architecture Analysis

**Key Finding:** Chapter 03 does NOT have a dedicated `embedding_config.py` file.

- **Chapter 00/01**: Used `embedding_config.py` → `get_embedding_model()` → returns LangChain `Embeddings` object
- **Chapter 03**: Uses `LLMAgnosticClient.acreate_embedding()` directly in `csv_rag_tool.py`

**Impact:** 
- **Good**: More streamlined, all LLM logic in one place
- **Action Required**: Ensure `llm_agnostic_layer.py` internal LLM detection covers both completion AND embedding calls

---

## 2. Implementation Plan

### Phase 1: Environment Configuration (No Code Changes)

#### Task 1.1: Create `.env.example` file
**File:** `chapter-03-llm-sandbox-and-multi-agent/.env.example`

**Action:** Copy from Chapter 01 `.env.example` with the following additions:

```bash
# =============================================================================
# INTERNAL LLM CONFIGURATION (Same as Chapter 01)
# =============================================================================
INTERNAL_LLM_API_KEY=""
INTERNAL_LLM_BASE_URL=""
INTERNAL_LLM_MODEL=""
INTERNAL_LLM_EMBEDDING_MODEL=""

# =============================================================================
# ADDITIONAL CHAPTER 03 VARIABLES
# =============================================================================
# Sandbox MCP Server
SANDBOX_MCP_SERVER_URL="http://sandbox_mcp_server:8082/mcp"
SANDBOX_MCP_SERVER_HOST="0.0.0.0"
SANDBOX_MCP_SERVER_PORT="8082"

# HPC MCP Server
HPC_MCP_SERVER_URL="http://hpc_mcp_server:8081/mcp"
HPC_MCP_SERVER_HOST="0.0.0.0"
HPC_MCP_SERVER_PORT="8081"

# Multi-Agent Configuration
MULTI_AGENT_DEFAULT_MODE="router"  # or "graph"
MULTI_AGENT_MAX_WORKERS="5"
```

**Testing:** Verify all env vars load correctly with `python-dotenv`

---

#### Task 1.2: Update `docker-compose.yaml`
**File:** `chapter-03-llm-sandbox-and-multi-agent/docker-compose.yaml`

**Changes Required:**

1. **Add internal LLM env vars to ALL services** (mcp_server, hpc_mcp_server, sandbox_mcp_server, streamlit_app):

```yaml
services:
  mcp_server:
    environment:
      # Add these at the top for highest priority
      - INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY}
      - INTERNAL_LLM_BASE_URL=${INTERNAL_LLM_BASE_URL}
      - INTERNAL_LLM_MODEL=${INTERNAL_LLM_MODEL}
      - INTERNAL_LLM_EMBEDDING_MODEL=${INTERNAL_LLM_EMBEDDING_MODEL}
      # ... existing vars
```

2. **Add to streamlit_app** (for agent initialization):
```yaml
  streamlit_app:
    environment:
      - INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY}
      - INTERNAL_LLM_BASE_URL=${INTERNAL_LLM_BASE_URL}
      - INTERNAL_LLM_MODEL=${INTERNAL_LLM_MODEL}
      - INTERNAL_LLM_EMBEDDING_MODEL=${INTERNAL_LLM_EMBEDDING_MODEL}
      # ... existing vars
```

3. **Add to hpc_mcp_server** (if it creates agents/LLMs):
```yaml
  hpc_mcp_server:
    environment:
      - INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY}
      - INTERNAL_LLM_BASE_URL=${INTERNAL_LLM_BASE_URL}
      - INTERNAL_LLM_MODEL=${INTERNAL_LLM_MODEL}
      - INTERNAL_LLM_EMBEDDING_MODEL=${INTERNAL_LLM_EMBEDDING_MODEL}
      # ... existing vars
```

4. **Add to sandbox_mcp_server** (if it uses LLMs for code generation):
```yaml
  sandbox_mcp_server:
    environment:
      - INTERNAL_LLM_API_KEY=${INTERNAL_LLM_API_KEY}
      - INTERNAL_LLM_BASE_URL=${INTERNAL_LLM_BASE_URL}
      - INTERNAL_LLM_MODEL=${INTERNAL_LLM_MODEL}
      - INTERNAL_LLM_EMBEDDING_MODEL=${INTERNAL_LLM_EMBEDDING_MODEL}
      # ... existing vars
```

**Testing:** `docker compose config` to verify env var expansion

---

### Phase 2: Core LLM Layer Updates

#### Task 2.1: Update `llm_agnostic_layer.py`
**File:** `src/agentic_framework_pkg/core/llm_agnostic_layer.py`

**Location:** Inside `_call_litellm()` method, BEFORE reading `model_name` (around line 150)

**Code to Add:**

```python
async def _call_litellm(self, ...):
    """Unified method to call LiteLLM with automatic provider detection."""
    
    # ============================================================================
    # PRIORITY 1: Check for internal LLM provider FIRST
    # ============================================================================
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")
    internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

    if internal_llm_api_key and internal_llm_base_url:
        logger.info(f"Using internal LLM provider: {internal_llm_base_url}")
        
        # Override model for embeddings
        if llm_purpose == "embedding" and internal_llm_embedding_model:
            model_name = internal_llm_embedding_model
            logger.info(f"Using internal embedding model: {model_name}")
        elif internal_llm_model:
            model_name = internal_llm_model
            logger.info(f"Using internal chat model: {model_name}")
        
        # LiteLLM requires openai/ prefix for custom base URLs
        if not model_name.startswith("openai/"):
            model_name = f"openai/{model_name}"
        
        # Call LiteLLM with internal provider config
        try:
            if llm_purpose == "embedding":
                return await litellm.aembedding(
                    model=model_name,
                    input=input_texts,  # Assuming embedding call
                    api_key=internal_llm_api_key,
                    api_base=internal_llm_base_url,
                    **kwargs
                )
            else:
                return await litellm.acompletion(
                    model=model_name,
                    messages=messages,
                    api_key=internal_llm_api_key,
                    api_base=internal_llm_base_url,
                    stream=stream,
                    **kwargs
                )
        except Exception as e:
            logger.error(f"Internal LLM call failed: {e}", exc_info=True)
            raise LLMServiceError(f"Internal LLM error: {e}")
    
    # ============================================================================
    # Continue with existing provider logic (Azure, OpenAI, etc.)
    # ============================================================================
    # ... rest of existing code
```

**Key Points:**
- ✅ Check internal LLM BEFORE parsing model name
- ✅ Handle both chat and embedding calls
- ✅ Use modern `base_url` parameter
- ✅ Add `openai/` prefix for LiteLLM compatibility
- ✅ Log provider selection for debugging

**Testing:**
- Unit test with mocked `litellm.acompletion`
- Unit test with mocked `litellm.aembedding`
- Verify precedence over Azure when both configured

---

#### Task 2.2: Update `langchain_agent.py`
**File:** `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`

**Location:** Inside `__init__()` method, BEFORE line 70 (before LLM initialization)

**Code to Add:**

```python
def __init__(self, mcp_session_id: Optional[str] = None):
    self.mcp_session_id = mcp_session_id
    self.llm_agnostic_client = LLMAgnosticClient()

    # ============================================================================
    # PRIORITY 1: Check for internal LLM provider FIRST
    # ============================================================================
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")

    if internal_llm_api_key and internal_llm_base_url and internal_llm_model:
        logger.info(f"Using internal LLM for agent: {internal_llm_base_url} / {internal_llm_model}")
        
        # Determine token limit based on model type
        is_reasoning_model = any(reasoning_prefix in internal_llm_model.lower() 
                                 for reasoning_prefix in ["o3", "o4"])
        max_tokens = 4000 if is_reasoning_model else 1000
        
        from langchain_openai import ChatOpenAI
        self.llm = ChatOpenAI(
            model=internal_llm_model,
            api_key=internal_llm_api_key,
            base_url=internal_llm_base_url,
            max_tokens=max_tokens,
            temperature=0,
        )
        logger.info(f"Internal LLM initialized with max_tokens={max_tokens}")
    
    # ============================================================================
    # Fallback to LLMAgnosticClient if internal not configured
    # ============================================================================
    else:
        try:
            self.llm = self.llm_agnostic_client.get_langchain_chat_model(
                llm_purpose="agent_main",
                model_name=os.getenv("LANGCHAIN_LLM_MODEL"),
            )
            logger.info(f"ScientificWorkflowAgent's LLM initialized via LLMAgnosticClient: {type(self.llm).__name__}")
        except ValueError as e:
            logger.error(f"Failed to initialize LLM for ScientificWorkflowAgent: {e}", exc_info=True)
            raise
    
    # ... rest of tool initialization
```

**Key Points:**
- ✅ Check internal LLM BEFORE calling `get_langchain_chat_model()`
- ✅ Reasoning model detection (o3-mini, o4-mini → 4000 tokens)
- ✅ Use modern `base_url` parameter
- ✅ Graceful fallback to cloud providers

**Testing:**
- Test with all 4 internal env vars set → uses internal LLM
- Test with only 3 env vars set → falls back to cloud
- Test reasoning model detection → gets 4000 tokens
- Test non-reasoning model → gets 1000 tokens

---

### Phase 3: Multi-Agent System Updates (NEW)

#### Task 3.1: Update `multi_agent_tool.py`
**File:** `src/agentic_framework_pkg/mcp_server/tools/multi_agent_tool.py`

**Critical Finding:** Multi-agent tools create LLMs via `_llm_agnostic_client_instance.get_langchain_chat_model()`. 

**Two Approaches:**

**Option A: Update `LLMAgnosticClient.get_langchain_chat_model()` (RECOMMENDED)**

This ensures ALL agent types (main, planner, worker, supervisor) automatically use internal LLM.

**Location:** In `llm_agnostic_layer.py`, inside `get_langchain_chat_model()` method

**Code to Add (at the beginning of method):**

```python
def get_langchain_chat_model(self, llm_purpose: str = "generic", model_name: Optional[str] = None, **kwargs) -> BaseChatModel:
    """Returns a Langchain-compatible chat model instance."""
    
    # ============================================================================
    # PRIORITY 1: Check for internal LLM provider FIRST
    # ============================================================================
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_model = os.getenv("INTERNAL_LLM_MODEL")
    
    if internal_llm_api_key and internal_llm_base_url and internal_llm_model:
        logger.info(f"get_langchain_chat_model: Using internal LLM for purpose '{llm_purpose}'")
        
        # Determine token limit based on model type
        is_reasoning_model = any(reasoning_prefix in internal_llm_model.lower() 
                                 for reasoning_prefix in ["o3", "o4"])
        max_tokens = kwargs.pop("max_tokens", 4000 if is_reasoning_model else 1000)
        
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=internal_llm_model,
            api_key=internal_llm_api_key,
            base_url=internal_llm_base_url,
            max_tokens=max_tokens,
            **kwargs  # Allow override of temperature, etc.
        )
    
    # ============================================================================
    # Continue with existing provider logic
    # ============================================================================
    # ... existing code for Azure, OpenAI, Ollama
```

**Benefits:**
- ✅ Single point of change
- ✅ Automatically covers ALL agent types
- ✅ Consistent behavior across codebase

**Option B: Update each agent creation function individually**

Not recommended due to code duplication and maintenance burden.

---

#### Task 3.2: Verify Multi-Agent LLM Usage Points

**Files to Review:**
- `multi_agent_tool.py`:
  - Line 62: `create_worker_agent()` → calls `get_langchain_chat_model(llm_purpose="agent_worker")`
  - Line 143: `create_planner_agent()` → calls `get_langchain_chat_model(llm_purpose="agent_planner")`
  - Supervisor creation (if exists) → same pattern

**Action:** No changes needed if Task 3.1 Option A is implemented.

**Testing:**
- Create multi-agent session → verify all agents use internal LLM
- Test planner agent → should use internal LLM for plan generation
- Test worker agents → should use internal LLM for task execution

---

### Phase 4: Embeddings Verification

#### Task 4.1: Verify Embedding Call Path
**File:** `src/agentic_framework_pkg/mcp_server/tools/csv_rag_tool.py`

**Current Architecture:**
```python
# Line 32: Global instance
_llm_client_instance: LLMAgnosticClient | None = None

# Later in code:
embeddings_list = await _llm_client_instance.acreate_embedding(
    input_texts=chunks,
    llm_purpose="embedding"  # This should trigger internal LLM
)
```

**Verification:**
1. Ensure `LLMAgnosticClient.acreate_embedding()` calls `_call_litellm()` with `llm_purpose="embedding"`
2. Ensure Task 2.1 changes handle `llm_purpose="embedding"` case
3. Verify `INTERNAL_LLM_EMBEDDING_MODEL` is used when set

**Testing:**
- Upload CSV → verify embeddings use internal LLM
- Query RAG → verify query embeddings use internal LLM
- Check logs for "Using internal embedding model: ..."

---

### Phase 5: Testing Strategy

#### 5.1 Unit Tests (New Files to Create)

**File 1:** `tests/test_internal_llm_config.py`

**Tests Required:**
```python
class TestInternalLLMConfiguration:
    def test_agent_initialization_with_internal_llm()
    def test_agent_fallback_to_azure()
    def test_agent_fallback_to_openai()
    def test_reasoning_model_max_tokens()
    def test_non_reasoning_model_max_tokens()
    def test_incomplete_config_falls_back()
    
    # NEW: Multi-agent tests
    def test_planner_agent_uses_internal_llm()
    def test_worker_agent_uses_internal_llm()
    def test_multi_agent_session_all_agents_use_internal()
```

**File 2:** `tests/test_llm_agnostic_layer.py`

**Tests Required:**
```python
class TestLLMAgnosticLayerInternalProvider:
    async def test_internal_llm_completion()
    async def test_internal_llm_embedding()
    async def test_internal_llm_priority_over_azure()
    
    # NEW: Multi-purpose tests
    async def test_get_langchain_chat_model_uses_internal()
    async def test_acreate_embedding_uses_internal()
```

**File 3:** `tests/test_multi_agent_internal_llm.py` (NEW)

**Tests Required:**
```python
class TestMultiAgentInternalLLM:
    def test_create_worker_agent_uses_internal_llm()
    def test_create_planner_agent_uses_internal_llm()
    def test_multi_agent_tool_initialization()
    
    @pytest.mark.asyncio
    async def test_multi_agent_session_creation_with_internal()
    
    @pytest.mark.asyncio
    async def test_planner_generates_plan_with_internal_llm()
```

---

#### 5.2 Integration Tests

**Scenario 1: Simple Agent Query**
```python
# Test that single-agent workflow uses internal LLM
agent = ScientificWorkflowAgent(mcp_session_id="test-session")
result = await agent.arun("What is 2+2?")
assert "4" in result["output"]
# Verify logs show "Using internal LLM"
```

**Scenario 2: Multi-Agent Session**
```python
# Test multi-agent workflow
# 1. Create session
# 2. Generate plan with planner agent
# 3. Execute plan with worker agents
# 4. Verify all agents used internal LLM (check logs)
```

**Scenario 3: RAG with Embeddings**
```python
# Test CSV upload → embedding → query flow
# 1. Upload CSV file
# 2. Verify embeddings created with internal model
# 3. Query RAG
# 4. Verify query embeddings use internal model
```

**Scenario 4: Sandbox Code Execution**
```python
# Test that sandbox tools work with internal LLM
# 1. Request code generation via agent
# 2. Agent calls sandbox execution tool
# 3. Verify code executes successfully
```

---

#### 5.3 Docker Integration Tests

**Test Script:** `tests/test_docker_internal_llm.sh`

```bash
#!/bin/bash
# Test internal LLM configuration in Docker environment

# 1. Verify env vars are passed to all containers
docker compose exec mcp_server printenv | grep INTERNAL_LLM
docker compose exec hpc_mcp_server printenv | grep INTERNAL_LLM
docker compose exec sandbox_mcp_server printenv | grep INTERNAL_LLM
docker compose exec streamlit_app printenv | grep INTERNAL_LLM

# 2. Test connectivity from each container
docker compose exec mcp_server curl -s ${INTERNAL_LLM_BASE_URL}/health
docker compose exec streamlit_app curl -s ${INTERNAL_LLM_BASE_URL}/health

# 3. Run pytest inside containers
docker compose exec mcp_server uv run pytest tests/test_internal_llm_config.py -v
```

---

### Phase 6: Documentation

#### 6.1 Create Implementation Summary (After Completion)

**File:** `INTERNAL_LLM_IMPLEMENTATION.md`

**Contents:**
- Overview of changes
- All files modified with line numbers
- Configuration requirements
- Test results
- Production issues and fixes (if any)
- Comparison with Chapter 01 implementation

#### 6.2 Create Quick Start Guide

**File:** `INTERNAL_LLM_QUICKSTART.md`

**Contents:**
- 4 environment variables to set
- How to verify it's working (log messages to look for)
- Common troubleshooting issues
- How to fall back to cloud providers

#### 6.3 Update README.md

**Section to Add:**

```markdown
## Using Internal LLM Providers

Chapter 03 supports internal/local LLM providers with OpenAI-compatible APIs.

### Configuration

Set these 4 environment variables in your `.env` file:

```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://your-internal-llm.example.com"
INTERNAL_LLM_MODEL="your-chat-model"
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"
```

When all 4 are set, the internal LLM takes precedence over cloud providers.

### Multi-Agent Support

All agent types use the internal LLM when configured:
- Main ScientificWorkflowAgent
- Planner agents (for multi-agent tasks)
- Worker agents (specialized roles)
- Supervisor agents (task coordination)

See `INTERNAL_LLM_QUICKSTART.md` for details.
```

---

## 3. Risk Analysis & Mitigation

### Risk 1: Multi-Agent Complexity
**Risk:** Different agent types might need different LLM configurations

**Mitigation:**
- Use `llm_purpose` parameter to differentiate agent types
- Allow per-purpose model override via env vars (e.g., `AGENT_PLANNER_MODEL`)
- Log which model each agent type uses

**Severity:** Medium

---

### Risk 2: Sandbox Server Isolation
**Risk:** Sandbox server might not need/want LLM access (security)

**Mitigation:**
- Make internal LLM env vars optional for sandbox server
- Sandbox tools should be pure execution, no LLM calls
- Add explicit check: "Does sandbox server actually use LLMs?"

**Action Before Implementation:** Verify if `sandbox_mcp_server` makes any LLM calls

**Severity:** Low

---

### Risk 3: Embedding Model Compatibility
**Risk:** Internal embedding model might have different dimensions than expected

**Mitigation:**
- Add dimension detection in embedding calls
- Log embedding dimensions for debugging
- Allow override via `INTERNAL_LLM_EMBEDDING_DIMENSIONS` env var

**Severity:** Medium

---

### Risk 4: HPC MCP Server Dependencies
**Risk:** HPC server might have different LLM requirements (on-premise restrictions)

**Mitigation:**
- Make HPC server LLM configuration independent
- Allow `HPC_INTERNAL_LLM_*` env vars if needed
- Test HPC workflows with and without internal LLM

**Severity:** Low

---

### Risk 5: Docker Network Connectivity
**Risk:** Internal LLM URL might not be reachable from Docker containers

**Mitigation:**
- Use `host.docker.internal` for host-based services
- Add connectivity test in startup scripts
- Provide clear error messages for network issues

**Example Health Check:**
```bash
# In start-chapter-resources.sh
if [ ! -z "$INTERNAL_LLM_BASE_URL" ]; then
    echo "Testing internal LLM connectivity..."
    curl -s "${INTERNAL_LLM_BASE_URL}/health" || echo "WARNING: Cannot reach internal LLM"
fi
```

**Severity:** High

---

## 4. Testing Checklist

### Pre-Implementation Testing
- [ ] Chapter 01 tests all pass
- [ ] Chapter 00 implementation reviewed
- [ ] Chapter 03 current state documented
- [ ] All files identified for modification
- [ ] No `embedding_config.py` confirmed (use `LLMAgnosticClient` directly)

### Phase 1 Testing (Configuration)
- [ ] `.env.example` created with all required vars
- [ ] `docker-compose.yaml` updated with internal LLM env vars
- [ ] `docker compose config` validates successfully
- [ ] All 4 services receive env vars (verified with `docker compose exec ... printenv`)

### Phase 2 Testing (Core LLM Layer)
- [ ] `llm_agnostic_layer.py` modified correctly
- [ ] Internal LLM detection logic added
- [ ] Embedding calls respect internal LLM
- [ ] `langchain_agent.py` modified correctly
- [ ] Agent initialization uses internal LLM
- [ ] Unit tests pass for `LLMAgnosticClient`

### Phase 3 Testing (Multi-Agent)
- [ ] `get_langchain_chat_model()` supports internal LLM
- [ ] Planner agent uses internal LLM
- [ ] Worker agents use internal LLM
- [ ] Multi-agent session creation works
- [ ] Unit tests pass for multi-agent tools

### Phase 4 Testing (Embeddings)
- [ ] CSV upload generates embeddings with internal model
- [ ] RAG queries use internal embedding model
- [ ] Embedding dimensions logged correctly
- [ ] ChromaDB ingestion works with internal embeddings

### Phase 5 Testing (Integration)
- [ ] Simple agent query uses internal LLM
- [ ] Multi-agent workflow uses internal LLM for all agents
- [ ] RAG workflow (upload → embed → query) works end-to-end
- [ ] Sandbox code execution works (if applicable)
- [ ] All services start successfully in Docker
- [ ] Logs confirm internal LLM usage

### Phase 6 Testing (Fallback & Edge Cases)
- [ ] Partial config (3/4 vars) falls back gracefully
- [ ] Missing config uses cloud providers
- [ ] Multiple providers configured → internal takes precedence
- [ ] Reasoning models get correct token limits
- [ ] Non-reasoning models get correct token limits

### Production Readiness
- [ ] All unit tests pass (target: 20+ tests)
- [ ] All integration tests pass
- [ ] Docker tests pass
- [ ] Documentation complete
- [ ] Known issues documented
- [ ] Rollback plan documented

---

## 5. Implementation Timeline

### Estimated Effort
- **Phase 1 (Config):** 1-2 hours
- **Phase 2 (Core LLM):** 2-3 hours
- **Phase 3 (Multi-Agent):** 2-3 hours
- **Phase 4 (Embeddings):** 1 hour
- **Phase 5 (Testing):** 3-4 hours
- **Phase 6 (Documentation):** 1-2 hours

**Total:** 10-15 hours of focused work

### Recommended Order
1. ✅ Phase 1: Configuration (low risk, enables testing)
2. ✅ Phase 2: Core LLM Layer (foundation for everything else)
3. ✅ Phase 5.2: Basic integration test (verify Phase 2 works)
4. ✅ Phase 3: Multi-Agent System (builds on Phase 2)
5. ✅ Phase 4: Embeddings verification (parallel with Phase 3)
6. ✅ Phase 5: Full testing suite
7. ✅ Phase 6: Documentation

---

## 6. Success Criteria

### Functional Requirements
- ✅ All 4 internal LLM env vars are recognized
- ✅ Internal LLM takes precedence over cloud providers
- ✅ All agent types use internal LLM when configured
- ✅ Embeddings use internal embedding model
- ✅ Graceful fallback to cloud providers when internal not configured

### Performance Requirements
- ✅ No performance regression compared to cloud providers
- ✅ Multi-agent workflows complete successfully
- ✅ RAG embedding generation completes within timeout

### Quality Requirements
- ✅ 20+ unit tests, all passing
- ✅ Integration tests cover all major workflows
- ✅ Code follows existing patterns from Chapter 00/01
- ✅ No API key leakage in logs
- ✅ Comprehensive documentation

---

## 7. Open Questions (To Resolve Before Implementation)

### Question 1: Does Sandbox MCP Server Use LLMs?
**Context:** Sandbox server executes code in isolated environment

**Need to Determine:**
- Does it generate code via LLM?
- Does it analyze code output via LLM?
- Or is it pure execution (no LLM)?

**Action:** Review `sandbox_mcp_server/` codebase for LLM usage

**Impact on Plan:** If sandbox uses LLMs, add internal LLM support; otherwise skip

---

### Question 2: HPC MCP Server LLM Requirements
**Context:** HPC server might have network restrictions

**Need to Determine:**
- Does HPC server create agents/LLMs?
- Can it reach internal LLM from HPC network?
- Should it use different internal LLM endpoint?

**Action:** Review HPC deployment architecture

**Impact on Plan:** Might need separate `HPC_INTERNAL_LLM_*` env vars

---

### Question 3: Embedding Dimension Compatibility
**Context:** Different embedding models have different dimensions

**Need to Determine:**
- What dimension does ChromaDB expect?
- What dimension does internal embedding model produce?
- How to handle dimension mismatches?

**Action:** Add dimension validation in embedding code

**Impact on Plan:** Might need dimension override or validation logic

---

## 8. Comparison with Chapter 01

| Aspect               | Chapter 01                      | Chapter 03                              | Impact                                |
| -------------------- | ------------------------------- | --------------------------------------- | ------------------------------------- |
| **MCP Servers**      | 1 (main)                        | 3 (main, HPC, sandbox)                  | More env var configuration            |
| **Agents**           | 1 (ScientificWorkflowAgent)     | 4+ (main, planner, supervisor, workers) | More LLM initialization points        |
| **Embedding Config** | Dedicated `embedding_config.py` | Integrated in `LLMAgnosticClient`       | Simpler, but verify carefully         |
| **Tools**            | ~15 tools                       | ~30 tools                               | More integration test coverage needed |
| **Complexity**       | Low                             | High                                    | Thorough testing critical             |

### Key Differences
1. **No `embedding_config.py`**: All embedding logic in `llm_agnostic_layer.py`
2. **Multi-Agent System**: Requires LLM config in `multi_agent_tool.py`
3. **More Services**: 3 MCP servers vs 1
4. **More Tools**: 2x the number of tools to test

### Advantages Over Chapter 01
1. **Centralized LLM Logic**: Single source of truth in `LLMAgnosticClient`
2. **Consistent Pattern**: All agents use `get_langchain_chat_model()`
3. **Better Tested**: Chapter 01 lessons learned applied

---

## 9. Approval Request

This plan is ready for review. Key decisions needed:

1. **Approve overall approach?** (Using Chapter 00/01 patterns)
2. **Confirm scope?** (All 3 MCP servers + multi-agent system)
3. **Approve testing strategy?** (20+ unit tests + integration tests)
4. **Any concerns about multi-agent complexity?**

**Next Steps After Approval:**
1. Resolve open questions (Section 7)
2. Begin Phase 1 (Configuration)
3. Proceed through phases sequentially
4. Report progress after each phase

---

## 10. Appendix: File Modification Summary

### Files to Create
- `tests/test_internal_llm_config.py` (NEW)
- `tests/test_llm_agnostic_layer.py` (NEW)
- `tests/test_multi_agent_internal_llm.py` (NEW)
- `tests/test_docker_internal_llm.sh` (NEW)
- `INTERNAL_LLM_IMPLEMENTATION.md` (after completion)
- `INTERNAL_LLM_QUICKSTART.md` (after completion)

### Files to Modify
- `.env.example` (CREATE from Chapter 01 template)
- `docker-compose.yaml` (add internal LLM env vars)
- `docker-compose-hpc.yaml` (optional, if HPC uses LLMs)
- `src/agentic_framework_pkg/core/llm_agnostic_layer.py` (add internal LLM detection)
- `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py` (add internal LLM init)
- `README.md` (add internal LLM usage section)

### Files to Verify (No Changes Expected)
- `src/agentic_framework_pkg/mcp_server/tools/csv_rag_tool.py` (verify embedding calls)
- `src/agentic_framework_pkg/mcp_server/tools/multi_agent_tool.py` (verify LLM usage)
- `src/agentic_framework_pkg/sandbox_mcp_server/server.py` (check for LLM usage)

---

**End of Plan - Awaiting Approval**
