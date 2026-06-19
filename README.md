# JobLens

JobLens is a job and internship assistant for students, freshers, and early-career candidates.

It combines scraped internship/job listings, resume parsing, hybrid retrieval, and a streaming chat agent so users can search roles, compare matches, inspect full job details, and use their resume as matching context.

## What Exists Now

- FastAPI backend with startup warmup for database, LLMs, and agent runtime.
- React/Vite frontend with Supabase Auth, chat UI, resume preview, job browser, filters, and job detail modal.
- Streaming chat endpoint with Server-Sent Events for status updates, tokens, retrieved jobs, errors, and final answers.
- Tool-calling agent with:
  - `search_jobs` for normal, resume-aware, and resume-only retrieval.
  - `get_job_details` for full details of selected listings.
- Resume upload flow:
  - PDF reading.
  - Structured resume parsing.
  - Resume embedding.
  - Resume search-intent generation and embeddings.
  - PDF and thumbnail upload to Supabase Storage.
  - Resume/profile persistence in Postgres.
- Retrieval pipeline:
  - Query parsing.
  - Full-text search.
  - Vector search.
  - Hybrid merge.
  - Resume-aware retrieval modes.
  - LLM reranking.
- Internshala scraping and ingestion pipeline with deduplication, embeddings, and periodic-ingestion-ready structure.
- Alembic migrations for database schema changes.
- Runtime logging configuration for readable terminal logs.

## Tech Stack

Backend:

- Python 3.13
- FastAPI
- SQLAlchemy async
- asyncpg
- Alembic
- pgvector
- LangChain
- OpenAI/Azure OpenAI-compatible LLM and embedding factories
- Supabase Postgres and Storage

Frontend:

- React
- TypeScript
- Vite
- Supabase Auth client
- React Markdown

## Main Backend Routes

- `POST /chat/sessions`
  Creates or restores a chat session for the authenticated user.

- `POST /chat/stream`
  Streams the agent response with SSE.

- `POST /pdf/upload`
  Uploads, parses, embeds, stores, and persists a resume.

- `GET /pdf/current`
  Loads the current user's uploaded resume metadata and preview URLs.

- `GET /jobs`
  Lists jobs for the frontend job browser with lightweight filters.

- `GET /jobs/{job_id}`
  Returns full details for one job card modal.

## Project Structure

```text
src/
  agent/
    tools/
    streaming_agent.py
    tool_calling.py
    state.py
  auth/
    dependencies.py
  db/
    migrations/
    models.py
    chat_ops.py
    job_ops.py
    resume_ops.py
  factories/
    llm_factory.py
    embedding_factory.py
  frontend/
    src/
    package.json
    vite.config.ts
  routes/
    chat.py
    jobs.py
    pdf_upload.py
  scraper/
    intershala/
    fetch_all_jobs.py
    job_ingestion_pipeline.py
  services/
    chat/
    llm/
    resume/
    retrieval/
    streaming/
  utils/
  main.py
```

## Backend Setup

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Run migrations:

```powershell
alembic upgrade head
```

Start the API:

```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

## Frontend Setup

```powershell
cd src/frontend
npm install
npm run dev
```

Frontend runs on:

```text
http://127.0.0.1:5173
```

## Environment

Backend environment variables live in the root `.env`.

Frontend environment variables live in `src/frontend/.env`.

Frontend public variables should use the `VITE_` prefix, for example:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
```

Do not commit real secrets. Use `.env.example` files for shareable configuration names.

## Job Ingestion

The current scraper pipeline focuses on Internshala categories.

Run the ingestion entrypoint from the project root:

```powershell
python -m src.scraper.job_ingestion_pipeline
```

The ingestion pipeline deduplicates jobs, builds embedding text, generates embeddings, and upserts active listings into Postgres.

## Notes

- The app name is JobLens.
- Current searchable listings are from the stored database, primarily Internshala.
- Voice mode is not implemented yet.
- Full realtime voice, additional job sources, and application-drafting subagents are future work.
