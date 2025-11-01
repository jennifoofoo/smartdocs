# SmartDocs - Your Personal AI Document Assistant

> **Privacy-First Document Intelligence powered by Local AI**

SmartDocs is a powerful RAG (Retrieval Augmented Generation) system that helps you search, analyze, and extract insights from your personal documents - completely locally, with no cloud dependency.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![AI](https://img.shields.io/badge/AI-Local%20LLM-purple.svg)

---

## ✨ Features

### 🔍 **Intelligent Document Search**

- Semantic search across all your documents using state-of-the-art embeddings
- Find information by meaning, not just keywords
- Cross-document insights and connections

### 📄 **Multi-Format Support**

- **Documents:** PDF, DOCX, XLSX, PPTX
- **Emails:** EML, MSG (with attachment extraction)
- **Smart Parsing:** Preserves document structure and metadata

### 🤖 **Local AI Processing**

- Powered by Ollama - run models like Qwen, Gemma, Llama locally
- **100% Privacy:** Your documents never leave your machine
- No API keys, no cloud costs, no data sharing

### ⚡ **Advanced Retrieval**

- Vector similarity search with Milvus
- Re-ranking for improved accuracy
- Configurable chunk size and retrieval parameters

### 💬 **Beautiful Chat Interface**

- Interactive Q&A with your documents
- Source attribution - see exactly where answers come from
- Streaming responses for immediate feedback

---

## Quick Start

### Prerequisites

1. **Python 3.10+**
2. **Ollama** - [Install from ollama.ai](https://ollama.ai)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd smartdocs

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull an LLM model (choose one or both)
ollama pull qwen2:7b
ollama pull gemma:2b
```

### First Run

1. **Add your documents:**

   ```bash
   # Place your files in organized folders under data/
   mkdir -p data/my_documents
   # Copy your PDFs, Word docs, etc. into data/my_documents/
   ```

2. **Index your documents:**

   ```bash
   python VectorizeDocuments.py --clear-collection
   ```

3. **Start the application:**

   ```bash
   chainlit run app.py -w
   ```

4. **Open your browser:**
   - Navigate to `http://localhost:8000`
   - Start asking questions about your documents!

---

## 📖 Usage Examples

### Example Questions:

- _"What were the key points discussed in the Q2 meeting notes?"_
- _"Find all invoices from last month"_
- _"Summarize the contract terms from document X"_
- _"Who sent me emails about project deadlines?"_

### Customization:

In the web interface, you can adjust:

- **LLM Model:** Choose between different local models
- **Chunk Retrieval:** How many text sections to analyze (3-15)
- **Re-Ranking:** Enable for better accuracy (slower but more precise)
- **Source Display:** Show/hide document references

---

## Architecture

```
┌─────────────────┐
│  Your Documents │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│   Document Processor        │
│  • PDF, DOCX, XLSX, PPTX   │
│  • Email (EML, MSG)         │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Text Splitter             │
│  • Smart chunking           │
│  • Context preservation     │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Embedding Model           │
│  • sentence-transformers    │
│  • 384-dim vectors          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Milvus Vector Database    │
│  • COSINE similarity        │
│  • Metadata filtering       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Retrieval & Re-Ranking    │
│  • Top-K search             │
│  • Cross-encoder reranking  │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Local LLM (Ollama)        │
│  • Qwen2, Gemma, Llama      │
│  • Contextual generation    │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   Chainlit Interface        │
│  • Streaming chat           │
│  • Source attribution       │
└─────────────────────────────┘
```

---

## Project Structure

```
smartdocs/
├── app.py                      # Main Chainlit application
├── VectorizeDocuments.py       # Document indexing script
├── requirements.txt            # Python dependencies
├── chainlit.md                 # Welcome screen content
├── data/                       # Your documents go here
│   └── [your_folders]/
├── src/
│   ├── core/
│   │   ├── email_handler.py    # Email parsing logic
│   │   ├── file_handler.py     # Document parsing
│   │   ├── file_ingestion.py   # Document processing pipeline
│   │   ├── milvus_mgmt.py      # Vector database management
│   │   └── flow_manager.py     # Processing orchestration
│   ├── datatypes/
│   │   └── emails_types.py     # Email data structures
│   ├── utilities/
│   │   ├── chunk_embed.py      # Chunking & embedding logic
│   │   ├── app_config.py       # Configuration
│   │   ├── logger_config.py    # Logging setup
│   │   └── parser_tools.py     # Parsing utilities
│   └── api/                    # API endpoints (optional)
├── InspectChunks.py            # CLI helper to inspect chunks (optional)
├── QueryDataBase.py            # CLI helper for vector search (optional)
└── QueryDataBase_LLM.py        # CLI helper with LLM answer (optional)
```

---

## ⚙️ Configuration

### Environment Variables (optional)

Create a `.env` file:

```env
# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Milvus Configuration
MILVUS_EMBEDDED_MODE=true
COLLECTION_NAME=smartdocs_collection

# Data paths
DATA_PATH=./data
UPLOAD_FOLDER=./uploads
```

### Advanced Options

Edit `src/utilities/app_config.py` to customize:

- Chunk size and overlap
- Embedding model
- Search parameters
- Re-ranking settings

---

## 🧪 Testing

Automated tests are not currently included. Suggested next steps if you want to
extend SmartDocs:

- Add unit tests for ingestion and retrieval helpers using a lightweight Milvus mock
- Add integration tests that index a small sample set and validate retrieval

If you add tests, remember to wire them into your CI pipeline (e.g., GitHub Actions).

---

## 🐳 Docker (Coming Soon)

```bash
docker-compose up
```

---

## 🛠️ Tech Stack

| Component               | Technology                 |
| ----------------------- | -------------------------- |
| **Backend**             | Python 3.10+               |
| **Web Framework**       | FastAPI, Chainlit          |
| **Vector Database**     | Milvus Lite                |
| **Embeddings**          | sentence-transformers      |
| **LLM**                 | Ollama (local)             |
| **Document Processing** | Unstructured, LangChain    |
| **Email Parsing**       | extract_msg, email library |

---

## 📊 Performance

- **Indexing Speed:** ~100 pages/minute (depending on format)
- **Search Latency:** <100ms for vector search
- **Response Time:** 1-5s depending on LLM model and chunk count
- **Privacy:** 100% local - zero external API calls

---

## 🔐 Privacy & Security

✅ **All processing happens locally on your machine**  
✅ **No cloud services or external APIs**  
✅ **Your documents never leave your computer**  
✅ **No telemetry or tracking**

Perfect for:

- Legal documents
- Medical records
- Financial information
- Confidential business data
- Personal correspondence

---

## 🗺️ Roadmap

- [ ] Docker containerization
- [ ] Multi-language support
- [ ] Document comparison feature
- [ ] Export conversations to PDF
- [ ] Citation graph visualization
- [ ] Mobile-responsive UI
- [ ] Batch document upload via web UI
- [ ] Custom embedding model fine-tuning

---

## 🤝 Contributing

Contributions are welcome! Feel free to:

- Report bugs
- Suggest features
- Submit pull requests

---

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

Built with:

- [Ollama](https://ollama.ai) - Local LLM inference
- [Milvus](https://milvus.io) - Vector database
- [Chainlit](https://chainlit.io) - Chat interface
- [LangChain](https://langchain.com) - LLM orchestration
- [Sentence Transformers](https://www.sbert.net) - Embeddings

---
