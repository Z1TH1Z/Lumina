<div align="center">
  
  # Lumina ( Your personal AI Finance Copilot )
  
  **Your Open-Source, Privacy-First AI Wealth Manager**

  [![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/)
  [![Ollama](https://img.shields.io/badge/Ollama-LLM-white?logo=ollama&logoColor=black)](https://ollama.com/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow)](https://opensource.org/licenses/MIT)

  *An intelligent financial dashboard that reads your documents, analyzes your spending, and answers complex financial questions using 100% local AI models.*

</div>

---

##  Overview

The **AI Financial Copilot** is a self-hostable, full-stack application designed to replace cloud-based financial aggregators. By combining traditional deterministic financial tools with advanced generative AI and machine learning techniques, it acts as a proactive financial advisor.

Crucially, this project emphasizes **privacy and data sovereignty**. By leveraging local LLMs (Ollama) and local databases (SQLite/PostgreSQL), your sensitive financial data never leaves your machine unless you explicitly configure it to.

---

## Key Features

-  **Intelligent Document Ingestion:** Drag and drop PDF bank statements or receipts. The system automatically categorizes and extracts transactions using OCR and structured parsing.
-  **RAG-Powered Chat Assistant:** Chat naturally with your financial data. Ask questions like *"How much did I spend on dining last month?"* and get instant, cited answers powered by `llama3.1`.
-  **Interactive Dashboards:** Visualizations built with Recharts surface your cash flow, top spending categories, and progress against monthly budgets.
-  **Predictive Forecasting:** Anticipate your future account balances with exponential smoothing and machine tracking models.
-  **Anomaly Detection:** ML-driven agent automatically analyzes your ledger to flag out-of-the-ordinary charges or potential double-billing.
-  **Deterministic Tools Base:** Pre-built calculators for compound interest, loan amortizations, and a secure Python sandbox for custom numbercrunching.

---

## 🛠️ Architecture & Tech Stack

**Frontend (Client)**
- React (Vite)
- Tailwind CSS
- Vanilla CSS + Glassmorphism UI
- Recharts (Data Visualization)
- Lucide React (Icons)

**Backend (Server / ML)**
- FastAPI (Python 3.10+)
- SQLAlchemy (Async SQLite)
- Ollama (`llama3.1` & `nomic-embed-text`)
- PyMuPDF & pdfplumber (Document processing)
- Sentence-Transformers & FAISS (Vector retrieval)

---

##  Getting Started

### Prerequisites

1. **Python 3.10+**
2. **Node.js 18+** & `npm`
3. **[Ollama](https://ollama.com/)** (Required for the AI features)

### 1. Model Setup

Ensure Ollama is running, then pull the required models:

```bash
ollama run llama3.1
ollama pull nomic-embed-text
```

### 2. Backend Setup

Navigate to the backend directory, install dependencies, and start the FastAPI server:

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Mac/Linux

pip install -r requirements.txt
cp .env.example .env  # Configure your secrets

uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

In a new terminal, navigate to the frontend directory and start the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

The application will be available at `http://localhost:5173`.

---

##  Environment Variables

Create a `.env` file in the `backend/` directory with the following base configuration:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/fincopilot.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_EMBED_MODEL=nomic-embed-text

SECRET_KEY=change_me_in_production
JWT_SECRET_KEY=change_me_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

##  Contributing

Contributions make the open-source community an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

##  License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <i>Built with ❤️ for privacy-conscious personal finance.</i>
</div>
