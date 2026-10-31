import os
import shutil
import sys
import time
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from answerer import answer_question_with_details, REFUSAL, GENERATION_MODEL
from chunker import chunk_documents
from indexing import build_index
from loader import load_documents, SUPPORTED_EXTENSIONS
from retriever import retrieve_chunks, MODEL_NAME as EMBEDDING_MODEL
from vector_store import load_vector_store

app = FastAPI(
    title="Document Q&A Bot API",
    description="High-performance RAG API powered by Google Gemini and FAISS",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to answer using indexed documents")
    top_k: int = Field(5, ge=1, le=10, description="Number of context chunks to retrieve")
    model: Optional[str] = Field(None, description="Optional Gemini generation model override")


class DocumentSummary(BaseModel):
    filename: str
    size_bytes: int
    size_formatted: str
    extension: str
    last_modified: float
    page_count: Optional[int] = None


def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    elif size_in_bytes < 1024 * 1024:
        return f"{size_in_bytes / 1024:.1f} KB"
    else:
        return f"{size_in_bytes / (1024 * 1024):.1f} MB"


@app.get("/api/status")
def get_system_status():
    """Get system health, active models, vector index counts, and document stats."""
    store_dir = PROJECT_ROOT / "vector_store"
    vector_count = 0
    index_loaded = False
    last_indexed = None

    try:
        index, chunks = load_vector_store(store_dir)
        vector_count = index.ntotal
        index_loaded = True
        index_file = store_dir / "index.faiss"
        if index_file.exists():
            last_indexed = index_file.stat().st_mtime
    except Exception:
        index_loaded = False
        vector_count = 0

    data_dir = PROJECT_ROOT / "data"
    doc_files = []
    if data_dir.exists():
        doc_files = [
            f.name for f in data_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))

    return {
        "status": "healthy",
        "gemini_api_configured": api_key_configured,
        "embedding_model": os.getenv("GEMINI_EMBEDDING_MODEL", EMBEDDING_MODEL),
        "generation_model": os.getenv("GEMINI_GENERATION_MODEL", GENERATION_MODEL),
        "vector_store": {
            "loaded": index_loaded,
            "vector_count": vector_count,
            "index_type": "FAISS FlatIP (L2 Normalized Inner Product)",
            "last_indexed": last_indexed,
        },
        "knowledge_base": {
            "document_count": len(doc_files),
            "documents": sorted(doc_files),
        },
    }


@app.get("/api/documents")
def list_documents():
    """List all documents currently residing in the data directory."""
    data_dir = PROJECT_ROOT / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)

    documents = []
    for path in sorted(data_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            stat = path.stat()
            documents.append({
                "filename": path.name,
                "size_bytes": stat.st_size,
                "size_formatted": format_file_size(stat.st_size),
                "extension": path.suffix.lower(),
                "last_modified": stat.st_mtime,
            })

    return {"documents": documents, "count": len(documents)}


@app.post("/api/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload new documents into the data directory."""
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    uploaded = []
    skipped = []

    for file in files:
        file_path = data_dir / file.filename
        suffix = Path(file.filename).suffix.lower()

        if suffix not in SUPPORTED_EXTENSIONS:
            skipped.append({"filename": file.filename, "reason": f"Unsupported format: {suffix}"})
            continue

        try:
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded.append(file.filename)
        except Exception as e:
            skipped.append({"filename": file.filename, "reason": str(e)})

    return {
        "message": f"Successfully uploaded {len(uploaded)} document(s).",
        "uploaded": uploaded,
        "skipped": skipped,
        "note": "Click 'Rebuild Vector Index' to index newly uploaded files.",
    }


@app.delete("/api/documents/{filename}")
def delete_document(filename: str):
    """Delete a document from the data directory."""
    data_dir = PROJECT_ROOT / "data"
    file_path = data_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.unlink()
        return {"status": "success", "message": f"Deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete {filename}: {e}")


@app.get("/api/documents/{filename}/preview")
def preview_document(filename: str):
    """Preview extracted text for a specific document."""
    data_dir = PROJECT_ROOT / "data"
    file_path = data_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    suffix = file_path.suffix.lower()
    from loader import load_pdf, load_txt, load_docx, load_image

    records = []
    try:
        if suffix == ".pdf":
            records = load_pdf(file_path)
        elif suffix == ".txt":
            records = load_txt(file_path)
        elif suffix == ".docx":
            records = load_docx(file_path)
        elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            records = load_image(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load document: {e}")

    return {
        "filename": filename,
        "page_count": len(records),
        "pages": [
            {
                "page": r["metadata"].get("page"),
                "text": r["text"],
                "char_count": len(r["text"]),
            }
            for r in records[:15]  # Limit preview to 15 pages for safety
        ]
    }


@app.post("/api/indexing/rebuild")
def trigger_indexing():
    """Trigger vector index rebuild from data directory."""
    try:
        t0 = time.perf_counter()
        stats = build_index()
        duration_s = round(time.perf_counter() - t0, 2)
        stats["duration_seconds"] = duration_s
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


@app.post("/api/query")
def query_rag(payload: QueryRequest):
    """Query the RAG pipeline with a question and return grounded answer with source citations."""
    try:
        details = answer_question_with_details(
            question=payload.question,
            top_k=payload.top_k,
            generation_model=payload.model,
        )
        return details
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {e}")


@app.get("/api/chunks")
def list_chunks(search: Optional[str] = None, source: Optional[str] = None, limit: int = 50):
    """Inspect stored chunks in the vector store with optional filtering."""
    try:
        _, chunks = load_vector_store()
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Vector store not loaded: {e}")

    filtered = chunks
    if source:
        filtered = [c for c in filtered if c["metadata"].get("source") == source]
    if search:
        search_lower = search.lower()
        filtered = [c for c in filtered if search_lower in c["text"].lower()]

    return {
        "total_chunks": len(chunks),
        "matched_chunks": len(filtered),
        "chunks": filtered[:limit],
    }


# Mount frontend static files if production build exists
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    is_dev = os.getenv("ENVIRONMENT", "development").lower() == "development"
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=is_dev)
