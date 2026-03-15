# CrossVerse

CrossVerse is an AI-powered platform for exploring sacred scripture across six major world religions. It uses RAG (Retrieval Augmented Generation) to answer questions grounded exclusively in scripture text — no opinion, no commentary, always cited.

## Supported Traditions

| Religion | Scripture | Translation |
|----------|-----------|-------------|
| Christianity | King James Bible | KJV |
| Islam | The Holy Quran | Sahih International |
| Hinduism | Bhagavad Gita | Public Domain |
| Buddhism | Dhammapada | F. Max Müller (1881) |
| Judaism | Torah / Tanakh | *(extend via ingestion script)* |
| Sikhism | Guru Granth Sahib | Public Domain |

## Features

- **Ask** — Chat interface for scripture-grounded Q&A with citations
- **Compare** — Side-by-side view of what each tradition says about any topic
- **Debate** — Each tradition's scriptures respond to a question independently
- **Explore** — Curated topic browser across 7 categories and 35+ topics
- **Contradictions** — Find apparent tensions within a single tradition

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11) |
| Vector DB | Qdrant |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o` |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Container | Docker + Docker Compose |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+
- An OpenAI API key

### 1. Clone and configure

```bash
git clone <repo-url>
cd crossVerse

# Create the backend .env file
cp backend/.env.example backend/.env
# Edit backend/.env and set your OPENAI_API_KEY
```

### 2. Start Qdrant + Backend via Docker Compose

```bash
docker-compose up -d
```

The backend will be available at `http://localhost:8000`.
Qdrant dashboard: `http://localhost:6333/dashboard`

### 3. Ingest Scripture Data

Run the ingestion scripts once to populate the vector database:

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run all ingestion (takes ~10-20 minutes depending on API rate limits)
python -m scripts.run_all_ingestion

# Or run individual scripts:
python -m scripts.ingest_gita           # Bhagavad Gita (~70 verses)
python -m scripts.ingest_dhammapada     # Dhammapada (~100 verses)
python -m scripts.ingest_guru_granth    # Guru Granth Sahib (~40 passages)
python -m scripts.ingest_quran          # Full Quran (~6236 ayahs)
python -m scripts.ingest_bible          # Full KJV Bible (~31,000 verses)
```

> **Note:** The Bible and Quran scripts download data from public APIs. The Gita, Dhammapada, and Guru Granth Sahib use curated public-domain datasets included in the scripts.

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:3000`.

---

## Development

### Backend (without Docker)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Set OPENAI_API_KEY and ensure Qdrant is running locally

uvicorn app.main:app --reload --port 8000
```

API documentation: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` if needed.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Main RAG Q&A endpoint |
| `POST` | `/compare` | Compare religions on a topic |
| `POST` | `/debate` | Multi-religion scripture debate |
| `POST` | `/contradictions` | Find tensions within one tradition |
| `GET` | `/verse/{religion}/{ref}` | Look up a specific verse |
| `GET` | `/topics` | Get curated topic list |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

### Example: Query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does scripture say about forgiveness?", "mode": "simple"}'
```

### Example: Compare

```bash
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"topic": "forgiveness", "religions": ["Christianity", "Islam", "Buddhism"]}'
```

---

## Project Structure

```
crossVerse/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/routes/          # All API route handlers
│   │   ├── core/                # Config, Qdrant client, OpenAI client
│   │   ├── models/schemas.py    # Pydantic data models
│   │   └── services/            # RAG pipeline, embeddings, scripture utils
│   ├── scripts/                 # Data ingestion scripts
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js App Router pages
│   ├── components/              # React components
│   ├── lib/                     # API client, TypeScript types
│   ├── package.json
│   └── tailwind.config.js
├── data/                        # Scripture raw/processed data directories
├── docker-compose.yml
└── README.md
```

---

## Design Principles

1. **Scripture-only answers** — The LLM is strictly instructed to answer only from retrieved passages
2. **Always cite** — Every claim must include a citation reference like [1], [2]
3. **No opinion** — The system never adds commentary, interpretation, or personal views
4. **Transparency** — All source passages are returned alongside every answer
5. **Impartiality** — All traditions are treated equally; no tradition is privileged

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `scriptures` | Qdrant collection name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | `gpt-4o` | OpenAI chat model |
