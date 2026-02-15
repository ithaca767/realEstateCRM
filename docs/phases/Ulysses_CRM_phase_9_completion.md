# Phase 9 – Universal Search

---

## Phase 9A – Deterministic Full-Text Search

Implemented PostgreSQL full-text search (FTS) across core entities.

### Entities Covered

- Contacts  
- Engagements  
- Transactions  
- Professionals  

### Features

- `websearch_to_tsquery`  
- Weighted ranking (`ts_rank`)  
- Snippet extraction  
- Per-type result grouping  
- Score display  
- Deep links to objects  
- Tenant-safe filtering (`user_id` scoped)  

### UI

- `/search` route  
- Search page with grouped results  
- Deterministic ranking  
- No AI dependency  

**Status: Complete**

---

## Phase 9B – Semantic Broadening (AI Retrieval Layer)

Implemented pgvector-based semantic similarity search.

### Infrastructure

- `search_index` table  
- `vector` extension installed  
- IVFFLAT index created  
- Embeddings stored per object  

### Objects Indexed

- Contacts  
- Engagements  
- Transactions  
- Professionals  

### Components

- `search_indexer.py`  
- `search_index_service.py`  
- `semantic_broaden()` in `search_service.py`  
- Admin rebuild endpoint  
- CLI rebuild script  

### Safeguards

- Tenant-safe scoping  
- No AI dependency for deterministic search  
- AI failures do not break search page  
- Adaptive similarity floor  
- Local threshold tuned to `0.40`  
- Production threshold to be calibrated later  

### UI

- “Broaden with AI” toggle  
- Separate AI results section  
- Preserves deterministic results  
- Does not hallucinate or generate content  

**Status: Complete**

---

## Phase 9C – AI Answer Mode

Not implemented.

### Will include

- Query interpretation  
- Grounded reasoning  
- Citation enforcement  
- Confidence scoring  
- Strict retrieval-only generation  

**Status: Deferred to next phase**

---

## Architectural State

Universal Search now operates in two layers:

- **Layer 1:** Deterministic PostgreSQL FTS  
- **Layer 2:** Optional Semantic Retrieval via pgvector  

No generative answering layer exists yet.

System is stable locally with small dataset.

---

## Production Notes

Before production rollout:

- Tune similarity threshold  
- Benchmark IVFFLAT index recall  
- Confirm embedding dimension consistency  
- Confirm background indexing strategy  

---

## Phase 9 Status

- Phase 9A – Complete  
- Phase 9B – Complete  
- Phase 9C – Pending  

Retrieval layer is considered deliverable and stable.
