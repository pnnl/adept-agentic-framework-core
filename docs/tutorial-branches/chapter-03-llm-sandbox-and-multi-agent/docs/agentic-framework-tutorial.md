# Agentic Framework Tutorial

Welcome to the Agentic Tool Framework tutorial! This guide will walk you through setting up your development environment, adding a new tool to the Model Context Protocol (MCP) server, and running an example scientific workflow.

## Part 1: Development Environment Setup

This section covers setting up your development environment on macOS and Windows.

### Prerequisites

Before you begin, ensure you have the following installed:

1.  **Git**: For version control.
2.  **Python**: Version 3.11 or higher.
3.  **Docker Desktop**: For containerizing and running the application.
4.  **Visual Studio Code (VS Code)**: Recommended code editor.

### macOS Setup

1.  **Homebrew**: If you don't have Homebrew, install it by running the command from [brew.sh](https://brew.sh/).
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2.  **Git**:
    ```bash
    brew install git
    ```

3.  **Python**: macOS comes with Python, but it's often older. Install Python 3.11+ via Homebrew:
    ```bash
    brew install python@3.11
    # Follow instructions from brew to add it to your PATH if needed
    ```
    Alternatively, download the official installer from [python.org](https://www.python.org/downloads/).

4.  **Docker Desktop**: Download and install Docker Desktop for Mac from the [Docker website](https://www.docker.com/products/docker-desktop/).

5.  **VS Code**: Download and install VS Code from [code.visualstudio.com](https://code.visualstudio.com/).
    *   **Recommended Extensions**:
        *   `Python` (Microsoft)
        *   `Docker` (Microsoft)

6.  **Terminal**:
    *   macOS has a built-in Terminal.
    *   iTerm2 is a popular alternative with more features.

### Windows Setup

1.  **Windows Subsystem for Linux (WSL)**: WSL allows you to run a Linux environment directly on Windows. This is highly recommended for a smoother development experience with Bash and Git.
    *   Open PowerShell as Administrator and run:
        ```powershell
        wsl --install
        ```
        This will install Ubuntu by default. Restart your computer when prompted.
    *   After restart, your Linux distribution will complete its installation.

2.  **Git**:
    *   **Inside WSL**: Once WSL is set up, open your Linux distribution (e.g., Ubuntu) and install Git:
        ```bash
        sudo apt update
        sudo apt install git
        ```
    *   **Git for Windows (Optional)**: You can also install Git for Windows, which provides Git Bash. However, using Git within WSL is often more seamless for projects developed with Linux in mind.

3.  **Python**:
    *   **Inside WSL**: Install Python 3.11+ in your WSL distribution:
        ```bash
        sudo apt update
        sudo apt install python3.11 python3.11-venv python3-pip
        ```
    *   **On Windows (Alternative)**: Download from python.org or install from the Microsoft Store. If you install Python on Windows directly, ensure it's added to your PATH.

4.  **Docker Desktop**: Download and install Docker Desktop for Windows from the Docker website.
    *   Ensure it's configured to use the **WSL 2 backend** for best performance. Docker Desktop usually prompts for this during installation or can be configured in its settings.

5.  **VS Code**: Download and install VS Code from code.visualstudio.com.
    *   **Recommended Extensions**:
        *   `Python` (Microsoft)
        *   `Docker` (Microsoft)
        *   `WSL` (Microsoft): Essential for working with projects inside WSL.

### Project Setup

1.  **Clone the Repository**:
    *   If using WSL, open your WSL terminal.
    *   Navigate to where you want to store the project (e.g., `cd ~`).
    *   Clone the repository:
        ```bash
        git clone https://github.com/pnnl/adept-agentic-framework-core.git
        cd adept-agentic-framework-core
        ```

2.  **Open in VS Code**:
    *   **If using WSL**: In your WSL terminal, inside the project directory, type:
        ```bash
        code .
        ```
        This will open the project in VS Code, connected to your WSL environment.
    *   **If not using WSL (macOS or Windows directly)**: Open VS Code and use "File > Open Folder..." to open the cloned project directory.

3.  **Set up `.env` file**:
    *   The project uses a `.env` file for environment variables.
    *   Copy the example environment file (if one exists, e.g., `.env.example`) to `.env`:
        ```bash
        cp .env.example .env
        ```
        If no example exists, create a new `.env` file in the project root.
    *   Edit the `.env` file and fill in necessary API keys and configurations:
        ```env
        # Example .env content
        # OpenAI API Key (if using OpenAI models directly)
        OPENAI_API_KEY="sk-..."

        # Azure OpenAI Credentials (if using Azure OpenAI)
        AZURE_API_KEY="..."
        AZURE_API_BASE="https://<your-azure-resource-name>.openai.azure.com/"
        AZURE_API_VERSION="2023-12-01-preview" # Or your API version
        LANGCHAIN_LLM_MODEL="<your-azure-deployment-name>" # For Langchain agent

        # NVIDIA API Key (for multi-modal document analysis)
        NVIDIA_API_KEY="nvapi-..."

        # Web Search (Tavily API Key)
        TAVILY_API_KEY="..."

        # MCP Server Configuration (defaults are usually fine for local Docker)
        # MCP_SERVER_HOST="0.0.0.0"
        # MCP_SERVER_PORT="8080"

        # Streamlit App Configuration
        # STREAMLIT_SERVER_PORT="8501"

        # Database path for ChromaDB (persistent storage)
        # Default is ./chroma_data relative to where the server runs (inside container: /app/chroma_data)
        # CHROMA_DB_PATH="/app/chroma_data" # Example for Docker
        # CHROMA_DB_PATH=":memory:" # For in-memory, non-persistent DB

        # Shared upload directory (must match volume mount in docker-compose.yml)
        # SHARED_UPLOAD_DIR="/app/shared_uploads" # Path inside container
        ```

4.  **Build and Run with Docker Compose (let's skip this for now)**:
    *   Ensure Docker Desktop is running.
    *   In your terminal (WSL terminal if using WSL), from the project root directory (where `docker-compose.yml` is located):
        ```bash
        docker compose up --build -d
        ```
        *   `--build`: Forces Docker to rebuild the images if Dockerfiles have changed.
        *   `-d`: Runs containers in detached mode (in the background).
    *   To view logs:
        ```bash
        docker compose logs -f # Follow logs for all services
        docker compose logs -f mcp_server # Follow logs for mcp_server
        docker compose logs -f streamlit_app # Follow logs for streamlit_app
        ```
    *   The Streamlit app should be accessible at `http://localhost:8501` (or the port configured for `streamlit_app`).
    *   The MCP server API (if you need to access it directly) will be at `http://localhost:8080` (or the port for `mcp_server`).

5.  **Python Environment Management (`uv`)**:
    *   This project uses `uv` for Python package management inside the Docker containers.
    *   Dependencies are defined in `pyproject.toml`.
    *   The Dockerfiles handle `uv venv` to create a virtual environment and `uv pip install` or `uv sync` to install dependencies. You generally don't need to interact with `uv` directly unless modifying dependencies or Dockerfiles.

6. **Testing within Python Environment**:
    *   Setup the `uv` environment
        * Open a new terminal within VS Code
        * Make sure that you have `python` and `pip` installed

            ```bash
            python --version
            pip --version
           ```
            
        * Setup the virtual environment within the root of the project
            ```bash
            pip install uv
            uv venv .venv
            ```

    *   Launch the MCP Server
        * Open a terminal window within VSCode (or navigate to the root of your checkout).
        * Make sure to enable the virtual environment:
            ```bash
            source .venv/bin/activate
            ```
        * Use `uv` to launch the MCP server application
            ```bash
            uv run run-mcp-server
            ```
    *   Launch the Streamlit UI App
        * Open a terminal window within VSCode (or navigate to the root of your checkout).
        * Make sure to enable the virtual environment:
            ```bash
            source .venv/bin/activate
            ```
        * Use `uv` to launch the MCP server application (if not already running)
            ```bash
            uv run run-streamlit-harness
            ```
        * Use this hack, in case a previous instance hasn't released a network socket yet:
            ```bash
            PYTHONPATH=src uv run streamlit run src/agentic_framework_pkg/streamlit_app/app.py
            ``` 
    *   On your desktop browser, navigate to the streamlit url, e.g., `http://localhost:8501`. The actual port will be noted in the terminal.

    * Here's a screenshot of the UI
        ![AgenticWorkflowScreenshot](images/screenshot.png)

## Part 2: Adding a New MCP Tool (PubChem Chemical Search)

This part demonstrates how to add a new tool that interacts with the PubChem PUG REST API to search for chemical compounds and retrieve their properties.

### Step 2.1: Understanding PubChem PUG REST API

PubChem provides a RESTful API called PUG REST for accessing its data. We'll use it for:
*   Searching compounds by name.
*   Retrieving compound properties by their CID (Compound ID).

Refer to the PubChem PUG REST Tutorial for details.

### Step 2.2: Create the Tool File

1.  Create a new Python file: `agentic_framework/src/agentic_framework_pkg/mcp_server/tools/pubchem_tool.py`.
2.  Add the following content to `pubchem_tool.py`:

    ```python
    from fastmcp import FastMCP, Context
    from ...logger_config import get_logger
    import httpx
    import asyncio
    from typing import Dict, Any, List, Optional

    # Use the centralized logger
    logger = get_logger(__name__)

    # PubChem API base URL
    PUBCHEM_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    # Helper for session ID (can be adapted from other tool files or a common utility)
    # For PubChem, session state on MCP server might not be strictly necessary for basic queries.
    # from .general_tools import ensure_session_initialized # If you need session state

    def register_tools(mcp: FastMCP):

        @mcp.tool()
        async def search_pubchem_by_name(ctx: Context, chemical_name: str, max_results: int = 5, mcp_session_id: Optional[str] = None) -> Dict[str, Any]:
            """
            Searches PubChem for compounds by chemical name.

            Args:
                chemical_name (str): The name of the chemical to search for (e.g., "aspirin", "glucose").
                max_results (int): Maximum number of results to return. Defaults to 5.
                ctx (Context): The FastMCP context object.
                mcp_session_id (str, optional): The MCP session ID.

            Returns:
                Dict[str, Any]: A dictionary containing a list of matching compound CIDs and their synonyms, or an error.
            """
            # session_id = await ensure_session_initialized(ctx) # If session state is needed
            await ctx.info(f"Searching PubChem for chemical name: '{chemical_name}', max_results: {max_results}")

            request_url = f"{PUBCHEM_BASE_URL}/compound/name/{chemical_name}/cids/JSON?list_return=listkey&listkey_count={max_results}"

            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Step 1: Get the list key for results
                    response_listkey = await client.get(request_url)
                    response_listkey.raise_for_status()
                    listkey_data = response_listkey.json()

                    if "IdentifierList" not in listkey_data or not listkey_data["IdentifierList"]["CID"]:
                        await ctx.info(f"No CIDs found for '{chemical_name}'.")
                        return {"query": chemical_name, "results": [], "message": "No compounds found for the given name."}

                    list_key = listkey_data["IdentifierList"]["listkey"]
                    cids = listkey_data["IdentifierList"]["CID"][:max_results] # Ensure we respect max_results

                    await ctx.info(f"Found {len(cids)} CIDs. Fetching synonyms for listkey: {list_key}")

                    # Step 2: Get synonyms for the found CIDs using the list key
                    # We'll fetch synonyms to give more context than just CIDs
                    synonyms_url = f"{PUBCHEM_BASE_URL}/compound/listkey/{list_key}/synonyms/JSON"
                    response_synonyms = await client.get(synonyms_url)
                    # It's possible this request might need to wait if the listkey isn't immediately ready.
                    # For simplicity, we assume it's ready. A robust implementation might poll.
                    if response_synonyms.status_code == 202: # Accepted, processing
                        await ctx.info("PubChem is processing the synonym request. Waiting briefly...")
                        await asyncio.sleep(5) # Simple wait
                        response_synonyms = await client.get(synonyms_url) # Retry

                    response_synonyms.raise_for_status()
                    synonyms_data = response_synonyms.json()

                    results = []
                    if "InformationList" in synonyms_data and "Information" in synonyms_data["InformationList"]:
                        for info in synonyms_data["InformationList"]["Information"]:
                            cid = info.get("CID")
                            syns = info.get("Synonym", [])[:5] # Get first 5 synonyms
                            if cid in cids: # Ensure we only process CIDs from our initial limited list
                                results.append({"cid": cid, "synonyms": syns})

                    return {"query": chemical_name, "results": results}

            except httpx.HTTPStatusError as e:
                err_msg = f"PubChem API request failed for '{chemical_name}' with status {e.response.status_code}. Response: {e.response.text[:200]}"
                logger.error(err_msg, exc_info=True)
                await ctx.error(f"PubChem API error: {e.response.status_code}")
                return {"error": "Failed to fetch data from PubChem.", "details": err_msg}
            except Exception as e:
                err_msg = f"An unexpected error occurred during PubChem search for '{chemical_name}': {e}"
                logger.error(err_msg, exc_info=True)
                await ctx.error("PubChem search failed.")
                return {"error": "An unexpected error occurred during PubChem search.", "details": str(e)}

        @mcp.tool()
        async def get_pubchem_compound_properties(ctx: Context, cid: int, properties: Optional[List[str]] = None, mcp_session_id: Optional[str] = None) -> Dict[str, Any]:
            """
            Retrieves specified properties for a given PubChem Compound ID (CID).

            Args:
                cid (int): The PubChem Compound ID (e.g., 2244 for aspirin).
                properties (List[str], optional): A list of properties to retrieve (e.g., ["MolecularFormula", "MolecularWeight", "InChIKey"]).
                                                  Defaults to a basic set if None.
                ctx (Context): The FastMCP context object.
                mcp_session_id (str, optional): The MCP session ID.

            Returns:
                Dict[str, Any]: A dictionary containing the compound's properties or an error.
            """
            await ctx.info(f"Fetching properties for PubChem CID: {cid}")

            if properties is None:
                properties = ["MolecularFormula", "MolecularWeight", "CanonicalSMILES", "InChIKey", "Title"]

            properties_str = ",".join(properties)
            request_url = f"{PUBCHEM_BASE_URL}/compound/cid/{cid}/property/{properties_str}/JSON"

            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    response = await client.get(request_url)
                    response.raise_for_status()
                    data = response.json()

                    if "PropertyTable" in data and "Properties" in data["PropertyTable"] and data["PropertyTable"]["Properties"]:
                        # The result is a list with one element for the compound
                        compound_props = data["PropertyTable"]["Properties"][0]
                        # Remove CID from props as it's already an input
                        compound_props.pop("CID", None)
                        return {"cid": cid, "properties": compound_props}
                    else:
                        await ctx.warning(f"No properties found or unexpected format for CID {cid}.")
                        return {"cid": cid, "properties": {}, "message": "No properties found or unexpected format."}

            except httpx.HTTPStatusError as e:
                err_msg = f"PubChem API property request failed for CID {cid} with status {e.response.status_code}. Response: {e.response.text[:200]}"
                logger.error(err_msg, exc_info=True)
                await ctx.error(f"PubChem API error: {e.response.status_code}")
                return {"error": f"Failed to fetch properties for CID {cid} from PubChem.", "details": err_msg}
            except Exception as e:
                err_msg = f"An unexpected error occurred fetching properties for CID {cid}: {e}"
                logger.error(err_msg, exc_info=True)
                await ctx.error("PubChem property retrieval failed.")
                return {"error": f"An unexpected error occurred for CID {cid}.", "details": str(e)}

        logger.info("PubChem MCP tools registered.")
    ```

### Step 2.3: Register the Tool in MCP Server

Modify `agentic_framework/src/agentic_framework_pkg/mcp_server/main.py`:
```diff
--- a/agentic_framework/src/agentic_framework_pkg/mcp_server/main.py
++++ b/agentic_framework/src/agentic_framework_pkg/mcp_server/main.py
@@ -8,7 +8,7 @@
 
 from .server import mcp
 from .state_manager import initialize_db 
-from .tools import general_tools, csv_rag_tool, uniprot_tool, websearch_tool, blast_tool # Added blast_tool
+from .tools import general_tools, csv_rag_tool, uniprot_tool, websearch_tool, blast_tool, pubchem_tool # Added pubchem_tool
 from ..core.llm_agnostic_layer import LLMAgnosticClient 
 from ..logger_config import get_logger # Use centralized logger
 
@@ -26,6 +26,7 @@
     csv_rag_tool.register_tools(mcp, llm_agnostic_client_instance) # Pass mcp and llm client
     uniprot_tool.register_tools(mcp) # Register UniProt tool
     websearch_tool.register_tools(mcp) # Register WebSearch tool
+    pubchem_tool.register_tools(mcp) # Register PubChem tool
     blast_tool.register_tools(mcp) # Register BLAST tool
     # Register other tool modules here as they are created
     logger.info("MCP tools registered.")

```

### Step 2.4: Create Langchain Wrappers

Modify `agentic_framework/src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py`:

```diff
--- a/agentic_framework/src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py
++++ b/agentic_framework/src/agentic_framework_pkg/scientific_workflow/mcp_langchain_tools.py
@@ -163,6 +163,17 @@
     hitlist_size: int = Field(10, description="The maximum number of hits to return. Defaults to 10.")
     mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")
 
+class SearchPubChemByNameInput(BaseModel):
+    chemical_name: str = Field(description="The name of the chemical to search for (e.g., 'aspirin', 'glucose').")
+    max_results: int = Field(5, description="Maximum number of results to return. Defaults to 5.")
+    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")
+
+class GetPubChemCompoundPropertiesInput(BaseModel):
+    cid: int = Field(description="The PubChem Compound ID (e.g., 2244 for aspirin).")
+    properties: Optional[List[str]] = Field(None, description="A list of properties to retrieve (e.g., ['MolecularFormula', 'MolecularWeight']). Defaults to a basic set if None.")
+    mcp_session_id: Optional[str] = Field(None, description="The MCP session ID.")
+
 
 # --- Factory functions to create Langchain tool instances ---
 def get_mcp_query_csv_tool_langchain(mcp_session_id: Optional[str] = None):
@@ -230,5 +241,25 @@
         mcp_session_id=mcp_session_id
     )
 
+def get_mcp_search_pubchem_by_name_tool_langchain(mcp_session_id: Optional[str] = None):
+    return MCPToolWrapper(
+        name="SearchPubChemByName",
+        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
+        actual_tool_name="search_pubchem_by_name",
+        description="Searches PubChem for compounds by chemical name and returns a list of matching CIDs and synonyms.",
+        args_schema=SearchPubChemByNameInput,
+        mcp_session_id=mcp_session_id
+    )
+
+def get_mcp_get_pubchem_compound_properties_tool_langchain(mcp_session_id: Optional[str] = None):
+    return MCPToolWrapper(
+        name="GetPubChemCompoundProperties",
+        mcp_client_url=MCP_SERVER_URL_FOR_LANGCHAIN,
+        actual_tool_name="get_pubchem_compound_properties",
+        description="Retrieves specified properties for a given PubChem Compound ID (CID).",
+        args_schema=GetPubChemCompoundPropertiesInput,
+        mcp_session_id=mcp_session_id
+    )
+
 # Add more Langchain tool wrappers for other MCP tools as needed.

```

### Step 2.5: Add Tool to Langchain Agent

Modify `agentic_framework/src/agentic_framework_pkg/scientific_workflow/langchain_agent.py`:

```diff
--- a/agentic_framework/src/agentic_framework_pkg/scientific_workflow/langchain_agent.py
++++ b/agentic_framework/src/agentic_framework_pkg/scientific_workflow/langchain_agent.py
@@ -12,7 +12,9 @@
     get_mcp_query_uniprot_tool_langchain,
     get_mcp_web_search_tool_langchain,
     get_mcp_blastp_tool_langchain, # Import BLASTP tool
-    get_mcp_blastn_tool_langchain  # Import BLASTN tool
+    get_mcp_blastn_tool_langchain,  # Import BLASTN tool
+    get_mcp_search_pubchem_by_name_tool_langchain, # Import PubChem search tool
+    get_mcp_get_pubchem_compound_properties_tool_langchain # Import PubChem properties tool
 )
 from ..logger_config import get_logger # Use centralized logger
 
@@ -79,7 +81,9 @@
             get_mcp_query_uniprot_tool_langchain(mcp_session_id=agent_session_id),
             get_mcp_web_search_tool_langchain(mcp_session_id=agent_session_id),
             get_mcp_blastp_tool_langchain(mcp_session_id=agent_session_id),
-            get_mcp_blastn_tool_langchain(mcp_session_id=agent_session_id)
+            get_mcp_blastn_tool_langchain(mcp_session_id=agent_session_id),
+            get_mcp_search_pubchem_by_name_tool_langchain(mcp_session_id=agent_session_id),
+            get_mcp_get_pubchem_compound_properties_tool_langchain(mcp_session_id=agent_session_id)
             # Add more wrapped MCP tools here
         ]
 
@@ -94,7 +98,8 @@
         system_prompt_message = (
             "You are a helpful scientific workflow assistant. "
             "You have access to several tools to help answer user queries and perform tasks. "
-            "These tools allow you to perform calculations, manage notes, search the web, query UniProt, "
+            "These tools allow you to perform calculations, manage notes, search the web, query UniProt, search PubChem for chemical compounds and their properties, "
             "perform protein (BLASTP) and nucleotide (BLASTN) sequence searches, "
             "and retrieve information from uploaded documents such as CSVs, PDFs, Word documents, and even images, once they are processed and have a file_id. "
             "When you use a tool that requires a session context (like storing notes or querying user-specific CSV data), "

```

### Step 2.6: Testing the New Tool

1.  **Rebuild Docker Images**:
    ```bash
    docker compose up --build -d
    ```
2.  **Test**:
    *   Open the Streamlit UI (`http://localhost:8501`).
    *   You can try calling the `search_pubchem_by_name` tool directly from the "MCP Tool Invocation" section if you've updated the mock tool list in `app.py` (or wait for dynamic tool listing if implemented).
    *   Alternatively, ask the Langchain agent to use it: "Search PubChem for aspirin."

## Part 3: Example Science Workflow

This workflow demonstrates a multi-step process involving document RAG, sequence analysis, and chemical search.

### Step 3.1: Scenario Overview

1.  Download a PDF related to cancer genomics (e.g., from PubMed Central).
2.  Upload the PDF to the system for RAG processing.
3.  Extract a protein sequence or name relevant to the study from the PDF using a RAG query.
4.  Perform a BLASTP search using the extracted protein sequence.
5.  Search for potential therapeutic compounds related to the protein or cancer type using the new PubChem tool.

### Step 3.2: Downloading a PDF

1.  Go to PubMed Central.
2.  Search for a relevant open-access article. For example, search for "cancer genomics KRAS protein".
3.  Download the PDF of an article. Let's assume you download a PDF named `cancer_study.pdf`.

*(For this tutorial, we assume manual download. The agent could use the `PerformWebSearch` tool to find links, but actual download and upload is manual via the UI).*

### Step 3.3: Uploading PDF for RAG

1.  Open the Streamlit UI (`http://localhost:8501`).
2.  In the sidebar, find the "document RAG Tool Test" expander.
3.  Click "Browse files" and upload your `cancer_study.pdf`.
4.  Click "Process Uploaded document for RAG".
5.  Wait for the processing to complete. The UI should display a "document Registration Result" with a `file_id`. Note this `file_id` (e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

### Step 3.4: Extracting Protein Information via RAG

1.  In the main chat interface of the Streamlit UI, ask the Langchain agent:
    ```
    Using the document with file_id "YOUR_FILE_ID_HERE", can you find mentions of a specific protein and its sequence, or a key protein involved in the study? For example, look for KRAS.
    ```
    (Replace `YOUR_FILE_ID_HERE` with the actual `file_id` you obtained).
2.  The agent should use the `QueryProcessedDocumentData` tool.
3.  Let's assume the agent extracts information about the KRAS protein, and perhaps a partial or full sequence if available in the text. If a full sequence isn't directly in the text, it might identify "KRAS protein".

### Step 3.5: Performing BLASTP Search

1.  Based on the agent's previous response:
    *   If a sequence was found:
        ```
        Perform a BLASTP search for the protein sequence: [PASTE_EXTRACTED_SEQUENCE_HERE].
        ```
    *   If only a protein name (e.g., "KRAS") was found, you might first query UniProt:
        ```
        Query UniProt for the human KRAS protein to get its sequence.
        ```
        Then, once the agent provides the sequence from UniProt:
        ```
        Perform a BLASTP search for the protein sequence: [PASTE_KRAS_SEQUENCE_FROM_UNIPROT].
        ```
2.  The agent will use the `PerformProteinBlastSearch` tool. Analyze the results for similar proteins.

### Step 3.6: Performing Chemical Search for Therapeutics

1.  Based on the context (e.g., KRAS protein, the type of cancer discussed in the PDF):
    ```
    Search PubChem for compounds that might be investigated as therapeutics targeting the KRAS protein or related pathways in [type of cancer mentioned, e.g., pancreatic cancer].
    ```
2.  The agent should use the `SearchPubChemByName` tool. It might search for "KRAS inhibitors" or similar terms.
3.  Review the list of CIDs returned. If the agent provides CIDs, you can ask for more details:
    ```
    Get the properties (like MolecularFormula, MolecularWeight, InChIKey) for PubChem CID [A_CID_FROM_PREVIOUS_STEP].
    ```
4.  The agent will use the `GetPubChemCompoundProperties` tool.

This workflow demonstrates how different tools can be chained together by the agent to answer complex scientific queries.

## Conclusion

This tutorial covered setting up your development environment, the process of adding a new custom tool (PubChem search) to the MCP server and Langchain agent, and an example of a multi-step scientific workflow. You can extend this framework by adding more tools and refining the agent's capabilities. Remember to consult the documentation for the specific APIs you intend to integrate.

Happy coding!
