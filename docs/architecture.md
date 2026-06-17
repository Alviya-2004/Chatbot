# CarePilot AI - Architecture Document (Milestone 1)

## 1. System Overview
CarePilot AI is an intelligent chatbot designed to act as a personal career assistant for the Portfolio Builders website. This document outlines the initial architecture for Milestone 1, focusing on establishing the core RAG (Retrieval-Augmented Generation) pipeline, FastAPI backend, and an embeddable React widget.

## 2. High-Level Architecture
The system consists of three main tiers:
1.  **Frontend Widget (React):** An embeddable floating chat UI that lives on the Portfolio Builders website. It communicates via REST API to the backend.
2.  **Backend API (FastAPI):** The central engine that receives chat requests, scores leads based on their queries, filters personas, and orchestrates the RAG pipeline.
3.  **Knowledge Base (ChromaDB + LlamaIndex):** The local vector database that holds the embeddings of the company's FAQs, course details, and internship policies.

## 3. Data Flow
1.  **User Input:** The user types a message in the React widget (e.g., "I want to learn UI/UX").
2.  **API Call:** The widget sends a POST request to `/api/chat/message` with the `session_id`, `message`, `user_persona` (if known), and `current_score`.
3.  **Lead Scoring:** The FastAPI server parses the message against a strict regex scoring system (e.g., +30 for "counselor call").
4.  **RAG Retrieval:** 
    - FastAPI queries LlamaIndex.
    - LlamaIndex converts the query into vector embeddings and searches ChromaDB.
    - Top matching chunks (FAQs, docs) are retrieved.
5.  **Response Generation:** The retrieved context + the user's question are sent to the LLM via a custom PromptTemplate.
6.  **Response:** The FastAPI server returns the AI's response, the `new_score`, and a boolean `trigger_form` if the score reaches 50.

## 4. Technology Stack
- **Frontend:** React, Vite, TailwindCSS (for rapid styling of the chat UI).
- **Backend:** Python 3, FastAPI, Uvicorn.
- **RAG Engine:** LlamaIndex.
- **Vector Store:** ChromaDB (Persistent local storage).
- **LLM Provider:** OpenAI (configured via `.env`).

## 5. Directory Structure
```
carepilot-ai-chatbot/
│
├── frontend-widget/
│   └── react-widget/       # Vite React application
│
├── backend/
│   ├── main.py             # FastAPI server and core logic
│   └── requirements.txt    # Python dependencies
│
├── docs/
│   └── architecture.md     # This document
│
├── scripts/
│   └── ingest_faqs.py      # Script to populate ChromaDB
│
└── data/                   # Markdown and JSON files for the knowledge base
```
