# Chapter-01 Test Suite

This directory contains tests for the internal LLM provider integration in chapter-01.

## Test Files

### `test_internal_llm_config.py`
Tests for `ScientificWorkflowAgent` internal LLM configuration:
- ✅ Internal LLM is prioritized over Azure/OpenAI
- ✅ Reasoning models (o4-mini, o3-mini) get `max_tokens=4000`
- ✅ Non-reasoning models get `max_tokens=1000`
- ✅ Fallback to Azure/OpenAI when internal LLM not configured
- ✅ Incomplete internal config causes proper fallback

### `test_llm_agnostic_layer.py`
Tests for `LLMAgnosticClient` (LiteLLM integration):
- ✅ Internal LLM used for completion calls
- ✅ Internal LLM embedding model used for embeddings
- ✅ Model override for embedding purpose
- ✅ Fallback to Azure SDK when no internal LLM

## Running Tests

From the chapter-01 directory:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_internal_llm_config.py -v

# Run with output capture
uv run pytest tests/ -v -s
```

## Test Environment

Tests use `patch.dict(os.environ, ...)` to simulate different LLM configurations without modifying the actual .env file.

## Architecture Notes

Chapter-01 uses:
- **LiteLLM** abstraction layer via `LLMAgnosticClient`
- **LangChain** for agent orchestration via `ScientificWorkflowAgent`
- **Internal LLM priority**: Internal → Azure → OpenAI → Ollama

This differs from chapter-00 which uses direct LangChain providers without LiteLLM.
