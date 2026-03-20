# CrossVerse

CrossVerse is an AI-powered platform for exploring sacred scripture across twelve world traditions. It uses RAG (Retrieval Augmented Generation) to answer questions grounded exclusively in scripture text — no opinion, no commentary, always cited.

**Live:** https://crossverse-frontend.fly.dev

---

## Scripture Database

**176,832 verses** across 12 traditions:

| Religion | Scriptures | Approx. Chunks |
|----------|-----------|----------------|
| Christianity | KJV Bible (full, 66 books) + Apocrypha (14 books) | ~35,000 |
| Islam | Full Quran + Sahih Bukhari Hadith | ~13,800 |
| Judaism | Full Tanakh (39 books, JPS 1917) + Mishnah + Talmud + Pirkei Avot | ~28,000 |
| Sikhism | Guru Granth Sahib (full, BaniDB) | ~24,700 |
| Hinduism | Bhagavad Gita · Yoga Sutras · Upanishads (19) · Bhagavata Purana · Ramayana · Mahabharata (18 Parvas) · Manusmriti · Four Vedas | ~35,000 |
| Buddhism | Dhammapada · Sutta Nipata · Diamond Sutra · Pali Canon selections | ~2,500 |
| Jainism | Acaranga Sutra · Uttaradhyayana Sutra (wisdomlib.org) | ~900 |
| Zoroastrianism | Gathas · Yasna · Vendidad · Visperad · Khordeh Avesta | ~1,800 |
| Confucianism | Analects · Doctrine of the Mean · Great Learning · Mencius | ~1,200 |
| Taoism | Tao Te Ching · Zhuangzi | ~800 |
| Bahai | Hidden Words · Seven Valleys · Epistle to Son of Wolf | ~700 |
| Shinto | Kojiki · Nihon Shoki excerpts | ~400 |

---

## Features

| Feature | Description |
|---------|-------------|
| **Living Hero** | Homepage auto-loads today's daily theme and animates 6 tradition cards on first load |
| **Ask** | Scripture-grounded Q&A with citations — Simple, Scholar, or Child mode |
| **Compare** | Side-by-side view of what each tradition says about any topic |
| **Debate** | Each tradition's scriptures respond to a question independently |
| **Universal Truth** | Enter any concept — find the single truth all 6 traditions agree on |
| **Mood Scripture** | Select how you're feeling (grief, joy, anxiety…) — receive scripture that meets you there |
| **Topic Explorer** | Curated topic browser across 7 categories and 35+ topics |
| **Daily Briefing** | A new spiritual theme each day with verses from all 6 traditions |
| **Concept Archaeology** | Trace how an idea evolved across traditions |
| **Semantic Graph** | Visual force-directed graph of verse similarities across traditions |
| **Spiritual Fingerprint** | Answer 10 questions, discover which tradition resonates most |
| **Life Situations** | Get scripture wisdom for specific life moments |
| **Fact Check** | Verify religious claims against actual scripture |
| **Ethics** | Multi-tradition ethical perspectives on moral dilemmas |
| **Study Plans** | AI-generated multi-day study plans on any topic |
| **Voice Input** | Speak your question — mic transcription built in |
| **Share & Cite** | Native OS share sheet + Chicago / MLA / SBL citation formats per verse |
| **Dark Mode** | Full dark mode across all pages |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11) |
| Vector DB | Qdrant Cloud (free tier, AWS us-east-1) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| LLM | Anthropic Claude Sonnet 4.6 |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Deployment | Fly.io (frontend + backend), Qdrant Cloud |

---

## Deployment

The app is deployed on Fly.io:

- **Frontend:** https://crossverse-frontend.fly.dev
- **Backend:** https://crossverse-backend.fly.dev
- **Vector DB:** Qdrant Cloud (AWS N. Virginia, private)

### Fly.io secrets required (backend)

```bash
fly secrets set OPENAI_API_KEY="sk-..."         -a crossverse-backend
fly secrets set ANTHROPIC_API_KEY="sk-ant-..."  -a crossverse-backend
fly secrets set QDRANT_URL="https://..."        -a crossverse-backend
fly secrets set QDRANT_API_KEY="..."            -a crossverse-backend
fly secrets set ALLOWED_ORIGINS="https://crossverse-frontend.fly.dev" -a crossverse-backend
```

### Redeploy

```bash
cd backend && fly deploy
cd frontend && fly deploy
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for local Qdrant)
- OpenAI API key (embeddings)
- Anthropic API key (LLM)

### 1. Clone and configure

```bash
git clone <repo-url>
cd crossVerse/backend
cp .env.example .env
# Edit .env:
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start Qdrant locally

```bash
docker run -p 6333:6333 -v ~/.qdrant/storage:/qdrant/storage qdrant/qdrant
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 4. Ingest scripture data

```bash
cd backend
# Run all ingestion (~30-60 min depending on API rate limits)
python -m scripts.run_all_ingestion
```

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:3000

### Migrate data to Qdrant Cloud

```bash
cd backend
QDRANT_CLOUD_URL="https://..." \
QDRANT_CLOUD_API_KEY="..." \
python3 scripts/migrate_to_cloud.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/query` | Main RAG Q&A — supports mode (simple/scholar/child), language, history |
| `POST` | `/compare` | Compare traditions on any topic |
| `POST` | `/debate` | Multi-tradition scripture debate |
| `POST` | `/contradictions` | Find tensions within one tradition |
| `POST` | `/situations` | Scripture wisdom for life situations |
| `POST` | `/factcheck` | Verify a religious claim against scripture |
| `POST` | `/ethics` | Multi-tradition ethical perspectives |
| `POST` | `/study` | Generate a multi-day study plan |
| `POST` | `/archaeology` | Trace a concept's development across traditions |
| `POST` | `/universal` | Find the universal truth all traditions share on a concept |
| `POST` | `/mood` | Scripture matched to an emotional state |
| `POST` | `/similarity/verse` | Find semantically similar verses cross-tradition |
| `POST` | `/similarity/graph` | Graph data for semantic similarity visualization |
| `POST` | `/fingerprint/analyze` | Analyze a user's spiritual fingerprint |
| `GET`  | `/fingerprint/questions` | Questions for spiritual fingerprint quiz |
| `GET`  | `/daily` | Daily scripture briefing (theme + verses per tradition) |
| `GET`  | `/daily?fresh=true` | New random theme |
| `GET`  | `/verse/{religion}/{ref}` | Look up a specific verse by reference |
| `GET`  | `/topics` | Curated topic list |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | Interactive API docs (Swagger) |

### Examples

```bash
# Universal Truth
curl -X POST https://crossverse-backend.fly.dev/universal \
  -H "Content-Type: application/json" \
  -d '{"concept": "compassion"}'

# Mood Scripture
curl -X POST https://crossverse-backend.fly.dev/mood \
  -H "Content-Type: application/json" \
  -d '{"mood": "grief"}'

# Ask a question
curl -X POST https://crossverse-backend.fly.dev/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does scripture say about forgiveness?", "mode": "scholar"}'
```

---

## Project Structure

```
crossVerse/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point + router registration
│   │   ├── api/routes/              # Route handlers (query, compare, debate, daily, universal, mood, …)
│   │   ├── core/                    # Config, Qdrant client, Anthropic LLM client
│   │   ├── models/schemas.py        # Pydantic request/response models
│   │   └── services/                # RAG pipeline, embeddings, scripture utils
│   ├── scripts/                     # Ingestion scripts + migrate_to_cloud.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   └── fly.toml
├── frontend/
│   ├── app/                         # Next.js App Router pages
│   │   ├── page.tsx                 # Homepage with Living Hero + mood strip
│   │   ├── query/                   # Ask the scriptures
│   │   ├── compare/                 # Compare traditions
│   │   ├── debate/                  # Debate engine
│   │   ├── daily/                   # Daily briefing
│   │   ├── universal/               # Universal Truth
│   │   ├── mood/                    # Mood Scripture
│   │   ├── situations/              # Life situations
│   │   ├── fingerprint/             # Spiritual fingerprint quiz
│   │   ├── graph/                   # Semantic similarity graph
│   │   ├── study/                   # Study plans
│   │   ├── archaeology/             # Concept archaeology
│   │   ├── factcheck/               # Fact checker
│   │   └── ethics/                  # Ethics perspectives
│   ├── components/
│   │   ├── ui/                      # VerseCard, ReligionBadge, GraphCanvas, …
│   │   ├── LivingHero.tsx           # Auto-loading homepage hero
│   │   ├── Navbar.tsx               # Navigation with dropdowns
│   │   └── SettingsPanel.tsx        # Global preferences
│   ├── lib/
│   │   ├── api.ts                   # All API client functions
│   │   └── types.ts                 # TypeScript interfaces
│   ├── Dockerfile
│   └── fly.toml
├── fly-qdrant/fly.toml              # Qdrant on Fly.io (alternative to cloud)
├── docker-compose.yml
└── README.md
```

---

## Design Principles

1. **Scripture-only answers** — Claude is strictly instructed to answer only from retrieved passages
2. **Always cite** — Every claim includes a passage reference
3. **No opinion** — The system never adds commentary or personal views
4. **Transparency** — All source passages are returned alongside every answer
5. **Impartiality** — All 12 traditions are treated with equal respect
6. **Guardrails** — Off-topic queries are redirected toward scripture

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | OpenAI key — used for embeddings only |
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic key — used for all LLM responses |
| `QDRANT_URL` | `` | Full Qdrant URL (overrides host+port; use for cloud/tunnel) |
| `QDRANT_API_KEY` | `` | Qdrant Cloud API key |
| `QDRANT_HOST` | `localhost` | Qdrant hostname (used if QDRANT_URL not set) |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `scriptures` | Qdrant collection name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | `claude-sonnet-4-6` | Anthropic Claude model ID |
| `TOP_K_RESULTS` | `8` | Number of passages retrieved per query |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `RATE_LIMIT` | `30/minute` | Rate limit per IP |
