import os
import shutil
import tempfile
import zipfile
import chromadb
import requests

CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def ollama_is_online() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)


def index_repository_from_zip(zip_file_bytes) -> int:
    """User ke upload kiye hue ZIP folder ko parse karke ChromaDB me store karta hai."""
    client = get_chroma_client()
    try:
        client.delete_collection("repo_context")
    except Exception:
        pass

    chroma_collection = client.get_or_create_collection(
        name="repo_context",
        metadata={"hnsw:space": "cosine"}
    )

    documents_text = []
    metadatas = []
    ids = []

    allowed_extensions = {".py", ".js", ".ts", ".cpp", ".c", ".java", ".json", ".md"}

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, "repo.zip")
        with open(zip_path, "wb") as f:
            f.write(zip_file_bytes)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        doc_idx = 0
        for root, _, files in os.walk(temp_dir):
            if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv", ".idea"]):
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_extensions:
                    file_full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_full_path, temp_dir)
                    try:
                        with open(file_full_path, "r", encoding="utf-8", errors="ignore") as code_f:
                            content = code_f.read().strip()
                            if content:
                                # Chunks of 1200 characters to keep search fast and accurate
                                chunk_size = 1200
                                for c_idx in range(0, len(content), chunk_size):
                                    chunk = content[c_idx:c_idx + chunk_size]
                                    documents_text.append(chunk)
                                    metadatas.append({
                                        "file_path": rel_path,
                                        "file_name": file,
                                        "chunk_id": doc_idx
                                    })
                                    ids.append(f"doc_{doc_idx}")
                                    doc_idx += 1
                    except Exception:
                        pass

    if documents_text:
        # Batch insert into ChromaDB (uses local fast built-in ONNX embeddings safely)
        batch_size = 100
        for i in range(0, len(documents_text), batch_size):
            chroma_collection.add(
                documents=documents_text[i:i + batch_size],
                metadatas=metadatas[i:i + batch_size],
                ids=ids[i:i + batch_size]
            )

    return len(metadatas)


def query_repository_context(query_code: str, top_k: int = 3) -> str:
    """Code me use hone wale functions aur classes ka context repo se retrieve karta hai."""
    try:
        client = get_chroma_client()
        collection = client.get_collection("repo_context")
        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[query_code[:1000]],
            n_results=min(top_k, collection.count())
        )

        retrieved_chunks = []
        if results and "documents" in results and results["documents"]:
            for i, doc_list in enumerate(results["documents"]):
                for j, doc_text in enumerate(doc_list):
                    meta = results["metadatas"][i][j] if "metadatas" in results else {}
                    file_name = meta.get("file_path", "unknown")
                    retrieved_chunks.append(f"--- Context from {file_name} ---\n{doc_text}")

        return "\n\n".join(retrieved_chunks)
    except Exception:
        return ""