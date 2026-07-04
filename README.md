# ⚖️ Legal Contract Analyzer

**Automated, structure-aware risk analysis for legal contracts — powered by a hybrid retrieval pipeline and calibrated LLM reasoning.**

Upload a contract PDF. Get back a clause-by-clause risk report — severity-rated, page-referenced, and grounded strictly in the document's own language.

> ⚠️ **Status: Research prototype / active development.** The core pipeline works end-to-end; hardening for production (packaging, auth, tests) is in progress. See [Roadmap](#-roadmap).

---

## Table of Contents

- [Why this exists](#-why-this-exists)
- [How it works](#-how-it-works)
- [Architecture](#-architecture)
- [Tech stack](#-tech-stack)
- [Getting started](#-getting-started)
- [API reference](#-api-reference)
- [Design decisions worth knowing about](#-design-decisions-worth-knowing-about)
- [Known limitations](#-known-limitations)
- [Roadmap](#-roadmap)
- [Project structure](#-project-structure)

---

## 🧭 Why this exists

Manually reviewing contracts for risk is slow, inconsistent, and easy to get wrong — a missed auto-renewal clause or an uncapped indemnity buried on page 14 can cost real money. Most "AI contract reviewers" either:

- paste raw text into a single LLM call and hope the context window and hallucination rate cooperate, or
- do naive keyword search with no legal structure awareness.

This project instead treats contract review as an **information retrieval problem with legal-domain constraints**: parse the document's actual legal structure (articles → sections → clauses → subclauses), retrieve the most risk-relevant passages using a hybrid search strategy built for legal language, and generate a risk report under an LLM prompt that is explicitly constrained against the most common and most dangerous failure mode in this domain — **hallucinating protections or obligations the contract doesn't actually contain.**

## 🔍 How it works

```
PDF Upload
   │
   ▼
┌─────────────────────────────┐
│  1. INGESTION                │
│  unstructured.partition_pdf  │  hi-res layout parsing, table + image extraction
│  → structure_builder.py      │  regex-based legal structure parser
│                               │  (Article / Section / Clause / Sub-clause)
│  → Vision model (Gemini)     │  tables → verbatim structured JSON
│                               │    + natural-language embedding text
└─────────────┬────────────────┘
              ▼
┌─────────────────────────────┐
│  2. CHUNKING                 │
│  Section-aware, 400-word cap │
│  Linked prev/next chunk IDs  │  for context stitching at generation time
└─────────────┬────────────────┘
              ▼
┌─────────────────────────────┐
│  3. HYBRID RETRIEVAL         │
│  BM25 (lexical) + FAISS      │  ~60 curated legal-risk query variants,
│  (dense, Qwen3-Embedding-4B) │  or LLM-generated queries for custom asks
│  → Reciprocal Rank Fusion     │
│  → Cross-encoder rerank       │  BAAI/bge-reranker-v2-m3
└─────────────┬────────────────┘
              ▼
┌─────────────────────────────┐
│  4. RISK GENERATION           │
│  Groq LLM (gpt-oss-120b)      │  calibrated severity rubric,
│  temperature = 0              │  deduplication rules,
│                               │  strict "no absence-based risk" constraint
└─────────────┬────────────────┘
              ▼
     Structured Risk Report
     (title, severity, section, clause #, page, why, consequences)
```

## 🏗️ Architecture

The system is split into five composable stages, each independently testable:

| Stage | File | Responsibility |
|---|---|---|
| Model registry | `src/models.py` | Lazily-initialized singletons for embedding, LLM, reranker, and vision models |
| Structure parsing | `src/structure_builder.py` | Regex-driven legal document parser (Articles/Sections/Clauses/Sub-clauses); routes table elements to the vision model |
| Ingestion & chunking | `src/ingestion_pipeline.py` | PDF partitioning, section-aware chunking, FAISS index construction |
| Retrieval | `src/retrieval_pipeline.py` | Hybrid BM25 + dense retrieval, Reciprocal Rank Fusion, cross-encoder reranking, final risk-report generation |
| Prompts | `src/prompts.py` | All LLM prompt templates, versioned as first-class artifacts |
| API | `src/main.py` | FastAPI surface (`/upload_pdf`) |

**Why hybrid retrieval instead of pure semantic search?** Legal risk language is often precise and lexical ("liquidated damages," "force majeure," "indemnify") — BM25 catches exact terminology that dense embeddings sometimes smooth over, while FAISS catches paraphrased or conceptually-related risk even when the exact term isn't present. Reciprocal Rank Fusion combines both rankings without needing to hand-tune a weighting scheme, and the cross-encoder rerank step does a final precision pass against a single, purpose-built "risk clause" query.

**Why route tables through a vision model instead of text-extracting them?** Tables in contracts (rate cards, liability matrices, SLA tables) lose their row/column relationships when flattened to text. Table images are sent to Gemini 2.5 Flash under a prompt that forbids inference, rephrasing, or omission, and returns two synchronized outputs — a natural-language version for embedding/retrieval, and a strict structured JSON version that the risk-generation LLM can reference for precise reasoning (e.g., "which party's liability cap is which").

## 🧰 Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| PDF parsing | `unstructured` (hi-res strategy, table/image extraction) |
| Structure parsing | Custom regex engine |
| Table understanding | Gemini 2.5 Flash (structured output via LangChain) |
| Embeddings | Qwen3-Embedding-4B (HuggingFace, GPU-accelerated when available) |
| Vector store | FAISS |
| Lexical retrieval | BM25 (rank-bm25) |
| Reranking | BAAI/bge-reranker-v2-m3 (cross-encoder) |
| Risk-report generation | Groq — `openai/gpt-oss-120b` |
| Orchestration | LangChain / LangGraph |

## 🚀 Getting started

### Prerequisites

- Python 3.11
- A [Groq API key](https://console.groq.com) (risk-report generation, query expansion)
- A Google Generative AI API key (table understanding via Gemini)
- (Recommended) a CUDA-capable GPU — the embedding and reranking models will run on CPU otherwise but noticeably slower

### Installation

```bash
git clone https://github.com/caspianfypex/legal-contract-analyzer.git
cd legal-contract-analyzer

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

> **Note:** `requirements.txt` is currently a full `pip freeze` output, which is heavier and less portable than a curated dependency list — see [Roadmap](#-roadmap).

### Configuration

Create a `.env` file in the project root:

```bash
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_generative_ai_key
```

### Run the API

```bash
cd src
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

### Analyze a contract

```bash
curl -X POST "http://127.0.0.1:8000/upload_pdf?mode=Standard" \
  -F "file=@/path/to/contract.pdf"
```

## 📡 API reference

### `POST /upload_pdf`

Uploads a contract PDF and returns a structured risk analysis.

**Query parameters**

| Parameter | Type | Values | Description |
|---|---|---|---|
| `mode` | string | `Low` \| `Standard` \| `High` \| `Ultra` | Controls the number of reranked chunks fed to the risk-generation LLM (10 / 15 / 25 / 40 respectively) — trades cost/latency for analysis depth |

**Body:** `multipart/form-data` with a `file` field containing the PDF.

**Response**

```json
{
  "content": "<LLM-generated risk report>"
}
```

Each risk entry in the report includes:

```
risk_title              — short, specific title
severity                — Critical / High / Medium / Low
section                 — section name and number
clause                  — clause number only
page                    — source page number
why_it_is_risky         — grounded in language present in the contract
possible_consequences   — practical business impact
```

## 🧠 Design decisions worth knowing about

- **The "absence rule."** The risk-generation prompt explicitly forbids flagging *missing* protections as risks (a common LLM failure mode — inventing "the contract lacks X" claims). It carves out one narrow, well-justified exception: dangling cross-references to obligations the text itself invokes but doesn't define elsewhere.
- **Liability-cap directionality.** The prompt corrects a subtle and common reasoning error: a liability cap protects the *breaching* party and limits the *injured* party's recovery — not the reverse. This is spelled out explicitly with correct/incorrect examples.
- **Deduplication with a mandatory merge rule.** Liability exclusions and liability caps are forced into a single risk entry rather than being double-counted, since they serve the same underlying risk-allocation function.
- **Context stitching without context bloat.** Instead of retrieving large windows around every match, only the immediate previous/next chunk of a *selected* chunk is pulled in — and only if it isn't already part of the selected set.

## ⚠️ Known limitations

This is an honest accounting of the current state, not a marketing page:

- **Single-file flow only** — no batch upload, no persistent history, no comparison across contract versions yet.
- **No authentication or rate limiting** on the API surface.
- **`requirements.txt`** is an unpruned `pip freeze` export (200+ packages, some GPU-nightly-specific) rather than a curated dependency list, and may need re-encoding to UTF-8 depending on your platform.
- **No automated test suite yet** — see Roadmap.
- **English-language contracts only** at present; no multilingual support.
- **Table understanding depends on Gemini API availability** — no offline/local fallback for table extraction currently.

## 🗺️ Roadmap

- [ ] Curated, pinned `requirements.txt` / migrate to `pyproject.toml`
- [ ] Unit + integration tests (structure parser, RRF fusion, prompt assembly)
- [ ] Dockerfile + docker-compose for reproducible deployment
- [ ] Request validation (file size/type) and basic auth on `/upload_pdf`
- [ ] Persisted vector stores per document (currently rebuilt per request)
- [ ] Structured (JSON) risk output instead of free-text LLM content
- [ ] Version-to-version contract comparison (redlining)
- [ ] Multilingual contract support

## 📁 Project structure

```
legal-contract-analyzer/
├── requirements.txt
└── src/
    ├── main.py                # FastAPI app and pipeline orchestration
    ├── models.py               # Embedding / LLM / reranker / vision model factories
    ├── prompts.py               # All prompt templates (vision, reranker, risk, query-gen)
    ├── ingestion_pipeline.py    # PDF partitioning + chunking + FAISS index build
    ├── retrieval_pipeline.py    # Hybrid retrieval, RRF, reranking, report generation
    └── structure_builder.py     # Legal document structure parser
```

---

*Built with FastAPI, LangChain, FAISS, and a genuine attempt to make an LLM tell the truth about contracts.*
