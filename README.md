# Lumina 🧠

[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi)](https://fastapi.tiangolo.com/) [![React](https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black)](https://react.dev/) [![Ollama](https://img.shields.io/badge/Ollama-LLM-white?logo=ollama&logoColor=black)](https://ollama.com/) 

A self-hosted, personal finance copilot that actually respects your privacy. 

I built Lumina because I wanted a single dashboard to track my spending, run financial projections, and chat with my bank statements—without handing over all my private financial data to a cloud aggregator or a third-party AI company.

Everything here runs locally on your own machine. The heavy lifting (like document parsing and transaction classification) is done through Python, and the conversational AI is powered directly by local Ollama instances.

---

### What it actually does

*   **Reads your PDFs:** Dump your bank statements or receipts into the app. It uses `pdfplumber` to extract the text and pull out individual transactions automatically.
*   **Talk to your ledger:** Lumina uses a local RAG (Retrieval-Augmented Generation) pipeline. You can literally ask, *"How much did I spend on food last month compared to this month?"* and get an answer instantly without your data leaving your laptop.
*   **Budgeting & Dashboards:** Built with React and Recharts, it visualizes your cash flow, tracks budget limits, and flags any weird or double-charged transactions.
*   **Calculators:** It comes with basic deterministic calculators (loan amortization, compound interest) and a Python sandbox if you just want to run custom scripts against your numbers.

---

### 🛠 Tech Stack

I kept the stack pretty standard so it's easy to deploy and hack on:
*   **Frontend:** React, Vite, TailwindCSS (for the glassmorphism UI)
*   **Backend:** FastAPI, AioSQLite (perfect for local setups)
*   **AI/Local LLM:** Ollama (`llama3.1` for chat, `nomic-embed-text` for the RAG embeddings)

---

### How to run it locally

You'll need Python 3.10+, Node 18, and [Ollama](https://ollama.com/) installed on your machine.

**1. Set up the local AI models**
Make sure Ollama is running in the background, then pull the models:
```bash
ollama run llama3.1
ollama pull nomic-embed-text
```

**2. Start the FastAPI backend**
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

uvicorn app.main:app --reload --port 8000
```

**3. Fire up the React frontend**
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

The app should now be live at `http://localhost:5173`.

---

### Environment Variables

Your `.env` file in the `backend/` folder should look something like this. Change the secret keys in production!

```env
DATABASE_URL=sqlite+aiosqlite:///./data/fincopilot.db
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
OLLAMA_EMBED_MODEL=nomic-embed-text

SECRET_KEY=change_this_to_something_random
JWT_SECRET_KEY=change_this_too
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

### Contributing
This is an open-source project, and pull requests are definitely welcome. If you find a bug or want to add a new visualization to the dashboard, feel free to open an issue or fork the repo.

**License:** MIT
