# LLM Configuration Tests

This directory contains smoke tests for the LLM configuration system, validating both traditional cloud provider patterns and the new internal LLM provider pattern.

## Test Coverage

### `test_llm_configuration.py`
Tests for `LLMAgnosticClient` (used by LiteLLM-based components):
- ✅ Initialization with default environment variables
- ✅ Internal LLM provider configuration (OpenAI-compatible format)
- ✅ Partial configuration handling
- ✅ Response generation with internal LLM provider
- ✅ Azure OpenAI integration
- ✅ Ollama integration
- ✅ Model override behavior
- ✅ Error handling
- ✅ Streaming responses
- ✅ Fallback to cloud providers

### `test_langchain_agent_llm_config.py`
Tests for `ScientificWorkflowAgent` (LangChain-based components):
- ✅ Azure OpenAI configuration
- ✅ Internal LLM provider configuration
- ✅ Ollama configuration
- ✅ LLM instance creation for each provider type
- ✅ Internal LLM precedence over other configs
- ✅ Full workflow initialization
- ✅ Multiple provider coexistence
- ✅ Environment variable compatibility

## Running the Tests

### Prerequisites
```bash
# Install test dependencies
cd /path/to/chapter-00-introduction
uv sync --dev
```

### Run All Tests
```bash
uv run pytest tests/
```

### Run Specific Test File
```bash
uv run pytest tests/test_llm_configuration.py
uv run pytest tests/test_langchain_agent_llm_config.py
```

### Run with Verbose Output
```bash
uv run pytest tests/ -v
```

### Run with Coverage
```bash
uv run pytest tests/ --cov=agentic_framework_pkg.core --cov=agentic_framework_pkg.scientific_workflow
```

## Configuration Patterns Tested

### Pattern 1: Internal LLM Provider (OpenAI-Compatible)
```bash
INTERNAL_LLM_API_KEY="your-api-key"
INTERNAL_LLM_BASE_URL="https://internal-llm.company.com/v1"
INTERNAL_LLM_MODEL="your-model-name"
INTERNAL_LLM_EMBEDDING_MODEL="your-embedding-model"
```

### Pattern 2: Azure OpenAI
```bash
AZURE_API_KEY="your-azure-key"
AZURE_API_BASE="https://your-resource.openai.azure.com/"
AZURE_API_VERSION="2023-05-15"
STREAMLIT_DEFAULT_MODEL="gpt-4"
```

### Pattern 3: Local Ollama
```bash
OLLAMA_API_BASE_URL="http://localhost:11434"
STREAMLIT_DEFAULT_MODEL="ollama/mistral"
```

### Pattern 4: Direct OpenAI
```bash
OPENAI_API_KEY="sk-your-key"
STREAMLIT_DEFAULT_MODEL="gpt-4-turbo"
```

## Test Environment Isolation

All tests use `patch.dict(os.environ, ...)` to ensure complete isolation between test cases. Each test starts with a clean environment and sets only the necessary variables for that specific scenario.

## Key Behaviors Validated

1. **Internal LLM Priority**: When internal LLM is fully configured, it takes precedence over other providers
2. **Fallback Logic**: System gracefully falls back to cloud providers when internal LLM is not configured
3. **Model Override**: Explicit model parameters override default configurations
4. **Error Handling**: Proper error messages when configurations are incomplete or invalid
5. **Backward Compatibility**: Existing cloud provider configurations continue to work unchanged
6. **Multi-Provider Coexistence**: Multiple provider configurations can exist simultaneously without conflict

## Adding New Tests

When adding support for new LLM providers or configuration patterns:

1. Add tests to verify initialization with the new configuration
2. Add tests for LLM instance creation
3. Add integration tests for full workflow
4. Ensure backward compatibility with existing patterns
5. Test error cases and edge conditions

## CI/CD Integration

These tests are designed to run in CI/CD pipelines without requiring actual API keys or LLM access. All external calls are mocked, making the tests fast and reliable for automated testing.
