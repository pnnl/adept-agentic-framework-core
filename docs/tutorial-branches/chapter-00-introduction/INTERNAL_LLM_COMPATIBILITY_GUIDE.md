# Internal AI Service Compatibility Guide

**Objective:** Add support for internal/local LLM providers with OpenAI-compatible APIs while maintaining full backward compatibility with existing cloud providers (Azure OpenAI, AWS Bedrock, Google Vertex AI, Ollama, etc.).

**Last Updated:** January 27, 2026

---

## Table of Contents

1. [Required Code Changes](#required-code-changes)
2. [Configuration Requirements](#configuration-requirements)
3. [Priority & Precedence Logic](#priority--precedence-logic)
4. [Testing Strategy](#testing-strategy)
5. [Deployment Checklist](#deployment-checklist)
6. [Multi-Chapter Porting](#multi-chapter-porting)
7. [Backward Compatibility Verification](#backward-compatibility-verification)

---

## Required Code Changes

### 1. Embedding Configuration (`embedding_config.py`)

**File:** `src/agentic_framework_pkg/core/embedding_config.py`

**Location:** Top of `get_embedding_model()` function (BEFORE all other provider checks)

**Code to Add:**
```python
def get_embedding_model() -> Embeddings:
    """Returns the llm instance to be used for embedding."""
    
    # ============================================================================
    # INTERNAL LLM PROVIDER - CHECK FIRST
    # ============================================================================
    internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
    internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
    internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

    if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
        logger.info(
            f"Using internal LLM provider for embeddings: {internal_llm_base_url} "
            f"with model {internal_llm_embedding_model}"
        )
        return OpenAIEmbeddings(
            model=internal_llm_embedding_model,
            api_key=internal_llm_api_key,
            base_url=internal_llm_base_url,
        )

    # Continue with existing provider logic (Azure, Ollama, Google, OpenAI)...
```

**Key Points:**
- ✅ Must be **first check** in the function
- ✅ All 3 env vars required (fail gracefully if partial)
- ✅ Use modern `base_url` parameter (not deprecated `openai_api_base`)
- ✅ Add informative logging

---

### 2. LangChain Agent Configuration (`langchain_agent.py`)

**File:** `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`

#### Change 2.1: Add Internal LLM to Config Dictionary

**Location:** `__init__()` method

**Code to Add:**
```python
def __init__(self):
    self._llm_config = {
        "model_name": os.getenv("STREAMLIT_DEFAULT_MODEL", "ollama/mistral"),
        "ollama_base_url": os.getenv("OLLAMA_API_BASE_URL") or os.getenv("OLLAMA_API_BASE"),
        "azure_api_version": os.getenv("AZURE_API_VERSION"),
        "azure_api_key": os.getenv("AZURE_API_KEY") or os.getenv("OPENAI_API_KEY"),
        "azure_api_base": os.getenv("AZURE_API_BASE"),
        "google_project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "google_location": os.getenv("GOOGLE_LOCATION"),
        # ADD THESE THREE LINES:
        "internal_llm_api_key": os.getenv("INTERNAL_LLM_API_KEY"),
        "internal_llm_base_url": os.getenv("INTERNAL_LLM_BASE_URL"),
        "internal_llm_model": os.getenv("INTERNAL_LLM_MODEL"),
    }
```

#### Change 2.2: Update `_get_llm_instance()` Method

**Location:** BEGINNING of `_get_llm_instance()` method (BEFORE reading `model_name`)

**Code to Add:**
```python
async def _get_llm_instance(self):
    # ============================================================================
    # INTERNAL LLM PROVIDER - CHECK FIRST (BEFORE model_name parsing)
    # ============================================================================
    if (
        self._llm_config["internal_llm_api_key"]
        and self._llm_config["internal_llm_base_url"]
        and self._llm_config["internal_llm_model"]
    ):
        internal_model = self._llm_config["internal_llm_model"]
        internal_base_url = self._llm_config["internal_llm_base_url"]
        internal_api_key = self._llm_config["internal_llm_api_key"]

        logger.info(
            f"Using internal LLM provider: {internal_base_url} with model {internal_model}"
        )

        # Reasoning models (o4-mini, o3-mini) need higher max_tokens
        # They consume tokens for internal reasoning before generating output
        max_tokens = (
            4000
            if "o4-mini" in internal_model or "o3-mini" in internal_model
            else 1000
        )

        return ChatOpenAI(
            model=internal_model,
            api_key=internal_api_key,
            base_url=internal_base_url,
            max_tokens=max_tokens,
        )

    # Continue with existing provider logic (model_name parsing, Azure, Ollama, etc.)...
    model_name = str(self._llm_config["model_name"]).lower()
    logger.info(f"Using model {model_name} for chat agent")
    # ... rest of existing code
```

**Key Points:**
- ✅ Check internal LLM **before** reading `model_name`
- ✅ Prevents model name prefixes (like "o3-mini") from triggering wrong provider
- ✅ Special handling for reasoning models (high token requirements)
- ✅ Use modern `base_url` parameter

#### Change 2.3: (Optional) Infinite Loop Prevention

**Location:** In `_call_llm_decision_node()` method

**Code to Add:**
```python
async def _call_llm_decision_node(self, state: AgentState) -> AgentState:
    # ... existing code to call LLM and get response ...
    
    tool_calls = response.tool_calls
    
    # Prevent infinite loops: Check if schema already retrieved
    schema_info = state.get("schema_info")
    if schema_info and tool_calls and tool_calls[0]["name"] == "get_sql_schema":
        logger.warning(
            "Schema already retrieved, but LLM wants to call get_sql_schema again. Ending."
        )
        return {
            **state,
            "next_action": "end",
            "agent_outcome": (
                "Based on the schema information already retrieved, I can see the database "
                "structure. However, I need a more specific query to proceed."
            ),
        }
    
    # ... rest of existing tool call logic ...
```

**And in `_call_get_sql_schema_tool_node()`:**
```python
async def _call_get_sql_schema_tool_node(self, state: AgentState) -> AgentState:
    # ... existing code to get schema ...
    
    if schema_info:
        return {
            **state,
            "schema_info": schema_info,  # Store in state to prevent re-fetching
            "chat_history": state.get("chat_history", [])
            + [AIMessage(content=f"Database Schema: {schema_info}")],
            "next_action": "continue",
        }
```

#### Change 2.4: (Optional) ChromaDB Document Flattening

**Location:** In `_call_query_csv_rag_tool_node()` method

**Code to Add:**
```python
async def _call_query_csv_rag_tool_node(self, state: AgentState) -> AgentState:
    # ... existing code to query RAG ...
    
    if parsed_result and parsed_result.get("documents"):
        # ChromaDB returns documents as nested list [[doc1, doc2, ...]]
        # Flatten to prevent TypeError
        documents = parsed_result["documents"]
        if documents and isinstance(documents[0], list):
            documents = documents[0]  # Get first query's results
        
        rag_docs = "\n\n".join(str(doc) for doc in documents)
        return {
            **state,
            "rag_documents": documents,
            "agent_outcome": f"Relevant Information from CSV: {rag_docs}",
        }
```

---

### 3. Environment Configuration (`.env.example`)

**File:** `.env.example`

**Code to Add:**
```bash
# ============================================================================
# INTERNAL / LOCAL LLM CONFIGURATION (OpenAI-compatible API)
# ============================================================================
# Configure these to use an internal LLM provider instead of cloud services.
# When all variables are set, internal LLM takes HIGHEST PRIORITY.
# Leave blank to use cloud providers (Azure, OpenAI, Ollama, Google, etc.).
#
# Requirements:
#   - API must be OpenAI-compatible (accepts /chat/completions and /embeddings)
#   - Base URL should NOT include /v1 suffix (added automatically by SDK)
#   - All 4 variables must be set for full functionality
#
# Example (AI Incubator):
#   INTERNAL_LLM_API_KEY="sk-your-api-key-here"
#   INTERNAL_LLM_BASE_URL="https://ai-incubator-api.pnnl.gov"
#   INTERNAL_LLM_MODEL="o4-mini-project"
#   INTERNAL_LLM_EMBEDDING_MODEL="text-embedding-3-small-project"

INTERNAL_LLM_API_KEY=""
INTERNAL_LLM_BASE_URL=""
INTERNAL_LLM_MODEL=""
INTERNAL_LLM_EMBEDDING_MODEL=""
```

**Placement:** Add this section near the top, after general LLM configuration, before Azure/Ollama/Google sections.

---

### 4. Docker Configuration (`docker-compose.yaml`)

**Optional Change:** File upload permissions fix

**Location:** `streamlit_app` service definition

**Code to Modify:**
```yaml
streamlit_app:
  platform: linux/amd64
  build:
    context: .
    dockerfile: Dockerfile
    target: streamlit_app
  container_name: agentic_streamlit_app_ch00  # Update chapter number per chapter
  user: "0:0"  # Run as root to allow writing to volumes (FILE UPLOAD FIX)
  ports:
    - "8501:8501"
  # ... rest of configuration
```

**Note:** Only needed if you encounter file upload permission issues.

---

## Configuration Requirements

### Minimum Required Environment Variables

For **chat/completion only**:
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://your-internal-api.example.com"  # No /v1 suffix
INTERNAL_LLM_MODEL="your-model-name"
```

For **chat + embeddings** (full functionality):
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://your-internal-api.example.com"
INTERNAL_LLM_MODEL="your-chat-model"
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"  # Required for RAG
```

### Configuration Rules

1. **All-or-Nothing**: All required variables must be set. Partial configuration is ignored.
2. **No /v1 Suffix**: Base URL should NOT end with `/v1` - the OpenAI SDK adds it automatically.
3. **Priority**: Internal LLM takes precedence over ALL other providers when configured.
4. **Fail-Safe**: If internal config is incomplete, system falls back to cloud providers.

---

## Priority & Precedence Logic

### Provider Selection Order

When user doesn't specify an explicit model:

```
1. Internal LLM (if all 3+ env vars set)
   ↓
2. Azure OpenAI (if model name starts with azure/, o3, o4, gpt AND Azure config exists)
   ↓
3. Ollama (if model name starts with ollama/)
   ↓
4. Google Vertex AI (if model name starts with google/)
   ↓
5. OpenAI (default fallback)
```

### Critical Implementation Detail

**⚠️ MUST check internal LLM BEFORE parsing model_name**

**Why?** Model names like `o3-mini` or `o4-mini` could trigger Azure logic if checked first.

**Correct Order:**
```python
async def _get_llm_instance(self):
    # 1. Check internal LLM FIRST (before reading model_name)
    if internal_llm_configured:
        return ChatOpenAI(...)
    
    # 2. THEN parse model_name and check other providers
    model_name = str(self._llm_config["model_name"]).lower()
    if model_name.startswith("azure/"):
        return AzureChatOpenAI(...)
    # ... etc
```

**Incorrect Order (causes bugs):**
```python
async def _get_llm_instance(self):
    # ❌ WRONG: Reading model_name first
    model_name = str(self._llm_config["model_name"]).lower()
    
    # ❌ BUG: "o3-mini" triggers Azure even if internal LLM is configured
    if model_name.startswith("o3"):
        return AzureChatOpenAI(...)
    
    # Too late - Azure already triggered
    if internal_llm_configured:
        return ChatOpenAI(...)
```

---

## Testing Strategy

### 1. Unit Tests to Add

**File:** `tests/test_embedding_internal_llm.py`

**Tests Required:**
- ✅ Internal LLM provider detection (all env vars set)
- ✅ Fallback to other providers when internal not configured
- ✅ Partial configuration ignored (graceful degradation)
- ✅ Internal LLM takes precedence over Azure/Ollama
- ✅ Base URL handling (with/without `/v1`)

**File:** `tests/test_user_scenario_o3_mini.py`

**Tests Required:**
- ✅ Model name prefixes don't interfere with internal LLM (e.g., `o3-mini`)
- ✅ Internal LLM checked before model name parsing
- ✅ All 3 env vars required for activation
- ✅ Modern `base_url` parameter used (not deprecated `openai_api_base`)

### 2. Integration Tests

**Test Scenarios:**
```python
# Scenario 1: Internal LLM + Azure both configured → Internal wins
env = {
    "INTERNAL_LLM_API_KEY": "test",
    "INTERNAL_LLM_BASE_URL": "https://internal.example.com",
    "INTERNAL_LLM_MODEL": "internal-model",
    "AZURE_API_KEY": "azure-key",  # Should be ignored
    "AZURE_API_BASE": "https://azure.example.com",
}

# Scenario 2: Partial internal config → Falls back to Azure
env = {
    "INTERNAL_LLM_API_KEY": "test",
    "INTERNAL_LLM_BASE_URL": "https://internal.example.com",
    # Missing INTERNAL_LLM_MODEL → Should use Azure
    "AZURE_API_KEY": "azure-key",
    "AZURE_API_BASE": "https://azure.example.com",
}

# Scenario 3: No internal config → Uses existing providers
env = {
    "OLLAMA_API_BASE_URL": "http://localhost:11434",
    "STREAMLIT_DEFAULT_MODEL": "ollama/mistral",
}
```

### 3. Manual Validation

**Checklist:**
```bash
# 1. Set internal LLM config in .env
INTERNAL_LLM_API_KEY="your-key"
INTERNAL_LLM_BASE_URL="https://your-api.example.com"
INTERNAL_LLM_MODEL="your-model"
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"

# 2. Restart Docker
./start-chapter-resources.sh  # Select "Restart"

# 3. Check logs show internal LLM is used
docker logs agentic_streamlit_app_chXX 2>&1 | grep -i "internal"

# Expected output:
# INFO - Using internal LLM provider: https://... with model ...
# INFO - Using internal LLM provider for embeddings: https://... with model ...

# 4. Run test suite
uv run pytest tests/ -v

# Expected: All tests pass

# 5. Test in UI
# - Upload a CSV file
# - Ask a query
# - Verify response comes from internal LLM
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All code changes implemented
- [ ] `.env.example` updated with clear documentation
- [ ] Unit tests added and passing (40+ total)
- [ ] Integration tests passing
- [ ] Docker containers rebuild successfully
- [ ] Logs show internal LLM detection
- [ ] No API keys committed to repository

### Development Environment

- [ ] `.env` file created from `.env.example`
- [ ] Internal LLM credentials configured
- [ ] Containers started: `./start-chapter-resources.sh`
- [ ] Logs verified: `docker logs agentic_streamlit_app_chXX`
- [ ] Manual testing in UI completed

### Production Environment

- [ ] Secrets management configured (not `.env` file)
- [ ] Internal API endpoint accessible from production network
- [ ] IP whitelisting configured (if required)
- [ ] Authentication tested (API key valid)
- [ ] Monitoring/logging configured for internal LLM usage
- [ ] Fallback provider configured (for high availability)

### Kubernetes-Specific (Chapter 4+)

- [ ] ConfigMap updated with `INTERNAL_LLM_*` variables
- [ ] Secret created for `INTERNAL_LLM_API_KEY`
- [ ] Environment variables injected into pods
- [ ] Service mesh / network policies allow internal API access
- [ ] Tested in staging cluster before production

---

## Multi-Chapter Porting

### Chapter-by-Chapter Strategy

#### Chapter 0 (Introduction)
**Status:** ✅ **COMPLETE**
- All changes implemented
- All tests passing
- Documented

#### Chapter 1 (Main)
**Complexity:** 🟢 **LOW** (most similar to chapter 0)

**Files to Update:**
- `.env.example`
- `src/agentic_framework_pkg/core/embedding_config.py`
- `src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`
- `docker-compose.yaml` (service names: `ch00` → `ch01`)
- `tests/test_embedding_internal_llm.py`
- `tests/test_user_scenario_o3_mini.py`

**Gotchas:**
- Service names in docker-compose: `agentic_streamlit_app_ch01`
- Network names: `agentic_network_ch01`
- Port numbers: Same as chapter 0 (no conflicts if run separately)

#### Chapter 2 (HPC + Chain-of-Thought)
**Complexity:** 🟡 **MEDIUM** (adds HPC gateway)

**Additional Files:**
- `docker-compose-hpc.yaml` (HPC-specific compose file)
- `src/.../hpc_gateway/` (if HPC gateway has its own LLM calls)

**Gotchas:**
- HPC gateway service might need **separate internal LLM config**
- Two docker-compose files: standard + HPC variant
- Chain-of-thought logic might have different LLM initialization

**Additional Checks:**
- [ ] Does HPC gateway call LLMs independently?
- [ ] If yes, add internal LLM support to HPC gateway code
- [ ] Test both docker-compose.yaml AND docker-compose-hpc.yaml

#### Chapter 3 (LLM Sandbox + Multi-Agent)
**Complexity:** 🟡 **MEDIUM** (multiple agents)

**Additional Services:**
- LLM Sandbox container
- Multiple agent instances

**Gotchas:**
- Each agent might need its own LLM instance
- Sandbox service might have different model requirements
- Multi-agent orchestration might use different models per agent

**Questions to Answer:**
- [ ] Do all agents use the same internal LLM model?
- [ ] Does sandbox need internal LLM access?
- [ ] Should different agents use different internal models?

**Possible Enhancement:**
```bash
# Option: Per-agent internal LLM models
INTERNAL_LLM_MODEL_AGENT1="reasoning-model"
INTERNAL_LLM_MODEL_AGENT2="fast-model"
```

#### Chapter 4 (Kubernetes Deployment)
**Complexity:** 🔴 **HIGH** (Kubernetes configuration)

**Additional Files:**
- `infra/k8s/configmap.yaml`
- `infra/k8s/secret.yaml`
- `infra/k8s/deployment.yaml`

**Gotchas:**
- `.env` pattern doesn't apply - must use ConfigMaps/Secrets
- Environment variables loaded differently in K8s
- Network policies might block internal API access
- Service mesh considerations

**Required K8s Changes:**

**ConfigMap:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-framework-config
data:
  INTERNAL_LLM_BASE_URL: "https://internal-api.example.com"
  INTERNAL_LLM_MODEL: "your-model"
  INTERNAL_LLM_EMBEDDING_MODEL: "your-embedding-model"
```

**Secret:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agentic-framework-secrets
type: Opaque
stringData:
  INTERNAL_LLM_API_KEY: "your-api-key"
```

**Deployment:**
```yaml
env:
  - name: INTERNAL_LLM_API_KEY
    valueFrom:
      secretKeyRef:
        name: agentic-framework-secrets
        key: INTERNAL_LLM_API_KEY
  - name: INTERNAL_LLM_BASE_URL
    valueFrom:
      configMapKeyRef:
        name: agentic-framework-config
        key: INTERNAL_LLM_BASE_URL
  # ... etc
```

#### Chapter 5 (OpenWebUI Integration)
**Complexity:** 🟡 **MEDIUM** (external integration)

**Additional Considerations:**
- OpenWebUI has its own model configuration
- Need to ensure compatibility between OpenWebUI and internal LLM
- API endpoints might differ

**Questions:**
- [ ] Does OpenWebUI call our agent or does it call LLMs directly?
- [ ] If direct LLM calls, does OpenWebUI support custom OpenAI endpoints?
- [ ] Are there conflicts between OpenWebUI config and our config?

#### Chapter 6 (Advanced Multi-Agent Orchestration)
**Complexity:** 🔴 **HIGH** (complex orchestration)

**Additional Considerations:**
- Multiple specialized agents
- Agent-to-agent communication
- Different models per agent role (possible enhancement)

**Potential Enhancements:**
```bash
# Specialized models per agent type
INTERNAL_LLM_MODEL_PLANNER="reasoning-model"
INTERNAL_LLM_MODEL_EXECUTOR="fast-model"
INTERNAL_LLM_MODEL_CRITIC="analysis-model"
```

---

## Backward Compatibility Verification

### Verification Checklist

**Before implementing internal LLM support, verify:**
- [ ] Run existing test suite: `uv run pytest tests/` → All pass
- [ ] Start containers with existing config → Works
- [ ] Test with Azure configuration only → Works
- [ ] Test with Ollama configuration only → Works
- [ ] Test with OpenAI configuration only → Works

**After implementing internal LLM support, verify:**
- [ ] Run full test suite: `uv run pytest tests/` → All still pass + new tests
- [ ] Test existing Azure config (without internal) → Still works
- [ ] Test existing Ollama config (without internal) → Still works
- [ ] Test existing OpenAI config (without internal) → Still works
- [ ] Test with internal LLM config → Internal LLM used
- [ ] Test with internal + Azure both configured → Internal takes precedence

### Regression Test Scenarios

**Scenario 1: Pure Azure (no changes)**
```bash
# .env
AZURE_API_KEY="your-azure-key"
AZURE_API_BASE="https://example.openai.azure.com/"
AZURE_API_VERSION="2023-05-15"
STREAMLIT_DEFAULT_MODEL="gpt-4"

# Expected: Uses Azure (exactly as before implementation)
```

**Scenario 2: Pure Ollama (no changes)**
```bash
# .env
OLLAMA_API_BASE_URL="http://localhost:11434"
STREAMLIT_DEFAULT_MODEL="ollama/mistral"
EMBEDDING_DEFAULT_MODEL="ollama/nomic-embed-text"

# Expected: Uses Ollama (exactly as before implementation)
```

**Scenario 3: Mixed Azure + Ollama (no changes)**
```bash
# .env
AZURE_API_KEY="azure-key"
AZURE_API_BASE="https://example.openai.azure.com/"
OLLAMA_API_BASE_URL="http://localhost:11434"
STREAMLIT_DEFAULT_MODEL="gpt-4"  # Uses Azure
EMBEDDING_DEFAULT_MODEL="ollama/nomic-embed-text"  # Uses Ollama

# Expected: Chat uses Azure, Embeddings use Ollama (exactly as before)
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Including `/v1` in Base URL

**Problem:**
```bash
INTERNAL_LLM_BASE_URL="https://api.example.com/v1"  # ❌ Wrong
```

**Why it fails:** OpenAI SDK appends `/v1` automatically → becomes `https://api.example.com/v1/v1/chat/completions` (404 error)

**Solution:**
```bash
INTERNAL_LLM_BASE_URL="https://api.example.com"  # ✅ Correct
```

### Pitfall 2: Checking Internal LLM After Model Name Parsing

**Problem:**
```python
async def _get_llm_instance(self):
    model_name = str(self._llm_config["model_name"]).lower()
    
    if model_name.startswith("o3"):  # ❌ Triggers for "o3-mini"
        return AzureChatOpenAI(...)
    
    if internal_configured:  # Never reached if model is "o3-mini"
        return ChatOpenAI(...)
```

**Solution:** Check internal LLM **before** reading `model_name`

### Pitfall 3: Partial Configuration Not Handled

**Problem:**
```python
if internal_llm_api_key:  # ❌ Doesn't check base_url or model
    return ChatOpenAI(...)  # Crashes if base_url is None
```

**Solution:** Check **all** required variables
```python
if internal_llm_api_key and internal_llm_base_url and internal_llm_model:
    return ChatOpenAI(...)
```

### Pitfall 4: Using Deprecated Parameter Names

**Problem:**
```python
return ChatOpenAI(
    openai_api_base=base_url,  # ❌ Deprecated
)
```

**Solution:** Use modern parameter names
```python
return ChatOpenAI(
    base_url=base_url,  # ✅ Correct
)
```

### Pitfall 5: Forgetting Reasoning Model Token Requirements

**Problem:** Reasoning models (o4-mini, o3-mini) consume all tokens for internal reasoning, leaving none for response.

**Solution:** Increase max_tokens for reasoning models
```python
max_tokens = (
    4000 if "o4-mini" in model or "o3-mini" in model else 1000
)
```

---

## Quick Reference Card

### Environment Variables (Copy-Paste Template)

```bash
# ============================================================================
# INTERNAL LLM CONFIGURATION
# ============================================================================
INTERNAL_LLM_API_KEY="your-api-key-here"
INTERNAL_LLM_BASE_URL="https://your-internal-api.example.com"
INTERNAL_LLM_MODEL="your-chat-model"
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"
```

### Code Snippet: Embedding Config

```python
# Top of get_embedding_model() in embedding_config.py
internal_llm_api_key = os.getenv("INTERNAL_LLM_API_KEY")
internal_llm_base_url = os.getenv("INTERNAL_LLM_BASE_URL")
internal_llm_embedding_model = os.getenv("INTERNAL_LLM_EMBEDDING_MODEL")

if internal_llm_api_key and internal_llm_base_url and internal_llm_embedding_model:
    logger.info(f"Using internal LLM provider for embeddings")
    return OpenAIEmbeddings(
        model=internal_llm_embedding_model,
        api_key=internal_llm_api_key,
        base_url=internal_llm_base_url,
    )
```

### Code Snippet: LangChain Agent

```python
# Beginning of _get_llm_instance() in langchain_agent.py
if (
    self._llm_config["internal_llm_api_key"]
    and self._llm_config["internal_llm_base_url"]
    and self._llm_config["internal_llm_model"]
):
    max_tokens = (
        4000 if "o4-mini" in internal_model or "o3-mini" in internal_model else 1000
    )
    return ChatOpenAI(
        model=self._llm_config["internal_llm_model"],
        api_key=self._llm_config["internal_llm_api_key"],
        base_url=self._llm_config["internal_llm_base_url"],
        max_tokens=max_tokens,
    )
```

### Validation Command

```bash
# Check logs for internal LLM usage
docker logs agentic_streamlit_app_chXX 2>&1 | grep -i "internal"

# Expected output:
# INFO - Using internal LLM provider: https://... with model ...
# INFO - Using internal LLM provider for embeddings: https://... with model ...
```

---

## Success Criteria

**Implementation is complete when:**

✅ All code changes implemented in all relevant files  
✅ Environment variables documented in `.env.example`  
✅ Unit tests added and passing (40+ total)  
✅ Integration tests passing  
✅ Docker containers start successfully  
✅ Logs show internal LLM detection when configured  
✅ Backward compatibility verified (existing configs still work)  
✅ Manual testing in UI successful  
✅ No API keys committed to version control  
✅ Documentation complete (this guide + TROUBLESHOOTING guide)  

**Ready for production when:**

✅ All chapters updated (if multi-chapter deployment)  
✅ Kubernetes manifests updated (if applicable)  
✅ Internal API endpoint tested and accessible  
✅ IP whitelisting configured (if required)  
✅ Secrets management configured  
✅ Monitoring/alerting configured  
✅ Fallback provider configured  
✅ Load testing completed  
✅ Security review completed  

---

## Related Documentation

- **[INTERNAL_LLM_IMPLEMENTATION.md](INTERNAL_LLM_IMPLEMENTATION.md)** - Detailed implementation summary for chapter 0
- **[BUGFIX_EMBEDDING_INTERNAL_LLM.md](BUGFIX_EMBEDDING_INTERNAL_LLM.md)** - Bug fix documentation
- **[TROUBLESHOOTING_INTERNAL_LLM.md](TROUBLESHOOTING_INTERNAL_LLM.md)** - Debugging guide
- **[.env.example](.env.example)** - Configuration template

---

## Support & Troubleshooting

**If internal LLM isn't working:**

1. Check all 4 env vars are set: `docker exec <container> env | grep INTERNAL_LLM`
2. Check logs: `docker logs <container> 2>&1 | grep -i "internal"`
3. Verify no `/v1` in base URL
4. Test API endpoint manually: `scripts/test_openai_sdk_direct.py`
5. Review [TROUBLESHOOTING_INTERNAL_LLM.md](TROUBLESHOOTING_INTERNAL_LLM.md)

**If backward compatibility breaks:**

1. Run regression tests: `uv run pytest tests/`
2. Test with ONLY Azure config (no internal LLM vars)
3. Check priority logic in `_get_llm_instance()` - internal should be first
4. Verify no hardcoded provider assumptions in code

**For chapter-specific issues:**

- Chapter 2+: Check HPC gateway LLM configuration
- Chapter 3+: Check sandbox and multi-agent configs
- Chapter 4+: Verify Kubernetes ConfigMaps and Secrets
- Chapter 5+: Check OpenWebUI integration compatibility
