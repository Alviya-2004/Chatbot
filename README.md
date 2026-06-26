# Portfolio Builders AI Chatbot (CarePilot)

CarePilot is a smart, AI-powered conversational assistant built specifically for Portfolio Builders. It acts as a friendly career guide, course recommender, and admission assistant. Using Retrieval-Augmented Generation (RAG) and the Llama 3.1 LLM, the chatbot can accurately answer user queries by dynamically fetching context from an embedded knowledge base.

## 🌟 Key Features

- **Conversational AI**: Powered by Groq's fast Llama 3.1 models for instant, intelligent replies.
- **Retrieval-Augmented Generation (RAG)**: Integrates ChromaDB to store and retrieve company facts, course details, and website context.
- **Automated Web Crawler**: Built-in scraper to automatically crawl the Portfolio Builders website and index content into the vector database.
- **Lead Generation & Scoring**: Dynamically evaluates chat interactions to categorize leads (Cold, Warm, Hot) based on intent and automatically prompts high-intent users with a lead-capture form.
- **Admin Dashboard**: A built-in React control panel to view chatbot analytics, manage the knowledge base, review unresolved fallback questions, and monitor captured leads.
- **Embeddable Widget**: A sleek, responsive React-based floating widget designed to be embedded on any external website.

---

## 🏗️ Project Architecture

The project is structured as a monorepo containing both the backend API and the frontend widget:

- `/backend` - Python FastAPI application serving the AI logic, RAG pipelines, and API endpoints.
- `/frontend-widget/react-widget` - React + Vite application for the user-facing chat UI and the Admin dashboard.

### Tech Stack
* **Backend**: FastAPI, Python, SQLAlchemy (SQLite), ChromaDB, LlamaIndex, Groq API (Llama 3.1)
* **Frontend**: React.js, Vite, Vanilla CSS

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for the frontend widget)
- A Groq API Key

### 2. Backend Setup
Navigate to the backend directory and set up your Python environment:

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory with your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
```

**Run the Backend Server:**
```bash
python main.py
# The API will be available at http://localhost:8000
```
*Note: On startup, the backend automatically seeds the vector database with markdown/text files found in the `backend/data/` folder.*

### 3. Frontend Setup
Navigate to the frontend directory:

```bash
cd frontend-widget/react-widget
npm install

# Start the development server
npm run dev
```

### 4. Crawling the Website (Optional)
To index the live website into the chatbot's brain, ensure the backend is running and execute:
```bash
cd backend
python scripts/crawl_website.py
```

---

## 🛡️ Security Note
This repository is protected against accidental secret leaks. Ensure your `.env` file is properly ignored by `.gitignore` (which is already configured) and **never** commit API keys to version control.
