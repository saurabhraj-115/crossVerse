# CrossVerse

CrossVerse is an AI-powered platform for exploring sacred scripture across six major world religions. It uses RAG (Retrieval Augmented Generation) to answer questions grounded exclusively in scripture text — no opinion, no commentary, always cited.

## Scripture Database

**120,000+ verses** across all six traditions:

| Religion | Scriptures | Verses |
|----------|-----------|--------|
| Christianity | King James Bible (full) | 31,100 |
| Islam | The Holy Quran (full) + Sahih Bukhari Hadith | 13,813 |
| Judaism | Full Tanakh (39 books, Sefaria / JPS 1917) | 23,307 |
| Sikhism | Guru Granth Sahib (full, BaniDB) | 24,703 |
| Hinduism | Bhagavad Gita · Yoga Sutras · 10 Upanishads · Bhagavata Purana · Ramayana · Mahabharata (18 Parvas) · Manusmriti · Four Vedas | 30,000+ |
| Buddhism | Dhammapada (full, SuttaCentral / Bhikkhu Sujato) | 514 |

---

## Features

| Feature | Description |
|---------|-------------|
| **Living Hero** | Homepage auto-loads today's daily theme and animates 6 tradition cards into view — the AHA moment on first load |
| **Ask** | Scripture-grounded Q&A with citations — Simple, Scholar, or Child mode |
| **Compare** | Side-by-side view of what each tradition says about any topic |
| **Debate** | Each tradition's scriptures respond to a question independently |
| **Universal Truth** | Enter any concept — find the single truth all 6 traditions agree on |
| **Mood Scripture** | Select how you're feeling (grief, joy, anxiety…) — receive scripture that meets you there |
| **Topic Explorer** | Curated topic browser across 7 categories and 35+ topics |
| **Daily Briefing** | A new spiritual theme each day with verses from all 6 traditions |
| **Concept Archaeology** | Trace how an idea (forgiveness, soul, justice…) evolved across traditions |
| **Semantic Graph** | Visual force-directed graph of verse similarities across traditions |
| **Spiritual Fingerprint** | Answer questions, discover which tradition resonates most |
| **Life Situations** | Get scripture wisdom for specific life moments (grief, marriage, career…) |
| **Fact Check** | Verify religious claims against actual scripture |
| **Ethics** | Multi-tradition ethical perspectives on moral dilemmas |
| **Study Plans** | AI-generated multi-week study plans on any topic |
| **Voice Input** | Speak your question — mic transcription built in |
| **Share & Cite** | Native OS share sheet + Chicago / MLA / SBL citation formats per verse |
| **Dark Mode** | Full dark mode across all pages |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.9) |
| Vector DB | Qdrant (local binary) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic Claude Sonnet 4.6 |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| UI Components | Lucide Icons, next-themes |

---

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- An OpenAI API key (embeddings)
- An Anthropic API key (LLM)
- Qdrant binary ([download here](https://qdrant.tech/documentation/quick-start/))

### 1. Clone and configure

```bash
git clone <repo-url>
cd crossVerse/backend

cp .env.example .env
# Edit .env and set:
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Start Qdrant

```bash
# Download the Qdrant binary for your platform, then:
./qdrant &
# Dashboard available at http://localhost:6333/dashboard
```

### 3. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 4. Ingest Scripture Data

```bash
cd backend

# Run all ingestion (takes ~30-60 min depending on API rate limits)
python -m scripts.run_all_ingestion

# Or run individual scripts:
python -m scripts.ingest_bible_full          # KJV Bible — 31,100 verses
python -m scripts.ingest_quran_full          # Full Quran — 6,236 ayahs
python -m scripts.ingest_hadith_full         # Sahih Bukhari Hadith — 7,577
python -m scripts.ingest_tanakh_full         # Full Tanakh (Sefaria) — 23,307 verses
python -m scripts.ingest_guru_granth_full    # Guru Granth Sahib (BaniDB) — 24,703 passages
python -m scripts.ingest_gita_full           # Bhagavad Gita — 700 verses
python -m scripts.ingest_yoga_sutras_full    # Yoga Sutras — 196 sutras
python -m scripts.ingest_dhammapada_full     # Dhammapada — 423 verses
python -m scripts.ingest_upanishads_full     # Isa, Katha, Kena Upanishads — 171 verses
python -m scripts.ingest_upanishads_more     # 9 more Upanishads (SBE Vol 1 & 15, Archive.org)
python -m scripts.ingest_bhagavatam          # Bhagavata Purana
python -m scripts.ingest_ramayana            # Ramayana (Griffith translation)
python -m scripts.ingest_mahabharata         # Mahabharata — 18 Parvas (Ganguli translation)
python -m scripts.ingest_manusmriti          # Manusmriti
python -m scripts.ingest_vedas               # Vedas (Griffith translation)
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend available at `http://localhost:3000`.

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
| `POST` | `/study` | Generate a multi-week study plan |
| `POST` | `/archaeology` | Trace a concept's development across traditions |
| `POST` | `/universal` | Find the universal truth all traditions share on a concept |
| `POST` | `/mood` | Scripture matched to an emotional state |
| `POST` | `/similarity/verse` | Find semantically similar verses cross-tradition |
| `POST` | `/similarity/graph` | Graph data for semantic similarity visualization |
| `POST` | `/fingerprint/analyze` | Analyze a user's spiritual fingerprint |
| `GET`  | `/fingerprint/questions` | Questions for spiritual fingerprint quiz |
| `GET`  | `/daily` | Daily scripture briefing (theme + verses per tradition) |
| `GET`  | `/daily?fresh=true` | New random theme and verses |
| `GET`  | `/verse/{religion}/{ref}` | Look up a specific verse by reference |
| `GET`  | `/topics` | Curated topic list |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | Interactive API documentation (Swagger) |

### Example: Universal Truth

```bash
curl -X POST http://localhost:8000/universal \
  -H "Content-Type: application/json" \
  -d '{"concept": "compassion"}'
# Returns: universal_truth sentence + how each of the 6 traditions expresses it
```

### Example: Mood Scripture

```bash
curl -X POST http://localhost:8000/mood \
  -H "Content-Type: application/json" \
  -d '{"mood": "grief"}'
# Returns: warm wisdom message + 12 verses from across traditions
```

### Example: Ask a question

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does scripture say about forgiveness?", "mode": "scholar"}'
```

### Example: Compare traditions

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
│   │   ├── main.py                  # FastAPI app entry point + router registration
│   │   ├── api/routes/              # Route handlers (query, compare, debate, daily, universal, mood, …)
│   │   ├── core/                    # Config, Qdrant client, Anthropic LLM client
│   │   ├── models/schemas.py        # Pydantic request/response models
│   │   └── services/                # RAG pipeline, embeddings, scripture utils
│   ├── scripts/                     # Data ingestion scripts (one per scripture)
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/
│   ├── app/                         # Next.js App Router pages
│   │   ├── page.tsx                 # Homepage with Living Hero
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
│   │   ├── ui/                      # VerseCard, ReligionBadge, …
│   │   ├── LivingHero.tsx           # Auto-loading homepage hero
│   │   ├── QueryChat.tsx            # Main chat interface
│   │   ├── CompareView.tsx          # Side-by-side comparison
│   │   └── Navbar.tsx               # Navigation
│   ├── lib/
│   │   ├── api.ts                   # API client functions
│   │   ├── types.ts                 # TypeScript interfaces
│   │   └── settings-context.tsx     # Global preferences context
│   └── tailwind.config.js
├── data/                            # Raw scripture data directories
├── docker-compose.yml
└── README.md
```

---

## Design Principles

1. **Scripture-only answers** — Claude is strictly instructed to answer only from retrieved passages
2. **Always cite** — Every claim must include a passage reference like [1], [2]
3. **No opinion** — The system never adds commentary, interpretation, or personal views
4. **Transparency** — All source passages are returned alongside every answer
5. **Impartiality** — All traditions are treated with equal respect; none is privileged
6. **Guardrails** — Off-topic queries (coding, trivia, general chat) are redirected toward scripture

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(required)* | OpenAI key — used for embeddings only |
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic key — used for all LLM responses |
| `QDRANT_HOST` | `localhost` | Qdrant hostname |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_COLLECTION` | `scriptures` | Qdrant collection name |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `LLM_MODEL` | `claude-sonnet-4-6` | Anthropic Claude model ID |
| `TOP_K_RESULTS` | `8` | Number of passages retrieved per query |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS allowed origins (comma-separated) |
| `RATE_LIMIT` | `30/minute` | Rate limit per IP (e.g. `60/minute`, `100/hour`) |
