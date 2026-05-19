# Chapter 02: HPC MCP Server and Chain-of-Thought

## Getting Started

To run this chapter, navigate to the current directory and execute the lifecycle script. This script will handle all the Docker services for you.

```bash
./start-chapter-resources.sh
```

---

This chapter enhances the ADEPT framework by introducing a dedicated MCP server for [High-Performance Computing (HPC)](#references) tasks and upgrading the agent to use [LangGraph](#references) for more sophisticated [Chain-of-Thought (CoT)](#references) reasoning.

## Key Additions

- **HPC MCP Server**: A new, separate `fastmcp` server is added to host computationally intensive tools like [Nextflow](#references) pipelines for [BLAST](#references) searches and video processing with [Whisper](#references). This separation of concerns prevents long-running tasks from blocking the main MCP server. The server is built with [FastAPI](#references) and run with [Uvicorn](#references).
- **LangGraph Integration**: The agent is upgraded from a simple agent to a more complex reasoning engine built with [LangGraph](#references) and [LangChain](#references). This allows for more explicit and controllable multi-step reasoning, which is a more advanced form of [Chain-of-Thought](#references). The agent can now create more complex plans and execute them.
- **Stateful Interactions**: The use of `mcp_session_id` is continued and becomes more important for tracking the state of these more complex, multi-step workflows. We use [ChromaDB](#references) for session state management.

## Technologies Used

This chapter utilizes several key technologies:

- **[FastAPI](#references)**: A modern, fast (high-performance) web framework for building APIs with Python.
- **[Uvicorn](#references)**: A lightning-fast ASGI server implementation, used to run FastAPI applications.
- **[LangGraph](#references)**: A library for building stateful, multi-actor applications with LLMs, built on top of LangChain.
- **[LangChain](#references)**: A framework for developing applications powered by language models.
- **[Nextflow](#references)**: A workflow system for creating scalable and reproducible scientific workflows.
- **[NCBI BLAST](#references)**: A program for comparing primary biological sequence information.
- **[OpenAI Whisper](#references)**: A general-purpose speech recognition model.
- **[yt-dlp](#references)**: A command-line program to download videos from YouTube and other video sites.
- **[LiteLLM](#references)**: A library to simplify LLM completion and embedding calls.
- **[ChromaDB](#references)**: An open-source embedding database.
- **[Pydantic](#references)**: A data validation and settings management library using Python type annotations.
- **[Docker](#references)**: A platform for developing, shipping, and running applications in containers.
- **[AlphaFold EBI](#references)**: A database of protein structure predictions.
- **[PubChemPy](#references)**: A Python wrapper for the PubChem PUG REST API.
- **[UniProt](#references)**: A comprehensive resource for protein sequence and annotation data.
- **[Biopython](#references)**: A set of freely available tools for biological computation written in Python.

## References

### How It Works: HPC and Advanced Reasoning

This chapter introduces two major advancements:

**Example User Query:** "Please transcribe the video at `https://www.youtube.com/watch?v=example` and give me the key takeaways."

1.  **HPC MCP Server**: A second, specialized MCP server is introduced to handle long-running, computationally intensive tasks. When the agent receives the user's query, it selects the `RunVideoTranscriptionPipelineHPC` tool. The request is routed to the dedicated HPC server, which then orchestrates a Nextflow pipeline to download, transcribe, and summarize the video, finally returning the summary to the user.

2.  **LangGraph for Chain-of-Thought (CoT)**: The agent's reasoning process is upgraded to use LangGraph. This allows the agent to create and execute complex, multi-step plans, giving it a more robust Chain-of-Thought capability. For example, if the user asked to first transcribe a video and then run a BLAST search on a sequence mentioned in the transcript, the agent would create a two-step plan and execute it in the correct order.

- [AlphaFold EBI](https://www.ebi.ac.uk/alphafold)
- [Biopython](https://biopython.org/)
- [Chain-of-Thought (CoT) Reasoning](https://www.promptingguide.ai/techniques/cot)
- [ChromaDB](https://docs.trychroma.com/)
- [Docker](https://docs.docker.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [High-Performance Computing (HPC)](https://www.hpc.llnl.gov/documentation/tutorials)
- [LangChain](https://www.langchain.com/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [LiteLLM](https://docs.litellm.ai/)
- [NCBI BLAST](https://blast.ncbi.nlm.nih.gov/Blast.cgi)
- [Nextflow](https://www.nextflow.io/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [PubChemPy](https://pubchempy.readthedocs.io/)
- [Pydantic](https://docs.pydantic.dev/)
- [Retrieval-Augmented Generation (RAG)](https://research.ibm.com/blog/retrieval-augmented-generation-RAG)
- [UniProt](https://www.uniprot.org/)
- [Uvicorn](https://www.uvicorn.org/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

## Additional Resources

### Tutorials and Courses

- **FastAPI:**
    - [Official Tutorial](https://fastapi.tiangolo.com/tutorial/)
    - [Full Stack Web Development with FastAPI and React](https://www.udemy.com/course/full-stack-web-development-with-fastapi-and-react/) (Udemy)
- **LangChain & LangGraph:**
    - [LangChain for LLM Application Development](https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/) (DeepLearning.AI)
    - [LangChain & Vector Databases in Generative AI](https://www.udemy.com/course/langchain-vector-databases-in-generative-ai-applications/) (Udemy)
    - [LangGraph Crash Course](https://www.youtube.com/watch?v=1Q_MDOWaljk) (YouTube)
- **Nextflow:**
    - [Nextflow Tutorial](https://www.nextflow.io/docs/latest/getstarted.html)
    - [Nextflow training](https://nf-co.re/training) (nf-core)
- **Docker:**
    - [Docker for Beginners](https://www.youtube.com/watch?v=3c-iBn73dDE) (YouTube)
    - [Docker and Kubernetes: The Complete Guide](https://www.udemy.com/course/docker-and-kubernetes-the-complete-guide/) (Udemy)

### Key Concepts Explained

- **Chain-of-Thought Reasoning:**
    - [Blog: A Gentle Introduction to Chain-of-Thought Prompting](https://www.promptingguide.ai/techniques/cot)
    - [Video: Chain-of-Thought Prompting Explained](https://www.youtube.com/watch?v=Kar2qfLDQ2c&t=45s)
- **High-Performance Computing (HPC):**
    - [Intel: What is High Performance Computing?](https://www.intel.com/content/www/us/en/high-performance-computing/what-is-hpc.html)
    - [Video: High Performance Computing Explained](https://www.youtube.com/watch?v=nIBu1EFYmBU)
- **Retrieval-Augmented Generation (RAG):**
    - [IBM Research: What is retrieval-augmented generation?](https://research.ibm.com/blog/retrieval-augmented-generation-RAG)
    - [Video: Retrieval Augmented Generation (RAG) Explained](https://www.youtube.com/watch?v=T-D1OfcDW1M)