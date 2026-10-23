# Basic Document Q&A Bot Using RAG

A Retrieval-Augmented Generation (RAG) application that answers questions using information retrieved from user-provided documents. Answers are generated using Google Gemini and include source citations when supported by the retrieved context.

## Features

- Load PDF, TXT, and DOCX documents.
- Extract text from scanned PDFs using OCR.
- Split text into overlapping chunks.
- Generate embeddings in batches using Google's Gemini embedding model.
- Store and search embeddings using FAISS.
- Generate context-grounded answers using Gemini.
- Display source filenames, page numbers, similarity scores, and retrieved text.
- Refuse to answer when the retrieved context does not contain enough information.

## Technology Stack

- Python 3.12
- Google Gemini API
- FAISS for vector similarity search
- PyMuPDF for PDF extraction
- python-docx for DOCX extraction
- Tesseract OCR and pytesseract for scanned documents
- python-dotenv for environment configuration
- unittest for automated tests

## Architecture

1. **Document loading:** Extract text and metadata from supported documents.
2. **Chunking:** Split extracted text into chunks of approximately 500 characters with 100 characters of overlap.
3. **Embedding:** Generate document embeddings in batches using `gemini-embedding-001`.
4. **Indexing:** Normalize embeddings and store them in a persistent FAISS index.
5. **Retrieval:** Embed the user's question and retrieve the most similar chunks.
6. **Answer generation:** Send the retrieved context and question to Gemini. Ask the model to answer only from the provided context and include source citations.
7. **CLI output:** Display the answer and retrieved source chunks.

## Project Structure

```text
document-qa-bot/
├── data/                 # Local documents; use only safe sample documents for GitHub
├── src/
│   ├── loader.py
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── indexing.py
│   ├── retriever.py
│   ├── retriever_cli.py
│   ├── answerer.py
│   ├── test_qa.py
│   └── pipeline_test.py
├── tests/
├── vector_store/         # Generated locally; not committed
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Setup

### 1. Prerequisites

Install Python 3.12 and Tesseract OCR if you need scanned-document OCR.

On macOS, install Tesseract with:

```bash
brew install tesseract
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure the API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_GENERATION_MODEL=gemini-2.5-flash
```

Never commit `.env` or expose your API key. The generation model can be changed using `GEMINI_GENERATION_MODEL`.

## Add Documents

Place supported documents in the local `data/` directory. For a public repository, use public or synthetic sample documents rather than personal or confidential records.

Supported formats include PDF, TXT, DOCX, and supported image formats for OCR.

## Build the Index

From the `src/` directory, run:

```bash
python indexing.py
```

This loads the documents, creates chunks, generates embeddings, and saves the FAISS index and chunk metadata in `vector_store/`.

Rebuild the index after changing the source documents.

## Ask Questions

### Option A: Modern Web Interface (Recommended for HR Presentation)

Start the unified FastAPI backend & web application from the project root:

```bash
uvicorn src.server:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to:

```text
http://localhost:8000
```

The web application provides:
- **Interactive RAG Chatbot:** Ask questions with verified citations, telemetry latency stats, and strict refusal triggers.
- **RAG Architecture Flowchart:** Step-by-step interactive visualizer detailing the document parsing, chunking, FAISS search, and generation pipeline.
- **Knowledge Base Explorer:** Drag-and-drop document uploader (PDF, TXT, DOCX, OCR images), preview extracted text, and trigger 1-click index rebuilds.
- **Vector Chunks Inspector:** Search and browse through all indexed chunks and metadata.
- **RAG Tuner:** Adjust Top-K retrieval depth, generation model, and explore grounding guardrails.

To run the frontend in Vite development mode with hot-reloading:

```bash
cd frontend
npm install
npm run dev
```

### Option B: Interactive CLI

Run the interactive command-line interface:

```bash
python src/qa_cli.py
```

Enter a question when prompted. The application displays the generated answer, page citations, similarity scores, and retrieved source chunks. Enter `exit` or `quit` to stop.

## Run Automated Tests

From the project root, run:

```bash
python -m unittest discover -s tests -v
```

The test suite checks document loading, boundary-aware chunking, vector retrieval, FAISS vector-store persistence, and anti-hallucination answer-generation behavior.


Use questions that are answerable from the sample documents, such as:

1. What skills are mentioned in the resume?
2. What education details appear in the document?
3. What responsibilities are listed in the sample experience document?
4. What information does the second sample document provide about its topic?
5. What is the capital of Mars?

The final question is intentionally unanswerable and should trigger the application's refusal response.

## Design Decisions

- **Chunking:** Approximately 500 characters per chunk with 100 characters of overlap to preserve context between adjacent chunks.
- **Embeddings:** `gemini-embedding-001` converts document chunks and user questions into vector representations.
- **Vector store:** FAISS provides local, persistent similarity search without requiring a separate database server.
- **Similarity:** L2-normalized vectors with inner-product search approximate cosine similarity.
- **Batching:** Document embeddings are generated in batches to reduce per-request overhead.
- **Grounding:** The language model receives retrieved context and is instructed not to use unsupported outside information.
- **Citations:** Source filename and page number are included when available.

## Limitations

- Answer quality depends on document extraction, chunk boundaries, retrieval quality, and model behavior.
- OCR can introduce errors in scanned documents.
- Source citations are model-generated and should be checked against the displayed retrieved chunks.
- The application requires a valid Gemini API key and network access for embedding and generation.
- Similarity scores are retrieval signals, not guaranteed measures of factual correctness.
- The current implementation is a local CLI prototype, not a production web service.

## Security

- Keep `.env`, personal documents, and generated indexes out of public Git commits.
- Never publish identity documents, marksheets, resumes containing private information, or confidential business files without authorization.
- Do not commit API keys or other credentials.

## Future Improvements

- Add retrieval confidence thresholds and stronger citation validation.
- Support more document formats and richer metadata.
- Add configurable chunk sizes and top-k retrieval.
- Build a web interface and evaluate retrieval quality on a curated question-answer dataset.

## License

Add an appropriate license before distributing the project publicly.

