"""
VECTOR MEMORY INTEGRATION SKILL
Purpose: To move beyond simple text logs to a queryable long-term memory (LTM) using a local ChromaDB.
This allows agents (like OpenClaw) to retrieve semantically relevant context before passing a task to Hermes or making a decision.

Action: Indexes the repo's Markdown files and key terminal logs into a local ChromaDB instance.
Provides a `query_memory(query: str, min_relevance: float = None)` function to retrieve relevant context.
"""
import os
import sys
import subprocess
from pathlib import Path

# --- Configuration ---
PROJECT_ROOT = Path("/home/ubuntu/human-ai")
VECTOR_DB_PATH = PROJECT_ROOT / ".vector_db"
COLLECTION_NAME = "swarm_memory"
# Files to index for long-term memory
FILES_TO_INDEX = [
    "ROADMAP.md",
    "MEMORY.md",
    "development_log.md",
    "decision_log.md",
    # Key logs for context
    "hermes-autonomous.log",
    "openclaw_auto_loop.log",
    "master_log.json"
]

# Default relevance threshold for query results (ChromaDB L2 distance: lower = more similar)
# A value of 1.5 is a reasonable starting point for filtering out weak matches.
DEFAULT_MIN_RELEVANCE = 1.5

def _check_and_install_chromadb():
    """Checks if chromadb is installed and installs it if not."""
    try:
        import chromadb
    except ImportError:
        print("[VECTOR MEMORY] Installing chromadb...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "chromadb"])
        print("[VECTOR MEMORY] ChromaDB installed.")

def _get_or_create_collection():
    """Initializes the ChromaDB client and gets or creates the collection."""
    _check_and_install_chromadb()
    import chromadb
    from chromadb.utils import embedding_functions

    # Ensure the DB directory exists
    VECTOR_DB_PATH.mkdir(exist_ok=True)

    # Use the default embedding function (SentenceTransformer)
    embedding_func = embedding_functions.DefaultEmbeddingFunction()

    # Initialize persistent client
    client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))

    # Get or create collection
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
    except Exception:
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_func
        )
    return collection

def _index_file_to_vector_db(file_path: Path, collection):
    """Reads a file and adds its content to the vector DB as a document."""
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        if not content.strip():
            return  # Skip empty files
        # Use the file path as the unique ID
        doc_id = str(file_path.relative_to(PROJECT_ROOT))
        # Add or update the document
        collection.upsert(
            documents=[content],
            ids=[doc_id]
        )
    except Exception as e:
        print(f"[VECTOR MEMORY ERROR] Failed to index {file_path.name}: {e}")

def build_memory_index():
    """Scans the repo and builds/updates the vector memory index."""
    print("[VECTOR MEMORY] Building vector memory index...")
    collection = _get_or_create_collection()
    for file_name in FILES_TO_INDEX:
        file_path = PROJECT_ROOT / file_name
        if file_path.exists():
            _index_file_to_vector_db(file_path, collection)
        else:
            print(f"[VECTOR MEMORY WARNING] File not found for indexing: {file_name}")
    print(f"[VECTOR MEMORY] Index build complete. Collection '{COLLECTION_NAME}' has {collection.count()} documents.")

def query_memory(query: str, min_relevance: float = DEFAULT_MIN_RELEVANCE) -> list:
    """
    Queries the vector memory for context relevant to the input query.
    Returns a list of the most relevant text snippets that meet the minimum relevance threshold.
    Args:
        query (str): The query string to search for.
        min_relevance (float, optional): The maximum distance (lower is more similar) for a result to be included.
                                         Defaults to 1.5 (ChromaDB L2 distance).
    Returns:
        list: A list of relevant text snippets (empty list if no results meet the threshold).
    """
    try:
        collection = _get_or_create_collection()
        results = collection.query(
            query_texts=[query],
            n_results=10  # Fetch more candidates to filter down from
        )
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        
        # Filter results by the minimum relevance threshold (lower distance = more similar)
        filtered_documents = [
            doc for doc, dist in zip(documents, distances)
            if dist <= min_relevance
        ]
        return filtered_documents
    except Exception as e:
        print(f"[VECTOR MEMORY ERROR] Query failed: {e}")
        return []

# --- Example Usage (for testing) ---
if __name__ == "__main__":
    print("[VECTOR MEMORY] Testing skill...")
    build_memory_index()
    test_query = "What is the current goal of the Researcher agent?"
    results = query_memory(test_query)
    print(f"\nQuery: '{test_query}'")
    print(f"Results with relevance <= {DEFAULT_MIN_RELEVANCE}:")
    if results:
        for i, res in enumerate(results, 1):
            print(f"  {i}. {res[:150]}...")
    else:
        print("  No results met the relevance threshold.")
    print(f"\nVector DB is ready at: {VECTOR_DB_PATH}")