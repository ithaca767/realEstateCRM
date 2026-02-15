# Ulysses CRM – Phase 9: AI Universal Search

## Date
2026-02-14

## Status
Planning and Design

## Phase Goal

A user can type natural language like:

- “client from last year looking for a 2 bedroom apartment and decided to wait”
- “who was the attorney who created a commercial seller’s contract for a restaurant”

…and Ulysses returns:

1) Ranked, linkable results (contacts, engagements, tasks, transactions, professionals)  
2) An AI Answer that is:
- correct (grounded, no guessing)
- scoped to current_user.id
- includes citations that link to specific records in Ulysses

## Operating Principles for Correctness

### Grounded answering only
AI is not allowed to “invent” names. It can only answer using retrieved records.

### Citations are mandatory
Every answer must include clickable “Sources” that deep-link to:
- /contacts/<id>#engagements
- /transactions/<id>
- /professionals/<id>
- etc.

### Retrieval beats generation
If retrieval is weak, the answer layer will be weak. So the design starts with retrieval.

## Phase 9 Deliverables

### 9.1 Global Search UI
- Navbar search box (always visible)
- Search page with:
  - query input
  - filters (type, date range, status)
  - results list with snippets + badges
  - “Answer with AI” toggle/button

### 9.2 Deterministic retrieval (Phase 9A)
Postgres full-text search (FTS) across core entities:
- contacts: name, notes, tags
- engagements: subject/title, notes, transcript, summary fields
- transactions: address, notes, metadata
- tasks: title, notes
- professionals: name, company, category, notes

Output includes:
- rank score
- snippet/highlight
- record type + deep link

This gives stable and fast “classic search.”

### 9.3 Semantic retrieval (Phase 9B)
Embeddings index of the same entities so natural language works.

Storage:
- one row per record, per user, containing:
  - combined “search_text”
  - embedding vector
  - updated_at

Query pipeline:
- run FTS
- run embeddings similarity
- merge and re-rank
- dedupe by (object_type, object_id)

### 9.4 AI Answer Mode (Phase 9C)
When user clicks “Answer with AI”:
1) interpret the question into a search plan
2) retrieve top K results with both methods
3) answer only using those results
4) return:
- a short answer
- citations with deep links
- confidence indicator (“High / Medium / Low”) based on evidence strength

## Search Text Composition

### Contact
- full name
- tags
- notes
- key preferences if stored (buyer/seller profile fields)

### Engagement
- subject/title
- notes
- transcript (if you store it)
- AI summary fields (these are gold)
- who it’s associated with (contact name, transaction address)

### Transaction
- address + town
- type, status
- notes
- parties (contact names)
- linked professionals (attorney name)

### Professional
- name
- category
- company
- notes
- “works on” metadata if you track it

### Task
- title
- notes
- linked contact + transaction

## Example Query Handling

### Example 1
“client from last year looking for a 2 bedroom apartment and decided to wait”

What we want retrieved:
- engagements mentioning “2 bedroom”, “apartment”, “wait”, “holding off”, “pause”
- plus contact + transaction context

AI answer output:
- “That appears to be Joseph Lopiccolo. In an engagement dated May 2025, you noted he wanted a 2BR apartment and decided to pause until later.”
- Sources:
  - Engagement link
  - Contact link

### Example 2
“who was the attorney who created a commercial seller’s contract for a restaurant”

What we want retrieved:
- engagement(s) mentioning “commercial seller contract” “restaurant” “attorney”
- professional record that matches attorney category
- transaction record if present

AI answer output:
- “The attorney was [Name], associated with Transaction [Address] and referenced in Engagement [date/title].”
- Sources:
  - Professional link
  - Engagement link
  - Transaction link

If there is no professional record but the name exists in an engagement note, the answer still works, but it will cite the engagement and suggest “Create Professional?” as a quick action.

## Engineering Plan

### Phase 9A (FTS only) schema changes
- Add tsvector generated columns or materialized search columns per table, or create a unified search view.
- Add GIN indexes for search vectors.

### Phase 9B (embeddings) schema changes
Add a single table:

- search_index
  - id
  - user_id
  - object_type
  - object_id
  - search_text
  - embedding (pgvector)
  - updated_at

Optional later:
- chunk table for long transcripts

### Phase 9C (AI answer) service
- services/ai_search.py
  - interpret_query(query) -> plan
  - retrieve(plan) -> results
  - answer(query, results) -> answer + citations

All calls:
- user-initiated
- tenant-scoped
- rate limited

## UI Design Rules

Each result row shows:
- Primary label: contact name / transaction address / professional name / engagement subject
- Secondary: date + type badges
- Snippet: highlighted excerpt
- Actions: open in new tab, quick-pin, copy link

AI Answer panel shows:
- answer text
- citations list as clickable chips
- “View all results” below

## Canon Safeguards
- No auto-writeback
- No invisible indexing of private data beyond what user already stores
- Embeddings computed only from user’s own rows
- Soft limits (per user per day) to control costs
- Always include sources

## Implementation Sequence
- Phase 9A: Global search page + FTS across engagements and contacts
- Expand FTS to transactions, professionals, tasks
- Phase 9B: Introduce search_index table and embeddings
- Phase 9C: Add AI Answer Mode grounded with citations
