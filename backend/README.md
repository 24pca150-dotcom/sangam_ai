# Sangam AI Backend

This is the backend service for **Sangam AI**, an AI-powered application designed for exploring and understanding Sangam Tamil Literature. It is built using **FastAPI** and utilizes advanced AI capabilities through Langchain, ChromaDB, and Groq.

## Technology Stack

- **Framework**: FastAPI
- **Vector Database**: ChromaDB
- **Relational Database**: SQLite (via SQLAlchemy)
- **AI/LLM Integration**: Langchain, Langchain-Groq
- **Embeddings**: Sentence Transformers (HuggingFace)

## Project Structure

- `api/` - API route definitions and endpoints.
- `models/` - SQLAlchemy models and Pydantic schemas.
- `rag/` - Retrieval-Augmented Generation (RAG) implementation.
- `services/` - Core business logic and API integrations.
- `utils/` - Helper functions and utilities.
- `vector_db/` - Vector database management (ChromaDB).
- `main.py` - Application entry point.
- `sangam.db` - SQLite database for local storage.

## Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Create Virtual Environment
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the root of the `backend` directory and add your required API keys (like Groq):
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Run the Application
Start the FastAPI server using Uvicorn:
```bash
uvicorn main:app --reload
```
The server will start at `http://127.0.0.1:8000`.

## API Documentation
FastAPI provides auto-generated interactive API documentation. Once the server is running, you can access it here:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
