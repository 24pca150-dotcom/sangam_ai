# Sangam AI

A production-ready RAG-based AI assistant for exploring and understanding classical Sangam Tamil literature.

## Architecture
- **Frontend**: Angular 18 (Standalone Components, TailwindCSS)
- **Backend**: FastAPI, SQLite, SQLAlchemy
- **Vector DB**: ChromaDB
- **AI/LLM Layer**: LangChain, Groq API (Llama 3), Hugging Face (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)

## Features
- Search Sangam literature by keyword, poet, or theme.
- View detailed explanations, modern meanings, and Thinais for every poem.
- RAG-powered AI chat to interact with classical texts.
- Admin upload pipeline to index new JSON datasets automatically.

## Setup Instructions

### Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Activate virtual environment (already created in `.venv` or `venv`):
   ```bash
   .\venv\Scripts\activate
   ```
3. Set up environment variables:
   - Edit `.env` file and add your `GROQ_API_KEY`.
4. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Start the Angular server:
   ```bash
   npm start
   ```

## Future Roadmap
- **Phase 1**: RAG-based Sangam Tamil Assistant (Current)
- **Phase 2**: LoRA Fine-Tuning
- **Phase 3**: Custom Tamil LLM Deployment
- **Phase 4**: Research-grade knowledge model integration
