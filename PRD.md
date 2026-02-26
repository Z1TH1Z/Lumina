# AI Financial Copilot (Open-Source Edition)
## Product Requirements Document (PRD)

---

# 1. Executive Summary

## 1.1 Vision

Develop a fully open-source AI Financial Copilot that:

- Ingests heterogeneous financial documents
- Automatically categorizes transactions
- Detects anomalies using hybrid ML systems
- Forecasts savings rates using time-series models
- Provides financial optimization strategies
- Answers financial queries using Retrieval-Augmented Generation (RAG)
- Executes deterministic financial calculations via secure sandboxed computation

The system must be:
- Fully open-source
- Self-hostable
- Privacy-first
- Compliance-aware
- Deterministic where required

---

# 2. Open-Source Technology Stack

## 2.1 Frontend

- React (Vite)
- TailwindCSS
- WebSocket streaming
- JWT-based authentication

Optional prototype:
- Streamlit (local testing only)

---

## 2.2 Backend

- FastAPI (Python 3.10+)
- Uvicorn (ASGI server)
- Celery (async tasks)
- Redis (queue + caching)

---

## 2.3 Database Layer

### Relational Database
- PostgreSQL (primary ledger)
- ACID compliant
- Immutable audit logs

### Vector Database
- FAISS (local)
- ChromaDB (alternative)
- HNSW indexing

---

## 2.4 LLM (Fully Open-Source)

Primary models:
- Llama 3 (via Ollama or vLLM)
- Mistral 7B
- Mixtral
- Phi-3-mini

Serving Framework:
- Ollama (local serving)
- vLLM (high-performance inference)
- Text Generation Inference (TGI)

Embeddings:
- BAAI/bge-large-en
- Instructor-XL
- E5-large

---

# 3. Core Modules

---

## 3.1 Document Ingestion

### Requirements
- Accept PDF, scanned documents
- Extract tabular financial data
- Template-agnostic normalization
- Output structured JSON

### Open-Source OCR

- Tesseract OCR
- PaddleOCR
- LayoutParser (table detection)

PDF Parsing:
- pdfplumber
- PyMuPDF

Output:
- Normalized JSON ledger format

---

## 3.2 Expense Categorization

### Model

- Fine-tuned BERT / DistilBERT
- Sentence-transformers
- LightGBM classifier

### Features Used

- Merchant name
- Amount
- Date
- Frequency
- Historical embedding similarity

Target:
- >90% categorization accuracy

Adaptive Learning:
- Vector similarity + few-shot retraining

---

## 3.3 Hybrid Anomaly Detection

### Layer 1 – Statistical

- Isolation Forest (sklearn)
- One-Class SVM
- Z-score baseline

### Layer 2 – ML Model

- XGBoost
- LightGBM

### Layer 3 – Contextual LLM Explanation

- Llama 3 (local)
- Structured prompt
- Outputs natural-language explanation

All anomaly alerts must:
- Provide numeric anomaly score
- Provide contextual explanation
- Allow user confirmation

---

## 3.4 Time-Series Forecasting

### Deterministic Forecast Models

- LSTM (PyTorch)
- GRU
- ARIMA (statsmodels)
- Prophet (open-source)

### Multimodal Fusion

- LLM extracts qualitative signals
- Embeddings injected into LSTM features

Outputs:
- Savings forecast
- Confidence interval
- Cash flow projection

---

## 3.5 Retrieval-Augmented Generation (RAG)

### Pipeline

1. Document chunking
2. Generate embeddings (bge-large)
3. Store in FAISS
4. Cosine similarity search
5. Inject retrieved chunks into LLM prompt
6. Generate cited answer

Framework:
- LangChain (open-source)
- LlamaIndex (open-source)

Requirements:
- Always cite source document
- No external internet lookup
- Hallucination fallback

---

## 3.6 Deterministic Tool-Calling

LLM must never perform raw math.

### Computation Engine

- Python sandbox (Restricted execution)
- NumPy
- Pandas
- SymPy

Example tools:
- Compound interest calculator
- Loan amortization schedule
- Tax estimation formula
- Portfolio optimization

Sandbox Security:
- Resource limits
- No filesystem access
- No network calls

Human-in-the-Loop required for:
- Budget modifications
- Financial transfers
- High-impact actions

---

# 4. Security & Privacy

---

## 4.1 PII Protection (Open-Source)

Use:
- Microsoft Presidio (open-source)
- spaCy NER
- Regex-based filters

Masking strategies:
- Hash (SHA-256)
- Redaction
- Token replacement

No raw PII leaves local environment.

---

## 4.2 Compliance-Ready Logging

All interactions stored in PostgreSQL:

- User input
- Retrieved RAG chunks
- Prompt version
- Model version
- Temperature
- Final output
- Tool execution trace

Logs must be immutable.

---

## 4.3 Hallucination Detection

Open-source evaluation:

- RAGAS
- DeepEval (community edition)
- Custom cosine similarity threshold validation

If confidence < threshold:
- Block output
- Return safe fallback

---

# 5. LLMOps (Open-Source)

---

## 5.1 Prompt Versioning

Prompts stored as:

- YAML files
- Versioned in Git
- Immutable hash history

Environment labels:
- dev
- staging
- production

---

## 5.2 Evaluation

Golden dataset stored via:
- DVC (Data Version Control)

CI/CD:
- GitHub Actions
- Local regression testing
- Batch prompt evaluation

Metrics checked:
- Accuracy
- Latency
- Hallucination rate
- Token usage

---

# 6. KPIs

---

## Efficiency
- Document processing time
- Inference latency
- Automation percentage

## Effectiveness
- Categorization accuracy (>90%)
- False positive rate
- Hallucination score

## System Stability
- Memory usage
- Token cost (local compute)
- Model uptime

## Compliance
- 100% audit logging
- Zero PII leakage

---

# 7. Non-Functional Requirements

- Fully self-hostable
- Dockerized deployment
- CPU-compatible (GPU optional)
- Offline-capable
- Encrypted storage
- Role-based access control

---

# 8. Deployment

### Local Development
- Docker Compose
- Ollama local LLM
- FAISS local index

### Production
- VPS / On-prem server
- GPU optional
- Reverse proxy (Nginx)
- HTTPS via Let's Encrypt

---

# 9. Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| LLM hallucination | RAG + RAGAS evaluation |
| Mathematical errors | Python sandbox only |
| Data breach | PII masking + local hosting |
| Model drift | Scheduled retraining |
| Overfitting | Cross-validation |

---

# 10. Strategic Positioning

This system is:

- Open-source
- Privacy-first
- Self-hostable
- Research-grade
- Startup-friendly
- Enterprise-upgradable

It is not dependent on:

- OpenAI API
- Pinecone
- Wolfram Alpha
- Azure
- Any proprietary LLM

---

# End of Document
